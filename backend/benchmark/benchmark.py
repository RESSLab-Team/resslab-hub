"""
Standalone performance benchmark for the resslab-hub backend.

It runs against a *throwaway* PostgreSQL database (``resslab_hub_bench``) that is
created and dropped around the run, so real data is never touched -- exactly like
the integration-test harness in ``tests/conftest.py``. It measures three layers
independently so a slow number can be attributed to the right place:

  * upload     - rows/second for the bulk ``COPY`` uploader (write path)
  * db         - raw SQL round-trips through the asyncpg engine (pure DB read)
  * api        - full-stack request latency through the ASGI app (DB + ORM +
                 pagination + serialization)

Good-practice timing: every scenario is run for a few *warmup* rounds (to prime
connection pools and query plans) and then many *timed* rounds with
``time.perf_counter``; we report min / median / mean / p95 / max rather than a
single number, because latency is a distribution, not a point.

Prerequisites: a running Postgres (``make dev-database``) reachable with the
credentials in ``secrets/.env``.

Usage (from ``backend/``)::

    make benchmark
    uv run python -m benchmark.benchmark --rows 5000 --rounds 50
    uv run python -m benchmark.benchmark --rows 20000 --rounds 100 --warmup 5
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os
import statistics
import time
from pathlib import Path
from urllib.parse import quote_plus

# ---------------------------------------------------------------------------
# Configure settings BEFORE importing any resslab_hub module: point at a
# throwaway database and disable the startup ``alembic upgrade`` (we build the
# schema from the ORM metadata instead). Mirrors tests/conftest.py.
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_DIR = _BACKEND_DIR.parent

os.environ.setdefault("DOTENV_PATH_FOR_DYNACONF", str(_REPO_DIR / "secrets" / ".env"))
BENCH_DB = os.environ.get("POSTGRES_BENCH_DB", "resslab_hub_bench")
os.environ["POSTGRES_DB"] = BENCH_DB
os.environ["DATABASE_UPGRADE"] = "false"

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.types import Boolean, Date, Integer, Numeric  # noqa: E402

from resslab_hub.config import settings  # noqa: E402
from resslab_hub.utils.database import Base, url  # noqa: E402

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------
class Stats:
    """Summary statistics for a list of per-round durations (seconds)."""

    def __init__(self, label: str, samples: list[float], unit_count: int = 1) -> None:
        self.label = label
        self.samples = sorted(samples)
        self.unit_count = unit_count  # rows processed per round (for throughput)

    @staticmethod
    def _pct(sorted_samples: list[float], pct: float) -> float:
        if not sorted_samples:
            return float("nan")
        k = (len(sorted_samples) - 1) * pct
        lo, hi = int(k), min(int(k) + 1, len(sorted_samples) - 1)
        return sorted_samples[lo] + (sorted_samples[hi] - sorted_samples[lo]) * (k - lo)

    @property
    def median(self) -> float:
        return statistics.median(self.samples)

    def row(self) -> list[str]:
        ms = 1_000.0
        mean = statistics.fmean(self.samples)
        throughput = self.unit_count / self.median if self.median else float("inf")
        return [
            self.label,
            f"{len(self.samples)}",
            f"{self.samples[0] * ms:.2f}",
            f"{self.median * ms:.2f}",
            f"{mean * ms:.2f}",
            f"{self._pct(self.samples, 0.95) * ms:.2f}",
            f"{self.samples[-1] * ms:.2f}",
            f"{throughput:,.0f}" if self.unit_count > 1 else "-",
        ]


def measure(label: str, fn, *, rounds: int, warmup: int, unit_count: int = 1) -> Stats:
    """Time a synchronous callable: ``warmup`` discarded rounds, then ``rounds``."""
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    for _ in range(rounds):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return Stats(label, samples, unit_count)


async def measure_async(
    label: str, coro_fn, *, rounds: int, warmup: int, unit_count: int = 1
) -> Stats:
    """Time an async callable (awaited fresh each round)."""
    for _ in range(warmup):
        await coro_fn()
    samples: list[float] = []
    for _ in range(rounds):
        start = time.perf_counter()
        await coro_fn()
        samples.append(time.perf_counter() - start)
    return Stats(label, samples, unit_count)


def print_table(title: str, rows: list[list[str]]) -> None:
    header = ["scenario", "n", "min", "median", "mean", "p95", "max", "rows/s"]
    widths = [
        max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(len(header))
    ]
    units = ["", "", "ms", "ms", "ms", "ms", "ms", ""]

    def fmt(cells: list[str]) -> str:
        return "  ".join(c.rjust(widths[i]) for i, c in enumerate(cells))

    print(f"\n{title}")
    print(fmt(header))
    print(fmt([("-" * w) for w in widths]))
    for r in rows:
        print(fmt(r))
    print(fmt([u.rjust(widths[i]) for i, u in enumerate(units)]))


# ---------------------------------------------------------------------------
# Throwaway database lifecycle (sync, mirrors tests/conftest.py)
# ---------------------------------------------------------------------------
def _maintenance_url() -> str:
    credential = f"{settings.postgres_user}:{quote_plus(settings.postgres_password)}"
    return (
        f"postgresql://{credential}"
        f"@{settings.postgres_host}:{settings.postgres_port}/postgres"
    )


def create_database() -> None:
    admin = create_engine(_maintenance_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{BENCH_DB}"'))
        conn.execute(text(f'CREATE DATABASE "{BENCH_DB}"'))
    admin.dispose()

    import resslab_hub.main  # noqa: F401  (registers every ORM table on Base)

    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()


def drop_database() -> None:
    admin = create_engine(_maintenance_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :db AND pid <> pg_backend_pid()"
            ),
            {"db": BENCH_DB},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{BENCH_DB}"'))
    admin.dispose()


# ---------------------------------------------------------------------------
# Fixture generation (self-contained; does not depend on the test suite)
# ---------------------------------------------------------------------------
_INVESTIGATORS = ["Alice", "Bob", "Carol", "Dan", "Erin"]
_SHAPES = ["HSS", "Wide Flange", "Angle", "Channel"]


def _default_for(column) -> str:
    column_type = column.type
    if isinstance(column_type, Boolean):
        return "yes"
    if isinstance(column_type, Date):
        return "01.01.20"
    if isinstance(column_type, Integer):
        return "1"
    if isinstance(column_type, Numeric):
        return "1.5"
    return "x"


def write_brace_csv(path: Path, model, rows: int) -> Path:
    """One CSV of ``rows`` brace records with varied filterable columns."""
    columns = [c.key for c in model.__table__.columns]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for i in range(rows):
            overrides = {
                "id": f"B{i:07d}",
                "cross_section_shape": _SHAPES[i % len(_SHAPES)],
                "investigator": _INVESTIGATORS[i % len(_INVESTIGATORS)],
                "f_yn": str(300 + (i % 200)),
            }
            writer.writerow(
                [
                    overrides.get(key, _default_for(model.__table__.c[key]))
                    for key in columns
                ]
            )
    return path


def write_measurement_csv(path: Path, points: int) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Displacement [mm]", "Force [kN]"])
        for i in range(points):
            writer.writerow([f"{i * 0.1:.3f}", f"{i * 1.2:.3f}"])
    return path


# ---------------------------------------------------------------------------
# Benchmark body
# ---------------------------------------------------------------------------
async def run_db_benchmarks(rounds: int, warmup: int) -> list[list[str]]:
    """Raw SQL latency through the same asyncpg engine the app uses."""
    from sqlalchemy import distinct, func, select

    from resslab_hub.models.database.brace import Brace
    from resslab_hub.utils.database import async_session, engine

    rows: list[list[str]] = []

    async def count_all() -> None:
        async with async_session() as session:
            await session.execute(select(func.count()).select_from(Brace))

    async def filtered_page() -> None:
        async with async_session() as session:
            await session.execute(
                select(Brace).where(Brace.cross_section_shape == "HSS").limit(50)
            )

    async def distinct_investigators() -> None:
        async with async_session() as session:
            await session.execute(select(distinct(Brace.investigator)))

    rows.append(
        (await measure_async("db: count(*)", count_all, rounds=rounds, warmup=warmup)).row()
    )
    rows.append(
        (
            await measure_async(
                "db: filtered limit 50", filtered_page, rounds=rounds, warmup=warmup
            )
        ).row()
    )
    rows.append(
        (
            await measure_async(
                "db: distinct investigator",
                distinct_investigators,
                rounds=rounds,
                warmup=warmup,
            )
        ).row()
    )

    await engine.dispose()
    return rows


async def run_api_benchmarks(rounds: int, warmup: int) -> list[list[str]]:
    """Full-stack latency through the ASGI app (in-process, no socket)."""
    import httpx

    from resslab_hub.main import app
    from resslab_hub.utils.database import engine

    transport = httpx.ASGITransport(app=app)
    rows: list[list[str]] = []
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        async def list_page() -> None:
            await client.get("/braces", params={"size": 50})

        async def filtered() -> None:
            await client.get("/braces", params={"query": "cross_section_shape:HSS"})

        async def counts() -> None:
            await client.get("/braces/counts", params={"fields": "investigator"})

        async def distinct() -> None:
            await client.get("/braces/distinct", params={"fields": "cross_section_shape"})

        async def value_range() -> None:
            await client.get("/braces/range", params={"field": "f_yn"})

        scenarios = [
            ("api: GET /braces (page 50)", list_page),
            ("api: GET /braces?query=...", filtered),
            ("api: GET /braces/counts", counts),
            ("api: GET /braces/distinct", distinct),
            ("api: GET /braces/range", value_range),
        ]
        for label, fn in scenarios:
            rows.append(
                (await measure_async(label, fn, rounds=rounds, warmup=warmup)).row()
            )

    await engine.dispose()
    return rows


def run_upload_benchmark(rows: int, tmp_dir: Path, warmup: int) -> Stats:
    """Time a single bulk upload of ``rows`` brace records (COPY write path).

    Upload is destructive (it replaces the table), so we cannot run many timed
    rounds independently; instead we warm up once on a small batch, then time a
    handful of full uploads and report the distribution.
    """
    from resslab_hub.data.uploader import Type, upload_one
    from resslab_hub.models.database.brace import Brace

    csv_path = write_brace_csv(tmp_dir / "braces_bench.csv", Brace, rows)

    def upload() -> None:
        upload_one(Type.BRACE, str(csv_path))

    # A small number of rounds: each round re-uploads all `rows` records.
    return measure("upload: braces (bulk COPY)", upload, rounds=3, warmup=warmup, unit_count=rows)


def seed(rows: int, tmp_dir: Path) -> None:
    """Load the dataset used by the read benchmarks."""
    from resslab_hub.data.uploader import Type, upload_one
    from resslab_hub.models.database.brace import Brace

    csv_path = write_brace_csv(tmp_dir / "braces_seed.csv", Brace, rows)
    upload_one(Type.BRACE, str(csv_path))

    # One measurement series so the displacement endpoint has data to read.
    measurement = write_measurement_csv(tmp_dir / "B0000000.csv", 500)
    upload_one(Type.BRACE_DISPLACEMENT, str(measurement))


async def main_async(args: argparse.Namespace) -> None:
    tmp_dir = Path(args.tmp_dir) if args.tmp_dir else _BACKEND_DIR / ".benchmark-tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"resslab-hub backend benchmark\n"
        f"  database : {BENCH_DB} @ {settings.postgres_host}:{settings.postgres_port}\n"
        f"  rows     : {args.rows:,}\n"
        f"  rounds   : {args.rounds} (+{args.warmup} warmup)"
    )

    create_database()
    try:
        # --- write path -----------------------------------------------------
        upload_stats = run_upload_benchmark(args.rows, tmp_dir, args.warmup)
        # Leave the table seeded for the read benchmarks.
        seed(args.rows, tmp_dir)

        # --- read paths -----------------------------------------------------
        db_rows = await run_db_benchmarks(args.rounds, args.warmup)
        api_rows = await run_api_benchmarks(args.rounds, args.warmup)

        print_table("Upload (write path)", [upload_stats.row()])
        print_table("Database (raw SQL through asyncpg)", db_rows)
        print_table("API (full stack through ASGI app)", api_rows)
        print()
    finally:
        drop_database()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rows", type=int, default=5_000, help="rows to seed/upload (default 5000)"
    )
    parser.add_argument(
        "--rounds", type=int, default=50, help="timed rounds per read scenario"
    )
    parser.add_argument(
        "--warmup", type=int, default=3, help="discarded warmup rounds per scenario"
    )
    parser.add_argument(
        "--tmp-dir", default=None, help="where to write fixture CSVs (default backend/.benchmark-tmp)"
    )
    return parser.parse_args()


def main() -> None:
    asyncio.run(main_async(parse_args()))


if __name__ == "__main__":
    main()
