"""Pure-unit tests for the CSV ingestion helpers (no database required)."""
from pathlib import Path

from resslab_hub.data.common import (
    get_abs_path,
    get_file_encoding,
    is_empty_row,
)


class TestIsEmptyRow:
    def test_all_blank_values_is_empty(self):
        assert is_empty_row([""]) is True
        assert is_empty_row(["", "", ""]) is True

    def test_empty_list_is_empty(self):
        assert is_empty_row([]) is True

    def test_any_non_blank_value_is_not_empty(self):
        assert is_empty_row(["", "x", ""]) is False
        assert is_empty_row(["value"]) is False


class TestGetAbsPath:
    def test_returns_absolute_path(self, tmp_path: Path):
        relative = "some/relative/file.csv"
        result = get_abs_path(relative)
        assert Path(result).is_absolute()
        assert result.endswith("some/relative/file.csv")


class TestGetFileEncoding:
    def test_plain_ascii_is_read_as_utf8_sig(self, tmp_path: Path):
        file_path = tmp_path / "ascii.csv"
        file_path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
        # ASCII is valid UTF-8, so the fast strict-decode path wins.
        assert get_file_encoding(str(file_path)) == "utf-8-sig"

    def test_utf8_with_bom_detected(self, tmp_path: Path):
        file_path = tmp_path / "bom.csv"
        file_path.write_text("name\nédgar\n", encoding="utf-8-sig")
        assert get_file_encoding(str(file_path)) == "utf-8-sig"

    def test_non_utf8_falls_back_to_chardet(self, tmp_path: Path):
        file_path = tmp_path / "latin1.csv"
        # 0xE9 ('é' in latin-1) is not valid UTF-8, forcing the chardet branch.
        file_path.write_bytes(b"name\n" + ("caf\xe9\n" * 50).encode("latin-1"))
        encoding = get_file_encoding(str(file_path))
        assert encoding
        assert encoding != "utf-8-sig"
