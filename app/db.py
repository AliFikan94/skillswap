import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, bio TEXT DEFAULT '',
  credits REAL NOT NULL DEFAULT 2
);
CREATE TABLE IF NOT EXISTS auth_tokens (
  token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
  expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS skills (
  user_id INTEGER NOT NULL REFERENCES users(id),
  skill TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('offer','want')),
  PRIMARY KEY (user_id, skill, kind)
);
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, learner_id INTEGER NOT NULL,
  skill TEXT NOT NULL, hours REAL NOT NULL, status TEXT NOT NULL DEFAULT 'scheduled',
  scheduled_for TEXT, swap INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS reviews (
  session_id INTEGER NOT NULL REFERENCES sessions(id), reviewer_id INTEGER NOT NULL,
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5), comment TEXT DEFAULT '',
  PRIMARY KEY (session_id, reviewer_id)
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(os.environ.get("SKILLSWAP_DB", "skillswap.db"), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    # Databases created before accounts existed lack these columns.
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
    for col in ("email", "password_hash"):
        if col not in cols:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email ON users(email)")
    conn.commit()
    return conn
