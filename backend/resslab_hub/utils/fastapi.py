from enum import Enum


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
    """
    return f'attachment; filename="{filename}"'
