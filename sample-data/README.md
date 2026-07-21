# Sample contribution records

Synthetic single-record CSVs for exercising the contribution pipeline
(`/contribute/new`). The values are invented — specimen IDs are prefixed `DEMO-`
and the investigator is "Demo Investigator" — but the column sets and value
*types* come straight from the SQLAlchemy models, so the backend validator
treats them as real submissions.

## Generate them first

The CSVs are **not committed** — they are generated output derived from the ORM
schema, so a stale copy in git would silently disagree with the current models.
Only `generate.py` and this README are versioned; the CSVs are gitignored.

Create them (needs the backend's `uv` environment, which you already need to run
the validator these files are tested against):

```bash
cd backend && uv run python ../sample-data/generate.py
```

Re-run it after any schema change — the fixtures are only ever as current as the
models. Without this step the `sample-data/` subdirectories are empty.

Per database:

| File | Expectation |
|---|---|
| `<name>.csv` | Every column populated with a valid value → quality check **passes** |
| `<name>.invalid.csv` | Same record with seeded type errors → quality check **fails** |
| `<subdir>/DEMO-*.csv` | Measured response (time-series), 60 rows, valid |

The directory layout mirrors what the backend expects inside an upload archive
(`get_args_all` in `backend/resslab_hub/data/uploader.py`).

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
found in primary CSV". Step 3 of the wizard renames attachments automatically
for this reason.

The generated series are an open hysteresis loop with growing amplitude — the
right *shape* for a cyclic test, but not real physics.

## Using them in the UI

1. Start the backend, database and `npm run dev`.
2. Go to `/contribute/new`, sign in, and pick the matching database in step 1.
3. In **step 2**, drop the record CSV on the prefill bar above the fields. It
   reads the first data row and fills the form; you can then edit any field.
4. In **step 3**, drop the matching time-series file on each slot. They are
   optional — the record validates without them.
5. **Step 4** runs the real quality check over the record and every attachment.

Step 1 must match the file — the importer aligns headers against the selected
database's columns and refuses a file with no overlap. Prefilling is optional;
every field can be typed in directly.

## Using them with curl

```bash
tar czf braces.tar.gz braces/
curl -u user:$API_PASSWORD -F file=@braces.tar.gz \
  "http://127.0.0.1:8000/validate?type=all-braces"
```

Note the archive must contain the component directory, not a bare CSV.

## Coverage

Only six of the nine databases can be validated. `validate_one_file` has no
branch for **tensile coupons, ductile fracture and EBF** — they raise
`NotImplementedError`, which surfaces as HTTP 500. The UI marks these
"validation not yet available" and skips the request, so their CSVs are useful
for exercising the import step but not the check.

## One difference between the two paths

An `.invalid.csv` reports **one fewer error through the UI** than via curl.

The seeded errors include `NA` in a non-nullable column. Posted directly, that
is a "Field cannot be null" error. Imported through the UI, `NA` is read as
"no value" (which is what it means in the archive format), so the field arrives
blank, gets submitted as `NR`, and the validator skips it. Both behaviours are
correct; they just exercise different branches.

## How the generator works

`generate.py` (run it as shown at the top) reads the ORM column types and seeds
one failure per validator branch into each `.invalid.csv`: a non-numeric value
in a numeric column, a non-numeric value in an integer column, a value outside
`yes`/`no` in a boolean, a malformed date, and an `NA` in a non-nullable column.
Databases without a boolean or date column simply get fewer seeds.
