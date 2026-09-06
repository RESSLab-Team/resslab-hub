"""
Sending the sign-in mail.

Without ``SMTP_HOST`` the mail is written to the log instead of being sent.
That is how local development and the tests work: the code is read from
``.wt-logs/backend.log`` (or captured by a fixture) and typed into the form,
so the whole flow can be exercised with no mail server anywhere.
"""

import logging
from email.message import EmailMessage

import aiosmtplib

from resslab_hub.config import settings

logger = logging.getLogger(__name__)


def configured() -> bool:
    """True when a real SMTP server is set up."""
    return bool(settings.smtp_host)


def build_message(email: str, code: str, link: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = str(settings.smtp_from)
    message["To"] = email
    message["Subject"] = f"{code} is your RESSLab Hub sign-in code"
    message.set_content(
        "Hello,\n\n"
        f"Your sign-in code for RESSLab Hub is: {code}\n\n"
        "Type it in the tab where you asked for it, or open this link on this "
        "device:\n\n"
        f"{link}\n\n"
        f"The code and the link both stop working in "
        f"{settings.login_code_ttl_minutes} minutes, and each of them can only "
        "be used once.\n\n"
        "If you did not ask to sign in, you can ignore this mail.\n"
    )
    return message


async def send_login_mail(email: str, code: str, link: str) -> None:
    """Mail the code and the link, or log them when SMTP is not configured."""
    if not configured():
        # One line, easy to grep for in the dev server log.
        logger.warning("Sign-in mail not sent (no SMTP_HOST).")
        logger.warning("Sign-in code for %s: %s", email, code)
        logger.warning("Sign-in link for %s: %s", email, link)
        return
    message = build_message(email, code, link)
    await aiosmtplib.send(
        message,
        hostname=str(settings.smtp_host),
        port=int(settings.smtp_port),
        username=str(settings.smtp_user) if settings.smtp_user else None,
        password=str(settings.smtp_password) if settings.smtp_password else None,
        start_tls=bool(settings.smtp_starttls),
    )
