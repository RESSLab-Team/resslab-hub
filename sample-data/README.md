# Sample contribution records

Synthetic **batches** of experiments for exercising the contribution pipeline
(`/contribute/new`). The values are invented — specimen IDs are prefixed `DEMO-`
and the investigator is "Demo Investigator" — but the column sets and value
*types* come from the SQLAlchemy models, and the numeric *magnitudes* come from
the data already in your database, so the backend validator treats them as real
submissions.

## Generate them first

The CSVs are **not committed** — they are generated output derived from the ORM
schema and the database contents, so a stale copy in git would silently disagree
with both. Only `generate.py` and this README are versioned.

```bash
make sample-data            # from the repo root, or from backend/
```

Options: `EXPERIMENTS=N` (default 15) and `OUTLIERS=N` (default 3, see below).
Re-run after any schema change or data upload. Without this step the
`sample-data/` subdirectories are empty.

Use the make target rather than calling `generate.py` directly — it points
dynaconf at `secrets/.env`, and without that the database is unreachable, so the
generator falls back to type-based values and seeds **no range warnings**. It
says so per database when that happens.

Per database:

| File | Expectation |
|---|---|
| `<name>.csv` | 15 experiments, all type-valid → quality check **passes**, with range warnings on the last 3 |
| `<name>.invalid.csv` | The same batch with type errors seeded into 2 rows → quality check **fails** |
| `<subdir>/DEMO-*.csv` | Measured response (time-series), one per experiment and per response type the database has (every database has at least one); row counts follow the real files |

The directory layout mirrors what the backend expects inside an upload archive
(`get_args_all` in `backend/resslab_hub/data/uploader.py`).

## Range warnings

`POST /validate` warns when a value sits more than one full span outside the
`[min, max]` of the existing data for that column, and only for columns with at
least `RANGE_MIN_COUNT` (20) values in the database. The warning does not make
the submission invalid — it asks the contributor to double-check the value.

The generator drives both sides of that rule from the same query the validator
uses:

- **In-range rows** — every numeric column with enough data gets a value drawn
  from inside its own observed range, spread across the batch. These raise no
  warnings, which is what makes the warnings on the other rows meaningful.
- **Out-of-range rows** — the last `--outliers` experiments (3 by default) each
  get 2 columns set to `max + 3 × span`, comfortably past the threshold. Each
  outlier row targets *different* columns, so the batch surfaces the warning on
  several fields rather than the same one repeatedly.

The run prints exactly which value on which specimen will warn, and against
which range, e.g.:

```
braces: 15 experiments × 71 columns -> braces/steel_braces.csv  [DEMO-BRC-001 … DEMO-BRC-015]
    in range: 38 columns have ≥ 20 values in the database, so their values are drawn from it
    warning: DEMO-BRC-013: area=68050.53 — outside 116.49 to 17100
    warning: DEMO-BRC-014: t_br=82.4 — outside 2 to 22.1
```

which is the same range the UI then quotes back: *"Value is far outside the
range of existing data for this column (116.49 to 17100) — please verify it."*

**A populated database is required** for this half to work. Against an empty
database no column reaches 20 values, the generator says so per database, and
the batch is still type-valid — just without warnings. `make upload-data` first.

Columns with fewer than 20 values keep a plain type-based default, since the
validator cannot warn about them either way.

## Time-series files

Six databases accept measured-response files, in fixed subdirectories:

| Database | Subdirectories |
|---|---|
| Braces | `force_displacement/` |
| Columns | `axial_shortening_rotation/`, `moment_rotation_strong/`, `moment_rotation_weak/` |
| Connections | `Beam_moment_rotation/`, `Beam_moment_rotation_west/`, `Global/`, `Global_west/`, `Panel_zone/` |
| HSS columns | `Moment_Rotation/` |
| Cyclic coupons | `stress_strain/` |
| Residual stresses | `Distributions/Distributions_{F1,F2,W1}/`, `QP_Coefficients/` |

Each has its own required column names, and **the filename is the foreign key**:
a time-series must be called `<specimen id>.csv` and travel in the same archive
as a record whose `id` matches, or validation fails with "Foreign key … not
found in primary CSV".

One file is written per experiment, so a 15-experiment batch produces 15
attachments per subdirectory — which is what the editor's drop zone is for: a
whole `sample-data/<db>/` folder (or a zip of it) lands in one go, the primary
CSV recognised by its headers, each curve file by its folder name and stem.

### Curve shapes

Each kind gets its own curve, because the card sparkline plots column 1 against
column 2 and **normalises both axes** — so two files sharing a shape look
identical no matter how their magnitudes differ. Amplitude alone is not enough.

The cyclic kinds integrate a bilinear kinematic-hardening model over a stepped
loading protocol (two cycles per amplitude step), which is the standard
idealisation of a steel test and the reason the loops enclose area instead of
tracing a single line. Peaks and row counts come from the matching directory in
the data repo:

| Kind | Shape |
|---|---|
| Braces, force–displacement | Asymmetric: tension yields and hardens, compression buckles and keeps fading |
| Columns, axial shortening | Ratchet — rotation cycles one-sided, shortening only ever accumulates |
| Moment–rotation, strong axis | Stable nested loops, slight strength loss |
| Moment–rotation, weak axis | More cycles, visibly shrinking loops |
| Connections, beam / global | As strong axis; the `_west` pair degrades faster |
| Panel zone | Pinched — the loop collapses to a waist through the origin |
| Cyclic coupon, stress–strain | No degradation, strong hardening — loops grow |
| Residual stress distributions | Spatial profile, not a loop: self-equilibrating across the section (flanges parabolic, web inverted, F2 tilted) |
| QP coefficients | Four values in a single column |

They are idealised, not measured: smooth, noise-free, and without the drift or
instrument scatter of the real files. Enough to exercise the UI and the
validator, not to stand in for real data.

## Using them in the UI

1. Start the backend, database and `npm run dev`.
2. Go to `/contribute/new` and pick the matching database.
3. Drop the `sample-data/<db>/` folder on the editor (or **Choose a folder**,
   or zip it and drop the zip) → 15 experiment cards with every curve file
   attached. The "Last drop" report notes that `<name>.invalid.csv` also looked
   like a primary CSV and was left alone.
4. Validation runs automatically ~2 s after you stop editing. Expect: 12 clean
   cards, 3 cards with range warnings on the fields listed by the generator.
5. Drop `<name>.invalid.csv` on its own to see errors (rows 2 and 7) alongside
   the warnings — a realistic mixed batch. A second drop merges by id, so the
   attachments stay.
6. To see the report's resolution controls, drop a few curve files loose (no
   folder) on Residual stresses: F1, F2 and W1 share headers, so the files are
   listed as ambiguous with a "set all" select.

Import aligns headers against the selected database's dictionary columns and
refuses a file with no overlap, so step 2 must match the file.

## Using them with curl

```bash
tar czf braces.tar.gz braces/
curl -F file=@braces.tar.gz "http://127.0.0.1:8000/validate?type=all-braces"
```

The archive must contain the component directory, not a bare CSV. `/validate`
needs no credentials; it always answers `200` with a structured body, so read
`valid` / `results`, not the HTTP status. Note that tarring the whole directory
includes `<name>.invalid.csv`, which the backend ignores (it globs the exact
primary CSV name) — copy the one file you want into a clean directory to check
the invalid variant.

## Coverage

Only six of the nine databases can be validated. `validate_one_file` has no
branch for **tensile coupons, ductile fracture and EBF** — they raise
`NotImplementedError`, which surfaces as HTTP 500. The UI marks these
"validation not yet available" and skips the request, so their CSVs are useful
for exercising the editor and import but not the check.

## One difference between the two paths

An `.invalid.csv` reports **one fewer error per seeded row through the UI** than
via curl.

The seeded errors include `NA` in a non-nullable column. Posted directly, that
is a "Field cannot be null" error. Imported through the UI, `NA` is read as
"no value" (which is what it means in the archive format), so the field arrives
blank, gets submitted as `NR`, and the validator skips it. Both behaviours are
correct; they just exercise different branches.

## How the generator works

`generate.py` reads the ORM column types, queries the database for per-column
`(count, min, max)` exactly as `TableValidator._range_stats` does, and seeds one
failure per validator branch into two rows of each `.invalid.csv`: a non-numeric
value in a numeric column, a non-numeric value in an integer column, a value
outside `yes`/`no` in a boolean, a malformed date, and an `NA` in a non-nullable
column. Databases without a boolean or date column simply get fewer seeds. Year
columns are never used as outliers — a date in the far future reads as a broken
record rather than a value worth double-checking.
