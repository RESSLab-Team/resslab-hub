import logging
import re
from os import path
from typing import List

from chardet import detect

CSV_READ_MODE = "rt"
UTF8_ENCODING = "utf-8"


def get_abs_path(file_path: str) -> str:
    """
    Get absolute path
    """
    abs_path = path.abspath(file_path)
    logging.debug(f"processing {abs_path}")
    return abs_path


def is_empty_row(row: List[str]) -> bool:
    return all([len(value) == 0 for value in row])


def detect_encoding(raw: bytes) -> str:
    """
    Encoding of an already-read file, with special handling for UTF-8 with BOM

    Fast path: the data files are UTF-8 (with or without BOM), so attempt a
    strict full-file UTF-8 decode first -- this reads every byte via the C
    decoder and is far cheaper than running ``chardet`` over the whole file.
    Only if a byte anywhere in the file is not valid UTF-8 do we fall back to
    ``chardet`` to sniff the real (legacy) encoding.

    Takes bytes rather than a path so a caller that already needs the raw
    content (the validator checks line endings and the final newline on it)
    reads the file once.
    """
    try:
        raw.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError:
        encoding = detect(raw)["encoding"]

    if not encoding:
        raise Exception("cannot detect encoding")

    return encoding


def get_file_encoding(file_path: str) -> str:
    """
    Get file encoding, with special handling for UTF-8 with BOM
    """
    with open(file_path, "rb") as file:
        encoding = detect_encoding(file.read())
    logging.debug(f"Detected encoding {encoding} for {file_path}")
    return encoding


#: A specimen id doubles as the file name of its time-series (``<id>.csv``) and
#: as a path inside the data repository, so it has to be one safe path segment
#: on every platform a curator may clone on: it starts with a letter or digit
#: and contains no path separators, no control characters and none of the
#: characters Windows refuses in a file name. Anything else (spaces, ``+``,
#: ``#``, accented or non-Latin letters) is fine.
#:
#: Spaces stay allowed here on purpose: this pattern also guards the
#: submission and curation paths, where the only question is whether the id
#: can be a file name. The READMEs ask for no spaces as a naming convention,
#: which the validator reports as a warning (cf. ``ID_SPACE_RULE``).
SAFE_ID_PATTERN = re.compile(r'^[^\W_][^<>:"/\\|?*\x00-\x1f\x7f]*$')

#: Human-readable version of ``SAFE_ID_PATTERN`` for error messages.
SAFE_ID_RULE = (
    "it must start with a letter or digit and cannot contain "
    '/ \\ < > : " | ? * or control characters'
)

#: Every README says the parts of an id are joined with underscores and that
#: the specimen designation is kept as reported, "hyphens and dots are fine,
#: spaces are not".
ID_SPACE_RULE = "Join the parts of an id with underscores, not spaces."
