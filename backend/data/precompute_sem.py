"""
Precompute SEM artifacts for the ductile-fracture tab.

For each specimen folder under ``<data_repo>/material/ductile_fracture/sem/<id>/``:
- Convert each ``*.tif`` to WebP.
- For non-global images, read the EXIF pixel size and run process_sem to extract
  per-image dimple diameters (mm). Pool everything into a "dimples_all.json".
- Upload WebPs and dimple JSONs to the EPFL enacit4r-cdn (skipped when
  DRY_RUN=1 — outputs go to a local ``_webp/`` directory instead).

The CDN model: uploads go to ``s3.epfl.ch`` into a shared enacit4r bucket, and
the same path inside that bucket is served at ``enacit4r-cdn.epfl.ch/...``.
So objects land at ``s3://<bucket>/resslab-hub/sem/<id>/...`` to be readable
at ``https://enacit4r-cdn.epfl.ch/resslab-hub/sem/<id>/...``.

Usage::

    DRY_RUN=1 python data/precompute_sem.py ../../resslab-hub-data
    python data/precompute_sem.py ../../resslab-hub-data        # uploads to CDN

Environment:
    DRY_RUN           If "1", skip CDN upload. WebPs and JSONs land in
                      ``<sem_dir>/_webp/<id>/``.
    ACCESS_KEY_ID, ACCESS_KEY_SECRET
                      S3 creds for the EPFL CDN (from EPFL KeeWeb).
    BUCKET_NAME       Shared enacit4r bucket name (from EPFL KeeWeb). Required.
    S3_ENDPOINT_URL   Defaults to https://s3.epfl.ch.
    CDN_PREFIX        Defaults to "resslab-hub". Matches VITE_SEM_CDN_BASE_URL
                      in frontend/.env.production.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import exifread
import numpy as np
from PIL import Image
from process_sem_lib import crop_legend, process_sem  # noqa: E402

DEFAULT_S3_ENDPOINT = "https://s3.epfl.ch"
DEFAULT_CDN_PREFIX = "resslab-hub"
WEBP_QUALITY = 85
EXIF_PIXEL_SIZE_TAG = "Image Tag 0x8546"
# Filename convention: "<location>_<magnification>[_<surface>].tif" or
# "global[_<surface>].tif". The optional trailing "_<n>" denotes the fracture
# surface: absent means surface 1, "_2" means the opposite surface of the
# ruptured bar (Ozden et al. coupons image both surfaces).
LOCAL_FILENAME = re.compile(
    r"^(?P<location>[a-zA-Z]+)_(?P<mag>\d+)(?:_(?P<surface>\d+))?\.tif$"
)
GLOBAL_FILENAME = re.compile(r"^global(?:_(?P<surface>\d+))?\.tif$")


def parse_filename(name: str) -> Optional[Tuple[str, Optional[int], int]]:
    """Return (location, magnification, surface) or None if name doesn't match.

    ``surface`` defaults to 1 when no ``_<n>`` suffix is present.
    """
    g = GLOBAL_FILENAME.match(name)
    if g:
        return "global", None, int(g.group("surface") or 1)
    m = LOCAL_FILENAME.match(name)
    if m:
        return (
            m.group("location").lower(),
            int(m.group("mag")),
            int(m.group("surface") or 1),
        )
    return None


def surface_subpath(surface: int) -> str:
    """CDN/local subpath prefix for a surface. Surface 1 stays flat."""
    return "" if surface == 1 else f"s{surface}/"


def read_pixel_size_mm(tif_path: Path) -> Optional[float]:
    """Extract pixel size (mm) from the SEM TIFF's EXIF tag 0x8546."""
    with open(tif_path, "rb") as fh:
        tags = exifread.process_file(fh, details=False)
    raw = tags.get(EXIF_PIXEL_SIZE_TAG)
    if raw is None:
        return None
    # The tag value is an ASCII byte array like
    # "PixelSize=3.722e-06m\x00..." per process_SEM.py.
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
    from botocore.config import Config  # noqa: WPS433

    # EPFL enacit4r-cdn rejects boto3 >=1.36's default trailing checksums
    # ("BadRequest: trailing checksum is not supported"). Opt out.
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL", DEFAULT_S3_ENDPOINT),
        aws_access_key_id=os.environ["ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["ACCESS_KEY_SECRET"],
        config=Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
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
    bucket = None if dry_run else os.environ["BUCKET_NAME"]
    cdn_prefix = os.environ.get("CDN_PREFIX", DEFAULT_CDN_PREFIX)

    out_dir: Optional[Path] = None
    if dry_run:
        out_dir = sem_dir / "_webp" / specimen_id
        out_dir.mkdir(parents=True, exist_ok=True)

    def emit(rel_path: str, body: bytes, content_type: str) -> None:
        """Write an artifact to the local _webp dir or upload it to the CDN.

        ``rel_path`` is relative to the specimen root (e.g. "global.webp" or
        "s2/north_250.webp").
        """
        if dry_run:
            dest = out_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
        else:
            _upload(
                s3,
                bucket,
                f"{cdn_prefix}/sem/{specimen_id}/{rel_path}",
                body,
                content_type,
            )

    tif_files = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".tif")
    if not tif_files:
        print(f"[skip] {specimen_id}: no .tif files")
        return

    # Per-surface accumulators, plus manifest metadata gathered across surfaces.
    pooled: dict[int, List[float]] = {}
    per_image: dict[int, List[Tuple[str, List[float]]]] = {}
    surfaces: set[int] = set()
    locations: set[str] = set()
    magnifications: set[int] = set()

    for tif in tif_files:
        parsed = parse_filename(tif.name)
        if parsed is None:
            print(f"[skip] {tif.name}: unrecognized name")
            continue
        location, magnification, surface = parsed
        surfaces.add(surface)
        sub = surface_subpath(surface)

        webp_name = (
            "global.webp"
            if location == "global"
            else f"{location}_{magnification}.webp"
        )
        emit(f"{sub}{webp_name}", tif_to_webp_bytes(tif), "image/webp")

        if location == "global":
            continue
        locations.add(location)
        magnifications.add(magnification)

        pixel_size_mm = read_pixel_size_mm(tif)
        if pixel_size_mm is None:
            print(f"[warn] {tif.name}: no pixel size in EXIF; skipping dimples")
            continue
        diameters = extract_dimples_mm(tif, pixel_size_mm)
        diameters.sort()
        per_image.setdefault(surface, []).append(
            (f"dimples_{location}_{magnification}.json", diameters)
        )
        pooled.setdefault(surface, []).extend(diameters)

    n_dimple_files = 0
    for surface in sorted(surfaces):
        sub = surface_subpath(surface)
        for name, diameters in per_image.get(surface, []):
            emit(
                f"{sub}{name}",
                json.dumps(diameters).encode("utf-8"),
                "application/json",
            )
            n_dimple_files += 1
        pooled_surface = sorted(pooled.get(surface, []))
        emit(
            f"{sub}dimples_all.json",
            json.dumps(pooled_surface).encode("utf-8"),
            "application/json",
        )

    manifest = {
        "surfaces": len(surfaces),
        "locations": sorted(locations),
        "magnifications": sorted(magnifications),
    }
    emit("manifest.json", json.dumps(manifest).encode("utf-8"), "application/json")

    print(
        f"[done] {specimen_id}: {len(tif_files)} tifs, "
        f"{len(surfaces)} surface(s), {n_dimple_files} per-image dimple files"
    )
    print(f"        Set has_sem=True for {specimen_id} in ductile_fracture.csv.")


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: python {argv[0]} <path-to-resslab-hub-data>", file=sys.stderr)
        return 2
    data_root = Path(argv[1]).resolve()
    sem_dir = data_root / "material" / "ductile_fracture" / "sem"
    if not sem_dir.is_dir():
        print(f"SEM directory not found: {sem_dir}", file=sys.stderr)
        return 1

    dry_run = os.environ.get("DRY_RUN") == "1"
    if dry_run:
        print(
            f"DRY_RUN=1 — writing WebPs/JSONs to {sem_dir / '_webp'} (no CDN upload)."
        )

    specimens = sorted(
        p.name for p in sem_dir.iterdir() if p.is_dir() and not p.name.startswith("_")
    )
    if not specimens:
        print(f"No specimen folders under {sem_dir}")
        return 0

    for specimen_id in specimens:
        process_specimen(sem_dir, specimen_id, dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main([sys.argv[0]] + sys.argv[1:]))
