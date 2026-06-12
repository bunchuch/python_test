"""
Server-side session store — maps a random token to {username, role, expires_at}.
Lives in process memory; clears only when the Streamlit server restarts.
"""

import secrets
import time

_store: dict[str, dict] = {}
_TTL = 8 * 3600  # 8 hours


def create_session(username: str, role: str) -> str:
    token = secrets.token_urlsafe(32)
    _store[token] = {
        "username": username,
        "role":     role,
        "expires_at": time.time() + _TTL,
    }
    _purge()
    return token


def validate_session(token: str) -> dict | None:
    entry = _store.get(token)
    if not entry:
        return None
    if time.time() > entry["expires_at"]:
        _store.pop(token, None)
        return None
    return entry


def delete_session(token: str) -> None:
    _store.pop(token, None)


def _purge() -> None:
    now = time.time()
    for t in [k for k, v in _store.items() if now > v["expires_at"]]:
        del _store[t]
