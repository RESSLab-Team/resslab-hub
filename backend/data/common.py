from os import path

CSV_READ_MODE = "rt"
UTF8_ENCODING = "utf-8"


def get_abs_path(file_path: str) -> str:
    """
    Get absolute path
    """
    abs_path = path.abspath(file_path)
    print(f"processing {abs_path}")
    return abs_path
