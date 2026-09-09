"""
Turn a specimen's SEM TIFs into the files the app reads.

For one folder of TIFs (one ductile-fracture coupon):
- Convert each ``*.tif`` to WebP.
- For non-global images, read the EXIF pixel size and run process_sem to
  extract per-image dimple diameters (mm). Pool everything per fracture
  surface into a "dimples_all.json".
- Describe what exists in a "manifest.json".

Everything comes back as bytes in memory, so the caller decides where it goes:
``resslab_hub.sem.cdn`` writes it to disk or uploads it to the CDN. The
submission pipeline will call the same function on the TIFs of one submission.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import exifread
import numpy as np
from PIL import Image

from .process_sem import crop_legend, process_sem

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

WEBP_CONTENT_TYPE = "image/webp"
JSON_CONTENT_TYPE = "application/json"
MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class Artifact:
    """One file to write or upload, relative to the specimen's own folder."""

    rel_path: str  # "global.webp", "s2/north_250.webp", "manifest.json"
    data: bytes
    content_type: str


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


def build_specimen_artifacts(
    tif_files: Sequence[Path],
    log: Callable[[str], None] = print,
) -> List[Artifact]:
    """Convert and measure one specimen's TIFs, in memory.

    ``tif_files`` are the ``*.tif`` of a single coupon, in any order. A file
    whose name doesn't match the convention is skipped with a warning. Returns
    an empty list when nothing matched.
    """
    artifacts: List[Artifact] = []

    # Per-surface accumulators, plus manifest metadata gathered across surfaces.
    pooled: Dict[int, List[float]] = {}
    per_image: Dict[int, List[Tuple[str, List[float]]]] = {}
    surfaces: Set[int] = set()
    locations: Set[str] = set()
    magnifications: Set[int] = set()

    for tif in tif_files:
        parsed = parse_filename(tif.name)
        if parsed is None:
            log(f"[skip] {tif.name}: unrecognized name")
            continue
        location, magnification, surface = parsed
        surfaces.add(surface)
        sub = surface_subpath(surface)

        webp_name = (
            "global.webp"
            if location == "global"
            else f"{location}_{magnification}.webp"
        )
        artifacts.append(
            Artifact(f"{sub}{webp_name}", tif_to_webp_bytes(tif), WEBP_CONTENT_TYPE)
        )

        if location == "global":
            continue
        locations.add(location)
        magnifications.add(magnification)

        pixel_size_mm = read_pixel_size_mm(tif)
        if pixel_size_mm is None:
            log(f"[warn] {tif.name}: no pixel size in EXIF; skipping dimples")
            continue
        diameters = extract_dimples_mm(tif, pixel_size_mm)
        diameters.sort()
        per_image.setdefault(surface, []).append(
            (f"dimples_{location}_{magnification}.json", diameters)
        )
        pooled.setdefault(surface, []).extend(diameters)

    if not surfaces:
        return []

    for surface in sorted(surfaces):
        sub = surface_subpath(surface)
        for name, diameters in per_image.get(surface, []):
            artifacts.append(Artifact(f"{sub}{name}", _json(diameters), JSON_CONTENT_TYPE))
        pooled_surface = sorted(pooled.get(surface, []))
        artifacts.append(
            Artifact(f"{sub}dimples_all.json", _json(pooled_surface), JSON_CONTENT_TYPE)
        )

    manifest = {
        "surfaces": len(surfaces),
        "locations": sorted(locations),
        "magnifications": sorted(magnifications),
    }
    artifacts.append(Artifact(MANIFEST_NAME, _json(manifest), JSON_CONTENT_TYPE))
    return artifacts


def read_manifest(artifacts: Sequence[Artifact]) -> Dict:
    """The manifest of a built list: surfaces, locations, magnifications."""
    for artifact in artifacts:
        if artifact.rel_path == MANIFEST_NAME:
            return json.loads(artifact.data)
    return {}


def count_dimple_files(artifacts: Sequence[Artifact]) -> int:
    """Per-image dimple files in the list, for the script's summary line."""
    return sum(
        1
        for a in artifacts
        if a.rel_path.rsplit("/", 1)[-1].startswith("dimples_")
        and not a.rel_path.endswith("dimples_all.json")
    )


def _json(value) -> bytes:
    return json.dumps(value).encode("utf-8")
