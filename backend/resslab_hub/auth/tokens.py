"""
Secrets used by the sign-in flows, and how they are compared.

Nothing that is mailed or put in a cookie is ever stored: the database keeps
the sha256 of it. The values are long random tokens (or, for the mailed code,
short-lived and attempt-limited), so a plain hash is enough — a password
hashing function would only slow down our own lookups.
"""

import hmac
import secrets
from hashlib import sha256

#: Digits in the code sent by mail. Six is what people expect to retype, and
#: the five-attempt cap plus the ten-minute lifetime make guessing hopeless.
CODE_DIGITS = 6


def new_code() -> str:
    """A numeric code to type back, zero-padded so it always has 6 digits."""
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def new_token() -> str:
    """A 256-bit URL-safe token for cookies and magic links."""
    return secrets.token_urlsafe(32)


def hash_token(value: str) -> str:
    """What gets stored: hex sha256 of the token or code."""
    return sha256(value.encode("utf-8")).hexdigest()


def matches(value: str, stored_hash: str) -> bool:
    """Constant-time comparison of a presented value against a stored hash."""
    if not value or not stored_hash:
        return False
    return hmac.compare_digest(hash_token(value), stored_hash)
