"""Password hashing utilities — no external dependencies required."""

import hashlib
import secrets


def hash_pw(password: str) -> str:
    """PBKDF2-SHA256 with a random 32-char hex salt.  Format: <salt>$<hex_dk>"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"{salt}${dk.hex()}"


def verify_pw(password: str, stored: str) -> bool:
    """Constant-time check of a plaintext password against a stored hash."""
    try:
        salt, hashed = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
        return secrets.compare_digest(dk.hex(), hashed)
    except Exception:
        return False
