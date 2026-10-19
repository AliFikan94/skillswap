import itertools
import os
import tempfile

os.environ["SKILLSWAP_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.matching import Profile, match_for  # noqa: E402

_n = itertools.count()


def user(name, offers=(), wants=(), password="password123"):
    """Sign up a new user and return a client holding their session cookie."""
    c = TestClient(app)
    r = c.post("/auth/signup", json={"name": name, "email": f"{name.lower()}{next(_n)}@x.test",
                                      "password": password, "offers": list(offers), "wants": list(wants)})
    assert r.status_code == 201, r.text
    c.me = r.json()
    return c


# ---- matching engine ------------------------------------------------------

def test_direct_matching():
    a = Profile(1, "A", {"design"}, {"python"})
    b = Profile(2, "B", {"python"}, {"design"})
    c = Profile(3, "C", {"spanish"}, {"design"})
    m = match_for(a, [a, b, c])
    assert len(m["direct"]) == 1
    assert {s["teacher"] for s in m["direct"][0]["steps"]} == {"A", "B"}
    assert m["loops"] == []


def test_three_way_loop():
    a = Profile(1, "A", {"design"}, {"python"})
    b = Profile(2, "B", {"python"}, {"spanish"})
    c = Profile(3, "C", {"spanish"}, {"design"})
    m = match_for(a, [a, b, c])
    assert m["direct"] == []
    assert len(m["loops"]) == 1 and m["loops"][0]["size"] == 3


# ---- accounts ---------------------------------------------------------------

def test_signup_login_logout_flow():
    c = user("Zed", ["Guitar"], ["Spanish"])
    assert c.me["offers"] == ["guitar"] and c.me["credits"] == 2
    assert "password_hash" not in c.me
    assert c.get("/me").json()["email"] == c.me["email"]
    c.post("/auth/logout")
    assert c.get("/me").status_code == 401
    assert c.post("/auth/login", json={"email": c.me["email"].upper(), "password": "password123"}).status_code == 200
    assert c.get("/me").status_code == 200


def test_signup_validation_and_bad_login():
    c = TestClient(app)
    base = {"name": "Q", "email": "q@x.test", "password": "password123"}
    assert c.post("/auth/signup", json={**base, "password": "short"}).status_code == 422
    assert c.post("/auth/signup", json={**base, "email": "not-an-email"}).status_code == 422
    assert c.post("/auth/signup", json=base).status_code == 201
    assert c.post("/auth/signup", json=base).status_code == 409
    assert c.post("/auth/login", json={"email": "q@x.test", "password": "wrong-password"}).status_code == 401
    assert c.post("/auth/login", json={"email": "nobody@x.test", "password": "password123"}).status_code == 401


def test_endpoints_require_auth_and_hide_private_fields():
    anon = TestClient(app)
    for path in ("/me", "/users", "/me/matches", "/me/sessions", "/me/credit-options"):
        assert anon.get(path).status_code == 401, path
    a, b = user("Pa"), user("Pb")
    other = a.get(f"/users/{b.me['id']}").json()
    assert "email" not in other and "credits" not in other


def test_update_profile():
    c = user("Prof", ["a"], [])
    r = c.patch("/me", json={"bio": "hello", "offers": ["Chess", "chess "], "wants": ["yoga"]}).json()
    assert r["bio"] == "hello" and r["offers"] == ["chess"] and r["wants"] == ["yoga"]


def test_matches_for_signed_in_user():
    a = user("Ma", ["design"], ["python"])
    user("Mb", ["python"], ["design"])
    assert len(a.get("/me/matches").json()["direct"]) == 1


# ---- sessions, credits, reviews ---------------------------------------------

def test_credit_flow_and_review():
    t, l = user("Teach", ["Guitar"]), user("Learn", [], ["guitar"])
    s = l.post("/sessions", json={"teacher_id": t.me["id"], "skill": "GUITAR", "hours": 1.5}).json()
    assert t.post(f"/sessions/{s['id']}/complete").status_code == 403  # learner confirms paid sessions
    assert l.post(f"/sessions/{s['id']}/complete").status_code == 200
    assert l.get("/me").json()["credits"] == 0.5
    assert t.get("/me").json()["credits"] == 3.5
    assert l.post(f"/sessions/{s['id']}/complete").status_code == 409
    assert l.post(f"/sessions/{s['id']}/review", json={"rating": 5}).status_code == 201
    assert l.post(f"/sessions/{s['id']}/review", json={"rating": 5}).status_code == 409
    assert t.get(f"/users/{t.me['id']}").json()["rating"] == 5


def test_booking_rules():
    t, l = user("T2", ["yoga"]), user("L2", [], ["yoga"])
    base = {"teacher_id": t.me["id"], "skill": "yoga"}
    assert l.post("/sessions", json={**base, "hours": 3}).status_code == 402
    assert l.post("/sessions", json={**base, "skill": "chess", "hours": 1}).status_code == 400
    assert l.post("/sessions", json={**base, "hours": 3, "swap": True}).status_code == 201
    assert t.post("/sessions", json={"teacher_id": t.me["id"], "skill": "yoga", "hours": 1}).status_code == 400


def test_outsiders_cannot_touch_sessions():
    t, l, x = user("T3", ["chess"]), user("L3", [], ["chess"]), user("X3")
    s = l.post("/sessions", json={"teacher_id": t.me["id"], "skill": "chess", "hours": 1}).json()
    assert x.post(f"/sessions/{s['id']}/complete").status_code == 403
    assert x.post(f"/sessions/{s['id']}/review", json={"rating": 1}).status_code == 403
    assert x.get("/swap-plan", params={"teacher_id": t.me["id"], "learner_id": l.me["id"], "skill": "chess"}).status_code == 403


def test_sessions_listing():
    t, l = user("ST", ["chess"]), user("SL", [], ["chess"])
    s = l.post("/sessions", json={"teacher_id": t.me["id"], "skill": "chess", "hours": 1}).json()
    rows = l.get("/me/sessions").json()
    assert rows[0]["id"] == s["id"] and rows[0]["teacher"] == "ST" and rows[0]["reviewed"] == 0
    l.post(f"/sessions/{s['id']}/complete")
    l.post(f"/sessions/{s['id']}/review", json={"rating": 4})
    assert l.get("/me/sessions").json()[0]["reviewed"] == 1


# ---- optional AI layer --------------------------------------------------------

def test_ai_fallback_and_model(monkeypatch):
    from app import ai
    t, l = user("PT", ["ski"]), user("PL", [], ["ski"])
    plan = l.get("/swap-plan", params={"teacher_id": t.me["id"], "learner_id": l.me["id"], "skill": "ski"}).json()
    assert plan["source"] == "template" and "PT" in plan["plan"]

    monkeypatch.setattr(ai, "_generate", lambda prompt, want_json=False: '{"skills": ["react"]}' if want_json else "Plan!")
    assert ai.canonicalize(["I do React stuff"]) == ["react"]
    assert ai.swap_plan("A", "B", "x") == {"plan": "Plan!", "source": "model"}
    monkeypatch.setattr(ai, "_generate", lambda prompt, want_json=False: "not json")
    assert ai.canonicalize(["Foo Bar"]) == ["foo bar"]
