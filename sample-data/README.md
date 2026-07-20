# Sample contribution records

Synthetic single-record CSVs for exercising the contribution pipeline
(`/contribute/new`). The values are invented — specimen IDs are prefixed `DEMO-`
and the investigator is "Demo Investigator" — but the column sets and value
*types* come straight from the SQLAlchemy models, so the backend validator
treats them as real submissions.

Two files per database:

| File | Expectation |
|---|---|
| `<name>.csv` | Every column populated with a valid value → quality check **passes** |
| `<name>.invalid.csv` | Same record with seeded type errors → quality check **fails** |

The directory layout mirrors what the backend expects inside an upload archive
(`get_args_all` in `backend/resslab_hub/data/uploader.py`).

## Using them in the UI

1. Start the backend, database and `npm run dev`.
2. Go to `/contribute/new`, sign in, and pick the matching database in step 1.
3. In **step 3**, drop the CSV on the import zone. It reads the first data row
   and fills the metadata form.
4. **Step 4** runs the real quality check.

Step 1 must match the file — the importer aligns headers against the selected
database's columns and refuses a file with no overlap.

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

## Regenerating

Re-run after any schema change — the fixtures are only as current as the models:

```bash
cd backend && uv run python ../sample-data/generate.py
```

`generate.py` reads the ORM column types and seeds one failure per validator
branch (non-numeric in a numeric column, non-integer in an integer column, a
value outside `yes`/`no` in a boolean, a malformed date, and the `NA` case
above). Databases without a boolean or date column simply get fewer seeds.
