# Playbook: Adding a New Component Tab to RESSLab-Hub

## Context

RESSLab-Hub exposes a fixed set of structural steel component types (braces, columns, connections, materials, residual stresses, HSS columns, EBF links). Each type is a full vertical slice: data dictionary → ORM model → Alembic migration → FastAPI router → generated TypeScript client → Vue views/components/charts → navigation wiring → overview-map integration → home-page indicator.

The EBF (Eccentric Braced Frames / "EBF Links") tab was added most recently (GitHub issue #215, PR #224) with a round of post-draft refinements (issue #225, 15 follow-up commits). That closed iteration is the most reliable template. This file captures every touchpoint so the next tab can be added quickly and without missing steps that were only discovered during EBF review.

**Intended outcome:** a single reference the dev (and future Claude sessions) can follow top-to-bottom to scaffold a new component tab, plus a "gotchas" section prebuilt from the EBF feedback so we don't relearn those lessons.

References consulted:
- Code repo: `/mnt/data/Documents/Code/resslab-hub`
- Data repo: `/home/pierre/dev/resslab-hub-data` (sibling of `../../resslab-hub-data` from the backend)
- Issue #215 (initial request) — https://github.com/RESSLab-Team/resslab-hub/issues/215
- PR #224 (initial merge, 34 files changed) — https://github.com/RESSLab-Team/resslab-hub/pull/224
- Issue #225 (post-draft feedback, 15 fix commits) — https://github.com/RESSLab-Team/resslab-hub/issues/225
- Data-repo EBF commits: `3eb60bc` (initial load), `f380501` (CSV formatting), `ac6facd` (processed_data), `4104f10` (final dictionary cleanup) — ~15 commits total, all on `main`
- Issue #176 (HSS Columns initial request) — https://github.com/RESSLab-Team/resslab-hub/issues/176
- Related HSS issues #212, #219, #220 (model equations, home/map indicators, input ranges).
- Data-repo HSS commits from `07153e8` (`feat(hss): add hss columns data`, Nov 2023) through ~17 follow-ups. HSS predates EBF and shows patterns EBF doesn't (Model view, section libraries, id-as-filename time-series).
- Braces tab history — the oldest and most feature-rich tab (initial schema 2016–2017 in code, data migration Feb 2024). Uniquely has a Fragility Curve view. Key commits: `4fcb268` (initial brace fragility curve matrix), `b06f426` / `213fa58` (fragility info tooltip), `bb422f2` (Model tab disabled #213).
- Fragility-curve parameter derivation lives in the sibling repo `resslab-hub-scripts` (MATLAB/Python). The frontend loads pre-computed values, not raw data.

---

## High-level flow

For any new component `NewThing` (snake_case: `new_thing`, plural: `new_things`, short name optional: e.g. "EBF"):

1. **Data repo** — add CSV + data dictionary in sibling `resslab-hub-data` repo.
2. **Backend codegen** — run `make generate-model` to emit ORM + Pydantic.
3. **Backend wiring** — router, `__init__.py`, `main.py`, uploader, Makefile targets.
4. **Backend migration** — `make database-revision name="add_new_thing_model"`, review, apply.
5. **API regeneration** — `make api` from repo root (updates `openapi.json` and `frontend/src/backend/`).
6. **Frontend scaffolding** — views, dashboard, table, detail, three chart types, utils, i18n.
7. **Cross-cutting frontend wiring** — router, nav, axios plugin, overview map, tooltip, home-page indicator.
8. **Static assets** — configuration diagrams / section CSVs under `frontend/public/img/{type}/` or `frontend/src/assets/{type}/`.
9. **Verify** — run backend + frontend dev servers, load the tab, check map tooltip and home indicator.

Each step below is exhaustive.

---

## Step 1 — Data repository (`resslab-hub-data`, sibling `../../resslab-hub-data`)

All schema work starts in the data repo. Nothing in the code repo will compile correctly until the data dictionary is stable, because `make generate-model` reads from it.

**Branch model**
- `main` → feeds production (`resslab-hub.epfl.ch`)
- `test` → feeds test deployment (`resslab-hub-test.epfl.ch`)
- Standard workflow: fork (or branch) → `git switch -c data/new-thing-initial-load` → commit → PR → validation CI → **squash-merge** (this is mandatory per the data-repo README; the CI validates only the final squashed diff on `main`).

### 1.1 Directory layout

Create `/home/pierre/dev/resslab-hub-data/new_things/` with:

| Path | Required | Notes |
|------|----------|-------|
| `new_things/new_things.csv` | yes | Main entity table. Header row + data rows. First column is the stable id (convention: `experimental_program_date_specimen_designation`, e.g. `Engelhardt_et_al_2000_DBBWWPZ`). |
| `new_things/new_things_data_dictionary.csv` | yes | 7-column dictionary (exact header order below). |
| `new_things/processed_data/` or `new_things/<subdir>/` | optional | One file per specimen holding time-series/curve data. |
| `new_things/README.md` | optional | Component-specific notes (like `connections/README.md`). Add one if the naming convention or file layout is non-obvious. |

**Time-series filename convention:** two idioms exist in the repo — **prefer id-as-filename** unless specimen ids would be filesystem-unfriendly. Two of three existing tabs (Braces, HSS) use it; EBF's integer-alias scheme is the outlier.
- **Id-as-filename (default — Braces, HSS):** `force_displacement/{spec_id}.csv` or `Moment_Rotation/{spec_id}.csv` — the file stem IS the specimen id (e.g. `Fadden_McCormick_2012__HSS-203.2x152.4x9.5.csv`, `Tremblay_RHS13.csv`). Transparent and self-documenting.
- **Integer alias (EBF):** `processed_data/id{N}.csv` (e.g. `id1.csv`, `id240.csv`) with an internal `data_ind` column tying back to the specimen row. Use only when specimen ids contain slashes, spaces, or non-ASCII characters — don't reach for this "to match EBF."

**Subdirectory naming is free-form.** HSS uses `Moment_Rotation/` (CamelCase), EBF uses `processed_data/` (lowercase), Connections uses `Panel_zone/`, `Global/`, `Beam_moment_rotation/`. The uploader globs whatever path you hand it — stay consistent between the data repo layout and the `upload-*` Makefile target.

### 1.2 Data dictionary format (authoritative header)

Header row is exactly:

```
column_name,description,symbol,unit,type,example_value,nullable
```

Rules (verified against `eccentric_braced_frames_data_dictionary.csv` and code-repo `data/generate_model.py`):

- `column_name` — lowercase snake_case, no spaces.
- `description` — plain text; quote cells that contain commas (`"Section type (e.g., hot-rolled)"`).
- `symbol` — optional markdown (backticks for code spans); leave empty with a blank cell if not applicable. Typical pattern: `` `id` ``, or empty.
- `unit` — `-` for dimensionless; otherwise `MPa`, `mm`, `mm²`, `mm³`, `degrees`, etc. Empty for free-text fields.
- `type` — one of `Numeric`, `DecimalFloat`, `SmallInteger` (< 30 000), `BigInteger` (up to 10^9), `Integer`, `String`, `Date` (ISO 8601; if only a year is available, use `SmallInteger`), `Boolean`.
- `example_value` — a realistic sample value (`1989`, `W12x16`, `Engelhardt & Popov`).
- `nullable` — `True` / `False`. Convention: `False` for ids/investigator/year/reference/nominal geometry; `True` for measured/expected properties, optional test details, anything that may legitimately be `NA`. Use the literal string `NA` in data cells for missing values — never empty cells.

> The data-repo's own README lists these fields in a different order (column_name, type, example_value, symbol, description, unit, nullable); **the CSV header order above is the canonical one** — `generate_model.py` indexes by column position.

### 1.3 Update the data-repo README

Edit `/home/pierre/dev/resslab-hub-data/README.md`. Under **Making Changes** (~line 58) there is an explicit bullet list of supported directories. Add the new folder to that list. The EBF commit did this — skipping it gives contributors the impression the new type isn't officially supported.

### 1.4 Wire the validation workflow (mandatory — EBF missed this)

File: `/home/pierre/dev/resslab-hub-data/.github/workflows/data-validation.yml`

The `changes` job uses `dorny/paths-filter` with a hardcoded list of component folders (around lines 27–33). **This file was never updated for EBF** — meaning PRs touching `eccentric_braced_frames/` don't actually trigger validation on the backend. Don't repeat that mistake:

```yaml
filters: |
  braces: 'braces/**'
  columns: 'columns/**'
  connections: 'connections/**'
  hss-columns: 'hss_columns/**'
  material: 'material/**'
  residual-stresses: 'residual_stresses/**'
  new-thing: 'new_things/**'       # ← add this line, hyphens in key, underscores in path
```

The downstream steps already handle the hyphen↔underscore conversion and call `POST $SERVER_URL/api/validate/?type=all-<filter-key>`. So `filter-key` must match the backend uploader `Type` enum value (`all-new-things` → filter key `new-things` → directory `new_things/`). Mismatches silently skip validation.

### 1.5 Expect iteration on the dictionary

EBF needed ~15 commits on the dictionary alone (type corrections, nullable flags, CSV quoting, column renames like `f_y_exp_l`). Plan for at least two rounds:
1. First pass: author the dictionary and master CSV, push, let validation run.
2. Second pass: fix types/nullables/quoting based on validation output.

Common dictionary mistakes seen in EBF history:
- Missing `"..."` quoting on descriptions containing commas (`fix(eccentric_braced_frames): correct CSV formatting`).
- Wrong nullable flag on columns full of `NA`/`NR` values (`fix(ebf): set l_s_d_pnl_2_f nullable as they are NA & NR values`).
- Using `Integer` for floats like `6000.0` (should be `DecimalFloat`).
- Typos in filename (`_dictionnary.csv` → `_dictionary.csv`) — the backend expects the exact suffix.

### 1.6 Large archives / tarballs

The repo contains a few pre-built archives at root (`braces.tar.gz`, `data.tar.gz`, `material.tar.gz`) used for manual `curl`-based uploads (see README "Process to compress & upload data"). No Git-LFS. Don't ship a `new_things.tar.gz` unless there's a concrete distribution need — the CI already tars on the fly.

### 1.7 Data-repo ↔ code-repo handshake

Once the dictionary is stable on a branch:
1. In the **code repo**, make sure `../../resslab-hub-data` points at that branch (or a local checkout with the same contents).
2. Run `make generate-model` (code repo, backend) — this is Step 2 below.
3. Only after the backend compiles cleanly, squash-merge the data-repo PR to `main` (or `test` first if you want to stage the new tab on `resslab-hub-test.epfl.ch` before prod).

---

## Step 2 — Backend: model generation

File: `/mnt/data/Documents/Code/resslab-hub/backend/Makefile`

Add a new stanza to the `generate-model:` target (append at the bottom, following the existing EBF block):

```makefile
uv run python data/generate_model.py \
    ../../resslab-hub-data/new_things/new_things_data_dictionary.csv \
    resslab_hub/models/database/new_thing.py \
    resslab_hub/models/api.py new_thing
```

Before running it, create the empty target files with the codegen markers so `generate_model.py` can update them in place:

- `/mnt/data/Documents/Code/resslab-hub/backend/resslab_hub/models/database/new_thing.py` — copy the skeleton from `eccentric_braced_frame.py`, keeping the `# START_OF_GENERATED_CODE` / `# END_OF_GENERATED_CODE` markers. If there is a child time-series table, mirror the `EccentricBracedFrameShearLinkAngle` pattern: composite PK `(new_thing_id, id)`, foreign key, BigInteger autoincrement, measurement columns, and the `shear_link_angle_count` column_property equivalent on the parent.
- `/mnt/data/Documents/Code/resslab-hub/backend/resslab_hub/models/api.py` — add new `# START_OF_GENERATED_CODE_new_thing` / `# END_OF_GENERATED_CODE_new_thing` block. After generation, manually append:
  ```python
  class NewThingField(str, Enum):
      # populated from NewThingModel.__fields__ — see existing EccentricBracedFrameField block
  class NewThingNumberField(str, Enum):
      # populated from numeric fields only
  ```
  plus any manual non-generated fields on the model (e.g. `shear_link_angle_count: int` on EBF).

Run `make generate-model` and review the diff — the codegen only overwrites between the markers.

---

## Step 3 — Backend: router

File: `/mnt/data/Documents/Code/resslab-hub/backend/resslab_hub/routers/new_thing.py` (NEW)

Template: copy `routers/eccentric_braced_frame.py` and rename. It exposes a standardized set of endpoints via the shared `Component` helper:

```
GET /new-thing                        # paginated list with sort/filter
GET /new-thing/fields                 # field metadata
GET /new-thing/counts                 # value occurrence counts
GET /new-thing/range                  # min/max for numeric field
GET /new-thing/matrix                 # cross-tab matrix (parallel chart)
GET /new-thing/csv                    # bulk export
GET /new-thing/distinct               # count distinct values
GET /new-thing/{id}/{sub}             # time-series sub-resource (per child table)
GET /new-thing/{id}/{sub}/csv         # sub-resource export
```

Construct the `Component` with:
- database type: `NewThing`
- model type: `NewThingModel`
- id column: `NewThing.id`
- ignored columns: any `*_count` column_properties that should not appear in field lists.

For each time-series child table, build a `SubComponent` mirroring the EBF `shear_link_angle_component` block (foreign key, id, measurement columns).

File: `/mnt/data/Documents/Code/resslab-hub/backend/resslab_hub/models/database/__init__.py`

Add one import line next to the existing component imports:
```python
import resslab_hub.models.database.new_thing
```

File: `/mnt/data/Documents/Code/resslab-hub/backend/resslab_hub/main.py`

Two edits:
- Add `new_thing` to the `from resslab_hub.routers import (...)` block.
- Add `app.include_router(new_thing.router)` near the other `include_router` calls.

---

## Step 4 — Backend: data uploader

File: `/mnt/data/Documents/Code/resslab-hub/backend/resslab_hub/data/uploader.py`

Three additions, modeled on the EBF block (see commit `12981ce`):

1. **Imports:** `from resslab_hub.models.database.new_thing import NewThing[, NewThingSubTable]`
2. **`Type` enum members:**
   ```python
   ALL_NEW_THING = "all-new-things"
   NEW_THING = "new-thing"
   NEW_THING_SUB = "new-thing-sub"   # per child table
   ```
3. **`upload_one()` handlers:**
   - `Type.NEW_THING` → `TableUploader(NewThing)` for the main CSV.
   - `Type.NEW_THING_SUB` → `CsvFileUploader(...)` for each time-series pattern (delete predicate + row→instance mapping; remember filename prefix, e.g. `id{spec}.csv` → `prefix="id"`).
4. **`get_args_all()` aggregate mapping** — map `ALL_NEW_THING` to the ordered list `[(NEW_THING, "new_things/new_things.csv"), (NEW_THING_SUB, "new_things/<subdir>/*.csv"), ...]`.
5. **`primary_types`** — append `Type.NEW_THING` so the main table is uploaded before its subsidiaries (FK constraint).

File: `/mnt/data/Documents/Code/resslab-hub/backend/Makefile`

Add:
```makefile
upload-new-thing:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-new-things ../../resslab-hub-data
```
And make sure `upload-data` still picks up the aggregate via `all` (it already dispatches via `get_args_all`).

Optionally add a `validate-new-things` rule — the existing `validate-%:` pattern works if the directory name matches.

---

## Step 5 — Backend: Alembic migration

```bash
cd backend
make database-revision name="add_new_thing_model"
```

Alembic autogenerates from the ORM diff. **Review the file** under `backend/alembic/versions/` — pay attention to:
- Correct nullability (compare to data dictionary's `nullable` column).
- Foreign-key cascade on the child table (`ondelete="CASCADE"` is the convention).
- Index on the foreign key column.
- Column types match (`Numeric(p, s)` vs `DecimalFloat`).

Apply locally with `make database-upgrade` (also runs automatically on backend startup unless `DATABASE_UPGRADE=false`).

If you later iterate on the data dictionary (very likely — see #225 which required a second migration `f5abf9d8561b_update_ebf_model.py`), rerun `make generate-model`, then `make database-revision name="update_new_thing_model"` for a schema-refinement revision. **Don't amend the first migration once merged.**

---

## Step 6 — Regenerate OpenAPI + frontend client

From the repo root:

```bash
make api
```

This runs `DATABASE_UPGRADE=false uv run python api.py ../openapi.json` and then `npm run api` in the frontend. Result: fresh `openapi.json` at the repo root plus regenerated `frontend/src/backend/` (with `NewThingApi`, `NewThingModel`, `NewThingField`, `NewThingNumberField`). Commit these regenerated files.

---

## Step 7 — Frontend: axios API client instance

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/plugins/axios.ts`

Two edits mirroring `ebfApi`:
```ts
import { NewThingApi } from '@/backend/api'
// ...
export const newThingApi = new NewThingApi(undefined, baseUrl, axiosInstance)
```

---

## Step 8 — Frontend: views and router

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/views/NewThingView.vue` (NEW)

Thin parent that renders `<router-view />` for child routes (copy `EbfView.vue`).

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/views/NewThingDatabase.vue` (NEW)

Imports and renders `NewThingDashboard.vue` (copy `EbfDatabase.vue`).

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/router/index.ts`

Add a block modeled on the EBF route:
```ts
{
  path: '/new-things',
  component: () => import('@/views/NewThingView.vue'),
  children: [
    { path: '', redirect: '/new-things/database' },
    { path: 'database', component: () => import('@/views/NewThingDatabase.vue') },
    // add 'model' or 'fragility-curve' children only if the component has those views
  ],
}
```

**Naming decision for the URL slug** — remember the #225 lesson: EBF moved from `/eccentric-braced-frames` to `/ebf-links`. Pick the short, user-facing slug up front, not the scientific full name, to avoid renaming later. Keep backend identifiers full snake_case; only the URL/nav labels get the short form.

**Optional: Model view.** Components that ship a published analytical model (closed-form backbone + fragility curve) add a second child route. HSS shows the full pattern:
- `frontend/src/views/HssModelView.vue` — thin router-view wrapper.
- `frontend/src/components/hss/HssModel.vue` — the UI itself (section picker backed by the transformed section CSVs in Step 14, parameter inputs, live-rendered backbone curves).
- Router block becomes:
  ```ts
  children: [
    { path: '', redirect: '/hss-columns/database' },
    { path: 'database', component: () => import('@/views/HssDatabase.vue') },
    { path: 'model',    component: () => import('@/views/HssModelView.vue') },
  ]
  ```
- Nav: add a `{ title: 'Model', to: '/model' }` entry alongside `Database` in `App.vue`.

Don't scaffold a Model view unless the component actually has a published model. EBF is database-only and deliberately ships without this route. Connections and Braces have one; HSS has one.

**You can scaffold the Model view and ship it disabled.** Braces did: `BracesModelView.vue` and `BraceModel.vue` exist and compile, but the menu entry is commented out (commits `bb422f2` / `f5c214b`, `fix(braces): hide component model tab braces #213`). If your analytical model isn't production-ready but the code skeleton is useful, drop the nav entry and leave the route unlisted — the files stay, the tab is simply not reachable from the UI.

**Optional: Fragility Curve view.** If your component has published fragility parameters (damage-state medians/dispersions as functions of specimen properties), add a third child route. Braces is the only example today:

- **View:** `frontend/src/views/NewThingFragilityCurve.vue` — thin router-view wrapper.
- **Component:** `frontend/src/components/new_thing/NewThingFragility.vue` — the UI. Reference implementation: `frontend/src/components/braces/BraceFragility.vue`.
- **Shared utility:** `frontend/src/utils/fragility.ts` — `fragilityCurve(median, sigma)` via `@stdlib/stats-base-dists-lognormal-cdf`, plus `univariateOption()` and the `DamageState` interface. Do NOT reinvent these; import from this file.
- **3D surface plots:** `echarts-gl` via `frontend/src/utils/echarts-gl.ts`. Already installed — no new npm deps needed.
- **Parameter source:** fragility parameters are **not** stored in the data repo or the database. They are computed externally in the sibling repo `resslab-hub-scripts` (e.g. `fragility_curves_steel_braces/`) and **hard-coded as TypeScript constants** in the fragility component. This is deliberate — fragility parameters are a published research artifact, not experimental data.
- **Router block becomes:**
  ```ts
  children: [
    { path: '', redirect: '/new-things/database' },
    { path: 'database',        component: () => import('@/views/NewThingDatabase.vue') },
    { path: 'fragility-curve', component: () => import('@/views/NewThingFragilityCurve.vue') },
    { path: 'model',           component: () => import('@/views/NewThingModelView.vue') },
  ]
  ```
- **Nav:** add `{ title: 'Fragility Curve', to: '/fragility-curve' }` in `App.vue` (kebab-case slug).

Skip this route entirely if you don't have parameters yet — no placeholder view.

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/App.vue`

Add to `menuItems[]`:
```ts
{
  title: 'Short Display Name',       // e.g. 'EBF Links'
  to: '/new-things',
  children: [ { title: 'Database', to: '/database' } ],
  // add 'Model' and 'Fragility Curve' children only if implemented
}
```

---

## Step 9 — Frontend: components

Create `/mnt/data/Documents/Code/resslab-hub/frontend/src/components/{short_name}/` — use the **short, human-friendly name** (EBF → `components/ebf/`, HSS → `components/hss/`), not the full snake_case. Backend module paths and data-repo folders use full snake_case; URL slug, frontend component folder, and class-name acronyms use the short form. Populate the folder with:

| File | Purpose | Template to copy |
|------|---------|------------------|
| `NewThingDashboard.vue` | Layout (table + detail + charts); defines `parallelFields`, `doubleChartFields`, color palette. Uses `useDashboard<NewThingModel>`. | `components/ebf/EbfDashboard.vue` |
| `NewThingTable.vue` | Paginated data grid. Uses `useTable<NewThingModel>` and `newThingApi.getNewThings()`. Emits row click to the dashboard. | `components/ebf/EbfTable.vue` |
| `NewThingDetail.vue` | Detail panel for selected row. Fetches time-series via `newThingApi.getNewThingSub()`. Wraps `CommonDetail.vue`. Renders configuration image via utility helper. | `components/ebf/EbfDetail.vue` |
| `charts/NewThingParallelChart.vue` | Parallel coordinates. Uses `useParallelChart<NewThingField>` + `getNewThingsMatrix`. i18n prefix `"new_thing."`. | `components/ebf/charts/EbfParallelChart.vue` |
| `charts/NewThingDoubleChart.vue` | Two-field histogram (typ. year × category). `useDoubleChart<NewThingField, NewThingNumberField>` + `getNewThingsCounts` + `getNewThingsRange`. | `components/ebf/charts/EbfDoubleChart.vue` |
| `charts/NewThingSingleChart.vue` | Single-field categorical bar. `useSingleChart<NewThingField>`. Pass the optional `mapping` prop introduced in PR #224 commit `bafde72` to map raw values (e.g. `hot-rolled` → `Hot-Rolled`). | `components/ebf/charts/EbfSingleChart.vue` |

No new composables needed — reuse `composables/dashboard.ts`, `table.ts`, `chart.ts` with the new type params.

---

## Step 10 — Frontend: utilities

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/utils/new_thing.ts` (NEW)

Per-component display mappings (raw DB value → human label). Mirror `utils/ebf.ts` which has `linkConfigurationMapping`, `linkTypeMapping`, `sectionTypeMapping`.

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/utils/component.ts`

Add `getNewThingImage(code: string): string` that returns the PNG path for a given configuration key. Pattern from `getEbfImage()`:
```ts
const map: Record<string, string> = { TF1: 'NT_1.png', ... }
return map[code] ? `/img/new_thing/${map[code]}` : ''
```
**Do not lower-case** the input — the #225 fix (`abcd882`) removed unnecessary `toLowerCase()` because the upstream data is already correctly cased.

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/utils/backend.ts`

Add the display name to the `Type` union and `typesNames[]` array:
```ts
export type Type = ... | 'New Thing Display Name'
export const typesNames: Type[] = [..., 'New Thing Display Name']
```

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/utils/overviewmap.ts`

If the component has geographic coords, add:
```ts
const _locationNewThingFields = [
  NewThingField.id, NewThingField.investigator, NewThingField.year,
  NewThingField.spec_id, /* ... */ NewThingField.latitude, NewThingField.longitude,
  NewThingField.reference, NewThingField.url,
]
export const locationNewThingFields = _locationNewThingFields
export type LocationNewThing = Pick<NewThingModel, typeof _locationNewThingFields[number]>
```

---

## Step 11 — Frontend: i18n

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/locales/en.json`

Add a `new_thing` namespace with every display-critical field label, e.g.:
```json
"new_thing": {
  "field_a": "Field A",
  "field_b": "Field B"
}
```
Only `en.json` exists today — no other language files to touch.

---

## Step 12 — Frontend: overview map + tooltip

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/components/map/OverviewMap.vue`

1. `import { newThingApi } from '@/plugins/axios'`
2. `import { locationNewThingFields, LocationNewThing } from '@/utils/overviewmap'`
3. Add a reactive ref `newThingLocations` fetching `newThingApi.getNewThingsFields(locationNewThingFields)`.
4. Add `newThingLocations.value.length` to the `dataLength` computed and render the markers in the same pattern as EBF.

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/components/map/TooltipContent.vue`

1. `import { getNewThingImage } from '@/utils/component'`
2. Add a `v-else-if="type === 'New Thing Display Name'"` block mirroring the EBF tooltip: header (investigator/year), 4–6 detail lines, configuration image if applicable, deep-link to `/new-things/database?id=${data.id}&detail=true`.

---

## Step 13 — Frontend: home page indicator

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/views/HomeView.vue`

1. Import `newThingApi` from `@/plugins/axios`.
2. Add `newThingApi.getNewThingsDistinct()` to the `Promise.all([...])` that aggregates the test-count indicator. Missing this is a common miss — #225 `3952af4` added EBF to this aggregation after the fact.

---

## Step 14 — Static assets

- Configuration diagrams (if any): `/mnt/data/Documents/Code/resslab-hub/frontend/public/img/new_thing/NT_1.png` … — keep the naming aligned with the keys used by `getNewThingImage`.
- Section/property CSVs (if the component has section libraries — like HSS or Connections):
  1. Add raw section CSVs to `resslab-hub-data/new_things/sections/*.csv` (one per standard, e.g. `aisc.csv`, `european.csv`, `japanese.csv`).
  2. Create `backend/data/new_thing_csv_transformer.py`, or reuse the generic `backend/data/csv_transformer.py` if your column headers/units already line up. HSS needed a dedicated transformer (`hss_csv_transformer.py`) because its raw section columns didn't match the frontend schema directly; Connections reuses `csv_transformer.py`.
  3. Add one line per standard to the `transform-data:` target in `backend/Makefile`:
     ```makefile
     transform-data:
         ...existing lines...
         uv run python data/new_thing_csv_transformer.py aisc     ../../resslab-hub-data/new_things/sections/aisc.csv     ../frontend/src/assets/new_thing/new_thing-aisc-sections.csv
         uv run python data/new_thing_csv_transformer.py european ../../resslab-hub-data/new_things/sections/european.csv ../frontend/src/assets/new_thing/new_thing-european-sections.csv
         uv run python data/new_thing_csv_transformer.py japanese ../../resslab-hub-data/new_things/sections/japanese.csv ../frontend/src/assets/new_thing/new_thing-japanese-sections.csv
     ```
  4. Run `cd backend && make transform-data`. Output CSVs land at `frontend/src/assets/new_thing/` and are committed to the repo — the Model component loads them with a static import, not an API call.

---

## Step 15 — Shared-component touch-ups commonly needed

The EBF iteration showed that adding a tab often requires *small* improvements to shared components. Keep an eye out for these:

- `components/commons/charts/SingleChart.vue` — accept an optional `mapping` prop if your values need humanization (commit `bafde72`).
- Parallel chart height — the #225 fix (`0bf430f`) made parallel chart height computed so every category is visible. This is now generic; just make sure your parallel chart's dimensions are set so no labels are cut off.
- `SteelTypeCardTitle.vue` or other card-title components — extend tooltips if your detail view surfaces new property categories.

---

## Gotchas harvested from issue #225 (do these up front, not as fixes later)

1. **Pick the short display name first.** We renamed "Eccentric Braced Frames" → "EBF Links" after launch; URLs, menus, `typesNames`, `Type` union all had to change. Commit to the short form before starting.
2. **Don't lower-case data values.** Keys like `TF1`/`LC5` are already correctly cased in the dictionary. Omit `.toLowerCase()` in frontend mappings; add it only if the data genuinely disagrees.
3. **Integrate indicators day one.** `HomeView.vue` test-count aggregation and overview-map data-length both need the new API. Adding these late means a second PR.
4. **Validate the data dictionary twice.** EBF needed a schema-refinement migration (`f5abf9d8561b`) because nullability/naming drifted during review. Run `make generate-model` → inspect diff → hand to a reviewer *before* the first migration lands.
5. **Chart colors.** Default palettes looked muddy for EBF; pick distinct colors early (see `EbfDashboard.vue` palette).
6. **Parallel-chart sort order.** Ordered categorical axes (`short → intermediate → long`) need explicit `sortValues`. Commit `a3bee8a` restored these after they were lost.
7. **Image sizing.** Detail images need a max-width (EBF fix: 50% of row). Set responsive CSS from the start, don't let the raw PNG expand.
8. **TypeScript imports.** Ensure all new types (`NewThingModel`, `NewThingField`, `NewThingNumberField`) are exported from the generated barrel so `vue-tsc` passes. `fix(ebf): fix import type build problem` (`573cc4a`) caught a circular-import regression — run `npm run type-check` before opening the PR.
9. **Info tooltips on table columns.** Users asked for field explanations (commit `476c98e`). Add `InfoTooltip` to column headers from the start with a short description from the data dictionary.
10. **Carousel / detail content.** Don't ship a detail view with only raw fields — group them ("Loading and Geometric Parameters", "Steel Material Designation (flange / web)") and label units. EBF got two rounds of detail-content rework (`bdec4f8`, `50ba7f7`, `e70b30d`).
11. **Data-repo validation workflow filter.** `.github/workflows/data-validation.yml` has a hardcoded `filters:` list. EBF was never added to it, so no EBF PR has ever been validated by CI. Add your filter line *before* opening the first data-repo PR; otherwise silent pass-through is indistinguishable from a real green check.
12. **Data-dictionary file name.** The suffix must be `_data_dictionary.csv` (not `_dictionnary.csv` — that typo actually shipped in EBF's first commit and had to be renamed). The backend `generate_model.py` invocation in `backend/Makefile` spells out the exact filename; mismatches produce an unhelpful "file not found" error.
13. **Squash-merge is mandatory on the data repo.** The validation CI only diffs `HEAD~1..HEAD` on `main` after merge, so any non-squashed merge makes the validation log useless. Configure the PR to "Squash and merge" before clicking.
14. **Router file naming — singular, not plural.** New routers should be `backend/resslab_hub/routers/new_thing.py`. HSS's `routers/hss_columns.py` is an older plural convention; don't copy it. The ORM class is singular (`NewThing`), the Pydantic model is singular (`NewThingModel`), and the uploader `Type` enum members are singular (`NEW_THING`), so the router file name should match.
15. **Acronym casing is free.** Use the widely-recognised form of the acronym in class/type names: HSS stays all-caps (`HSSColumn`, `HSSColumnModel`, `getHSSColumnImage`), while EBF uses TitleCase in helpers (`getEbfImage`, `ebfApi`). For URL slugs, component folders, and display names, use the short form in its natural case (`/hss-columns`, `components/hss/`, `"HSS Columns"`; `/ebf-links`, `components/ebf/`, `"EBF Links"`). Backend Python module paths and data-repo folders always use full snake_case (`hss_column.py`, `eccentric_braced_frame.py`, `eccentric_braced_frames/`).
16. **Prefer id-as-filename for time-series.** Two of three existing tabs (Braces, HSS) use id-as-filename — it's the majority idiom and simpler to debug. EBF's integer-alias scheme (`id{N}.csv` + `data_ind` column) is the exception, justified only when specimen ids contain filesystem-unfriendly characters. Don't copy EBF's pattern reflexively.
17. **Fragility parameters are hard-coded, not data-sourced.** If your tab has a Fragility Curve view (Braces is the only current example), the damage-state medians/dispersions live as TypeScript constants inside the fragility component — not in the data repo, not in the database. They come from pre-computed research artifacts in the sibling `resslab-hub-scripts` repo. Don't design a DB table or a CSV dictionary for them.

---

## Critical files to have open while doing this work

Backend:
- `backend/resslab_hub/routers/eccentric_braced_frame.py` — router template.
- `backend/resslab_hub/models/database/eccentric_braced_frame.py` — ORM template (parent + time-series child).
- `backend/resslab_hub/models/database/__init__.py` — package imports.
- `backend/resslab_hub/models/api.py` — Pydantic + Field enums.
- `backend/resslab_hub/main.py` — router registration.
- `backend/resslab_hub/data/uploader.py` — ingestion logic.
- `backend/data/generate_model.py` — codegen (don't edit, just understand).
- `backend/Makefile` — `generate-model`, `upload-*`, `transform-data`, `validate-%` targets.
- `backend/alembic/versions/869602dd5a65_add_ebf_model.py` + `f5abf9d8561b_update_ebf_model.py` — migration shapes.

Frontend:
- `frontend/src/views/EbfView.vue`, `EbfDatabase.vue`.
- `frontend/src/components/ebf/*` (dashboard, table, detail, 3 charts).
- `frontend/src/utils/ebf.ts`, `component.ts`, `backend.ts`, `overviewmap.ts`.
- `frontend/src/plugins/axios.ts` — API client registrations.
- `frontend/src/router/index.ts`, `App.vue` — routing + nav.
- `frontend/src/locales/en.json` — i18n.
- `frontend/src/views/HomeView.vue` — indicator aggregation.
- `frontend/src/components/map/OverviewMap.vue`, `TooltipContent.vue`.
- `frontend/src/components/commons/charts/SingleChart.vue` — shared chart with `mapping` prop.

HSS-specific references (useful when your tab needs a Model view or section libraries — neither of which EBF has):
- `backend/resslab_hub/routers/hss_columns.py` — older plural-named router; still a clean example of the shared `Component` + `SubComponent` shape.
- `frontend/src/views/HssModelView.vue`, `frontend/src/components/hss/HssModel.vue` — Model-tab template.
- `backend/data/hss_csv_transformer.py` — custom section-library transformer template.
- `frontend/src/assets/hss/hss-aisc-sections.csv`, `hss-european-sections.csv`, `hss-japanese-sections.csv` — output shape of the transformed section libraries (these are committed assets, not runtime fetches).

Braces-specific references (useful when your tab needs a Fragility Curve view — Braces is the only example today):
- `backend/resslab_hub/routers/braces.py` — the oldest router, plural convention like HSS; still a clean example of the shared `Component` + `SubComponent` shape with id-as-filename time-series.
- `frontend/src/views/BracesFragilityCurve.vue` — thin view wrapper for the fragility tab.
- `frontend/src/components/braces/BraceFragility.vue` — **the reference fragility component.** Hard-coded `DamageState[]` constants (4 cross-section types × 3 damage states + slenderness KL/r data), `echarts-gl` 3D surface plot, `@stdlib` lognormal CDF.
- `frontend/src/utils/fragility.ts` — shared fragility math (`fragilityCurve`, `univariateOption`, `DamageState` interface). Any new fragility view imports from here.
- `frontend/src/utils/echarts-gl.ts` — 3D chart type definitions for `SurfaceGlChart` / `UnitChart`.

---

## Verification checklist

After implementation, run end-to-end locally:

0. **Data repo**
   - `new_things/new_things.csv` and `new_things/new_things_data_dictionary.csv` exist with matching columns.
   - `README.md` lists `new_things` under "Making Changes".
   - `.github/workflows/data-validation.yml` has a `new-things: 'new_things/**'` filter.
   - Open a PR and confirm the `validate (new-things)` matrix job actually runs and reports `✓ All validations passed` (an absent job means the filter is wrong).
   - Squash-merge (not standard merge) when green.

1. **Backend alone**
   - `cd backend && make database-upgrade` — apply migrations cleanly.
   - `make dev` — start FastAPI on `:8000`.
   - `curl http://127.0.0.1:8000/new-thing?limit=5` — list endpoint.
   - `curl http://127.0.0.1:8000/new-thing/fields` — fields metadata.
   - `curl http://127.0.0.1:8000/new-thing/{id}/{sub}` — time-series.
   - `curl http://127.0.0.1:8000/docs` — the new section appears in Swagger.
   - `cd backend && uv run pytest` — existing tests still pass.

2. **Data upload**
   - `cd backend && make upload-new-thing` — ingest succeeds without errors.
   - Verify row counts in psql: `SELECT COUNT(*) FROM new_thing; SELECT COUNT(*) FROM new_thing_sub_table;`.

3. **Frontend regeneration + dev**
   - From repo root: `make api` — no errors; diff shows new client under `frontend/src/backend/`.
   - `cd frontend && npm run type-check` — clean.
   - `cd frontend && npm run lint` — clean.
   - `make dev-frontend` — Vite up.
   - Navigate `http://127.0.0.1:5173/new-things/database`:
     - Table renders rows; pagination, sorting, filtering work.
     - Clicking a row opens the detail panel; carousel shows curves; configuration image loads.
     - Parallel, double, single charts render; colors are distinct; labels aren't truncated.
     - CSV export downloads.
   - Home page `/` — the test-count indicator includes the new component.
   - Overview map — markers for the new type appear; tooltip renders with the new template and deep-links back to `/new-things/database?id=...&detail=true`.
   - Switch locale (if multiple locales exist) — all new labels translate.

4. **Build**
   - `cd frontend && npm run build` — production build passes.
   - `cd .. && make run` — full Docker stack comes up; hit `https://localhost/api/new-thing` through Traefik (remember the `/api` prefix in prod).

5. **Commit hygiene**
   - Follow Conventional Commits (`feat(<short_name>): ...`, `fix(<short_name>): ...`) — commitlint is enforced.
   - Keep migrations in their own commit; keep generated `openapi.json`/`frontend/src/backend/` updates in the same commit as the backend changes they reflect.

---

## Summary: minimum file set for a new tab with one time-series child (like EBF)

Backend (NEW unless noted):
- `backend/resslab_hub/routers/new_thing.py`
- `backend/resslab_hub/models/database/new_thing.py`
- `backend/resslab_hub/models/database/__init__.py` *(edit — 1 line)*
- `backend/resslab_hub/models/api.py` *(edit — add Model + 2 enums)*
- `backend/resslab_hub/main.py` *(edit — import + include_router)*
- `backend/resslab_hub/data/uploader.py` *(edit — Type enum, handlers, get_args_all)*
- `backend/Makefile` *(edit — `generate-model` + `upload-new-thing`)*
- `backend/alembic/versions/<rev>_add_new_thing_model.py` *(autogenerated, reviewed)*

Frontend (NEW unless noted):
- `frontend/src/views/NewThingView.vue`
- `frontend/src/views/NewThingDatabase.vue`
- `frontend/src/components/new_thing/NewThingDashboard.vue`
- `frontend/src/components/new_thing/NewThingTable.vue`
- `frontend/src/components/new_thing/NewThingDetail.vue`
- `frontend/src/components/new_thing/charts/NewThingParallelChart.vue`
- `frontend/src/components/new_thing/charts/NewThingDoubleChart.vue`
- `frontend/src/components/new_thing/charts/NewThingSingleChart.vue`
- `frontend/src/utils/new_thing.ts`
- `frontend/src/utils/component.ts` *(edit — add `getNewThingImage`)*
- `frontend/src/utils/backend.ts` *(edit — `Type` + `typesNames`)*
- `frontend/src/utils/overviewmap.ts` *(edit — location fields + type)*
- `frontend/src/plugins/axios.ts` *(edit — `newThingApi`)*
- `frontend/src/router/index.ts` *(edit — route block)*
- `frontend/src/App.vue` *(edit — menu item)*
- `frontend/src/locales/en.json` *(edit — `new_thing.*` keys)*
- `frontend/src/views/HomeView.vue` *(edit — distinct call)*
- `frontend/src/components/map/OverviewMap.vue` *(edit — fetch + length)*
- `frontend/src/components/map/TooltipContent.vue` *(edit — template block)*
- `frontend/public/img/new_thing/*.png` *(assets, if configuration diagrams)*
- `openapi.json` + `frontend/src/backend/*` *(regenerated, committed)*

Total for a tab like EBF: ~20 edits + ~14 new files + auto-regenerated client and migration.
