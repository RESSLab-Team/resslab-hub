"""
Absolute URLs the backend hands out, and the redirect targets it accepts.

Behind Traefik the ``/api`` prefix is stripped before the request reaches the
app, and the ``Host`` header is the internal service name, so neither
``request.url`` nor ``url_for`` can build a URL a browser could follow. They
are all derived from the ``public_base_url`` setting instead.
"""

from urllib.parse import urlparse

from resslab_hub.config import settings


def public_base() -> str:
    """Where the SPA is served, e.g. ``https://resslab-hub.epfl.ch``."""
    return str(settings.public_base_url).rstrip("/")


def api_base() -> str:
    """Where this API is reached from a browser, ``/api`` prefix included."""
    return public_base() + str(settings.root_path).rstrip("/")


def frontend_url(path: str) -> str:
    """Absolute URL of an SPA route."""
    return public_base() + safe_redirect(path)


def api_url(path: str) -> str:
    """Absolute URL of one of our own endpoints (an OAuth callback)."""
    return api_base() + ("" if path.startswith("/") else "/") + path


def cookie_secure() -> bool:
    """Whether session cookies carry ``Secure``.

    Derived from the public URL's scheme unless the setting overrides it: the
    deployments are https, the dev server and the test client are not (and a
    Secure cookie would simply be dropped there).
    """
    override = settings.session_cookie_secure
    if override is not None:
        return bool(override)
    return public_base().startswith("https://")


def safe_redirect(target: str, fallback: str = "/") -> str:
    """Reduce a caller-supplied ``redirect_to`` to a path on our own site.

    Anything absolute, protocol-relative or otherwise off-site becomes the
    fallback, so a sign-in link can never bounce a browser to another host.
    """
    if not target or not target.startswith("/") or target.startswith("//"):
        return fallback
    # A backslash is a path separator to some browsers: "/\evil.com" would
    # navigate off-site. urlparse also rejects anything with a scheme or host.
    if "\\" in target:
        return fallback
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return fallback
    return target
