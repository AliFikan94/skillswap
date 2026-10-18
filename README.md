# SkillSwap

Peer-to-peer skill bartering. Users list what they can teach and what they want to learn; the app finds:

- **Direct swaps** – A teaches what B wants and B teaches what A wants.
- **Loops** – multi-way cycles (A→B→C→A) found by DFS over the skill graph (`app/matching.py`, up to `max_loop` people).
- **Time-credits** – fallback when no swap exists: learners pay hours (everyone starts with 2) to any teacher.

Sessions can be scheduled, completed (moves credits unless it is a swap) and reviewed.

## Run

    pip install -r requirements.txt
    uvicorn app.main:app --reload     # UI at http://localhost:8000, API docs at /docs
    pytest

Set `SKILLSWAP_DB` to change the SQLite file path.

## API

| Endpoint | Purpose |
|---|---|
| `POST /users`, `GET /users[/{id}]` | profiles with offers/wants, credits, rating |
| `GET /users/{id}/matches` | direct swaps and loops |
| `GET /users/{id}/credit-options` | teachers payable in credits |
| `POST /sessions`, `/sessions/{id}/complete`, `/sessions/{id}/review` | scheduling, credit transfer, reviews |
