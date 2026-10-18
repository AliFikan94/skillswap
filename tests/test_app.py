import os
import tempfile

os.environ["SKILLSWAP_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.matching import Profile, match_for  # noqa: E402

client = TestClient(app)


def mk(name, offers, wants):
    return client.post("/users", json={"name": name, "offers": offers, "wants": wants}).json()


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


def test_credit_flow_and_review():
    t = mk("Teach", ["Guitar"], [])
    l = mk("Learn", [], ["guitar"])
    s = client.post("/sessions", json={"teacher_id": t["id"], "learner_id": l["id"], "skill": "GUITAR", "hours": 1.5}).json()
    assert client.post(f"/sessions/{s['id']}/complete").status_code == 200
    assert client.get(f"/users/{l['id']}").json()["credits"] == 0.5
    assert client.get(f"/users/{t['id']}").json()["credits"] == 3.5
    assert client.post(f"/sessions/{s['id']}/complete").status_code == 409
    r = client.post(f"/sessions/{s['id']}/review", json={"reviewer_id": l["id"], "rating": 5})
    assert r.status_code == 201
    assert client.get(f"/users/{t['id']}").json()["rating"] == 5


def test_insufficient_credits_and_validation():
    t = mk("T2", ["yoga"], [])
    l = mk("L2", [], ["yoga"])
    base = {"teacher_id": t["id"], "learner_id": l["id"], "skill": "yoga"}
    assert client.post("/sessions", json={**base, "hours": 3}).status_code == 402
    assert client.post("/sessions", json={**base, "skill": "chess", "hours": 1}).status_code == 400
    assert client.post("/sessions", json={**base, "hours": 3, "swap": True}).status_code == 201
