"""
The overview map: the pure site rules (utils/map_sites.py) and GET /map/sites.
"""

from resslab_hub.data.uploader import Type, upload_one
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.material import Material
from resslab_hub.models.map import MapCategory
from resslab_hub.utils.map_sites import ProgramRow, merge_rows, site_key, usable
from tests.conftest import write_main_csv


def _row(category=MapCategory.braces, lat=46.519, lng=6.567, n=1, **kwargs):
    kwargs.setdefault("program", "Program A")
    kwargs.setdefault("year", 2020)
    kwargs.setdefault("first_id", "X1")
    return ProgramRow(category=category, lat=lat, lng=lng, n=n, **kwargs)


# ---------------------------------------------------------------------------
# Pure rules
# ---------------------------------------------------------------------------
def test_site_key_rounds_to_two_decimals():
    assert site_key(46.519, 6.567) == "46.52,6.57"
    assert site_key(46.517, 6.569) == "46.52,6.57"
    assert site_key(-36.8523, 174.7691) == "-36.85,174.77"


def test_site_key_has_no_negative_zero():
    assert site_key(-0.001, 0.0) == "0.00,0.00"


def test_usable():
    assert usable(46.5, 6.5)
    assert not usable(None, 6.5)
    assert not usable(46.5, None)
    assert not usable(float("nan"), 6.5)
    assert not usable(91.0, 6.5)
    assert not usable(46.5, -181.0)


def test_merge_rows_puts_one_campus_in_one_site():
    sites = merge_rows(
        [
            _row(MapCategory.materials, 46.519, 6.567, n=3, first_id="M2"),
            _row(MapCategory.materials, 46.517, 6.569, n=1, first_id="M1"),
            _row(MapCategory.braces, 35.03, 135.78, n=2),
        ]
    )
    assert [site.sid for site in sites] == ["46.52,6.57", "35.03,135.78"]
    epfl = sites[0]
    assert epfl.n == 4
    # centroid weighted by count
    assert epfl.lat == round((46.519 * 3 + 46.517) / 4, 4)
    assert epfl.lng == round((6.567 * 3 + 6.569) / 4, 4)
    # same category, program and year: one program, the smallest id kept
    assert len(epfl.programs) == 1
    assert epfl.programs[0].n == 4
    assert epfl.programs[0].first_id == "M1"


def test_merge_rows_sums_counts_per_category():
    sites = merge_rows(
        [
            _row(MapCategory.braces, n=2, program="A"),
            _row(MapCategory.braces, n=3, program="B"),
            _row(MapCategory.tensile_coupon, n=5, program="A"),
        ]
    )
    assert len(sites) == 1
    assert sites[0].n == 10
    assert sites[0].counts == {
        MapCategory.braces: 5,
        MapCategory.tensile_coupon: 5,
    }


def test_merge_rows_sorts_programs_biggest_first():
    sites = merge_rows(
        [
            _row(n=1, program="Small"),
            _row(n=7, program="Big"),
            _row(n=3, program="Middle", year=2001),
            _row(n=3, program="Middle", year=1999),
        ]
    )
    programs = [(p.program, p.year) for p in sites[0].programs]
    assert programs == [
        ("Big", 2020),
        ("Middle", 1999),
        ("Middle", 2001),
        ("Small", 2020),
    ]


def test_merge_rows_program_name_falls_back_to_reference_then_dash():
    sites = merge_rows(
        [
            _row(program=None, reference="Smith et al. 2010", n=2),
            _row(program="  ", reference=None, n=1),
        ]
    )
    names = [p.program for p in sites[0].programs]
    assert names == ["Smith et al. 2010", "-"]


def test_merge_rows_ignores_empty_and_unusable_rows():
    sites = merge_rows(
        [
            _row(n=0),
            _row(lat=None, lng=6.5),
            _row(lat=120.0),
        ]
    )
    assert sites == []


# ---------------------------------------------------------------------------
# GET /map/sites
# ---------------------------------------------------------------------------
def _seed(tmp_path):
    braces = tmp_path / "steel_braces.csv"
    write_main_csv(
        braces,
        Brace,
        [
            {
                "id": "B1",
                "investigator": "Alice",
                "date": "2010",
                "boundary_condition": "Pinned",
                "latitude": "46.519",
                "longitude": "6.567",
            },
            {
                "id": "B2",
                "investigator": "Alice",
                "date": "2010",
                "boundary_condition": "Pinned",
                "latitude": "46.517",
                "longitude": "6.569",
            },
            {
                "id": "B3",
                "investigator": "Bob",
                "date": "2015",
                "latitude": "NR",
                "longitude": "NR",
            },
        ],
    )
    upload_one(Type.BRACE, str(braces))

    materials = tmp_path / "steel_material.csv"
    write_main_csv(
        materials,
        Material,
        [
            {
                "id": "M1",
                "experimental_program": "Coupons",
                "date": "01.06.2018",
                "latitude": "46.518",
                "longitude": "6.568",
            },
            {
                "id": "M2",
                "experimental_program": "Kyoto tests",
                "date": "01.06.2012",
                "latitude": "35.03",
                "longitude": "135.78",
            },
        ],
    )
    upload_one(Type.MATERIAL, str(materials))


async def test_map_sites(client, tmp_path):
    _seed(tmp_path)
    response = await client.get("/map/sites")
    assert response.status_code == 200
    body = response.json()

    # B3 has "NR" coordinates, so it is counted but not placed
    assert body["skipped"] == 1
    assert [site["sid"] for site in body["sites"]] == ["46.52,6.57", "35.03,135.78"]

    epfl = body["sites"][0]
    assert epfl["n"] == 3
    assert epfl["counts"] == {"braces": 2, "materials": 1}
    assert epfl["programs"][0] == {
        "category": "braces",
        "program": "Alice",
        "year": 2010,
        "n": 2,
        "reference": "x",
        "link": "x",
        "first_id": "B1",
        "figure": "Pinned",
    }
    coupons = epfl["programs"][1]
    assert coupons["category"] == "materials"
    assert coupons["year"] == 2018
    assert coupons["figure"] is None


async def test_map_sites_empty(client):
    response = await client.get("/map/sites")
    assert response.status_code == 200
    assert response.json() == {"sites": [], "skipped": 0}
