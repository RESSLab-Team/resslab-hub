"""
Precompute SEM artifacts for the ductile-fracture tab.

For each specimen folder under ``<data_repo>/ductile_fracture/sem/<id>/``:
- Convert each ``*.tif`` to WebP.
- For non-global images, read the EXIF pixel size and run process_sem to extract
  per-image dimple diameters (mm). Pool everything into a "dimples_all.json".
- Upload WebPs and dimple JSONs to the EPFL enacit4r-cdn under
  ``s3://<bucket>/sem/<id>/`` (skipped when DRY_RUN=1 — outputs go to a local
  ``_webp/`` directory instead).

Usage::

    DRY_RUN=1 python data/precompute_sem.py ../../resslab-hub-data
    python data/precompute_sem.py ../../resslab-hub-data        # uploads to CDN

Environment:
    DRY_RUN           If "1", skip CDN upload. WebPs and JSONs land in
                      ``<sem_dir>/_webp/<id>/``.
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_ENDPOINT_URL, S3_BUCKET
                      S3 creds for the EPFL CDN. Defaults:
                      S3_ENDPOINT_URL=https://enacit4r-cdn.epfl.ch,
                      S3_BUCKET=resslab-hub.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import exifread
import numpy as np
from PIL import Image

from process_sem_lib import crop_legend, process_sem  # noqa: E402

DEFAULT_S3_ENDPOINT = "https://enacit4r-cdn.epfl.ch"
DEFAULT_S3_BUCKET = "resslab-hub"
WEBP_QUALITY = 85
EXIF_PIXEL_SIZE_TAG = "Image Tag 0x8546"
# Filename convention: "<location>_<magnification>.tif" or "global.tif".
LOCAL_FILENAME = re.compile(r"^(?P<location>[a-zA-Z]+)_(?P<mag>\d+)\.tif$")


def parse_filename(name: str) -> Optional[Tuple[str, Optional[int]]]:
    """Return (location, magnification) or None if the filename doesn't match."""
    if name == "global.tif":
        return "global", None
    m = LOCAL_FILENAME.match(name)
    if m:
        return m.group("location").lower(), int(m.group("mag"))
    return None


def read_pixel_size_mm(tif_path: Path) -> Optional[float]:
    """Extract pixel size (mm) from the SEM TIFF's EXIF tag 0x8546."""
    with open(tif_path, "rb") as fh:
        tags = exifread.process_file(fh, details=False)
    raw = tags.get(EXIF_PIXEL_SIZE_TAG)
    if raw is None:
        return None
    # The tag value is an ASCII byte array like "PixelSize=3.722e-06m\x00..." per process_SEM.py.
    return float(str(raw.values)[9:21])


def tif_to_webp_bytes(tif_path: Path) -> bytes:
    """Encode the TIF as WebP and return the bytes."""
    with Image.open(tif_path) as im:
        buf = io.BytesIO()
        im.save(buf, format="webp", quality=WEBP_QUALITY)
        return buf.getvalue()


def extract_dimples_mm(tif_path: Path, pixel_size_mm: float) -> List[float]:
    """Run process_sem on the cropped image and return dimple diameters in mm."""
    arr = np.array(Image.open(tif_path))
    # SEM TIFs are RGB but channel 0 carries the grayscale signal.
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    arr = crop_legend(arr)
    _, radii_px = process_sem(arr)
    # diameter = 2 * radius, convert pixel→mm. process_SEM.py multiplies by 1000
    # because the EXIF pixel size is reported in metres; keep that.
    return [float(r * pixel_size_mm * 2 * 1000) for r in radii_px]


def _make_s3_client():
    """Lazy import boto3 so DRY_RUN runs don't require the dep."""
    import boto3  # noqa: WPS433

    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL", DEFAULT_S3_ENDPOINT),
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )


def _upload(s3, bucket: str, key: str, body: bytes, content_type: str) -> None:
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
        ACL="public-read",
    )


def process_specimen(sem_dir: Path, specimen_id: str, dry_run: bool) -> None:
    folder = sem_dir / specimen_id
    if not folder.is_dir():
        return

    s3 = None if dry_run else _make_s3_client()
    bucket = os.environ.get("S3_BUCKET", DEFAULT_S3_BUCKET)

    out_dir: Optional[Path] = None
    if dry_run:
        out_dir = sem_dir / "_webp" / specimen_id
        out_dir.mkdir(parents=True, exist_ok=True)

    pooled_diameters: List[float] = []
    per_image_paths: List[Tuple[str, List[float]]] = []
    tif_files = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".tif")
    if not tif_files:
        print(f"[skip] {specimen_id}: no .tif files")
        return

    for tif in tif_files:
        parsed = parse_filename(tif.name)
        if parsed is None:
            print(f"[skip] {tif.name}: unrecognized name")
            continue
        location, magnification = parsed

        webp_name = (
            "global.webp"
            if location == "global"
            else f"{location}_{magnification}.webp"
        )
        webp_bytes = tif_to_webp_bytes(tif)
        if dry_run:
            (out_dir / webp_name).write_bytes(webp_bytes)
        else:
            _upload(
                s3,
                bucket,
                f"sem/{specimen_id}/{webp_name}",
                webp_bytes,
                "image/webp",
            )

        if location == "global":
            continue

        pixel_size_mm = read_pixel_size_mm(tif)
        if pixel_size_mm is None:
            print(f"[warn] {tif.name}: no pixel size in EXIF; skipping dimples")
            continue
        diameters = extract_dimples_mm(tif, pixel_size_mm)
        diameters.sort()
        per_image_paths.append((f"dimples_{location}_{magnification}.json", diameters))
        pooled_diameters.extend(diameters)

    pooled_diameters.sort()

    for name, diameters in per_image_paths:
        body = json.dumps(diameters).encode("utf-8")
        if dry_run:
            (out_dir / name).write_bytes(body)
        else:
            _upload(s3, bucket, f"sem/{specimen_id}/{name}", body, "application/json")

    pooled_body = json.dumps(pooled_diameters).encode("utf-8")
    if dry_run:
        (out_dir / "dimples_all.json").write_bytes(pooled_body)
    else:
        _upload(
            s3,
            bucket,
            f"sem/{specimen_id}/dimples_all.json",
            pooled_body,
            "application/json",
        )

    print(
        f"[done] {specimen_id}: {len(tif_files)} tifs, "
        f"{len(per_image_paths)} per-image dimple files, "
        f"{len(pooled_diameters)} pooled dimples"
    )
    print(f"        Set has_sem=True for {specimen_id} in ductile_fracture.csv.")


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: python {argv[0]} <path-to-resslab-hub-data>", file=sys.stderr)
        return 2
    data_root = Path(argv[1]).resolve()
    sem_dir = data_root / "ductile_fracture" / "sem"
    if not sem_dir.is_dir():
        print(f"SEM directory not found: {sem_dir}", file=sys.stderr)
        return 1

    dry_run = os.environ.get("DRY_RUN") == "1"
    if dry_run:
        print(f"DRY_RUN=1 — writing WebPs/JSONs to {sem_dir / '_webp'} (no CDN upload).")

    specimens = sorted(p.name for p in sem_dir.iterdir() if p.is_dir() and not p.name.startswith("_"))
    if not specimens:
        print(f"No specimen folders under {sem_dir}")
        return 0

    for specimen_id in specimens:
        process_specimen(sem_dir, specimen_id, dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main([sys.argv[0]] + sys.argv[1:]))
