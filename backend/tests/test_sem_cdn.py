"""Where the SEM artifacts go: local folder or CDN keys (no database, no S3).

These run in CI. resslab_hub.sem.cdn takes its Artifact type from
resslab_hub.sem.models (no OpenCV, no Pillow) and imports the enacit4r-files
library only inside make_s3_service, so nothing here needs the ``sem``
dependency group.
"""

import json
from types import SimpleNamespace

import pytest

from resslab_hub.sem.cdn import (
    CdnConfig,
    CdnNotConfigured,
    s3_folder_and_name,
    upload_artifacts,
    write_artifacts,
)
from resslab_hub.sem.models import (
    JSON_CONTENT_TYPE,
    WEBP_CONTENT_TYPE,
    Artifact,
)

SPECIMEN = "Ozden_et_al_CNT_C_R0_5_C2"

ARTIFACTS = [
    Artifact("global.webp", b"webp-1", WEBP_CONTENT_TYPE),
    Artifact("s2/north_250.webp", b"webp-2", WEBP_CONTENT_TYPE),
    Artifact("s2/dimples_all.json", b"[1.0]", JSON_CONTENT_TYPE),
    Artifact("manifest.json", b'{"surfaces": 2}', JSON_CONTENT_TYPE),
]

FULL_SETTINGS = dict(
    s3_endpoint_protocol="https://",
    s3_endpoint_hostname="s3.epfl.ch",
    s3_region="EU",
    s3_bucket="10208-abc",
    s3_path_prefix="resslab-hub/sem",
    s3_access_key_id="key",
    s3_secret_access_key="secret",
)


class FakeS3:
    """Stands in for enacit4r-files' S3Service.upload_file."""

    def __init__(self):
        self.calls = []

    async def upload_file(self, upload_file, s3_folder=""):
        self.calls.append(
            (
                s3_folder,
                upload_file.filename,
                upload_file.content_type,
                upload_file.file.read(),
            )
        )


class TestUploadArtifacts:
    async def test_builds_the_cdn_key_layout(self):
        """The frontend reads <prefix>/<id>/[s2/]<name>, so the surface folder
        goes in s3_folder and the bare name in the filename."""
        s3 = FakeS3()

        count = await upload_artifacts(s3, SPECIMEN, ARTIFACTS)

        assert count == 4
        assert sorted(c[:3] for c in s3.calls) == sorted(
            [
                (SPECIMEN, "global.webp", "image/webp"),
                (f"{SPECIMEN}/s2", "north_250.webp", "image/webp"),
                (f"{SPECIMEN}/s2", "dimples_all.json", "application/json"),
                (SPECIMEN, "manifest.json", "application/json"),
            ]
        )

    async def test_sends_the_bytes(self):
        s3 = FakeS3()

        await upload_artifacts(s3, SPECIMEN, ARTIFACTS)

        sent = {(folder, name): body for folder, name, _, body in s3.calls}
        assert sent[(SPECIMEN, "global.webp")] == b"webp-1"
        assert sent[(f"{SPECIMEN}/s2", "north_250.webp")] == b"webp-2"

    async def test_a_failure_propagates(self):
        class Failing(FakeS3):
            async def upload_file(self, upload_file, s3_folder=""):
                raise RuntimeError("BadRequest")

        # The caller must not record the specimen as uploaded.
        with pytest.raises(RuntimeError):
            await upload_artifacts(Failing(), SPECIMEN, ARTIFACTS)


class TestS3FolderAndName:
    @pytest.mark.parametrize(
        "rel_path,folder,name",
        [
            ("global.webp", "id", "global.webp"),
            ("s2/north_250.webp", "id/s2", "north_250.webp"),
            ("manifest.json", "id", "manifest.json"),
        ],
    )
    def test_splits_on_the_last_slash(self, rel_path, folder, name):
        assert s3_folder_and_name("id", rel_path) == (folder, name)


class TestWriteArtifacts:
    def test_writes_the_tree_and_the_bytes(self, tmp_path):
        write_artifacts(tmp_path, ARTIFACTS)

        assert (tmp_path / "global.webp").read_bytes() == b"webp-1"
        assert (tmp_path / "s2" / "north_250.webp").read_bytes() == b"webp-2"
        assert json.loads((tmp_path / "manifest.json").read_text())["surfaces"] == 2

    def test_overwrites_a_previous_run(self, tmp_path):
        write_artifacts(tmp_path, ARTIFACTS)
        write_artifacts(tmp_path, [Artifact("global.webp", b"new", WEBP_CONTENT_TYPE)])

        assert (tmp_path / "global.webp").read_bytes() == b"new"


class TestCdnConfig:
    def test_reads_the_seven_settings(self):
        config = CdnConfig.from_settings(SimpleNamespace(**FULL_SETTINGS))

        assert config.endpoint_url == "https://s3.epfl.ch"
        assert config.bucket == "10208-abc"
        assert config.path_prefix == "resslab-hub/sem"

    def test_names_every_missing_setting(self):
        partial = dict(FULL_SETTINGS, s3_bucket=None, s3_region="")

        with pytest.raises(CdnNotConfigured) as excinfo:
            CdnConfig.from_settings(SimpleNamespace(**partial))

        assert "S3_REGION" in str(excinfo.value)
        assert "S3_BUCKET" in str(excinfo.value)
        assert "S3_ACCESS_KEY_ID" not in str(excinfo.value)
