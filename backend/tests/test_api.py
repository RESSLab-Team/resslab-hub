"""
API round-trip tests: upload a fixture through the uploader, then read it back
through the REST endpoints and assert the rows/filters/series come back exactly
as uploaded.

Assertions are deliberately format-agnostic (numbers coerced with ``float``, ids
compared as strings, set membership rather than ordering) so they pin data
behaviour rather than the exact JSON serialization, which lets them survive the
backend framework upgrade on later branches.
"""
from resslab_hub.data.uploader import Type, upload_one
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.material import Material
from tests.conftest import write_main_csv, write_measurement_csv


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
    # Both fixture rows default to 01.01.20 -> 2020-01-01.
    assert body["min"] == "2020-01-01"
    assert body["max"] == "2020-01-01"
