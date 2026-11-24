"""Review 04 (pipeline input): proofs on ``safe_extract_targz``. No database.

Each test states what the code should do. It fails today, so it is marked
``xfail(strict=True)``: once the finding is fixed the test passes, the run
fails, and the mark must go. Findings: docs/archive/review/findings/04-pipeline-input.md
"""

import gzip
import io
import random
import tarfile
import tracemalloc

import pytest

from resslab_hub.utils.safe_archive import (
    ArchiveError,
    ArchiveTooLarge,
    safe_extract_targz,
)

REFUSED = (ArchiveError, ArchiveTooLarge)


def _targz(members) -> io.BytesIO:
    """A gzipped tar from (name, bytes or None for a directory) pairs."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
        for name, data in members:
            info = tarfile.TarInfo(name)
            if data is None:
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    buffer.seek(0)
    return buffer


def _truncated() -> io.BytesIO:
    # Data that does not compress, so half of the gzip stream is cut mid-member.
    data = random.Random(0).randbytes(30_000).hex().encode()
    full = _targz([("braces/steel_braces.csv", data)]).getvalue()
    return io.BytesIO(full[: len(full) // 2])


BROKEN = {
    # EOFError from gzip: not a TarError.
    "truncated gzip": _truncated,
    # OSError ENAMETOOLONG from extractall.
    "name of 300 bytes": lambda: _targz(
        [("braces/force_displacement/" + "B" * 300 + ".csv", b"x")]
    ),
    # NotADirectoryError: "braces" is a file, then a folder.
    "file then folder": lambda: _targz(
        [("braces", b"x"), ("braces/steel_braces.csv", b"id\n")]
    ),
    # IsADirectoryError: "braces" is a folder, then a file.
    "folder then file": lambda: _targz([("braces", None), ("braces", b"x")]),
}


@pytest.mark.xfail(strict=True, reason="review 04: 04-1")
@pytest.mark.parametrize("make", BROKEN.values(), ids=BROKEN.keys())
def test_broken_archive_is_refused_as_a_bad_archive(make, tmp_path):
    """A broken archive must give ArchiveError (400), not a generic 500."""
    with pytest.raises(REFUSED):
        safe_extract_targz(make(), str(tmp_path))


def _gnu_long_name(size: int) -> io.BytesIO:
    """A GNU long-name header that says the next member's name is ``size`` bytes.

    tarfile reads that whole name into memory to build the next member, so
    before ``safe_extract_targz`` sees any member and checks any cap.
    """
    header = tarfile.TarInfo("././@LongLink")
    header.type = tarfile.GNUTYPE_LONGNAME
    header.size = size
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=9) as gz:
        gz.write(header.tobuf(format=tarfile.GNU_FORMAT))
        chunk = b"a" * 2**20
        for _ in range(size // len(chunk)):
            gz.write(chunk)
        gz.write(tarfile.TarInfo("x.csv").tobuf(format=tarfile.GNU_FORMAT))
        gz.write(b"\0" * 1024)
    out.seek(0)
    return out


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-2")
def test_long_name_header_is_not_read_into_memory(tmp_path):
    """64 MB of name in a ~64 kB upload: memory must stay far below that."""
    archive = _gnu_long_name(64 * 2**20)
    assert len(archive.getvalue()) < 200_000
    tracemalloc.start()
    try:
        try:
            safe_extract_targz(archive, str(tmp_path))
        except Exception:  # noqa: BLE001
            # Today an OSError (ENAMETOOLONG), so also a 500: see 04-1.
            pass
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 8 * 2**20, (
        f"peak {peak / 2**20:.0f} MB for a {len(archive.getvalue())} B upload"
    )
