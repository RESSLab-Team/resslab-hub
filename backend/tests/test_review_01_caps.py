"""
Review 01, 01-3: a stranger can see that an address reached its mail cap.

The answer body is the same, but a capped start sets no ``resslab_login``
cookie. So the next verify says ``invalid_or_expired`` where a real start
gives ``invalid_code``. See docs/archive/review/findings/01-sign-in.md.
"""

import pytest

from resslab_hub.auth import email_login
from resslab_hub.utils.rate_limit import limiter


@pytest.fixture(autouse=True)
def _no_rate_limits(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)


@pytest.fixture(autouse=True)
def _no_mail(monkeypatch):
    async def _send(*args):
        return None

    monkeypatch.setattr(email_login.mailer, "send_login_mail", _send)


async def _start(client):
    response = await client.post(
        "/auth/email/start", json={"email": "ada@example.edu", "redirect_to": "/"}
    )
    assert response.json() == {"sent": True}
    return response


@pytest.mark.xfail(strict=True, reason="review 01: 01-3")
async def test_a_capped_start_looks_like_a_real_one(client):
    for _ in range(email_login.MAX_MAILS_PER_HOUR):
        assert "resslab_login" in (await _start(client)).cookies

    client.cookies.clear()
    capped = await _start(client)

    assert "resslab_login" in capped.cookies
