"""
What one SEM artifact is, kept apart from how it is built.

``artifacts.py`` needs OpenCV, Pillow and exifread (the ``sem`` dependency
group); this file needs nothing. So ``cdn.py``, its tests and anything that
only moves the bytes around can import the type without the heavy group.
"""

from __future__ import annotations

from dataclasses import dataclass

WEBP_CONTENT_TYPE = "image/webp"
JSON_CONTENT_TYPE = "application/json"
MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class Artifact:
    """One file to write or upload, relative to the specimen's own folder."""

    rel_path: str  # "global.webp", "s2/north_250.webp", "manifest.json"
    data: bytes
    content_type: str
