"""
Hardened extraction for caller-supplied gzipped tar uploads.

``/validate`` and ``/upload`` accept an archive from anyone (validate is
unauthenticated by design until per-user auth lands), then extract it to a temp
directory. A naive ``tarfile.extractall`` on untrusted input is exposed to:

* path traversal / absolute paths / symlinks writing outside the temp dir, and
* decompression bombs (a tiny upload expanding to fill the disk or OOM the pod).

``filter="data"`` (Python 3.12+) rejects the traversal/symlink/device class of
attacks. The size and member-count caps below bound the decompression bomb: tar
member headers declare each entry's uncompressed size, so we can total them
*before* writing anything to disk.
"""

import tarfile
from typing import BinaryIO

#: Maximum number of files in one archive.
MAX_MEMBERS = 500
#: Maximum declared uncompressed size of any single member.
MAX_MEMBER_BYTES = 50 * 2**20  # 50 MB
#: Maximum declared uncompressed size of the whole archive.
MAX_TOTAL_BYTES = 200 * 2**20  # 200 MB


class ArchiveError(Exception):
    """Malformed or unsafe archive — maps to HTTP 400."""


class ArchiveTooLarge(Exception):
    """Archive exceeds a size/member cap — maps to HTTP 413."""


def safe_extract_targz(fileobj: BinaryIO, dest: str) -> None:
    """Extract a gzipped tar into ``dest``, rejecting unsafe or oversized inputs.

    Raises:
        ArchiveError: unreadable archive or a non-regular member.
        ArchiveTooLarge: member count or declared size exceeds a cap.
    """
    try:
        with tarfile.open(fileobj=fileobj, mode="r:gz") as tar:
            members = []
            total = 0
            for member in tar:
                # Directory entries are fine (parents are created implicitly),
                # but reject anything that is not a plain file or directory:
                # symlinks, hardlinks, devices, fifos.
                if not (member.isreg() or member.isdir()):
                    raise ArchiveError(
                        f"Unsupported archive member type: {member.name}"
                    )
                if member.isreg():
                    if member.size > MAX_MEMBER_BYTES:
                        raise ArchiveTooLarge(
                            f"Member {member.name} exceeds {MAX_MEMBER_BYTES} bytes"
                        )
                    total += member.size
                    if total > MAX_TOTAL_BYTES:
                        raise ArchiveTooLarge(
                            f"Archive exceeds {MAX_TOTAL_BYTES} bytes uncompressed"
                        )
                members.append(member)
                if len(members) > MAX_MEMBERS:
                    raise ArchiveTooLarge(
                        f"Archive has more than {MAX_MEMBERS} members"
                    )

            # filter="data" blocks absolute paths, "..", symlinks and devices.
            tar.extractall(dest, members=members, filter="data")
    except (ArchiveError, ArchiveTooLarge):
        raise
    except tarfile.TarError as exc:
        raise ArchiveError(f"Could not read archive: {exc}") from exc
