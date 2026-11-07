import re
from enum import Enum
from urllib.parse import quote


class MediaType(Enum):
    """
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types
    """

    CSV = "text/csv"


class HttpHeader(Enum):
    """
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers
    """

    CONTENT_DISPOSITION = "Content-Disposition"


def attachment(filename: str) -> str:
    """
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition

    The name can come from a query (#264 Low). A quote, a `;` or a line break
    in it must not end the value or add a header field. So `filename` gets a
    plain ASCII copy, and `filename*` the real name, percent-encoded
    (RFC 6266), which browsers prefer when they read it.
    """
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename) or "download"
    return (
        f'attachment; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )
