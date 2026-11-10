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
5. **API regeneration** — `make api` from repo root (updates `openapi.json`, `database-columns.json` and `frontend/src/backend/`).
6. **Frontend scaffolding** — views, dashboard, table, detail, three chart types, utils, i18n.
7. **Cross-cutting frontend wiring** — router, nav, axios plugin, overview map, home-page indicator.
8. **Static assets** — configuration diagrams / section CSVs under `frontend/public/img/{type}/` or `frontend/src/assets/{type}/`.
9. **Verify** — run backend + frontend dev servers, load the tab, check the overview map and home indicator.

Each step below is exhaustive.

---

## Commit order / methodology

Both tabs added to date (HSS — issue #176, Dec 2023; EBF — issue #215 / PR #224, Mar 2025) were committed in essentially the same sequence. Reconstructed from reflog; the messages below are the actual commits that landed.

**Guiding principle: one logical layer per commit, inside-out.** Data layer → API layer → ingestion → generated bridge → frontend scaffolding → frontend assets → cross-cutting wiring → polish. Each step should be independently reviewable, and the stack should compile (backend at least) at every commit so `git bisect` stays useful.

### EBF (branch `feat/EBF_TAB`, every commit references `#215`)

1. `feat(ebf): generate ebf model & alembic revision` — ORM model + Alembic migration from the data dictionary (`make generate-model` + `make database-revision`).
2. `feat(ebf): create ebf api & router model` — Pydantic schema + FastAPI router.
3. `feat(ebf): add uploader & fix model/alembic with correct null columns & add NAN to None in analyser` — CSV uploader + late null-column fixups on the model/migration.
4. `feat(ebf): generate open api files` — regenerated `openapi.json` + `frontend/src/backend/` TS client. **This is its own commit — don't mix it with either backend logic or frontend code.**
5. `feat: add all ebf components` — one big frontend commit: views (`EbfView.vue`, `EbfDatabase.vue`, removed since), `components/ebf/*` (dashboard + table + detail + 3 charts, now the generic `Dataset*Chart`), `utils/ebf.ts`, `App.vue` nav, `router/index.ts`, `plugins/axios.ts`, `locales/en.json`. (HSS split this into three — your call.)
6. `feat(ebf): allow mapping prop to single chart for label` — tiny shared-chart tweak the tab needed (`components/commons/charts/SingleChart.vue`).
7. `feat(ebf): add ebf detail images` — static PNGs under `frontend/public/img/ebf/`.
8. `feat(ebf): update detail with correct path for images` — wire `getEbfImage()` paths to the new PNGs.
9. `feat(ebf): add ebf to overview map & create tooltip` — `OverviewMap.vue` + `TooltipContent.vue` + `HomeView.vue` indicator. **Cross-cutting wiring last.**

Then a multi-week feedback round (issue #225) added ~15 more `feat(ebf):` / `fix(ebf):` commits for renaming "Eccentric Braced Frames" → "EBF Links", chart color tuning, detail content restructuring, a second migration `update_ebf_model`, etc. This is expected — budget for a polish round and don't try to ship it in the initial commit stream.

### HSS (issue `#176`, Dec 2023 — same shape, finer-grained frontend splits)

1. `feat(hss): create model & alembic revision`
2. `feat(hss): create api & router model`
3. `fix(hss): change precision moment rotation` — schema precision fix that surfaced as soon as the router started using the model.
4. `feat(hss): add uploader`
5. `feat(hss): generate open api files`
6. `feat(hss): add date column` — additive schema iteration (re-ran codegen → new migration → regen client). Fine to do mid-stream before the frontend gets big.
7. `feat(hss): create hss views & first commit dashboard` — scaffold only.
8. `fix(hss): lowercase hss components` — naming-convention cleanup immediately after the scaffold landed.
9. `feat(hss): add all charts dashboard`
10. `feat(hss): add hss detail`
11. `feat(hss): add mapping parallel view field & add it boundary condition` — last of the frontend UI commits.

Cross-cutting wiring (home indicator, map tooltip, configuration images) was deferred to separate PRs over the following year (`feat(hss): connect home indicators to hss api #219`, `feat(hss): add hss location to overviewmap #219`, `feat(hss): add hss configuration images #176`). That deferral was deliberate — the tab shipped hidden and was unveiled in stages. **For a brand-new tab today, prefer EBF's pattern and land the cross-cutting wiring in the initial PR** so the map/home experience is coherent at launch.

The HSS Model view was added one commit later (`feat(hss): add hss component model #176`) once the analytical model was ready. Model/Fragility views should be their own commits, layered on top of the database vertical slice — never mixed into the initial commit stream.

### Distilled template for the next tab

| #     | Commit                                                          | Layer             | Notes                                                                  |
| ----- | --------------------------------------------------------------- | ----------------- | ---------------------------------------------------------------------- |
| 1     | `feat(<tab>): generate <tab> model & alembic revision #<issue>` | Backend data      | Output of `make generate-model` + `make database-revision`             |
| 2     | `feat(<tab>): create <tab> api & router model #<issue>`         | Backend API       | Pydantic schema + FastAPI router + `main.py` wiring                    |
| 3     | `feat(<tab>): add uploader #<issue>`                            | Backend ingest    | `uploader.py` + Makefile `upload-<tab>` target                         |
| 4     | `feat(<tab>): generate open api files #<issue>`                 | Generated bridge  | `openapi.json` + `frontend/src/backend/` — nothing else in this commit |
| 5     | `feat(<tab>): create <tab> views & dashboard #<issue>`          | Frontend scaffold | Views + dashboard + router + nav + `axios.ts` + i18n                   |
| 6     | `feat(<tab>): add charts #<issue>`                              | Frontend UI       | Parallel + Double + Single charts                                      |
| 7     | `feat(<tab>): add detail #<issue>`                              | Frontend UI       | Detail panel + time-series carousel                                    |
| 8     | `feat(<tab>): add utils & mappings #<issue>`                    | Frontend util     | `utils/<tab>.ts`, `component.ts`, `backend.ts` edits                   |
| 9     | `feat(<tab>): add detail images #<issue>`                       | Frontend assets   | `public/img/<tab>/*.png`                                               |
| 10    | `feat(<tab>): add <tab> to overview map #<issue>`               | Cross-cutting     | `routers/map.py`, `mapCategories.ts`, `HomeView.vue`                   |
| (11+) | `feat(<tab>): add <tab> model view #<issue>`                    | Optional          | Only if the component has a published analytical model                 |
| (11+) | `feat(<tab>): add <tab> fragility view #<issue>`                | Optional          | Only if fragility parameters exist (Braces only today)                 |

You can split or fuse rows if the diff is trivial or huge — EBF fused 5–10 into one "feat: add all ebf components" commit, HSS split them. What matters is the **order**: backend-first, generated-bridge as its own commit, frontend scaffold before UI details, cross-cutting wiring last.

### Rules of thumb

- **Every commit references the tracking issue** (`#215`, `#176`, `#219`). Release Please + commitlint are happy, and grep-by-issue works for archaeology.
- **Commit scope is the short tab name** (`feat(ebf):`, `feat(hss):`), not the full snake_case (`eccentric_braced_frames`). Short form matches the frontend folder and display name.
- **Keep generated files (`openapi.json`, `frontend/src/backend/`) in their own commit.** Mixing them with backend logic or frontend UI makes review noisy because the diff is huge and mechanical.
- **Migrations live with the commit that produced them.** The `feat(<tab>): generate model & alembic revision` commit owns the initial migration; schema refinements that come later get their own migration in their own commit (`update_<tab>_model`). **Never amend a merged migration.**
- **If a backend fixup is needed after the API commit (precision, nullability), land it as a separate `fix(<tab>):` commit rather than amending.** HSS did this with `fix(hss): change precision moment rotation`; EBF folded its fixups into the uploader commit, which worked but made that commit's message awkward.
- **Cross-cutting polish (shared chart props, parallel-axis sort order, info tooltips) belongs in its own commit, not hidden inside the scaffolding commit.** EBF's `feat(ebf): allow mapping prop to single chart for label` is the model here.
- **Expect a polish round after the initial PR merges.** EBF had ~15 follow-up commits on issue #225 covering renames, chart colors, home/map integration gaps, detail content redesign. Plan for it.

---

## Step 1: Data repository (`resslab-hub-data`, sibling `../../resslab-hub-data`)

All schema work starts in the data repo. Nothing in the code repo will compile correctly until the data dictionary is stable, because `make generate-model` reads from it.

**Branch model**

- `main` is the only long-lived branch. It builds the `resslab-hub-data:main` image that every environment (dev, test, prod) uploads from.
- Standard workflow: fork (or branch) → `git switch -c data/new-thing-initial-load` → commit → PR → validation CI → **squash-merge** (this is mandatory per the data-repo README; the CI validates only the final squashed diff on `main`).

### 1.1 Directory layout

Create `new_things/` at the root of the data repo with:

| Path                                                   | Required | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `new_things/new_things.csv`                            | yes      | Main entity table. Header row + data rows. First column is the stable id (convention: `experimental_program_date_specimen_designation`, e.g. `Engelhardt_et_al_2000_DBBWWPZ`).                                                                                                                                                                                                                                                                                                        |
| `new_things/new_things_data_dictionary.csv`            | yes      | 8-column dictionary (exact header order below).                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `new_things/processed_data/` or `new_things/<subdir>/` | optional | One file per specimen holding time-series/curve data.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `new_things/README.md`                                 | yes      | The contributor guide for the database, on the model of the nine existing ones (contents, identifier convention, response files with exact headers and units, submitting). It is uploaded with the data (`Type.README`, keyed by folder in `README_DATABASES` in `uploader.py`, so add the new folder there), served by `GET /dictionary/{database}/readme` and rendered in the submission form next to the dictionary table. Do not duplicate the dictionary in it; link to the CSV. |

**Time-series filename convention:** two idioms exist in the repo — **prefer id-as-filename** unless specimen ids would be filesystem-unfriendly. Two of three existing tabs (Braces, HSS) use it; EBF's integer-alias scheme is the outlier.

- **Id-as-filename (default — Braces, HSS):** `force_displacement/{spec_id}.csv` or `Moment_Rotation/{spec_id}.csv` — the file stem IS the specimen id (e.g. `Fadden_McCormick_2012__HSS-203.2x152.4x9.5.csv`, `Tremblay_RHS13.csv`). Transparent and self-documenting.
- **Integer alias (EBF):** `processed_data/id{N}.csv` (e.g. `id1.csv`, `id240.csv`) with an internal `data_ind` column tying back to the specimen row. Use only when specimen ids contain slashes, spaces, or non-ASCII characters — don't reach for this "to match EBF."

**Subdirectory naming is free-form.** HSS uses `Moment_Rotation/` (CamelCase), EBF uses `processed_data/` (lowercase), Connections uses `Panel_zone/`, `Global/`, `Beam_moment_rotation/`. The uploader globs whatever path you hand it — stay consistent between the data repo layout and the `upload-*` Makefile target.

### 1.2 Data dictionary format (authoritative header)

Header row is exactly:

```
column_name,description,symbol,unit,type,example_value,nullable,group
```

Rules (verified against `eccentric_braced_frames_data_dictionary.csv` and code-repo `data/generate_model.py`):

- `column_name` — lowercase snake_case, no spaces.
- `description` — plain text; quote cells that contain commas (`"Section type (e.g., hot-rolled)"`).
- `symbol` — optional markdown (backticks for code spans); leave empty with a blank cell if not applicable. Typical pattern: `` `id` ``, or empty.
- `unit` — `-` for dimensionless; otherwise `MPa`, `mm`, `mm²`, `mm³`, `degrees`, etc. Empty for free-text fields.
- `type` — one of `Numeric`, `DecimalFloat`, `SmallInteger` (< 30 000), `BigInteger` (up to 10^9), `Integer`, `String`, `Date` (ISO 8601; if only a year is available, use `SmallInteger`), `Boolean`.
- `example_value` — a realistic sample value (`1989`, `W12x16`, `Engelhardt & Popov`).
- `nullable` — `True` / `False`. Convention: `False` for ids/investigator/year/reference/nominal geometry; `True` for measured/expected properties, optional test details, anything that may legitimately be `NA`. Use the literal string `NA` in data cells for missing values — never empty cells.
- `group`: the scientific category of the column (`Experimental program details`, `Section properties`, `Material properties`, ...). It drives the collapsible groups of the filter rail, the contribution editor, the review panel and the drawer. Pick from the names in [variable-categories.md](variable-categories.md); a new name needs a matching id in `frontend/src/utils/fieldGroups.ts`. `generate_model.py` ignores this column, the uploader reads it (`DictionaryUploader`) and `GET /dictionary` serves it. A column with no group and no matching pattern in `fieldGroups.ts` fails `fieldGroups.spec.ts`.

> The data-repo's own README lists these fields in a different order (column_name, type, example_value, symbol, description, unit, nullable); **the CSV header order above is the canonical one** — `generate_model.py` indexes by column position.

### 1.3 Update the data-repo README

Edit the data repo's `README.md`. Under **Making Changes** (~line 58) there is an explicit bullet list of supported directories. Add the new folder to that list. The EBF commit did this, skipping it gives contributors the impression the new type isn't officially supported.

### 1.4 Wire the validation workflow (mandatory)

File: `.github/workflows/data-validation.yml` in the data repo.

The `changes` job uses `dorny/paths-filter` with a hardcoded list of component folders. A folder missing from that list is never validated, and nothing warns about it (EBF shipped like that for a while). Add the new one:

```yaml
filters: |
  braces: 'braces/**'
  columns: 'columns/**'
  connections: 'connections/**'
  eccentric-braced-frames: 'eccentric_braced_frames/**'
  hss-columns: 'hss_columns/**'
  material: 'material/**'
  residual-stresses: 'residual_stresses/**'
  new-things: 'new_things/**'       # ← add this line, hyphens in key, underscores in path
```

The same workflow has a `line-endings` job (LF and a final newline on every CSV); it needs no change for a new folder.

The downstream steps already handle the hyphen↔underscore conversion and call `POST $SERVER_URL/api/validate?type=all-<filter-key>`. So `filter-key` must match the backend uploader `Type` enum value (`all-new-things` → filter key `new-things` → directory `new_things/`). Mismatches silently skip validation.

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

Don't commit archives (`new_things.tar.gz`): the CI and `make validate-<type>` tar on the fly. Git LFS is used only for the SEM TIFs of ductile fracture (`.gitattributes`); CSVs stay plain git. Large binary assets for a new tab go the SEM way (LFS in the data repo, WebP on the EPFL CDN), not into this repo.

### 1.7 Data-repo ↔ code-repo handshake

Once the dictionary is stable on a branch:

1. In the **code repo**, make sure `../../resslab-hub-data` points at that branch (or a local checkout with the same contents).
2. Run `make generate-model` (code repo, backend) — this is Step 2 below.
3. Only after the backend compiles cleanly, squash-merge the data-repo PR to `main`. Every environment uploads from `main`: the data repo sends the changed files to each hub when the PR lands. A hub that doesn't run the new backend yet has no table for them. Once it does, run its upload CronJob from ArgoCD (dev also rebuilds each night). See [backend/README.md](../backend/README.md#upload-data-to-a-deployed-environment-dev-stage-prod).

---

## Step 2: Backend: model generation

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
  After `# END_OF_GENERATED_CODE`, also add the list of the empty values that were not reported (#427), the same line as the other tabs: `not_reported = Column(ARRAY(String), nullable=False, server_default=text("'{}'"))`. Without it, every empty number in the drawers says "Not applicable". `test_database_columns.py` fails when a model has no such column. The autogenerated migration picks it up.
- `/mnt/data/Documents/Code/resslab-hub/backend/resslab_hub/models/api.py` — add new `# START_OF_GENERATED_CODE_new_thing` / `# END_OF_GENERATED_CODE_new_thing` block. After generation, manually append:
  ```python
  class NewThingField(str, Enum):
      # populated from NewThingModel.__fields__ — see existing EccentricBracedFrameField block
  class NewThingNumberField(str, Enum):
      # populated from numeric fields only
  ```
  plus any manual non-generated fields on the model (e.g. `shear_link_angle_count: int` on EBF), and `not_reported: List[str]` after the end marker.

Run `make generate-model` and review the diff — the codegen only overwrites between the markers.

---

## Step 3: Backend: router

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
- ignored columns: `NewThing.not_reported`, and any `*_count` column_properties that should not appear in field lists.

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

## Step 4: Backend: data uploader

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
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python -m resslab_hub.data.uploader all-new-things ../../resslab-hub-data
```

And make sure `upload-data` still picks up the aggregate via `all` (it already dispatches via `get_args_all`).

Optionally add a `validate-new-things` rule — the existing `validate-%:` pattern works if the directory name matches.

### 4.1 Validator (mandatory — tensile coupons, EBF and ductile fracture all missed this, see #274)

File: `backend/resslab_hub/data/validator.py`

The uploader and the validator are two separate dispatch tables, and only the first one was on this checklist. Without a validator branch, `validate_one_file` raises `NotImplementedError`, `/validate` answers 500, and the contribution editor has to lock the database (`qualityCheckSupported: false` in `frontend/src/utils/contribution.ts`), which means nobody can submit to it through the hub.

1. **`validate_one_file()` branches**, mirroring the uploader:
   - `Type.NEW_THING` → `TableValidator(NewThing)`
   - `Type.NEW_THING_SUB` → `CsvFileValidator(NewThing, [<the exact headers the uploader reads>], "id")` for each time-series type.
2. **`PRIMARY_TYPE_MAP`** — add `Type.NEW_THING_SUB: Type.NEW_THING` for each child type. `PRIMARY_TYPES` and the primary-CSV lookup in `validate_all` derive from it.
3. Frontend: in `frontend/src/utils/contribution.ts` set `qualityCheckSupported: true`, and in `frontend/src/utils/timeseries.ts` give each kind the same `requiredColumns` as the validator (`tests/test_contribution_layout.py` pins the directories; `TestTensileCoupons` in `tests/test_validator.py` is the model for the backend test).

---

## Step 5: Backend: Alembic migration

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

## Step 6: Regenerate OpenAPI + frontend client

From the repo root:

```bash
make api
```

This runs `DATABASE_UPGRADE=false uv run python api.py ../openapi.json`, then `python -m resslab_hub.data.columns ../database-columns.json`, then `pnpm run api` in the frontend. Result: fresh `openapi.json` and `database-columns.json` at the repo root plus regenerated `frontend/src/backend/` (with `NewThingApi`, `NewThingModel`, `NewThingField`, `NewThingNumberField`). Commit these regenerated files.

---

## Step 7: Frontend: axios API client instance

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/plugins/axios.ts`

Two edits mirroring `ebfApi`:

```ts
import { NewThingApi } from "@/backend/api";
// ...
export const newThingApi = new NewThingApi(undefined, baseUrl, axiosInstance);
```

---

## Step 8: Frontend: router

No file in `views/`: the routes point at the components of Step 9 directly. The parent route has no component, so vue-router renders the children in `App.vue`'s `<router-view>`.

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/router/index.ts`

Add a block modeled on the EBF route:

```ts
{
  path: '/new-things',
  children: [
    { path: '', redirect: '/new-things/database' },
    { path: 'database', component: () => import('@/components/new_thing/NewThingDashboard.vue') },
    // add 'model' or 'fragility-curve' children only if the component has those views
  ],
}
```

**Naming decision for the URL slug** — remember the #225 lesson: EBF moved from `/eccentric-braced-frames` to `/ebf-links`. Pick the short, user-facing slug up front, not the scientific full name, to avoid renaming later. Keep backend identifiers full snake_case; only the URL/nav labels get the short form.

**Optional: Model view.** Components that ship a published analytical model (closed-form backbone + fragility curve) add a second child route. HSS shows the full pattern:

- `frontend/src/components/hss/HssModel.vue` — the UI itself, routed directly (section picker backed by the transformed section CSVs in Step 14, parameter inputs, live-rendered backbone curves).
- Router block becomes:
  ```ts
  children: [
    { path: "", redirect: "/hss-columns/database" },
    { path: "database", component: () => import("@/components/hss/HssDashboard.vue") },
    { path: "model", component: () => import("@/components/hss/HssModel.vue") },
  ];
  ```
- Nav: add a `{ title: 'Model', to: '/model' }` entry alongside `Database` in `App.vue`.

Don't scaffold a Model view unless the component actually has a published model. EBF is database-only and deliberately ships without this route. Connections and Braces have one; HSS has one.

**You can scaffold the Model view and ship it disabled.** Braces did: `BraceModel.vue` exists and compiles, but the menu entry is commented out (commits `bb422f2` / `f5c214b`, `fix(braces): hide component model tab braces #213`). If your analytical model isn't production-ready but the code skeleton is useful, drop the nav entry and leave the route unlisted — the files stay, the tab is simply not reachable from the UI.

**Optional: Fragility Curve view.** If your component has published fragility parameters (damage-state medians/dispersions as functions of specimen properties), add a third child route. Braces is the only example today:

- **Component:** `frontend/src/components/new_thing/NewThingFragility.vue` — the UI, routed directly. Reference implementation: `frontend/src/components/braces/BraceFragility.vue`.
- **Shared utility:** `frontend/src/utils/fragility.ts` — `fragilityCurve(median, sigma)` via `@stdlib/stats-base-dists-lognormal-cdf`, plus `univariateOption()` and the `DamageState` interface. Do NOT reinvent these; import from this file.
- **3D surface plots:** `echarts-gl` via `frontend/src/utils/echarts-gl.ts`. Already installed — no new deps needed.
- **Parameter source:** fragility parameters are **not** stored in the data repo or the database. They are computed externally in the sibling repo `resslab-hub-scripts` (e.g. `fragility_curves_steel_braces/`) and **hard-coded as TypeScript constants** in the fragility component. This is deliberate — fragility parameters are a published research artifact, not experimental data.
- **Router block becomes:**
  ```ts
  children: [
    { path: "", redirect: "/new-things/database" },
    {
      path: "database",
      component: () => import("@/components/new_thing/NewThingDashboard.vue"),
    },
    {
      path: "fragility-curve",
      component: () => import("@/components/new_thing/NewThingFragility.vue"),
    },
    { path: "model", component: () => import("@/components/new_thing/NewThingModel.vue") },
  ];
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

## Step 9: Frontend: components

Create `/mnt/data/Documents/Code/resslab-hub/frontend/src/components/{short_name}/` — use the **short, human-friendly name** (EBF → `components/ebf/`, HSS → `components/hss/`), not the full snake_case. Backend module paths and data-repo folders use full snake_case; URL slug, frontend component folder, and class-name acronyms use the short form. Populate the folder with:

| File                               | Purpose                                                                                                                                                                                      | Template to copy                             |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `NewThingDashboard.vue`            | Layout (table + detail + charts); defines `parallelFields`, `doubleChartFields`, color palette. Uses `useDashboard<NewThingModel>`.                                                          | `components/ebf/EbfDashboard.vue`            |
| `NewThingTable.vue`                | Paginated data grid. Uses `useTable<NewThingModel>` and `newThingApi.getNewThings()`. Emits row click to the dashboard.                                                                      | `components/ebf/EbfTable.vue`                |
| `NewThingDetail.vue`               | Detail panel for selected row. Fetches time-series via `newThingApi.getNewThingSub()`. Wraps `CommonDetail.vue`. Renders configuration image via utility helper.                             | `components/ebf/EbfDetail.vue`               |
| `data.ts`                          | The dataset key and fetcher, plus `NEW_THING_SOURCE: DatasetSource<NewThingField>` (key, fetcher, i18n prefix `'new_thing.'`, id field, `NewThingNumberField`). The dashboard passes it to every chart.                       | `components/ebf/data.ts`                     |

No chart component per tab: the dashboard uses the generic `DatasetSingleChart`, `DatasetDoubleChart` and `DatasetParallelChart` from `components/commons/charts/` with `:source="NEW_THING_SOURCE"`. `DatasetSingleChart` takes an optional `mapping` prop to map raw values (e.g. `hot-rolled` → `Hot-Rolled`, see the EBF `l_confi` cell) and `image-for` for a figure in the tooltip. No new composables needed: reuse `composables/dashboard.ts`, `table.ts`, `chart.ts` with the new type params.

What the copied templates give you, so you know what not to reinvent (the whole engine is described in [dashboard-architecture.md](dashboard-architecture.md)):

- The dashboard sits in `components/commons/DashboardShell.vue` (head, toolbar, active filter chips, `#table` / `#charts` / `#detail` slots) and gets its data from `useDataset()`: one drain of the paginated list endpoint, then every count, range and matrix is computed in the browser. The filter rail (`AutoFilterRail.vue`, `useAutoFilters()`) is derived from the data dictionary, so a new column shows up as a filter without any list to edit.
- `NewThingDetail.vue` wraps `components/commons/CommonDetail.vue` and hands it `DetailCarouselItem[][]` (title, axis labels, series or a promise of one), plus `databaseId` and `record` so the drawer lists every property grouped by scientific category (`GroupedProperties.vue`).
- The table uses `useVirtualRows()` and `useColumnWidths()` through the shared table component; do not add a Vuetify data table.
- Chart colours for categorical fields come from `useDataset(...).colorFor(field)`, never from a palette in the chart (see Step 10b).

---

## Step 10: Frontend: utilities

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

The overview map needs no field list here any more, see Step 12.

---

## Step 10b: Field groups and colours

Two things the test suite and the UI expect from every new column:

- **A scientific category.** `frontend/src/utils/fieldGroups.ts` maps every column of every database to a group id; `groupFor()` prefers the `group` column of the data dictionary (Step 1.2) and falls back to the per-database patterns in that file. A column with neither lands in `other`, and `fieldGroups.spec.ts` fails: it reads the real column list from `database-columns.json` (add the database to `DATABASE_MODELS` in `backend/resslab_hub/data/columns.py`, then `make api`). Add the database to `FIELD_GROUPS` there, mirroring the dictionary. Tables of the existing groups: [variable-categories.md](variable-categories.md).
- **Stable colours.** `frontend/src/utils/categoryColors.ts` gives Okabe-Ito slots per field by frequency in the unfiltered dataset, so the treemap, the stacked histogram and the brush agree and a value keeps its colour when filters change. Nothing to add for a new tab; pin a value with `CATEGORY_COLOR_OVERRIDES` (`'<dataset key>:<field>'`) only if a colour people learnt gets reshuffled by a data upload.

---

## Step 11: Frontend: i18n

Files: `frontend/src/locales/en.json` and `frontend/src/locales/fr.json`

Add a `new_thing` namespace with every display-critical field label, e.g.:

```json
"new_thing": {
  "field_a": "Field A",
  "field_b": "Field B"
}
```

Every key must exist in both files. French keeps its accents (`Propriétés de la section`, not `Proprietes`).

---

## Step 12: Overview map

The home map reads one endpoint, `GET /map/sites`, which groups the rows of every database by site (lat/lon rounded to 2 decimals). If the new table has `latitude` and `longitude`, it needs four small edits:

1. `backend/resslab_hub/models/map.py`: add a `MapCategory` value, the same string as the router's `Component`.
2. `backend/resslab_hub/routers/map.py`: add a `_Source` to `_SOURCES`. It names the table and the columns that hold the program (`investigator` or `experimental_program`), the year, the link and, if the tab has schematics, the column that picks one (`figure`). Then `make api`.
3. `frontend/src/utils/mapCategories.ts`: add an entry to `MAP_CATEGORIES` (label key, alt key, database route). The colours come from the 8 Okabe-Ito slots then one grey, so a 10th database needs its own colour: `mapCategories.spec.ts` fails if two categories share one.
4. `frontend/src/utils/mapSites.ts`: add a case to `programImage()` that returns the schematic from `utils/component.ts`. Add `map.category_<x>` and `map.alt_<x>` to `en.json` and `fr.json`.

The map, its panel and its legend pick up the new category from there. Site names come from `frontend/src/assets/map-sites.json` (keyed by the same `lat,lng`); a new lab shows its coordinates until someone adds it there.

---

## Step 13: Frontend: home page indicator

File: `/mnt/data/Documents/Code/resslab-hub/frontend/src/views/HomeView.vue`

1. Import `newThingApi` from `@/plugins/axios`.
2. Add `newThingApi.getNewThingsDistinct()` to the `Promise.all([...])` that aggregates the test-count indicator. Missing this is a common miss — #225 `3952af4` added EBF to this aggregation after the fact.

---

## Step 14: Static assets

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

## Step 15: Shared-component touch-ups commonly needed

The EBF iteration showed that adding a tab often requires _small_ improvements to shared components. Keep an eye out for these:

- `components/commons/charts/SingleChart.vue` — accept an optional `mapping` prop if your values need humanization (commit `bafde72`).
- Parallel chart height — the #225 fix (`0bf430f`) made parallel chart height computed so every category is visible. This is now generic; just make sure your parallel chart's dimensions are set so no labels are cut off.
- `SteelTypeCardTitle.vue` or other card-title components — extend tooltips if your detail view surfaces new property categories.

---

## Step 16: Contribution, validation and curation

A tab is not done when it browses. Contributors must be able to submit to it and the lab to review it:

| Where                                   | What                                                                                                                                                                                                                                                                                                                                                 |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/resslab_hub/data/validator.py` | a `case Type.NEW_THING` branch (and one per series type) in `validate_one_file`, so `POST /validate` checks the CSV against the model and the README's rules. Without it the type raises `NotImplementedError` (tensile coupons, EBF and ductile fracture shipped like that, #274). Range warnings come for free from `TableValidator._check_range`. |
| `backend/resslab_hub/data/uploader.py`  | `README_DATABASES` entry for the folder (Step 1.1), and the `get_args_all` tuples the contribution archive layout follows.                                                                                                                                                                                                                           |
| `frontend/src/utils/contribution.ts`    | a `CONTRIBUTION_DATABASES` entry: backend `Type`, primary CSV path inside the archive, `qualityCheckSupported: true` once the validator branch exists. This is also what the curation review and the edit flow use to place files.                                                                                                                   |
| `frontend/src/utils/timeseries.ts`      | `requiredColumns` per series directory, so the editor recognises a dropped curve file by its headers and folder name.                                                                                                                                                                                                                                |
| `sample-data/generate.py`               | a `DATABASES` entry and the `TIME_SERIES` shapes, so `make sample-data` produces a test batch.                                                                                                                                                                                                                                                       |
| `backend/resslab_hub/data/columns.py`   | a `DATABASE_MODELS` entry keyed by the frontend database id, then `make api`, so `database-columns.json` lists the new columns and `fieldGroups.spec.ts` checks their categories.                                                                                                                                                                    |
| `frontend/src/utils/curation.ts`        | derived columns (`withDerivedCells`) if the ORM computes any `column_property` the review must show.                                                                                                                                                                                                                                                 |

Then walk the whole pipeline once with the sample batch: [contributing-data.md](contributing-data.md) and [curation.md](curation.md). Close the pull request it opens on the data repo, never merge it.

---

## Gotchas harvested from issue #225 (do these up front, not as fixes later)

1. **Pick the short display name first.** We renamed "Eccentric Braced Frames" → "EBF Links" after launch; URLs, menus, `typesNames`, `Type` union all had to change. Commit to the short form before starting.
2. **Don't lower-case data values.** Keys like `TF1`/`LC5` are already correctly cased in the dictionary. Omit `.toLowerCase()` in frontend mappings; add it only if the data genuinely disagrees.
3. **Integrate indicators day one.** `HomeView.vue` test-count aggregation and overview-map data-length both need the new API. Adding these late means a second PR.
4. **Validate the data dictionary twice.** EBF needed a schema-refinement migration (`f5abf9d8561b`) because nullability/naming drifted during review. Run `make generate-model` → inspect diff → hand to a reviewer _before_ the first migration lands.
5. **Chart colors.** Default palettes looked muddy for EBF; pick distinct colors early (see `EbfDashboard.vue` palette).
6. **Parallel-chart sort order.** Ordered categorical axes (`short → intermediate → long`) need explicit `sortValues`. Commit `a3bee8a` restored these after they were lost.
7. **Image sizing.** Detail images need a max-width (EBF fix: 50% of row). Set responsive CSS from the start, don't let the raw PNG expand.
8. **TypeScript imports.** Ensure all new types (`NewThingModel`, `NewThingField`, `NewThingNumberField`) are exported from the generated barrel so `vue-tsc` passes. `fix(ebf): fix import type build problem` (`573cc4a`) caught a circular-import regression — run `pnpm run type-check` before opening the PR.
9. **Info tooltips on table columns.** Users asked for field explanations (commit `476c98e`). Add `InfoTooltip` to column headers from the start with a short description from the data dictionary.
10. **Carousel / detail content.** Don't ship a detail view with only raw fields — group them ("Loading and Geometric Parameters", "Steel Material Designation (flange / web)") and label units. EBF got two rounds of detail-content rework (`bdec4f8`, `50ba7f7`, `e70b30d`).
11. **Data-repo validation workflow filter.** `.github/workflows/data-validation.yml` has a hardcoded `filters:` list. EBF was never added to it, so no EBF PR has ever been validated by CI. Add your filter line _before_ opening the first data-repo PR; otherwise silent pass-through is indistinguishable from a real green check.
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

- `frontend/src/components/ebf/*` (dashboard, table, detail, `data.ts` with `EBF_SOURCE`).
- `frontend/src/components/commons/charts/Dataset{Single,Double,Parallel}Chart.vue`: the dashboard charts.
- `frontend/src/utils/ebf.ts`, `component.ts`, `backend.ts`, `mapCategories.ts`, `mapSites.ts`.
- `frontend/src/plugins/axios.ts` — API client registrations.
- `frontend/src/router/index.ts`, `App.vue` — routing + nav.
- `frontend/src/locales/en.json` — i18n.
- `frontend/src/views/HomeView.vue` — indicator aggregation.
- `backend/resslab_hub/routers/map.py`, `models/map.py` — the overview map's data.
- `frontend/src/components/commons/charts/SingleChart.vue` — shared chart with `mapping` prop.

HSS-specific references (useful when your tab needs a Model view or section libraries — neither of which EBF has):

- `backend/resslab_hub/routers/hss_columns.py` — older plural-named router; still a clean example of the shared `Component` + `SubComponent` shape.
- `frontend/src/components/hss/HssModel.vue` — Model-tab template.
- `backend/data/hss_csv_transformer.py` — custom section-library transformer template.
- `frontend/src/assets/hss/hss-aisc-sections.csv`, `hss-european-sections.csv`, `hss-japanese-sections.csv` — output shape of the transformed section libraries (these are committed assets, not runtime fetches).

Braces-specific references (useful when your tab needs a Fragility Curve view — Braces is the only example today):

- `backend/resslab_hub/routers/braces.py` — the oldest router, plural convention like HSS; still a clean example of the shared `Component` + `SubComponent` shape with id-as-filename time-series.
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
   - `cd frontend && pnpm run type-check` — clean.
   - `cd frontend && pnpm run lint` — clean.
   - `make dev-frontend` — Vite up.
   - Navigate `http://127.0.0.1:5173/new-things/database`:
     - Table renders rows; pagination, sorting, filtering work.
     - Clicking a row opens the detail panel; carousel shows curves; configuration image loads.
     - The URL gets `?specimen=<id>`. The drawer's share link opens the same specimen in a new tab.
     - Parallel, double, single charts render; colors are distinct; labels aren't truncated.
     - CSV export downloads.
   - Home page `/` — the test-count indicator includes the new component.
   - Overview map — the new category is in the legend and the markers; a site's program opens `/new-things/database?specimen=...` from "View experimental data".
   - Switch locale to French, every new label translates, nothing falls back to the key.

4. **Build**

   - `cd frontend && pnpm run build` — production build passes.
   - `cd .. && make run` — full Docker stack comes up; hit `https://localhost/api/new-thing` through Traefik (remember the `/api` prefix in prod).

5. **Commit hygiene**
   - Follow Conventional Commits (`feat(<short_name>): ...`, `fix(<short_name>): ...`) — commitlint is enforced.
   - Keep migrations in their own commit; keep generated `openapi.json`/`frontend/src/backend/` updates in the same commit as the backend changes they reflect.

---

## Summary: minimum file set for a new tab with one time-series child (like EBF)

Backend (NEW unless noted):

- `backend/resslab_hub/routers/new_thing.py`
- `backend/resslab_hub/models/database/new_thing.py`
- `backend/resslab_hub/models/database/__init__.py` _(edit — 1 line)_
- `backend/resslab_hub/models/api.py` _(edit — add Model + 2 enums)_
- `backend/resslab_hub/main.py` _(edit — import + include_router)_
- `backend/resslab_hub/data/uploader.py` _(edit — Type enum, handlers, get_args_all)_
- `backend/Makefile` _(edit — `generate-model` + `upload-new-thing`)_
- `backend/alembic/versions/<rev>_add_new_thing_model.py` _(autogenerated, reviewed)_

Frontend (NEW unless noted):

- `frontend/src/components/new_thing/NewThingDashboard.vue`
- `frontend/src/components/new_thing/NewThingTable.vue`
- `frontend/src/components/new_thing/NewThingDetail.vue`
- `frontend/src/components/new_thing/data.ts` _(with `NEW_THING_SOURCE`)_
- `frontend/src/utils/new_thing.ts`
- `frontend/src/utils/component.ts` _(edit — add `getNewThingImage`)_
- `frontend/src/utils/backend.ts` _(edit — `Type` + `typesNames`)_
- `frontend/src/utils/mapCategories.ts`, `mapSites.ts` _(edit — map category + schematic)_
- `frontend/src/plugins/axios.ts` _(edit — `newThingApi`)_
- `frontend/src/router/index.ts` _(edit — route block)_
- `frontend/src/App.vue` _(edit — menu item)_
- `frontend/src/locales/en.json` _(edit — `new_thing._` keys)\*
- `frontend/src/views/HomeView.vue` _(edit — distinct call)_
- `backend/resslab_hub/models/map.py`, `routers/map.py` _(edit — `MapCategory` + `_SOURCES`)_
- `frontend/public/img/new_thing/*.png` _(assets, if configuration diagrams)_
- `openapi.json` + `frontend/src/backend/*` _(regenerated, committed)_

Total for a tab like EBF: ~20 edits + ~14 new files + auto-regenerated client and migration.
