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


def get_file_encoding(file_path: str) -> str:
    """
    Get file encoding, with special handling for UTF-8 with BOM

    Fast path: the data files are UTF-8 (with or without BOM), so attempt a
    strict full-file UTF-8 decode first -- this reads every byte via the C
    decoder and is far cheaper than running ``chardet`` over the whole file.
    Only if a byte anywhere in the file is not valid UTF-8 do we fall back to
    ``chardet`` to sniff the real (legacy) encoding.
    """
    with open(file_path, "rb") as file:
        raw = file.read()

    try:
        raw.decode("utf-8-sig")
        logging.debug(f"Detected encoding utf-8-sig for {file_path}")
        return "utf-8-sig"
    except UnicodeDecodeError:
        encoding = detect(raw)["encoding"]

    if not encoding:
        raise Exception("cannot detect encoding")

    logging.debug(f"Detected encoding {encoding} for {file_path}")
    return encoding


#: A specimen id doubles as the file name of its time-series (``<id>.csv``) and
#: as a path inside the data repository, so it has to be one safe path segment
#: on every platform a curator may clone on: it starts with a letter or digit
#: and contains no path separators, no control characters and none of the
#: characters Windows refuses in a file name. Anything else (spaces, ``+``,
#: ``#``, accented or non-Latin letters) is fine.
SAFE_ID_PATTERN = re.compile(r'^[^\W_][^<>:"/\\|?*\x00-\x1f\x7f]*$')

#: Human-readable version of ``SAFE_ID_PATTERN`` for error messages.
SAFE_ID_RULE = (
    "it must start with a letter or digit and cannot contain "
    '/ \\ < > : " | ? * or control characters'
)
