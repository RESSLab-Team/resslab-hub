"""Review 04 (pipeline input): proofs through the real app, over ASGI.

No database and no network: the requests go straight into the ASGI app, with
the machine credential where a caller is needed (``require_service`` compares
it with no database). The validator's database checks fail softly.
Each test states what the code should do and is ``xfail(strict=True)`` until
the finding is fixed. Findings: docs/review/findings/04-pipeline-input.md
"""

import asyncio
import io
import tarfile
import time

import httpx
import pytest

from resslab_hub.main import app
from resslab_hub.models.database.brace import Brace
from tests.conftest import SERVICE_AUTH, write_main_csv


def _targz(members: dict, fmt=tarfile.PAX_FORMAT) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", format=fmt) as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _primary(tmp_path) -> bytes:
    file_path = tmp_path / "steel_braces.csv"
    write_main_csv(file_path, Brace, [{"id": "B1"}])
    return file_path.read_bytes()


def _client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def _validate(client, archive: bytes):
    return await client.post(
        "/validate",
        params={"type": "all-braces"},
        files={"file": ("batch.tar.gz", archive, "application/gzip")},
        auth=SERVICE_AUTH,
    )


# --- 04-3: the body is read before the caller is known -----------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-3")
async def test_body_is_not_read_before_the_auth_check():
    """No credential: the answer is 401, but the whole body is read first."""
    head = (
        b'--x\r\nContent-Disposition: form-data; name="file"; '
        b'filename="a.tar.gz"\r\nContent-Type: application/gzip\r\n\r\n'
    )
    chunk = b"\0" * 2**20
    parts = [head] + [chunk] * 20 + [b"\r\n--x--\r\n"]
    consumed = 0
    status = {}

    async def receive():
        nonlocal consumed
        if not parts:
            return {"type": "http.disconnect"}
        body = parts.pop(0)
        consumed += len(body)
        return {"type": "http.request", "body": body, "more_body": bool(parts)}

    async def send(message):
        if message["type"] == "http.response.start":
            status["code"] = message["status"]

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/validate",
        "raw_path": b"/validate",
        "query_string": b"type=all-braces",
        "root_path": "",
        # Chunked: no Content-Length, so enforce_request_size has nothing to read.
        "headers": [
            (b"host", b"test"),
            (b"content-type", b"multipart/form-data; boundary=x"),
            (b"transfer-encoding", b"chunked"),
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("test", 80),
    }
    await app(scope, receive, send)

    assert status["code"] in (401, 403)
    assert consumed < 2**20, f"{consumed / 2**20:.0f} MB read before the 401"


# --- 04-4: a validation stops every other request ----------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-4")
async def test_event_loop_keeps_running_during_a_validation(tmp_path):
    """An 8 MB curve file (22 kB gzipped): the loop must not stop meanwhile."""
    curve = b"Displacement [mm],Force [kN]\n" + b"0.001650,190.822911\n" * 440_000
    archive = _targz(
        {
            "braces/steel_braces.csv": _primary(tmp_path),
            "braces/force_displacement/B1.csv": curve,
        }
    )
    gaps = []
    done = asyncio.Event()

    async def ticker():
        # Stands for any other request: its handler is a task on the same loop.
        last = time.monotonic()
        while not done.is_set():
            await asyncio.sleep(0.01)
            now = time.monotonic()
            gaps.append(now - last)
            last = now

    async with _client() as client:
        tick = asyncio.create_task(ticker())
        response = await _validate(client, archive)
        done.set()
        await tick

    assert response.status_code == 200, response.text
    # A free loop ticks every 10 ms. Today: 0.7 s here.
    assert max(gaps) < 0.2, (
        f"the loop stopped for {max(gaps):.1f} s ({len(archive)} B uploaded)"
    )


# --- 04-7: a member name that is not UTF-8 -----------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-7")
async def test_member_name_not_utf8_is_a_report_not_a_500(tmp_path):
    name = b"braces/force_displacement/\xff.csv".decode("utf-8", "surrogateescape")
    archive = _targz(
        {
            "braces/steel_braces.csv": _primary(tmp_path),
            name: b"Displacement [mm],Force [kN]\n0,0\n",
        },
        fmt=tarfile.GNU_FORMAT,
    )
    async with _client() as client:
        response = await _validate(client, archive)

    assert response.status_code in (200, 400), response.status_code
