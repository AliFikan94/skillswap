import os
import re
import sqlite3
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, auth, db, semantic
from .matching import Profile, gives, match_for, norm

app = FastAPI(title="SkillSwap")
conn = db.connect()
STATIC = Path(__file__).parent.parent / "static"
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COOKIE = "session"


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(max_length=200)
    password: str = Field(min_length=8, max_length=200)
    bio: str = Field(default="", max_length=300)
    offers: list[str] = []
    wants: list[str] = []


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=300)
    offers: list[str] | None = None
    wants: list[str] | None = None


class SessionIn(BaseModel):
    teacher_id: int
    skill: str
    hours: float = Field(gt=0, le=8)
    scheduled_for: str | None = None
    swap: bool = False  # True = reciprocal swap, no credits move


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=500)


def _skills(uid: int, kind: str) -> list[str]:
    rows = conn.execute("SELECT skill FROM skills WHERE user_id=? AND kind=? ORDER BY skill", (uid, kind))
    return [r["skill"] for r in rows]


def _user(uid: int, private: bool = False) -> dict:
    row = conn.execute("SELECT id, name, bio, credits, email FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        raise HTTPException(404, "user not found")
    rating = conn.execute(
        "SELECT AVG(r.rating) a, COUNT(*) n FROM reviews r JOIN sessions s ON s.id=r.session_id "
        "WHERE s.teacher_id=? AND r.reviewer_id=s.learner_id", (uid,)).fetchone()
    out = {"id": row["id"], "name": row["name"], "bio": row["bio"],
           "offers": _skills(uid, "offer"), "wants": _skills(uid, "want"),
           "rating": rating["a"], "reviews": rating["n"]}
    if private:  # only the account owner sees balance and email
        out.update(credits=row["credits"], email=row["email"])
    return out


def current_user(request: Request) -> int:
    uid = auth.user_for_token(conn, request.cookies.get(COOKIE))
    if uid is None:
        raise HTTPException(401, "not signed in")
    return uid


def _set_skills(uid: int, kind: str, items: list[str]):
    conn.execute("DELETE FROM skills WHERE user_id=? AND kind=?", (uid, kind))
    for s in set(ai.canonicalize(items)):
        conn.execute("INSERT OR IGNORE INTO skills VALUES (?,?,?)", (uid, s, kind))


def create_account(u: SignupIn) -> int:
    email = u.email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(422, "enter a valid email address")
    try:
        cur = conn.execute("INSERT INTO users (name, bio, email, password_hash) VALUES (?,?,?,?)",
                           (u.name.strip(), u.bio, email, auth.hash_password(u.password)))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "an account with that email already exists")
    _set_skills(cur.lastrowid, "offer", u.offers)
    _set_skills(cur.lastrowid, "want", u.wants)
    conn.commit()
    return cur.lastrowid


def _login_response(uid: int, response: Response) -> dict:
    response.set_cookie(COOKIE, auth.issue_token(conn, uid), max_age=auth.TOKEN_TTL,
                        httponly=True, samesite="lax",
                        secure=os.environ.get("SKILLSWAP_COOKIE_SECURE") == "1")
    return _user(uid, private=True)


def _profiles() -> list[Profile]:
    return [Profile(r["id"], r["name"], set(_skills(r["id"], "offer")), set(_skills(r["id"], "want")))
            for r in conn.execute("SELECT id, name FROM users")]


# ---- auth ---------------------------------------------------------------

@app.post("/auth/signup", status_code=201)
def signup(u: SignupIn, response: Response):
    return _login_response(create_account(u), response)


@app.post("/auth/login")
def login(body: LoginIn, response: Response):
    row = conn.execute("SELECT id, password_hash FROM users WHERE email=?", (body.email.strip().lower(),)).fetchone()
    if not auth.verify_password(body.password, row["password_hash"] if row else None):
        raise HTTPException(401, "incorrect email or password")
    return _login_response(row["id"], response)


@app.post("/auth/logout")
def logout(request: Request, response: Response):
    auth.revoke_token(conn, request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/me")
def me(uid: int = Depends(current_user)):
    return _user(uid, private=True)


@app.patch("/me")
def update_me(p: ProfileIn, uid: int = Depends(current_user)):
    if p.name is not None:
        conn.execute("UPDATE users SET name=? WHERE id=?", (p.name.strip(), uid))
    if p.bio is not None:
        conn.execute("UPDATE users SET bio=? WHERE id=?", (p.bio, uid))
    if p.offers is not None:
        _set_skills(uid, "offer", p.offers)
    if p.wants is not None:
        _set_skills(uid, "want", p.wants)
    conn.commit()
    return _user(uid, private=True)


# ---- people & matching --------------------------------------------------

@app.get("/users")
def list_users(_: int = Depends(current_user)):
    return [_user(r["id"]) for r in conn.execute("SELECT id FROM users ORDER BY name")]


@app.get("/users/{uid}")
def get_user(uid: int, _: int = Depends(current_user)):
    return _user(uid)


def _similar(profiles: list[Profile]):
    return semantic.make_similar(conn, {s for p in profiles for s in p.offers | p.wants})


@app.get("/me/matches")
def matches(max_loop: int = 4, uid: int = Depends(current_user)):
    profiles = _profiles()
    me_ = next(p for p in profiles if p.id == uid)
    return match_for(me_, profiles, max(2, min(max_loop, 6)), _similar(profiles))


@app.get("/me/credit-options")
def credit_options(uid: int = Depends(current_user)):
    """Fallback when no swap exists: people who teach something I want, payable in credits."""
    me_ = _user(uid, private=True)
    profiles = _profiles()
    mine = next(p for p in profiles if p.id == uid)
    similar = _similar(profiles)
    out = []
    for p in profiles:
        found = gives(p, mine, similar) if p.id != uid else {}
        if found:
            out.append({"teacher_id": p.id, "name": p.name, "skills": sorted(found),
                        "for": {o: w for o, w in found.items() if o != w}})
    return {"balance": me_["credits"], "teachers": out}


# ---- sessions -----------------------------------------------------------

@app.get("/me/sessions")
def my_sessions(uid: int = Depends(current_user)):
    rows = conn.execute(
        "SELECT s.*, t.name teacher, l.name learner, "
        "(SELECT COUNT(*) FROM reviews r WHERE r.session_id=s.id AND r.reviewer_id=?) reviewed "
        "FROM sessions s JOIN users t ON t.id=s.teacher_id JOIN users l ON l.id=s.learner_id "
        "WHERE s.teacher_id=? OR s.learner_id=? ORDER BY s.id DESC", (uid, uid, uid))
    return [dict(r) for r in rows]


@app.get("/swap-plan")
def swap_plan(teacher_id: int, learner_id: int, skill: str, uid: int = Depends(current_user)):
    if uid not in (teacher_id, learner_id):
        raise HTTPException(403, "not a participant")
    return ai.swap_plan(_user(teacher_id)["name"], _user(learner_id)["name"], norm(skill))


@app.post("/sessions", status_code=201)
def create_session(s: SessionIn, uid: int = Depends(current_user)):
    """The signed-in user is always the learner and books a session with a teacher."""
    if s.teacher_id == uid:
        raise HTTPException(400, "you can't book yourself")
    teacher, learner = _user(s.teacher_id), _user(uid, private=True)
    skill = norm(s.skill)
    if skill not in teacher["offers"]:
        raise HTTPException(400, "teacher does not offer that skill")
    if not s.swap and learner["credits"] < s.hours:
        raise HTTPException(402, "insufficient credits")
    cur = conn.execute(
        "INSERT INTO sessions (teacher_id, learner_id, skill, hours, scheduled_for, swap) VALUES (?,?,?,?,?,?)",
        (s.teacher_id, uid, skill, s.hours, s.scheduled_for, int(s.swap)))
    conn.commit()
    return dict(conn.execute("SELECT * FROM sessions WHERE id=?", (cur.lastrowid,)).fetchone())


def _participant_session(sid: int, uid: int):
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "session not found")
    if uid not in (row["teacher_id"], row["learner_id"]):
        raise HTTPException(403, "not a participant")
    return row


@app.post("/sessions/{sid}/complete")
def complete_session(sid: int, uid: int = Depends(current_user)):
    row = _participant_session(sid, uid)
    if row["status"] != "scheduled":
        raise HTTPException(409, f"session already {row['status']}")
    if not row["swap"]:
        if uid != row["learner_id"]:
            raise HTTPException(403, "only the learner confirms a paid session")
        bal = conn.execute("SELECT credits FROM users WHERE id=?", (row["learner_id"],)).fetchone()["credits"]
        if bal < row["hours"]:
            raise HTTPException(402, "insufficient credits")
        conn.execute("UPDATE users SET credits=credits-? WHERE id=?", (row["hours"], row["learner_id"]))
        conn.execute("UPDATE users SET credits=credits+? WHERE id=?", (row["hours"], row["teacher_id"]))
    conn.execute("UPDATE sessions SET status='completed' WHERE id=?", (sid,))
    conn.commit()
    return dict(conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone())


@app.post("/sessions/{sid}/review", status_code=201)
def review(sid: int, r: ReviewIn, uid: int = Depends(current_user)):
    row = _participant_session(sid, uid)
    if row["status"] != "completed":
        raise HTTPException(409, "session not completed")
    try:
        conn.execute("INSERT INTO reviews VALUES (?,?,?,?)", (sid, uid, r.rating, r.comment))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "already reviewed")
    conn.commit()
    return {"ok": True}


@app.get("/healthz")
def healthz():
    conn.execute("SELECT 1")
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
