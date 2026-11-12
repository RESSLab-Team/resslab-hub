"""
Review 01: two requests on the same sign-in code at the same time.

``verify_code`` reads the challenge with a plain SELECT, checks ``attempts``
and ``consumed_at`` in Python, then writes. A barrier after the read makes
the requests all read the row before any of them writes, so the order is
fixed and the tests cannot flake.

- 01-2: one code gives a session to each parallel request.
- 01-N1 (not proven in the browser): parallel wrong codes are all compared,
  so more than five codes are tried on one challenge.

See docs/review/findings/01-sign-in.md.
"""

import asyncio

import pytest
from sqlalchemy import select

from resslab_hub.auth import email_login
from resslab_hub.models.database.auth import LoginChallenge, Session
from resslab_hub.utils.rate_limit import limiter


@pytest.fixture(autouse=True)
def _no_rate_limits(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)


@pytest.fixture
def mailbox(monkeypatch):
    sent = []

    async def _send(email, code, link):
        sent.append({"email": email, "code": code, "link": link})

    monkeypatch.setattr(email_login.mailer, "send_login_mail", _send)
    return sent


def _hold_after_read(monkeypatch, parties):
    """Make ``parties`` requests wait for each other right after the read."""
    barrier = asyncio.Barrier(parties)
    real_load = email_login._load

    async def _load(*args, **kwargs):
        challenge = await real_load(*args, **kwargs)
        await asyncio.wait_for(barrier.wait(), timeout=10)
        return challenge

    monkeypatch.setattr(email_login, "_load", _load)


async def _start(client, mailbox):
    response = await client.post(
        "/auth/email/start", json={"email": "ada@example.edu", "redirect_to": "/"}
    )
    assert response.status_code == 200
    return mailbox[-1]["code"]


def _verify(client, code):
    return client.post("/auth/email/verify", json={"code": code})


@pytest.mark.xfail(strict=True, reason="review 01: 01-2")
async def test_one_code_gives_one_session(client, mailbox, monkeypatch, db_session):
    code = await _start(client, mailbox)
    _hold_after_read(monkeypatch, 2)

    first, second = await asyncio.gather(_verify(client, code), _verify(client, code))

    statuses = sorted([first.status_code, second.status_code])
    sessions = db_session.execute(select(Session)).scalars().all()
    assert statuses == [200, 400]
    assert len(sessions) == 1


@pytest.mark.xfail(strict=True, reason="review 01: 01-N1, not proven")
async def test_parallel_wrong_codes_stop_at_five(
    client, mailbox, monkeypatch, db_session
):
    code = await _start(client, mailbox)
    wrong = [str(100000 + i) for i in range(10) if str(100000 + i) != code][:8]
    _hold_after_read(monkeypatch, len(wrong))

    await asyncio.gather(*(_verify(client, guess) for guess in wrong))

    # ``attempts`` counts each code that was compared to the hash.
    attempts = db_session.execute(select(LoginChallenge.attempts)).scalar_one()
    assert attempts <= email_login.MAX_ATTEMPTS
