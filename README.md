# SkillSwap

Peer-to-peer skill bartering. Users list what they can teach and what they want to learn; the app finds:

- **Direct swaps** – A teaches what B wants and B teaches what A wants.
- **Loops** – multi-way cycles (A→B→C→A) found by DFS over the skill graph (`app/matching.py`, up to `max_loop` people).
- **Time-credits** – fallback when no swap exists: learners pay hours (everyone starts with 2) to any teacher.

Sessions can be scheduled, completed (moves credits unless it is a swap) and reviewed.

## Open-source AI

Optional and fully local: set `SKILLSWAP_OLLAMA_URL=http://localhost:11434` (and `SKILLSWAP_MODEL`, default `gemma3`) to run an open-weight model through [Ollama](https://ollama.com). It (1) canonicalizes free-text skills ("I do React stuff" -> "react") so matching works, and (2) writes a starter plan for each swap's first session. Without it the app falls back to plain normalization and a template, so it works offline with no keys and no cost; profile data never leaves the machine.

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
