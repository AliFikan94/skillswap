"""Password hashing (scrypt) and opaque session tokens. Standard library only."""
import hashlib
import hmac
import os
import secrets
import time

TOKEN_TTL = 60 * 60 * 24 * 30


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str | None) -> bool:
    # Always burn a hash so unknown emails take as long as wrong passwords.
    salt_hex, _, digest_hex = (stored or "00$00").partition("$")
    try:
        salt, want = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
    except ValueError:
        return False
    got = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return stored is not None and hmac.compare_digest(got, want)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO auth_tokens VALUES (?,?,?)", (_digest(token), user_id, time.time() + TOKEN_TTL))
    conn.commit()
    return token


def user_for_token(conn, token: str | None):
    if not token:
        return None
    row = conn.execute("SELECT user_id, expires_at FROM auth_tokens WHERE token_hash=?", (_digest(token),)).fetchone()
    if not row or row["expires_at"] < time.time():
        return None
    return row["user_id"]


def revoke_token(conn, token: str | None):
    if token:
        conn.execute("DELETE FROM auth_tokens WHERE token_hash=?", (_digest(token),))
        conn.commit()
