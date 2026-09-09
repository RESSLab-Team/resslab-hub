"""
Where the SEM artifacts go: the EPFL enacit4r-cdn, or a local folder.

The CDN model: uploads go to ``s3.epfl.ch`` into a shared enacit4r bucket, and
the same path inside that bucket is served at ``enacit4r-cdn.epfl.ch/...``.
So objects land at ``s3://<bucket>/<prefix>/<id>/...`` to be readable at
``https://enacit4r-cdn.epfl.ch/<prefix>/<id>/...``, with the prefix matching
``VITE_SEM_CDN_BASE_URL`` in the frontend.

The upload runs on ``enacit4r-files``, ENAC IT4R's S3 client, the one the other
ENAC apps use. It disables the trailing checksums the EPFL endpoint rejects
(``with_checksums=False``, its default); do not turn them on.

Every value comes from the settings, none from this file: the five public ones
from the resslab-hub-backend ConfigMap in k8s (secrets/.env on a laptop), the
two keys from Infisical. See docs/sem-images.md.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from fastapi.datastructures import UploadFile
from starlette.datastructures import Headers

from .artifacts import Artifact

# Setting name -> attribute of CdnConfig. The setting names are the ENAC ones,
# so the ConfigMap of this app looks like the ConfigMap of every other one.
S3_SETTINGS = {
    "s3_endpoint_protocol": "endpoint_protocol",
    "s3_endpoint_hostname": "endpoint_hostname",
    "s3_region": "region",
    "s3_bucket": "bucket",
    "s3_path_prefix": "path_prefix",
    "s3_access_key_id": "access_key_id",
    "s3_secret_access_key": "secret_access_key",
}


class CdnNotConfigured(RuntimeError):
    """Raised when an upload is asked for without the S3 settings."""


@dataclass(frozen=True)
class CdnConfig:
    endpoint_protocol: str  # "https://"
    endpoint_hostname: str  # "s3.epfl.ch"
    region: str  # "EU"
    bucket: str  # the shared enacit4r bucket
    path_prefix: str  # "resslab-hub/sem"
    access_key_id: str
    secret_access_key: str

    @classmethod
    def from_settings(cls, settings) -> "CdnConfig":
        """Read the seven S3 settings, or say which ones are missing."""
        values = {}
        missing = []
        for name, field in S3_SETTINGS.items():
            value = getattr(settings, name, None)
            if value is None or str(value).strip() == "":
                missing.append(name.upper())
            else:
                values[field] = str(value)
        if missing:
            raise CdnNotConfigured(
                f"{', '.join(missing)} not set. The SEM upload needs the S3 "
                "settings (secrets/.env locally, the ConfigMap and Infisical "
                "in the deployments). See docs/sem-images.md."
            )
        return cls(**values)

    @property
    def endpoint_url(self) -> str:
        return f"{self.endpoint_protocol}{self.endpoint_hostname}"


def make_s3_service(config: CdnConfig):
    """Build the enacit4r-files S3 client.

    Imported lazily: converting images and writing them locally must not need
    the library, so a DRY_RUN run works without it.
    """
    from enacit4r_files.services import S3Service

    return S3Service(
        config.endpoint_url,
        config.access_key_id,
        config.secret_access_key,
        config.region,
        config.bucket,
        config.path_prefix,
    )


def s3_folder_and_name(specimen_id: str, rel_path: str) -> Tuple[str, str]:
    """Split "s2/north_250.webp" into the S3 folder and the file name.

    The library builds the key as ``<path_prefix>/<s3_folder>/<name>``, so the
    surface subfolder belongs to the folder, not to the name.
    """
    head, _, name = rel_path.rpartition("/")
    folder = f"{specimen_id}/{head}" if head else specimen_id
    return folder, name


def _upload_file(artifact: Artifact, name: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(artifact.data),
        filename=name,
        size=len(artifact.data),
        headers=Headers({"content-type": artifact.content_type}),
    )


async def upload_artifacts(s3, specimen_id: str, artifacts: Sequence[Artifact]) -> int:
    """Upload one specimen's artifacts, in memory. Returns the file count.

    A failure raises (``S3Error`` from the library), which is what we want: the
    caller must not record the specimen as uploaded.
    """
    uploads = []
    for artifact in artifacts:
        folder, name = s3_folder_and_name(specimen_id, artifact.rel_path)
        uploads.append(s3.upload_file(_upload_file(artifact, name), s3_folder=folder))
    await asyncio.gather(*uploads)
    return len(uploads)


def write_artifacts(out_dir: Path, artifacts: Iterable[Artifact]) -> List[Path]:
    """Write the artifacts under ``out_dir``, creating the surface subfolders."""
    written = []
    for artifact in artifacts:
        dest = out_dir / artifact.rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(artifact.data)
        written.append(dest)
    return written
