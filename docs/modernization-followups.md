# Toolchain: done and follow-ups

Status of the dependency and performance work that started on
`perf/performance-improvements` in June 2026 and is merged in `dev` since.
The first table is history, the rest is the list of what is still open.

## Done

| Area                         | Change                                                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backend lint                 | `black`+`flake8`+`isort` → **ruff** (`ruff` + `ruff-format`, `backend/.pre-commit-config.yaml`)                                                                                                                                                                                                                                                                                      |
| Frontend build               | Vite 4 → **6**, `@vitejs/plugin-vue` 4 → **5**, `vite-plugin-vuetify` 1 → **2**                                                                                                                                                                                                                                                                                                      |
| Frontend types               | TypeScript 4.8 → **5.9**, `vue-tsc` 1.8 → **2.2**, `@vue/tsconfig` 0.1 → **0.7** — type-check **14.4 s → ~9.5 s**, now incremental                                                                                                                                                                                                                                                   |
| Frontend tests               | Vitest 0.31 → 2 (`deps.inline` → `server.deps.inline`), then **4** (4.1.10 today)                                                                                                                                                                                                                                                                                                    |
| Frontend framework           | Vue 3.3 → **3.5**, Vuetify 3.3 → **3.12**, vue-router/pinia/echarts/axios bumped; `vuetify/labs/VDataTable` → `vuetify/components`                                                                                                                                                                                                                                                   |
| Backend API                  | FastAPI 0.95 → **0.115**, **Pydantic v1 → v2**, uvicorn 0.22 → 0.49, Python 3.13 unblocked (`requires-python <3.14`)                                                                                                                                                                                                                                                                 |
| `make api` under OpenAPI 3.1 | generator-cli 7.24.0 in `openapitools.json`, spec and `frontend/src/backend/` regenerated. The model-level `model_serializer` on `ApiModel` collapsed serialization schemas to `{}` and was replaced by plain `float` field types (`Numeric` -> `float` in `generate_model.py`); series endpoints return JSON numbers, nullable fields are typed `T \| null` in the client (2026-07) |
| `*_count` flags              | the correlated `column_property` subqueries became real `SmallInteger` columns, recomputed at the end of every upload (migration `2a42de2d3438_materialize_count_flags.py`, `resslab_hub/data/count_flags.py`)                                                                                                                                                                       |
| HTTP cache                   | weak ETag on a process-wide data version + `Cache-Control: max-age` + an in-process store of rendered bodies, bumped by `/upload` (`resslab_hub/utils/caching.py`); the hot URLs are rendered at startup and refreshed before expiry (`utils/warmup.py`). See `docs/dashboard-architecture.md`                                                                                       |
| Backend tests                | from one test to 18 files and about 380 tests, run in CI against a Postgres service with coverage (`make test-cov`)                                                                                                                                                                                                                                                                  |
| Package manager              | npm → **pnpm** for the root and the frontend (#313)                                                                                                                                                                                                                                                                                                                                  |

## Upload ingestion perf (done)

`make upload-data` / the `/upload` endpoint, profiled and optimized against the
live local DB (resslab-hub-data, ~11.3M measurement rows). End-to-end wall time
**3:44.8 → 1:00.4 (−73%)**, with per-table row counts and the skipped-file set
**identical at every step** (16 pre-existing data issues reproduced exactly).

| Step                                           | Commit    | Wall   | Change |
| ---------------------------------------------- | --------- | ------ | ------ |
| Original (per-row ORM `merge`/`add`)           | —         | 3:44.8 | —      |
| `bulk_save_objects` + UTF-8 encoding fast-path | `58484a7` | 2:28.8 | −34%   |
| Core `insert()` + dict mappings                | `72825bb` | 1:50.8 | −51%   |
| `COPY FROM STDIN` (text format)                | `86c34a7` | 1:22.6 | −63%   |
| LPT scheduling (biggest-first, `chunksize=1`)  | `3873024` | 1:00.4 | −73%   |

What the profiling showed (`backend/resslab_hub/data/uploader.py`,
`common.py`):

- **Encoding** (`get_file_encoding`): strict full-file `utf-8-sig` decode first,
  `chardet` only on fallback — every byte still checked, no sampling. Was ~real,
  now 0.3% of the work.
- **Core insert's win came from dropping ORM object construction** (build-rows
  phase 251s → 27s), _not_ faster inserts — `insertmanyvalues` batching only cut
  the insert itself ~11%. That left INSERT at **93%** of measurement work, which
  justified COPY.
- **COPY** streams each file in one op (vs ~1 statement per 1,000 rows). Text
  format keeps skip behaviour identical: `None` → `\N` (NULL), empty string
  stays empty (still fails numeric columns → same files skipped); runs on the
  session's transaction so delete + COPY commit/roll back together.
- The `TableUploader` per-row `merge` → upsert idea was **dropped**: entity
  tables total ~1.6k rows (~6s), not worth it.
- **LPT scheduling** (`upload_parallel`): `starmap`'s default chunksize batched
  the 5 consecutive 300k-row `moment_rotation_strong` files onto one worker
  (~26s serial tail). Sorting args biggest-first + `chunksize=1` fans them out
  across 5 workers; verified via worker-PID assignment in the run log. −22s.

Remaining headroom is now **aggregate-throughput-bound**, not single-file-bound:
the largest file is ~6.6s in-worker against a ~60s wall, and the 5 giants run in
parallel. Splitting a single file's rows across workers would **not** help
(its time is already far below the wall) and adds real complexity (chunked COPY

- coordinating the one delete). Going below ~60s needs faster per-row throughput
  (COPY is already near-optimal) or more cores — not a different scheme.

## Still open

### Frontend lint (churn-heavy)

- ESLint 8 → 9: flat config rewrite of `.eslintrc.cjs`, drop
  `@rushstack/eslint-patch`, move `--ignore-path .gitignore` into flat
  `ignores`. `lefthook.yml` has a comment tied to ESLint 8.
- Prettier 2 → 3: one whole-repo reflow commit, bump
  `@vue/eslint-config-prettier` / `-typescript`, update the lefthook hooks.

### Bleeding-edge majors (baseline kept at Vite 6 / TS 5.9)

- Vite 6 → **8**, TypeScript 5.9 → **6** (needs `vue-tsc` 2 → **3**).
- Vuetify 3 → **4**, vue-router 4 → **5**, pinia 2 → **3**, echarts 5 → **6**,
  `vue-echarts` 6 → **8**, mathjs 11 → **15**.
- `@intlify/unplugin-vue-i18n` + `vue-i18n` 9 → **11** (vue-i18n v9 is EOL;
  the precompiled-message format changed, so plugin and runtime move together).
- Why not yet: `vue-tsc` 2 pairs with TS 5, not TS 6, and the Vuetify, echarts
  and i18n plugins are not all certified against Vite 8.

### Minor

- Dart Sass legacy JS API warning from `vite-plugin-vuetify`. Silence with
  `css.preprocessorOptions.scss.api = 'modern-compiler'` in `vite.config.ts`
  once checked that Vuetify's compiled output does not change. Not set today.

### Backend DB perf (needs a live Postgres + the data repo)

Each item needs an Alembic migration and a `make upload-data` (which wipes the
local DB):

- Secondary indexes on the frontend filter/sort/facet columns. The only
  indexes today are the ids of the child tables and the auth tables.
- `get_series` row_number() subsampling, instead of the computed-mod full
  scan (`resslab_hub/utils/common.py`, `func.mod(id_column, n) == 0`).

### Other

- Dependabot reported about 118 vulnerabilities on the default branch in
  June 2026. Check the current count on GitHub and triage separately.
