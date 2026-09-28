"""
Sending the sign-in mail.

Without ``SMTP_HOST`` the mail is written to the log instead of being sent.
That is how local development and the tests work: the code is read from
``.wt-logs/backend.log`` (or captured by a fixture) and typed into the form,
so the whole flow can be exercised with no mail server anywhere.

In the deployments the relay is the EPFL one, ``mail.epfl.ch:587`` with
STARTTLS and a service account. That server offers ``AUTH GSSAPI NTLM LOGIN``;
aiosmtplib knows cram-md5, plain and login, so it picks LOGIN. See
``docs/auth.md`` for the settings and the deploy runbook.

A relay that refuses or does not answer raises :class:`MailError`. The caller
undoes the challenge it had just written, so a broken relay does not eat the
hourly caps of the person trying to sign in.
"""

import logging
from email.message import EmailMessage
from email.utils import formataddr
from functools import lru_cache
from html import escape
from pathlib import Path

import aiosmtplib

from resslab_hub.config import settings

logger = logging.getLogger(__name__)

#: Per-operation SMTP timeout: the connect, then each command's answer.
#: aiosmtplib defaults to 60 s, much longer than a sign-in request should hang.
TIMEOUT_SECONDS = 15

#: Display name in the From header. The address itself is ``SMTP_FROM``.
FROM_NAME = "RESSLab Hub"

#: The two parts of the mail, designed together (docs/design/). Shipped as
#: files rather than strings because the HTML one is 8 kB of table layout.
TEMPLATE_DIR = Path(__file__).parent / "templates" / "email"


#: Images referenced by the html part, by content id. They travel with the
#: mail rather than sitting behind a URL: Gmail and Outlook strip inline SVG,
#: and a hosted file would not load from a laptop running on 127.0.0.1.
#: Two marks because the ink has to flip on a dark card.
LOGOS = {
    "rl-mark-light": "mark-light.png",
    "rl-mark-dark": "mark-dark.png",
    "rl-epfl": "epfl.png",
}


@lru_cache(maxsize=None)
def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def _image(name: str) -> bytes:
    return (TEMPLATE_DIR / name).read_bytes()


def _fill(template: str, values: dict) -> str:
    """Replace the ``{name}`` placeholders.

    Not ``str.format``: the HTML carries a CSS block full of braces.
    """
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


class MailError(Exception):
    """The relay refused the mail or did not answer. Not the caller's fault."""


def configured() -> bool:
    """True when a real SMTP server is set up."""
    return bool(settings.smtp_host)


def build_message(email: str, code: str, link: str) -> EmailMessage:
    ttl = str(settings.login_code_ttl_minutes)
    text = _fill(
        _template("signin_email.txt"),
        {"code": code, "link": link, "ttl_minutes": ttl},
    )
    # The link holds a "&" between its two query parameters, and it is written
    # both in an href and as visible text, so it needs escaping in the HTML.
    html = _fill(
        _template("signin_email.html"),
        {
            "code": escape(code),
            "link": escape(link, quote=True),
            "ttl_minutes": escape(ttl),
        },
    )

    message = EmailMessage()
    # A display name reads better in a mailbox list. aiosmtplib takes the bare
    # address out of it for the envelope, so the relay still sees just that.
    message["From"] = formataddr((FROM_NAME, str(settings.smtp_from)))
    message["To"] = email
    message["Subject"] = f"{code} is your RESSLab Hub sign-in code"
    # Text first, HTML second: that is the order multipart/alternative wants,
    # last part being the preferred one.
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    # The images hang off the html part, not off the message, so a reader
    # that only wants the text part never downloads them.
    html_part = message.get_payload()[-1]
    for content_id, file_name in LOGOS.items():
        html_part.add_related(
            _image(file_name),
            maintype="image",
            subtype="png",
            cid=f"<{content_id}>",
            filename=file_name,
            disposition="inline",
        )
    return message


async def send_login_mail(email: str, code: str, link: str) -> None:
    """Mail the code and the link, or log them when SMTP is not configured.

    Raises :class:`MailError` when the relay fails.
    """
    if not configured():
        # One line, easy to grep for in the dev server log.
        logger.warning("Sign-in mail not sent (no SMTP_HOST).")
        logger.warning("Sign-in code for %s: %s", email, code)
        logger.warning("Sign-in link for %s: %s", email, link)
        return
    message = build_message(email, code, link)
    try:
        await aiosmtplib.send(
            message,
            hostname=str(settings.smtp_host),
            port=int(settings.smtp_port),
            username=str(settings.smtp_user) if settings.smtp_user else None,
            password=str(settings.smtp_password) if settings.smtp_password else None,
            start_tls=bool(settings.smtp_starttls),
            timeout=TIMEOUT_SECONDS,
        )
    except (aiosmtplib.SMTPException, OSError) as exc:
        # The reason, never the code or the link: this line ends up in
        # kubectl logs, where a sign-in code has no business being.
        logger.error("Sign-in mail to %s failed: %s", email, exc)
        raise MailError(str(exc)) from exc
