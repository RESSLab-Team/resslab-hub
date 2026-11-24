"""
Precompute the SEM artifacts of every ductile-fracture coupon.

Walks ``<data_repo>/material/ductile_fracture/sem/<id>/``, converts each folder
of TIFs (``resslab_hub.sem.artifacts``), writes the result next to it under
``sem/_webp/<id>/``, uploads it to the EPFL enacit4r-cdn
(``resslab_hub.sem.cdn``) and sets ``has_sem`` in ``ductile_fracture.csv``.

Usage::

    DRY_RUN=1 python data/precompute_sem.py ../../resslab-hub-data
    python data/precompute_sem.py ../../resslab-hub-data        # uploads to CDN

Environment:
    DRY_RUN     If "1", skip the CDN upload and the CSV write. The WebPs and
                JSONs are still written to ``<sem_dir>/_webp/<id>/``, which is
                what the local dev symlink (frontend/public/sem) reads.
    S3_ENDPOINT_PROTOCOL, S3_ENDPOINT_HOSTNAME, S3_REGION, S3_BUCKET,
    S3_PATH_PREFIX, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY
                The CDN, read through the app settings, so ``secrets/.env``
                or the shell. Required unless DRY_RUN. See docs/src/sem-images.md.
"""

from __future__ import annotations

import asyncio
import csv
import io
import os
import sys
from pathlib import Path
from typing import List

from resslab_hub.config import settings
from resslab_hub.sem.artifacts import (
    build_specimen_artifacts,
    count_dimple_files,
    read_manifest,
)
from resslab_hub.sem.cdn import (
    CdnConfig,
    CdnNotConfigured,
    make_s3_service,
    upload_artifacts,
    write_artifacts,
)


def update_has_sem(data_root: Path, specimen_ids: List[str], dry_run: bool) -> None:
    """Flip ``has_sem`` to "yes" in ductile_fracture.csv for processed specimens.

    Set-only: a specimen folder missing locally proves nothing (LFS may not be
    pulled), so flags are never cleared here. The operator commits the CSV
    change to the data repo — git stays the source of truth.
    """
    csv_path = data_root / "material" / "ductile_fracture" / "ductile_fracture.csv"
    raw = csv_path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    header = rows[0]
    id_col = header.index("id")
    sem_col = header.index("has_sem")

    wanted = set(specimen_ids)
    changed = []
    for row in rows[1:]:
        if row[id_col] in wanted and row[sem_col].strip().lower() != "yes":
            row[sem_col] = "yes"
            changed.append(row[id_col])
    missing = wanted - {row[id_col] for row in rows[1:]}
    if missing:
        print(f"[warn] not in ductile_fracture.csv: {', '.join(sorted(missing))}")
    if not changed:
        print("has_sem already up to date in ductile_fracture.csv")
        return
    if dry_run:
        print(f"DRY_RUN — would set has_sem=yes for: {', '.join(changed)}")
        return

    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    encoding = "utf-8-sig" if bom else "utf-8"
    csv_path.write_bytes(buf.getvalue().encode(encoding))
    print(
        f"Set has_sem=yes for: {', '.join(changed)} — "
        "commit ductile_fracture.csv to the data repo."
    )


async def run(data_root: Path, dry_run: bool) -> int:
    sem_dir = data_root / "material" / "ductile_fracture" / "sem"
    if not sem_dir.is_dir():
        print(f"SEM directory not found: {sem_dir}", file=sys.stderr)
        return 1

    specimens = sorted(
        p.name for p in sem_dir.iterdir() if p.is_dir() and not p.name.startswith("_")
    )
    if not specimens:
        print(f"No specimen folders under {sem_dir}")
        return 0

    # Fail before any conversion when the CDN is asked for but not configured.
    s3 = None if dry_run else make_s3_service(CdnConfig.from_settings(settings))
    out_root = sem_dir / "_webp"
    print(
        f"Writing WebPs/JSONs to {out_root}"
        + (" (DRY_RUN=1, no CDN upload)." if dry_run else " and uploading them.")
    )

    processed: List[str] = []
    try:
        for specimen_id in specimens:
            folder = sem_dir / specimen_id
            tif_files = sorted(
                p for p in folder.iterdir() if p.suffix.lower() == ".tif"
            )
            if not tif_files:
                print(f"[skip] {specimen_id}: no .tif files")
                continue

            artifacts = build_specimen_artifacts(tif_files)
            if not artifacts:
                print(f"[skip] {specimen_id}: no recognized file name")
                continue

            write_artifacts(out_root / specimen_id, artifacts)
            surfaces = read_manifest(artifacts).get("surfaces", 0)
            print(
                f"[done] {specimen_id}: {len(tif_files)} tifs, "
                f"{surfaces} surface(s), {count_dimple_files(artifacts)} "
                "per-image dimple files"
            )
            if s3 is not None:
                count = await upload_artifacts(s3, specimen_id, artifacts)
                print(f"[upload] {specimen_id}: {count} files")
            processed.append(specimen_id)
    finally:
        if s3 is not None:
            await s3.close()

    if processed:
        update_has_sem(data_root, processed, dry_run)
    return 0


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: python {argv[0]} <path-to-resslab-hub-data>", file=sys.stderr)
        return 2
    data_root = Path(argv[1]).resolve()
    dry_run = os.environ.get("DRY_RUN") == "1"
    try:
        return asyncio.run(run(data_root, dry_run))
    except CdnNotConfigured as err:
        # Nothing was converted yet, so there is nothing to clean up.
        print(
            f"{err}\nRun with DRY_RUN=1 to convert without uploading.", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main([sys.argv[0]] + sys.argv[1:]))
