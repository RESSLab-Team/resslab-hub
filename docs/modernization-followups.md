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

## Required follow-up (created by this work)

- **`make api` — regenerate the frontend client under OpenAPI 3.1.**
  Pydantic v2 makes FastAPI emit **OpenAPI 3.1.0** (was 3.0.x): nullables become
  `anyOf: [<type>, {type: null}]` instead of `nullable: true`. The committed
  `openapi.json` + `frontend/src/backend/` were generated under 3.0, so they are
  now stale. Run `make api` and review the (large) generated diff; confirm the
  `typescript-axios` generator (`openapitools.json`, generator-cli 6.4.0) handles
  3.1 cleanly — bump the generator if not. Left out on purpose so it can be
  reviewed as its own change.

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
