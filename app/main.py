from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, db
from .matching import Profile, match_for, norm

app = FastAPI(title="SkillSwap")
conn = db.connect()
STATIC = Path(__file__).parent.parent / "static"


class UserIn(BaseModel):
    name: str = Field(min_length=1)
    bio: str = ""
    offers: list[str] = []
    wants: list[str] = []


class SessionIn(BaseModel):
    teacher_id: int
    learner_id: int
    skill: str
    hours: float = Field(gt=0, le=8)
    scheduled_for: str | None = None
    swap: bool = False  # True = reciprocal swap, no credits move


class ReviewIn(BaseModel):
    reviewer_id: int
    rating: int = Field(ge=1, le=5)
    comment: str = ""


def _skills(uid: int, kind: str) -> list[str]:
    rows = conn.execute("SELECT skill FROM skills WHERE user_id=? AND kind=? ORDER BY skill", (uid, kind))
    return [r["skill"] for r in rows]


def _user(uid: int) -> dict:
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        raise HTTPException(404, "user not found")
    rating = conn.execute(
        "SELECT AVG(r.rating) a, COUNT(*) n FROM reviews r JOIN sessions s ON s.id=r.session_id "
        "WHERE s.teacher_id=? AND r.reviewer_id=s.learner_id", (uid,)).fetchone()
    return {**dict(row), "offers": _skills(uid, "offer"), "wants": _skills(uid, "want"),
            "rating": rating["a"], "reviews": rating["n"]}


def _profiles() -> list[Profile]:
    out = []
    for r in conn.execute("SELECT id, name FROM users"):
        out.append(Profile(r["id"], r["name"], set(_skills(r["id"], "offer")), set(_skills(r["id"], "want"))))
    return out


@app.post("/users", status_code=201)
def create_user(u: UserIn):
    cur = conn.execute("INSERT INTO users (name, bio) VALUES (?, ?)", (u.name.strip(), u.bio))
    for kind, items in (("offer", u.offers), ("want", u.wants)):
        for s in set(ai.canonicalize(items)):
            conn.execute("INSERT OR IGNORE INTO skills VALUES (?,?,?)", (cur.lastrowid, s, kind))
    conn.commit()
    return _user(cur.lastrowid)


@app.get("/users")
def list_users():
    return [_user(r["id"]) for r in conn.execute("SELECT id FROM users ORDER BY id")]


@app.get("/users/{uid}")
def get_user(uid: int):
    return _user(uid)


@app.get("/users/{uid}/matches")
def matches(uid: int, max_loop: int = 4):
    _user(uid)
    profiles = _profiles()
    me = next(p for p in profiles if p.id == uid)
    return match_for(me, profiles, max(2, min(max_loop, 6)))


@app.get("/users/{uid}/credit-options")
def credit_options(uid: int):
    """Fallback when no swap exists: people who teach something I want, payable in credits."""
    me = _user(uid)
    out = []
    for p in _profiles():
        if p.id != uid and (p.offers & set(me["wants"])):
            out.append({"teacher_id": p.id, "name": p.name, "skills": sorted(p.offers & set(me["wants"]))})
    return {"balance": me["credits"], "teachers": out}


@app.get("/swap-plan")
def swap_plan(teacher_id: int, learner_id: int, skill: str):
    return ai.swap_plan(_user(teacher_id)["name"], _user(learner_id)["name"], norm(skill))


@app.post("/sessions", status_code=201)
def create_session(s: SessionIn):
    if s.teacher_id == s.learner_id:
        raise HTTPException(400, "teacher and learner must differ")
    teacher, learner = _user(s.teacher_id), _user(s.learner_id)
    skill = norm(s.skill)
    if skill not in teacher["offers"]:
        raise HTTPException(400, "teacher does not offer that skill")
    if not s.swap and learner["credits"] < s.hours:
        raise HTTPException(402, "insufficient credits")
    cur = conn.execute(
        "INSERT INTO sessions (teacher_id, learner_id, skill, hours, scheduled_for, swap) VALUES (?,?,?,?,?,?)",
        (s.teacher_id, s.learner_id, skill, s.hours, s.scheduled_for, int(s.swap)))
    conn.commit()
    return dict(conn.execute("SELECT * FROM sessions WHERE id=?", (cur.lastrowid,)).fetchone())


@app.post("/sessions/{sid}/complete")
def complete_session(sid: int):
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "session not found")
    if row["status"] != "scheduled":
        raise HTTPException(409, f"session already {row['status']}")
    if not row["swap"]:
        bal = conn.execute("SELECT credits FROM users WHERE id=?", (row["learner_id"],)).fetchone()["credits"]
        if bal < row["hours"]:
            raise HTTPException(402, "insufficient credits")
        conn.execute("UPDATE users SET credits=credits-? WHERE id=?", (row["hours"], row["learner_id"]))
        conn.execute("UPDATE users SET credits=credits+? WHERE id=?", (row["hours"], row["teacher_id"]))
    conn.execute("UPDATE sessions SET status='completed' WHERE id=?", (sid,))
    conn.commit()
    return dict(conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone())


@app.post("/sessions/{sid}/review", status_code=201)
def review(sid: int, r: ReviewIn):
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "session not found")
    if row["status"] != "completed":
        raise HTTPException(409, "session not completed")
    if r.reviewer_id not in (row["teacher_id"], row["learner_id"]):
        raise HTTPException(403, "not a participant")
    try:
        conn.execute("INSERT INTO reviews VALUES (?,?,?,?)", (sid, r.reviewer_id, r.rating, r.comment))
    except Exception:
        raise HTTPException(409, "already reviewed")
    conn.commit()
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
