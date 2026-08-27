"""Unit tests for the hardened archive extraction (no database needed)."""

import io
import tarfile

import pytest

from resslab_hub.utils.safe_archive import (
    MAX_MEMBERS,
    ArchiveError,
    ArchiveTooLarge,
    safe_extract_targz,
)


def _targz(members: list[tuple[str, bytes]]) -> io.BytesIO:
    """Build an in-memory gzipped tar from (name, content) pairs."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in members:
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    buffer.seek(0)
    return buffer


def test_extracts_regular_files(tmp_path):
    archive = _targz([("braces/steel_braces.csv", b"id\nB1\n")])
    safe_extract_targz(archive, str(tmp_path))
    assert (tmp_path / "braces" / "steel_braces.csv").read_text() == "id\nB1\n"


def test_rejects_path_traversal(tmp_path):
    # filter="data" strips the traversal; nothing escapes the destination.
    archive = _targz([("../evil.csv", b"x")])
    with pytest.raises((ArchiveError, ArchiveTooLarge)):
        safe_extract_targz(archive, str(tmp_path))
    assert not (tmp_path.parent / "evil.csv").exists()


def test_absolute_path_is_contained_not_escaped(tmp_path):
    # The data filter strips the leading slash, so an absolute member lands
    # inside the destination (etc/evil.csv) rather than at the real /etc.
    archive = _targz([("/etc/evil.csv", b"x")])
    safe_extract_targz(archive, str(tmp_path))
    assert (tmp_path / "etc" / "evil.csv").exists()


def test_rejects_symlink_member(tmp_path):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        link = tarfile.TarInfo(name="link.csv")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        tar.addfile(link)
    buffer.seek(0)
    with pytest.raises(ArchiveError):
        safe_extract_targz(buffer, str(tmp_path))


def test_accepts_a_bulk_contribution(tmp_path):
    # 200 specimens with three response files each — the batch size the
    # contribution editor's folder drop is meant for — fits under the cap.
    members = [("columns/steel_columns.csv", b"id\n")] + [
        (f"columns/{kind}/C{i}.csv", b"x")
        for i in range(200)
        for kind in ("moment_rotation_strong", "moment_rotation_weak", "axial")
    ]
    safe_extract_targz(_targz(members), str(tmp_path))
    assert len(list((tmp_path / "columns" / "axial").iterdir())) == 200


def test_rejects_too_many_members(tmp_path):
    archive = _targz([(f"f{i}.csv", b"x") for i in range(MAX_MEMBERS + 5)])
    with pytest.raises(ArchiveTooLarge):
        safe_extract_targz(archive, str(tmp_path))


def test_rejects_oversized_member(tmp_path):
    # Declared size is checked from the header before writing to disk; a member
    # claiming to exceed the per-member cap is rejected.
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="big.csv")
        info.size = 51 * 2**20  # 51 MB > MAX_MEMBER_BYTES
        tar.addfile(info, io.BytesIO(b"\0" * info.size))
    buffer.seek(0)
    with pytest.raises(ArchiveTooLarge):
        safe_extract_targz(buffer, str(tmp_path))


def test_rejects_non_gzip(tmp_path):
    with pytest.raises(ArchiveError):
        safe_extract_targz(io.BytesIO(b"not a tar"), str(tmp_path))
