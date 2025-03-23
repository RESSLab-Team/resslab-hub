import logging
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
    """
    with open(file_path, "rb") as file:
        # First check for BOM
        raw = file.read(4)  # Read enough bytes to detect BOM

        # UTF-8 BOM check (EF BB BF)
        if raw.startswith(b"\xef\xbb\xbf"):
            logging.debug(f"Detected UTF-8 with BOM in {file_path}")
            return "utf-8-sig"  # Special encoding that handles BOM

        # Rewind and use chardet for other encodings
        file.seek(0)
        detection = detect(file.read())

    encoding = (detection or {}).get("encoding")
    if not encoding:
        raise Exception("cannot detect encoding")

    logging.debug(f"Detected encoding {encoding} for {file_path}")
    return encoding
