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

Optional and fully local: run [Ollama](https://ollama.com) and set `SKILLSWAP_OLLAMA_URL=http://localhost:11434`. Two open-weight models do the work:

- **Semantic matching** (`app/semantic.py`): skill names are embedded with `embeddinggemma` (change with `SKILLSWAP_EMBED_MODEL`), so "ui design" matches "figma". Two skills match when cosine similarity is at least `SKILLSWAP_SIM_THRESHOLD` (default 0.75). Matches that are not exact show up as `figma ≈ ui design` in the UI. Vectors are cached in SQLite, so each skill is embedded once.
- **Text generation** (`app/ai.py`): a Gemma chat model (`SKILLSWAP_MODEL`, default `gemma3`) canonicalizes free-text skills and writes a starter plan for each swap.

Setup: `ollama pull embeddinggemma && ollama pull gemma3`.

Without a model (or if it goes down; failures trip a 30 s circuit breaker) the app falls back to exact matching and a template plan, so it works offline with no keys and no cost, and profile data never leaves the machine. The default threshold is a starting point: tune it by looking at which pairs you want matched.

## Run

    pip install -r requirements.txt
    uvicorn app.main:app --reload     # UI at http://localhost:8000, API docs at /docs
    pytest

Set `SKILLSWAP_DB` to change the SQLite file path. Demo users from `python -m app.seed` sign in with `ada@demo.test` / `demo12345` (also ben, carla, dev, eli).

Upgrading from the first version? Existing databases are migrated automatically, but old profiles have no password; delete `skillswap.db` and re-seed for a clean start.

## Deploy to Render

`render.yaml` is a Render Blueprint, so deploying is: push this branch (or merge it), then in Render choose **New → Blueprint**, connect the repo and branch, and apply. The service seeds the demo users on first boot (sign in as `ada@demo.test` / `demo12345`) and serves over HTTPS with a `Secure` session cookie.

Things to know about the free plan:
- The disk is ephemeral, so the SQLite database resets on every redeploy or restart (and the demo users are re-seeded). For persistent data, attach a Render disk and set `SKILLSWAP_DB` to a path on it, or move to Postgres.
- The service sleeps after inactivity, so the first request after a pause is slow.
- Render cannot reach Ollama on your laptop. Without `SKILLSWAP_OLLAMA_URL` the live demo uses exact skill matching and template plans; semantic matching needs an Ollama server you host (for example on a DigitalOcean GPU Droplet).
- The seeded demo accounts have a public password; do not use the demo database for real users.

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
