"""
Shared rate limiter instance.

Kept in its own module so routers can decorate endpoints without importing from
``main`` (which imports the routers -- a circular import).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory storage: limits are per replica. uvicorn takes the client IP from
# X-Forwarded-For when the request comes from an address in
# FORWARDED_ALLOW_IPS (the proxy), and get_remote_address reads that IP.
limiter = Limiter(key_func=get_remote_address)
