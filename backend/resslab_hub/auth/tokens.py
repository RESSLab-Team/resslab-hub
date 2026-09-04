"""
Secrets used by the sign-in flows, and how they are compared.

Nothing that is mailed or put in a cookie is ever stored, only its sha256. The
values are long random tokens, or a short code that is attempt-limited and
short-lived, so a plain hash is enough.
"""

import hmac
import secrets
from hashlib import sha256

#: Digits in the mailed code. Six is what people expect to retype.
CODE_DIGITS = 6


def new_code() -> str:
    """A numeric code to type back, zero-padded to 6 digits."""
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
