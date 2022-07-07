from os import path

CSV_READ_MODE = "rt"
CSV_ENCODING = "unicode_escape"


def get_abs_path(file_path: str) -> str:
    """
    Get absolute path
    """
    abs_path = path.abspath(file_path)
    print(f"processing {abs_path}")
    return abs_path
