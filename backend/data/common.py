import logging
from os import path
from typing import List

CSV_READ_MODE = "rt"
UTF8_ENCODING = "utf-8"
ASCII_ENCODING = "ascii"


def get_abs_path(file_path: str) -> str:
    """
    Get absolute path
    """
    abs_path = path.abspath(file_path)
    logging.debug(f"processing {abs_path}")
    return abs_path


def is_empty_row(row: List[str]) -> bool:
    return all([len(value) == 0 for value in row])
