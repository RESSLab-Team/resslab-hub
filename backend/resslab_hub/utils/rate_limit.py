"""
Shared rate limiter instance.

Kept in its own module so routers can decorate endpoints without importing from
``main`` (which imports the routers -- a circular import).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory storage: limits are per replica. Traefik forwards the real client
# IP (FORWARDED_ALLOW_IPS="*"), so get_remote_address reads X-Forwarded-For.
limiter = Limiter(key_func=get_remote_address)
