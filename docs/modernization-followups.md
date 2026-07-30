# Modernization — done & follow-ups

Status of the dependency-modernization pass on `perf/performance-improvements`
(June 2026). Lists what landed and what is deliberately left for later.

## Done (on this branch)

| Area | Change |
|---|---|
| Backend lint | `black`+`flake8`+`isort` → **ruff** (`ruff` + `ruff-format`) |
| Frontend build | Vite 4 → **6**, `@vitejs/plugin-vue` 4 → **5**, `vite-plugin-vuetify` 1 → **2** |
| Frontend types | TypeScript 4.8 → **5.9**, `vue-tsc` 1.8 → **2.2**, `@vue/tsconfig` 0.1 → **0.7** — type-check **14.4 s → ~9.5 s**, now incremental |
| Frontend tests | Vitest 0.31 → **2** (`deps.inline` → `server.deps.inline`) |
| Frontend framework | Vue 3.3 → **3.5**, Vuetify 3.3 → **3.12**, vue-router/pinia/echarts/axios bumped; `vuetify/labs/VDataTable` → `vuetify/components` |
| Backend API | FastAPI 0.95 → **0.115**, **Pydantic v1 → v2**, uvicorn 0.22 → 0.49, Python 3.13 unblocked (`requires-python <3.14`) |

## Upload ingestion perf (done on this branch)

`make upload-data` / the `/upload` endpoint, profiled and optimized against the
live local DB (resslab-hub-data, ~11.3M measurement rows). End-to-end wall time
**3:44.8 → 1:00.4 (−73%)**, with per-table row counts and the skipped-file set
**identical at every step** (16 pre-existing data issues reproduced exactly).

| Step | Commit | Wall | Change |
|---|---|---|---|
| Original (per-row ORM `merge`/`add`) | — | 3:44.8 | — |
| `bulk_save_objects` + UTF-8 encoding fast-path | `58484a7` | 2:28.8 | −34% |
| Core `insert()` + dict mappings | `72825bb` | 1:50.8 | −51% |
| `COPY FROM STDIN` (text format) | `86c34a7` | 1:22.6 | −63% |
| LPT scheduling (biggest-first, `chunksize=1`) | `3873024` | 1:00.4 | −73% |

What the profiling showed (`backend/resslab_hub/data/uploader.py`,
`common.py`):
- **Encoding** (`get_file_encoding`): strict full-file `utf-8-sig` decode first,
  `chardet` only on fallback — every byte still checked, no sampling. Was ~real,
  now 0.3% of the work.
- **Core insert's win came from dropping ORM object construction** (build-rows
  phase 251s → 27s), *not* faster inserts — `insertmanyvalues` batching only cut
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
+ coordinating the one delete). Going below ~60s needs faster per-row throughput
(COPY is already near-optimal) or more cores — not a different scheme.

## Required follow-up (created by this work)

- **`make api` — regenerate the frontend client under OpenAPI 3.1.** ✅ Done
  (2026-07): generator-cli bumped to 7.24.0 in `openapitools.json`, spec and
  `frontend/src/backend/` regenerated under 3.1. The model-level
  `model_serializer` on `ApiModel` collapsed serialization schemas to `{}` and
  had to be replaced by plain `float` field types (`Numeric` -> `float` in
  `generate_model.py`); series endpoints now return JSON numbers instead of
  Decimal-as-string; nullable fields are typed `T | null` in the client.

## Deferred — deliberately out of scope this round

### Frontend lint modernization (churn-heavy)
- ESLint 8 → 9 (**flat config** rewrite of `.eslintrc.cjs`; drop
  `@rushstack/eslint-patch`; move `--ignore-path .gitignore` into flat `ignores`).
- Prettier 2 → 3 (**whole-repo reflow** in one commit; bump
  `@vue/eslint-config-prettier`/`-typescript`). Update the lefthook hooks.

### Bleeding-edge majors (proven baseline kept at Vite 6 / TS 5.9)
- Vite 6 → **8**, TypeScript 5.9 → **6** (needs `vue-tsc` 2 → **3**).
- Vuetify 3 → **4**, vue-router 4 → **5**, pinia 2 → **3**, echarts 5 → **6**,
  `vue-echarts` 6 → **8**, mathjs 11 → **15**.
- `@intlify/unplugin-vue-i18n` + `vue-i18n` 9 → **11** (vue-i18n v9 is EOL /
  deprecation-warned; the precompiled-message format changed, so plugin and
  runtime must move together).
- Rationale: `vue-tsc` 2 (the type-check speedup) pairs with TS 5, not TS 6; and
  the Vuetify/echarts/i18n plugins are not all certified against Vite 8 yet.

### Minor
- **Dart Sass legacy-JS-API deprecation** warning from `vite-plugin-vuetify`
  (Sass building Vuetify styles). Silence via
  `css.preprocessorOptions.scss.api = 'modern-compiler'` in `vite.config.ts`
  once verified it doesn't change Vuetify's compiled output.

### Backend DB-schema perf (needs a live Postgres + the `resslab-hub-data` repo)
Each item needs an Alembic migration + `make upload-data` (which **wipes** the
local DB), so they were left for a session with the data repo available:
- Denormalize the `*_count` `column_property` correlated subqueries into real
  Integer columns (defs are hand-written below `# END_OF_GENERATED_CODE`).
- Secondary indexes on the frontend filter/sort/facet columns.
- `get_series` row_number() subsampling (drop the computed-mod full scan).
- ETag / `Cache-Control` keyed off a data-version stamp on the static aggregate
  endpoints (`/fields`, `/counts`, `/range`, `/matrix`, `/distinct`, per-id
  series/CSV).

### Other (pre-existing, not from this work)
- Backend test suite is **one test** — the Pydantic v2 migration was verified by
  live endpoint testing, not by coverage. Worth building out.
- Dependabot reports ~118 vulnerabilities on the default branch — triage
  separately.
