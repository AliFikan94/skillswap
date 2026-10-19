# SkillSwap

Peer-to-peer skill bartering. Users list what they can teach and what they want to learn; the app finds:

- **Direct swaps** – A teaches what B wants and B teaches what A wants.
- **Loops** – multi-way cycles (A→B→C→A) found by DFS over the skill graph (`app/matching.py`, up to `max_loop` people).
- **Time-credits** – fallback when no swap exists: learners pay hours (everyone starts with 2) to any teacher.

Sessions can be booked, completed (moves credits unless it is a swap) and reviewed.

## Accounts

Email and password sign-up with a two-step onboarding (account, then skills). Passwords are hashed with scrypt, sessions use an opaque random token stored hashed server-side in an HttpOnly cookie, and the learner is always the signed-in user, so nobody can act as someone else. Other people's emails and credit balances are never exposed.

## Pages

Landing, sign in / sign up, Discover (swaps, loops, credits), People (search and profiles), Sessions (upcoming / completed, reviews) and Profile. The UI follows macOS conventions: translucent sidebar, system fonts, dark mode, sheets and toasts; the sidebar becomes a tab bar on phones.

## Open-source AI

Optional and fully local: set `SKILLSWAP_OLLAMA_URL=http://localhost:11434` (and `SKILLSWAP_MODEL`, default `gemma3`) to run an open-weight model through [Ollama](https://ollama.com). It (1) canonicalizes free-text skills ("I do React stuff" -> "react") so matching works, and (2) writes a starter plan for each swap's first session. Without it the app falls back to plain normalization and a template, so it works offline with no keys and no cost; profile data never leaves the machine.

## Run

    pip install -r requirements.txt
    uvicorn app.main:app --reload     # UI at http://localhost:8000, API docs at /docs
    pytest

Set `SKILLSWAP_DB` to change the SQLite file path. Demo users from `python -m app.seed` sign in with `ada@demo.test` / `demo12345` (also ben, carla, dev, eli).

Upgrading from the first version? Existing databases are migrated automatically, but old profiles have no password; delete `skillswap.db` and re-seed for a clean start.

## API

Everything except `/auth/signup` and `/auth/login` requires the session cookie.

| Endpoint | Purpose |
|---|---|
| `POST /auth/signup`, `/auth/login`, `/auth/logout` | accounts |
| `GET/PATCH /me` | own profile, balance, skills |
| `GET /users`, `/users/{id}` | public profiles |
| `GET /me/matches` | direct swaps and loops |
| `GET /me/credit-options` | teachers payable in credits |
| `GET /me/sessions`, `POST /sessions`, `/sessions/{id}/complete`, `/sessions/{id}/review` | booking, credit transfer, reviews |
| `GET /swap-plan` | starter plan for a session |
