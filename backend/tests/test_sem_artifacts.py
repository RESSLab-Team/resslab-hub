"""Pure-unit tests for the SEM conversion (no database, no S3).

OpenCV, Pillow and exifread live in the optional ``sem`` dependency group (the
artifacts are precomputed by hand, not at run time), so these skip where it is
absent — as in CI, which syncs without that group.
"""

import json

import pytest

pytest.importorskip("cv2")
pytest.importorskip("PIL")

from PIL import Image  # noqa: E402

from resslab_hub.sem.artifacts import (  # noqa: E402
    build_specimen_artifacts,
    count_dimple_files,
    parse_filename,
    read_manifest,
    surface_subpath,
)


class TestParseFilename:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("global.tif", ("global", None, 1)),
            ("global_2.tif", ("global", None, 2)),
            ("north_250.tif", ("north", 250, 1)),
            ("north_250_2.tif", ("north", 250, 2)),
            ("NORTH_2000.tif", ("north", 2000, 1)),
            ("notes.txt", None),
            ("north.tif", None),
            ("global.webp", None),
        ],
    )
    def test_reads_the_convention(self, name, expected):
        assert parse_filename(name) == expected

    def test_surface_one_stays_flat(self):
        assert surface_subpath(1) == ""
        assert surface_subpath(2) == "s2/"


def _write_tif(path, size=(8, 8)):
    """A tiny grayscale TIF with no EXIF pixel size."""
    Image.new("L", size, color=128).save(path, format="tiff")


class TestBuildSpecimenArtifacts:
    def test_converts_each_surface_into_its_own_folder(self, tmp_path):
        _write_tif(tmp_path / "global.tif")
        _write_tif(tmp_path / "global_2.tif")
        _write_tif(tmp_path / "north_250.tif")
        _write_tif(tmp_path / "north_250_2.tif")

        artifacts = build_specimen_artifacts(
            sorted(tmp_path.glob("*.tif")), log=lambda _: None
        )

        paths = {a.rel_path for a in artifacts}
        assert {"global.webp", "north_250.webp"} <= paths
        assert {"s2/global.webp", "s2/north_250.webp"} <= paths
        assert {"s2/dimples_all.json", "dimples_all.json", "manifest.json"} <= paths

    def test_the_manifest_describes_what_exists(self, tmp_path):
        _write_tif(tmp_path / "global.tif")
        _write_tif(tmp_path / "north_250.tif")
        _write_tif(tmp_path / "south_2000_2.tif")

        artifacts = build_specimen_artifacts(
            sorted(tmp_path.glob("*.tif")), log=lambda _: None
        )

        manifest = read_manifest(artifacts)
        assert manifest["surfaces"] == 2
        assert manifest["locations"] == ["north", "south"]
        assert manifest["magnifications"] == [250, 2000]

    def test_warns_and_converts_when_the_pixel_size_is_missing(self, tmp_path):
        """No EXIF tag 0x8546 means no dimples, but the image still converts."""
        _write_tif(tmp_path / "north_250.tif")
        messages = []

        artifacts = build_specimen_artifacts(
            [tmp_path / "north_250.tif"], log=messages.append
        )

        assert any("no pixel size" in m for m in messages)
        assert "north_250.webp" in {a.rel_path for a in artifacts}
        assert count_dimple_files(artifacts) == 0
        pooled = next(a for a in artifacts if a.rel_path == "dimples_all.json")
        assert json.loads(pooled.data) == []

    def test_skips_an_unknown_name(self, tmp_path):
        _write_tif(tmp_path / "north_250.tif")
        (tmp_path / "notes.tif").write_bytes(b"not an image")
        messages = []

        artifacts = build_specimen_artifacts(
            sorted(tmp_path.glob("*.tif")), log=messages.append
        )

        assert any("unrecognized name" in m for m in messages)
        assert "north_250.webp" in {a.rel_path for a in artifacts}

    def test_nothing_recognized_gives_nothing(self, tmp_path):
        (tmp_path / "notes.tif").write_bytes(b"not an image")

        assert (
            build_specimen_artifacts([tmp_path / "notes.tif"], log=lambda _: None) == []
        )

    def test_the_webps_carry_their_content_type(self, tmp_path):
        _write_tif(tmp_path / "global.tif")

        artifacts = build_specimen_artifacts(
            [tmp_path / "global.tif"], log=lambda _: None
        )

        webp = next(a for a in artifacts if a.rel_path == "global.webp")
        assert webp.content_type == "image/webp"
        assert webp.data[:4] == b"RIFF"
