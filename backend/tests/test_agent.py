"""
The routes for AI agents (routers/agent.py): the guide pages, built from the
dictionary, the README and the validator's own layout, and the public check.
"""

import io
import os
import tarfile

import pytest

from resslab_hub.agent import guide
from resslab_hub.config import settings
from resslab_hub.data.uploader import README_DATABASES, Type, upload_one
from resslab_hub.models.database.brace import Brace
from resslab_hub.routers import agent
from resslab_hub.utils.rate_limit import limiter
from tests.conftest import write_main_csv


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(settings, "contributions_enabled", True)
    agent._values_cache.clear()
    yield
    agent._values_cache.clear()


BRACES_README = """# Steel braces database

Cyclic and monotonic tests on steel braces.

## Specimen identifier

```text
# not a heading
{Investigator(s)}_{specimen_ID}
```
"""

BRACES_DICTIONARY = (
    "column_name,description,symbol,unit,type,example_value,nullable,group\n"
    "id,Unique identifier,,-,String,B1,False,Experimental program details\n"
    "cross_section_shape,Shape | family,,-,String,HSS,False,Section\n"
    "area,Cross-section area,A,mm2,DecimalFloat,120.5,True,Section properties\n"
)


def _seed_guide(tmp_path):
    folder = tmp_path / "braces"
    folder.mkdir()
    (folder / "README.md").write_text(BRACES_README, encoding="utf-8")
    upload_one(Type.README, str(folder / "README.md"))
    dictionary = folder / "steel_braces_data_dictionary.csv"
    dictionary.write_text(BRACES_DICTIONARY, encoding="utf-8")
    upload_one(Type.DICTIONARY, str(dictionary))
    rows = [
        {
            "id": f"B{i}",
            "area": str(10 + i),
            "cross_section_shape": "HSS" if i < 15 else "Wide Flange",
        }
        for i in range(20)
    ]
    data = tmp_path / "steel_braces.csv"
    write_main_csv(data, Brace, rows)
    upload_one(Type.BRACE, str(data))


def _archive(tmp_path, rows, arcname="braces/steel_braces.csv") -> bytes:
    csv_path = tmp_path / "upload.csv"
    write_main_csv(csv_path, Brace, rows)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(csv_path, arcname=arcname)
    return buffer.getvalue()


def _file(content: bytes):
    return {"file": ("submission.tar.gz", content, "application/gzip")}


# --- The guide, without a database -----------------------------------------


def test_every_database_has_a_layout():
    # The agent map must cover every database the uploader knows, and agree
    # with it on the folder.
    assert set(guide.DATABASE_TYPES) == set(README_DATABASES.values())
    for folder, database in README_DATABASES.items():
        assert guide.layout(database).folder == folder


def test_layout_comes_from_the_validator():
    braces = guide.layout("braces")
    assert braces.primary_csv == "braces/steel_braces.csv"
    assert [r.folder for r in braces.responses] == ["braces/force_displacement"]
    assert braces.responses[0].columns == ("Displacement [mm]", "Force [kN]")
    # EBF names its response files after the id with a prefix.
    assert guide.layout("ebf").responses[0].file_name == "id<id>.csv"


def test_readme_headings_go_two_levels_down_outside_code():
    demoted = guide._demote(BRACES_README)
    assert "### Steel braces database" in demoted
    assert "#### Specimen identifier" in demoted
    assert "\n# not a heading\n" in demoted


def test_readme_title_and_summary():
    assert guide.readme_title(BRACES_README, "braces") == "Steel braces"
    assert guide.readme_title(None, "braces") == "braces"
    assert guide.readme_summary(BRACES_README) == (
        "Cyclic and monotonic tests on steel braces."
    )


def test_the_method_has_no_placeholder_left():
    urls = guide.Urls(site="https://hub.test", api="https://hub.test/api")
    page = guide.render_index(urls, {})
    assert "$" not in page
    assert "https://hub.test/api/agent/validate?database=<database>" in page
    assert "https://hub.test/contribute/new" in page


# --- GET /agent/guide -------------------------------------------------------


async def test_index_lists_the_databases(client, tmp_path):
    _seed_guide(tmp_path)
    response = await client.get("/agent/guide")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    page = response.text
    assert "| Steel braces | `braces` | Cyclic and monotonic tests" in page
    assert "/agent/guide/braces" in page
    assert "## How to work" in page


async def test_database_page_has_everything(client, tmp_path):
    _seed_guide(tmp_path)
    response = await client.get("/agent/guide/braces")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    page = response.text
    # The method, with this database filled in.
    assert "## How to work" in page
    assert "/agent/validate?database=braces" in page
    assert "tar -czf submission.tar.gz braces" in page
    # The layout, from the validator.
    assert "braces/steel_braces.csv" in page
    assert "`Displacement [mm]`, `Force [kN]`" in page
    # The README, under our own headings.
    assert "### Steel braces database" in page
    # The dictionary, with what the hub holds now.
    assert "| `area` | Cross-section area | mm2 | DecimalFloat | no | 120.5 |" in page
    assert "10 to 29 (20 values)" in page
    assert "Shape \\| family" in page
    assert "`HSS`, `Wide Flange`" in page
    assert "`B1`" not in page  # ids are never listed


async def test_database_page_works_without_readme_and_data(client):
    response = await client.get("/agent/guide/cyclic")
    assert response.status_code == 200
    assert "material/cyclic_coupons/stress_strain" in response.text
    assert "no contributor guide yet" in response.text


async def test_unknown_database_is_404(client):
    response = await client.get("/agent/guide/bridges")
    assert response.status_code == 404
    assert "braces" in response.json()["detail"]


async def test_agent_routes_follow_the_contributions_switch(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "contributions_enabled", False)
    assert (await client.get("/agent/guide")).status_code == 404
    assert (await client.get("/agent/guide/braces")).status_code == 404
    response = await client.post(
        "/agent/validate",
        params={"database": "braces"},
        files=_file(_archive(tmp_path, [{"id": "N1"}])),
    )
    assert response.status_code == 404


# --- POST /agent/validate ---------------------------------------------------


async def test_validate_needs_no_account(client, tmp_path):
    response = await client.post(
        "/agent/validate",
        params={"database": "braces"},
        files=_file(_archive(tmp_path, [{"id": "N1"}, {"id": "N2"}])),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["results"][0]["path"] == "braces/steel_braces.csv"
    # The legacy arrays are for the data-repo CI only.
    assert "error_results" not in body
    assert "valid_results" not in body


async def test_validate_reports_errors_and_existing_ids(client, tmp_path):
    _seed_guide(tmp_path)
    response = await client.post(
        "/agent/validate",
        params={"database": "braces"},
        files=_file(
            _archive(tmp_path, [{"id": "B1"}, {"id": "N2", "date": "2025-13-45"}])
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    errors = body["results"][0]["errors"]
    assert any(e["column"] == "date" and e["row"] == 2 for e in errors)
    assert any(e["column"] == "id" and e["value"] == "B1" for e in errors)


async def test_validate_refuses_an_archive_with_the_wrong_root(client, tmp_path):
    # `tar -czf x.tar.gz output` puts everything under output/: the validator
    # finds no file, which must not read as a pass.
    response = await client.post(
        "/agent/validate",
        params={"database": "braces"},
        files=_file(
            _archive(tmp_path, [{"id": "N1"}], arcname="output/braces/steel_braces.csv")
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["error_count"] == 1
    assert (
        "No file found at braces/steel_braces.csv"
        in (body["results"][0]["errors"][0]["message"])
    )


async def test_validate_unknown_database_is_422(client, tmp_path):
    response = await client.post(
        "/agent/validate",
        params={"database": "bridges"},
        files=_file(_archive(tmp_path, [{"id": "N1"}])),
    )
    assert response.status_code == 422


async def test_validate_is_capped_at_10_mb(client):
    response = await client.post(
        "/agent/validate",
        params={"database": "braces"},
        files=_file(os.urandom(agent.MAX_AGENT_BYTES + 1)),
    )
    assert response.status_code == 413


async def test_validate_runs_one_check_at_a_time(client, tmp_path):
    async with agent._validation_lock:
        response = await client.post(
            "/agent/validate",
            params={"database": "braces"},
            files=_file(_archive(tmp_path, [{"id": "N1"}])),
        )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "5"
