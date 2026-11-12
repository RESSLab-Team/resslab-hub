"""
API round-trip tests: upload a fixture through the uploader, then read it back
through the REST endpoints and assert the rows/filters/series come back exactly
as uploaded.

Assertions are deliberately format-agnostic (numbers coerced with ``float``, ids
compared as strings, set membership rather than ordering) so they pin data
behaviour rather than the exact JSON serialization, which lets them survive the
backend framework upgrade on later branches.
"""

import io
import tarfile

import pytest

from resslab_hub.data.uploader import Type, upload_one
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.material import Material
from tests.conftest import SERVICE_AUTH, write_main_csv, write_measurement_csv


def _seed_braces(tmp_path):
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(
        csv_path,
        Brace,
        [
            {
                "id": "B1",
                "cross_section_shape": "HSS",
                "investigator": "Alice",
                "f_yn": "355",
            },
            {
                "id": "B2",
                "cross_section_shape": "Wide Flange",
                "investigator": "Bob",
                "f_yn": "460",
            },
        ],
    )
    upload_one(Type.BRACE, str(csv_path))

    measurement = tmp_path / "B1.csv"
    write_measurement_csv(
        measurement,
        ["Displacement [mm]", "Force [kN]"],
        [["0.0", "0.0"], ["1.0", "12.0"], ["2.0", "24.0"]],
    )
    upload_one(Type.BRACE_DISPLACEMENT, str(measurement))


def _seed_materials(tmp_path):
    csv_path = tmp_path / "steel_material.csv"
    write_main_csv(
        csv_path,
        Material,
        [
            {"id": "M1", "grade": "S355", "investigator": "Alice"},
            {"id": "M2", "grade": "S460", "investigator": "Bob"},
        ],
    )
    upload_one(Type.MATERIAL, str(csv_path))


# ---------------------------------------------------------------------------
# Braces
# ---------------------------------------------------------------------------
async def test_braces_list_pagination_envelope(client, tmp_path):
    _seed_braces(tmp_path)
    response = await client.get("/braces")
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"items", "total", "page", "size", "pages"}
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {"B1", "B2"}


async def test_braces_query_filters_rows(client, tmp_path):
    _seed_braces(tmp_path)
    response = await client.get("/braces", params={"query": "cross_section_shape:HSS"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == ["B1"]


@pytest.mark.parametrize(
    "params",
    [
        {"sort_by": "nope"},
        {"sort_by": "__class__", "sort_desc": "false"},
        {"query": "nope:1"},
        {"query": "metadata:1"},
        {"query": "f_yn:abc"},
        {"query": "f_yn:1<<x"},
        {"query": "f_yn:>x"},
        {"query": "date:1990,x"},
    ],
)
async def test_braces_bad_query_or_sort_answers_400(client, tmp_path, params):
    # An unknown key or a value that does not parse is the caller's mistake,
    # not a server error (#264 M7).
    _seed_braces(tmp_path)
    response = await client.get("/braces", params=params)
    assert response.status_code == 400
    assert "detail" in response.json()


async def test_braces_query_value_with_colon(client, tmp_path):
    # Only the first ":" splits the key from the value (#265).
    _seed_braces(tmp_path)
    response = await client.get("/braces", params={"query": "investigator:a:b"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_braces_query_typed_list_and_compare(client, tmp_path):
    _seed_braces(tmp_path)
    # A number list on a float column, and `>` on it, compare as numbers.
    response = await client.get("/braces", params={"query": "f_yn:355,1"})
    assert [item["id"] for item in response.json()["items"]] == ["B1"]
    response = await client.get("/braces", params={"query": "f_yn:>400.5"})
    assert [item["id"] for item in response.json()["items"]] == ["B2"]
    response = await client.get("/braces", params={"query": "displacement_count:>0"})
    assert response.status_code == 200
    response = await client.get(
        "/braces", params={"sort_by": "f_yn", "sort_desc": "true"}
    )
    assert [item["id"] for item in response.json()["items"]] == ["B2", "B1"]


async def test_braces_counts_group_by_field(client, tmp_path):
    _seed_braces(tmp_path)
    response = await client.get("/braces/counts", params={"fields": "investigator"})
    assert response.status_code == 200
    counts = {tuple(row["names"]): row["value"] for row in response.json()}
    assert counts == {("Alice",): 1, ("Bob",): 1}


async def test_braces_distinct(client, tmp_path):
    _seed_braces(tmp_path)
    response = await client.get(
        "/braces/distinct", params={"fields": "cross_section_shape"}
    )
    assert response.status_code == 200
    assert response.json() == 2


async def test_braces_range(client, tmp_path):
    _seed_braces(tmp_path)
    response = await client.get("/braces/range", params={"field": "f_yn"})
    assert response.status_code == 200
    body = response.json()
    assert float(body["min"]) == 355.0
    assert float(body["max"]) == 460.0


async def test_braces_csv_headers_and_rows(client, tmp_path):
    _seed_braces(tmp_path)
    response = await client.get("/braces/csv", params={"ids": ["B1", "B2"]})
    assert response.status_code == 200
    lines = [line for line in response.text.splitlines() if line]
    assert "id" in lines[0].split(",")
    assert len(lines) - 1 == 2  # two data rows beyond the header


async def test_braces_page_carries_the_not_reported_list(client, tmp_path):
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(csv_path, Brace, [{"id": "B1", "area": "NR", "b_br": "NA"}])
    upload_one(Type.BRACE, str(csv_path))
    response = await client.get("/braces")
    assert response.json()["items"][0]["not_reported"] == ["area"]


async def test_braces_csv_writes_nr_and_na_like_the_source(client, tmp_path):
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(csv_path, Brace, [{"id": "B1", "area": "NR", "b_br": "NA"}])
    upload_one(Type.BRACE, str(csv_path))
    response = await client.get("/braces/csv", params={"ids": ["B1"]})
    header, row = [line for line in response.text.splitlines() if line]
    cells = dict(zip(header.split(","), row.split(",")))
    assert "not_reported" not in cells
    assert cells["area"] == "NR"
    assert cells["b_br"] == "NA"


async def test_braces_displacement_series(client, tmp_path):
    _seed_braces(tmp_path)
    response = await client.get("/braces/B1/displacement")
    assert response.status_code == 200
    series = response.json()
    assert [[float(d), float(f)] for d, f in series] == [
        [0.0, 0.0],
        [1.0, 12.0],
        [2.0, 24.0],
    ]


# ---------------------------------------------------------------------------
# Materials (second family + the Date column path)
# ---------------------------------------------------------------------------
async def test_materials_list_and_filter(client, tmp_path):
    _seed_materials(tmp_path)

    response = await client.get("/materials")
    assert response.status_code == 200
    assert response.json()["total"] == 2

    filtered = await client.get("/materials", params={"query": "grade:S355"})
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "M1"


async def test_materials_date_range(client, tmp_path):
    _seed_materials(tmp_path)
    response = await client.get("/materials/date-range", params={"field": "date"})
    assert response.status_code == 200
    body = response.json()
    # Both fixture rows default to 01.01.2020.
    assert body["min"] == "2020-01-01"
    assert body["max"] == "2020-01-01"


# ---------------------------------------------------------------------------
# /validate — structured response + archive hardening
#
# These calls carry the machine credential, which is how the data repository's
# validation workflow reaches this endpoint. The contributor's way in (a
# session cookie) is covered in test_auth_flow.py.
# ---------------------------------------------------------------------------
def _braces_targz(tmp_path, rows) -> bytes:
    """A gzipped tar holding only the primary braces CSV (no DB needed)."""
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(csv_path, Brace, rows)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(csv_path, arcname="braces/steel_braces.csv")
    return buffer.getvalue()


def _upload(field_bytes, filename="c.tar.gz"):
    return {"file": (filename, field_bytes, "application/gzip")}


async def test_validate_valid_archive_returns_200_structured(client, tmp_path):
    archive = _braces_targz(tmp_path, [{"id": "B1"}, {"id": "B2"}])
    response = await client.post(
        "/validate",
        params={"type": "all-braces"},
        files=_upload(archive),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["error_count"] == 0
    # Structured results carry the archive-relative path.
    assert len(body["results"]) == 1
    assert body["results"][0]["path"] == "braces/steel_braces.csv"
    assert body["results"][0]["valid"] is True
    # Legacy arrays are still present for the data-repo CI.
    assert "error_results" in body and "valid_results" in body


async def test_validate_with_trailing_slash_answers_json(client, tmp_path):
    # The data CI called /validate/ for a long time. A redirect would lose the
    # /api prefix behind Traefik and land on nginx (an HTML 405), so the slash
    # must be served directly.
    archive = _braces_targz(tmp_path, [{"id": "B1"}])
    response = await client.post(
        "/validate/",
        params={"type": "all-braces"},
        files=_upload(archive),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


async def test_validate_unhandled_error_answers_json(tmp_path):
    # An error outside the route's own try (here a dependency) must still be
    # JSON, with a fixed message, never Starlette's plain text 500.
    import httpx

    from resslab_hub.main import app
    from resslab_hub.routers.root import enforce_request_size

    def broken():
        raise RuntimeError("secret detail")

    app.dependency_overrides[enforce_request_size] = broken
    try:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/validate",
                params={"type": "all-braces"},
                files=_upload(_braces_targz(tmp_path, [{"id": "B1"}])),
                auth=SERVICE_AUTH,
            )
    finally:
        app.dependency_overrides.pop(enforce_request_size, None)
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


@pytest.mark.parametrize("route", ["/validate", "/upload"])
async def test_oversized_body_without_content_length_answers_413(
    tmp_path, monkeypatch, route
):
    # A chunked body has no Content-Length, so only the parsed file size can
    # stop it (#264 M3). The header check is skipped here to play that client.
    import httpx

    from resslab_hub.main import app
    from resslab_hub.routers import root

    monkeypatch.setattr(root, "MAX_REQUEST_BYTES", 100)
    app.dependency_overrides[root.enforce_request_size] = lambda: None
    try:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                route,
                params={"type": "all-braces"},
                files=_upload(_braces_targz(tmp_path, [{"id": "B1"}])),
                auth=SERVICE_AUTH,
            )
    finally:
        app.dependency_overrides.pop(root.enforce_request_size, None)
    assert response.status_code == 413
    assert response.json() == {"detail": "Upload exceeds the maximum allowed size."}


async def test_validate_invalid_data_is_200_with_structured_issue(client, tmp_path):
    # 'area' is a Float column; a non-numeric value is a data error, not a
    # transport error, so it comes back as 200 valid=false.
    archive = _braces_targz(tmp_path, [{"id": "B1", "area": "not-a-number"}])
    response = await client.post(
        "/validate",
        params={"type": "all-braces"},
        files=_upload(archive),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["error_count"] >= 1
    issues = body["results"][0]["errors"]
    assert any(issue["column"] == "area" and issue["row"] == 1 for issue in issues)


async def test_validate_rejects_path_traversal(client, tmp_path):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="../evil.csv")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"x"))
    response = await client.post(
        "/validate",
        params={"type": "all-braces"},
        files=_upload(buffer.getvalue()),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 400


async def test_validate_rejects_non_archive(client, tmp_path):
    response = await client.post(
        "/validate",
        params={"type": "all-braces"},
        files=_upload(b"not a tar"),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 400


async def test_validate_ignores_dictionary_files(client, tmp_path):
    # Data-repo CI archives contain the dictionary CSV alongside the data; it
    # must be skipped, not validated (there is no validator for it).
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(csv_path, Brace, [{"id": "B1"}])
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(csv_path, arcname="braces/steel_braces.csv")
        dictionary = (
            b"column_name,description,symbol,unit,type,example_value,nullable\n"
        )
        info = tarfile.TarInfo(name="braces/steel_braces_data_dictionary.csv")
        info.size = len(dictionary)
        tar.addfile(info, io.BytesIO(dictionary))
    response = await client.post(
        "/validate",
        params={"type": "all-braces"},
        files=_upload(buffer.getvalue()),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert [entry["path"] for entry in body["results"]] == ["braces/steel_braces.csv"]


async def test_validate_surfaces_range_warnings(client, tmp_path):
    # Seed enough braces that "the norm" is established, then validate an
    # outlier: it must warn (far outside the range) while remaining valid.
    seed_path = tmp_path / "seed.csv"
    write_main_csv(
        seed_path,
        Brace,
        [{"id": f"B{i}", "area": str(10 + i)} for i in range(20)],
    )
    upload_one(Type.BRACE, str(seed_path))

    archive = _braces_targz(tmp_path, [{"id": "NEW", "area": "10000"}])
    response = await client.post(
        "/validate",
        params={"type": "all-braces"},
        files=_upload(archive),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    warnings = body["results"][0]["warnings"]
    assert any(
        w["column"] == "area" and "Far outside" in w["message"] for w in warnings
    )
    # Legacy arrays still carry the same information for the data-repo CI.
    assert any("Far outside" in w for w in body["valid_results"][0]["warnings"])


async def test_readme_endpoint_serves_uploaded_markdown(client, tmp_path):
    from resslab_hub.data.uploader import upload_one as upload

    folder = tmp_path / "residual_stresses"
    folder.mkdir()
    (folder / "README.md").write_text("# Residual stresses\n", encoding="utf-8")
    upload(Type.README, str(folder / "README.md"))

    response = await client.get("/dictionary/residuals/readme")
    assert response.status_code == 200
    assert response.json() == {
        "database": "residuals",
        "content": "# Residual stresses\n",
    }


async def test_readme_endpoint_404_when_missing(client):
    response = await client.get("/dictionary/braces/readme")
    assert response.status_code == 404


async def test_validate_ignores_readme_files(client, tmp_path):
    # Data-repo archives carry the folder README next to the CSVs; like the
    # dictionary it is metadata, not data, and must not reach the validator.
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(csv_path, Brace, [{"id": "B1"}])
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(csv_path, arcname="braces/steel_braces.csv")
        readme = b"# Braces\n"
        info = tarfile.TarInfo(name="braces/README.md")
        info.size = len(readme)
        tar.addfile(info, io.BytesIO(readme))
    response = await client.post(
        "/validate",
        params={"type": "all-braces"},
        files=_upload(buffer.getvalue()),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


# ---------------------------------------------------------------------------
# /dictionary
# ---------------------------------------------------------------------------
async def test_dictionary_endpoint_groups_by_database(client, tmp_path):
    from resslab_hub.data.uploader import upload_one as upload

    file_path = tmp_path / "steel_braces_data_dictionary.csv"
    file_path.write_text(
        "column_name,description,symbol,unit,type,example_value,nullable,group\n"
        "id,Unique identifier,,-,String,B1,False,Experimental program details\n"
        "area,Cross-section area,A,mm2,DecimalFloat,120.5,True,Section properties\n",
        encoding="utf-8",
    )
    upload(Type.DICTIONARY, str(file_path))

    response = await client.get("/dictionary")
    assert response.status_code == 200
    body = response.json()
    assert body["braces"] == [
        {
            "name": "id",
            "description": "Unique identifier",
            "symbol": "",
            "unit": "-",
            "type": "String",
            "example": "B1",
            "nullable": False,
            "group": "Experimental program details",
        },
        {
            "name": "area",
            "description": "Cross-section area",
            "symbol": "A",
            "unit": "mm2",
            "type": "DecimalFloat",
            "example": "120.5",
            "nullable": True,
            "group": "Section properties",
        },
    ]


# ---------------------------------------------------------------------------
# /upload: 200 when every file went in, 422 with the failed paths (#405)
# ---------------------------------------------------------------------------
def _braces_with_curves_targz(tmp_path, ids, curves) -> bytes:
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(csv_path, Brace, [{"id": i} for i in ids])
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(csv_path, arcname="braces/steel_braces.csv")
        for curve_id in curves:
            curve = write_measurement_csv(
                tmp_path / f"{curve_id}.csv",
                ["Displacement [mm]", "Force [kN]"],
                [["0.0", "0.0"]],
            )
            tar.add(curve, arcname=f"braces/force_displacement/{curve_id}.csv")
    return buffer.getvalue()


async def test_upload_answers_200_when_every_file_went_in(client, tmp_path):
    archive = _braces_with_curves_targz(tmp_path, ["B1"], ["B1"])
    response = await client.post(
        "/upload",
        params={"type": "all-braces"},
        files=_upload(archive),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Upload successful"
    assert len(body["uploads"]) == 2
    assert "failed" not in body


async def test_upload_answers_422_with_the_failed_paths(client, tmp_path):
    # X has no main row, so its curve breaks the foreign key.
    archive = _braces_with_curves_targz(tmp_path, ["B1"], ["B1", "X"])
    response = await client.post(
        "/upload",
        params={"type": "all-braces"},
        files=_upload(archive),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["failed"] == ["braces/force_displacement/X.csv"]
    # The good files are still in, and no error text leaks out.
    assert len(body["uploads"]) == 2
    assert not [m for m in body["uploads"] if "Skipping" in m]

    series = await client.get("/braces/B1/displacement")
    assert series.status_code == 200
    assert series.json() == [[0.0, 0.0]]
