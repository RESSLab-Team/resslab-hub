# Sample contribution batches

Test batches for the contribution pipeline (`/contribute/new` and `POST /validate`), one per database. Each row starts from a real record of the database, so the values look like real data. Some values are wrong on purpose, to show the warnings and the errors of the validator.

## Make them first

The CSVs are not committed. They come from the ORM schema, the database and the data repo, so a copy in git would go stale. Only `generate.py` and this README are in git.

```bash
make sample-data            # from the repo root, or from backend/
```

Options: `EXPERIMENTS=N` (default 15) and `OUTLIERS=N` (default 3). Run it again after a schema change or a data upload.

Use the make target. It points dynaconf at `secrets/.env` (without it, the database is unreachable) and passes the data repo with `--data-dir $(RESSLAB_DATA_DIR)`. The script has more flags. To use them, run it the way the target does, from `backend/`:

```bash
DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python ../sample-data/generate.py \
    --data-dir "$RESSLAB_DATA_DIR" --seed 1 --max-rows 200
```

| Flag | Default | What it does |
|---|---|---|
| `--experiments` | 15 | Rows per batch |
| `--outliers` | 3 | Rows at the end with values far out of range |
| `--seed` | 0 | Another seed picks other records and other jitter. The same seed gives the same files |
| `--data-dir` | none | The `resslab-hub-data` checkout, for the real curves |
| `--max-rows` | 500 | Longest curve kept. Longer real curves are downsampled |
| `--no-check` | off | Skip the self-check at the end |

Per database, you get:

| File | Expected result |
|---|---|
| `<name>.csv` | N experiments. The quality check passes, with range warnings on the last 3 rows only |
| `<name>.invalid.csv` | The same batch with one problem per row. The quality check fails |
| `<subdir>/<id>.csv` | The measured curves of each experiment, named after its id |

The folders follow the layout that the backend expects inside an upload archive (`get_args_all` in `backend/resslab_hub/data/uploader.py`).

## Where the values come from

The script reads every row of the table and keeps the complete ones: no empty mandatory cell, and the rules of the database hold (ductile fracture lists are lists of numbers, residual stresses declare 1 or 2 flanges). It then picks N of them, one research program after the other, so a batch mixes several programs. When the data repo is there, it prefers the records that have all their curves.

Each row copies its record (its "template"), then changes it:

- The numbers move by a few percent: one factor per row (0.94 to 1.06), times a small noise per column (0.99 to 1.01). The factor is shared by the whole row, so the ratios between columns stay close to real (b/t, fu/fy, kl/r). The decimals stay the same as the source.
- Some numbers do not move: whole numbers, years and dates, latitude and longitude, and columns with fewer than 5 different values in the table (E = 200000, a fixed temperature). A value that would leave the existing range also keeps its template value.
- The fields that say who did the test are replaced: `id` (`DEMO-<prefix>-001`), investigator, reference, link and url, and the specimen name (`DEMO-SPEC-01`).
- EBF ids must be whole numbers, so EBF rows get the next free ids after the largest one in the table.
- Ductile fracture `has_sem` is `NR`, because the hub sets it.
- Residual stresses keep the `flange_nr_data` of the template, and get a second flange curve only when it says 2.

The run prints how many records were usable, for example `values: from 15 real records (271 of 294 usable)`.

Without the database, or with an empty table, each column gets one fixed value of its type, and no range warning is possible. The run says so for each database.

## Range warnings

`POST /validate` warns when a number is more than one full span outside the `[min, max]` of the existing data for its column. It only does this for columns with at least `RANGE_MIN_COUNT` (20) values in the database. The warning does not block the submission. It asks the contributor to check the value.

The last `--outliers` rows each get 2 columns out of range, a different pair on each row. The value looks like a real mistake: the template value times 1000 (a unit slip, mm written as µm) when that is far enough, else `max + 3 × span`. Years and coordinates are never used.

The run prints each one with the range that the UI quotes back:

```
braces: 15 experiments x 71 columns -> braces/steel_braces.csv  [DEMO-BRC-001 ... DEMO-BRC-015]
    values: from 15 real records (271 of 294 usable), numbers moved by up to 7 %
    warning: row 13: area=639000 (unit slip x1000, range 116.49 to 17100)
    warning: row 13: d_br=74000 (unit slip x1000, range 3.3 to 356)
```

Tensile coupons have fewer than 20 records, so they get no range warning.

## The invalid file

Each row of `<name>.invalid.csv` gets one problem, in this order. A database without the right kind of column skips that problem, so the row numbers move. The run prints the real row of each one.

| Problem | Example | Expected |
|---|---|---|
| Decimal comma without quotes | `3,5` | Error: the row has one value too many |
| Text in a number column | `N/A` | Error |
| A range in a whole-number column | `1980-1981` | Error |
| A decimal in a whole-number column | `2005.5` | Warning: it will be truncated |
| Not yes or no | `maybe` | Error |
| Bad date | `2025-13-45` | Error |
| Empty cell, column that accepts NA | | Warning |
| Empty cell, mandatory column | | Error |
| NaN | `NaN` | Warning (error in a mandatory column) |
| NA in a mandatory number column | `NA` | Error |
| NR in a mandatory text column | `NR` | Warning |
| Id with a space | `DEMO BRC 010` | Warning (error for EBF, ids are whole numbers) |
| Id with a slash | `DEMO-BRC/011` | Error: not a safe file name |
| Id of an earlier row | `DEMO-BRC-002` | Error: appears more than once |
| Id of the real record the row comes from | `Takeuchi_Matsui_1228` | Error: already exists in the database |

Some databases have their own checks:

| Database | Problem | Expected |
|---|---|---|
| Ductile fracture | `has_sem=yes` | Warning: leave it NR in a contribution |
| Ductile fracture | A list without its brackets (`loading_protocol`) | Warning |
| Residual stresses | `flange_nr_data` says 1 but a second flange curve is there, or the other way | Warning |

When there are more problems than rows, the rest go on the first rows again, on another column. The last rows keep their range warnings too, so the file also mixes errors and warnings like a real batch.

With very few rows (5 or less), the id problems run out of rows and some are dropped.

## Self-check

At the end, the script runs the real validator on both files, the way a submission does (`validate_all` with `check_duplicate_ids`). The clean folder must give the seeded range warnings and nothing else, curves included. The invalid file must give each expected message on its row, and nothing else. The run prints `check: ok` for each database, or the differences, and exits with an error if one database fails.

## Curves

All nine databases take measured curves, in fixed folders:

| Database | Folders |
|---|---|
| Braces | `force_displacement/` |
| Columns | `axial_shortening_rotation/`, `moment_rotation_strong/`, `moment_rotation_weak/` |
| Connections | `Beam_moment_rotation/`, `Beam_moment_rotation_west/`, `Global/`, `Global_west/`, `Panel_zone/` |
| HSS columns | `Moment_Rotation/` |
| EBF links | `processed_data/` |
| Cyclic coupons | `stress_strain/` |
| Tensile coupons | `stress_strain/` |
| Ductile fracture | `force_elongation/`, `force_radial/`, and the five simulation folders `force_elongation_simulation/`, `force_radial_simulation/`, `equivalent_plastic_strain_elongation_simulation/`, `lode_angle_elongation_simulation/`, `triaxiality_elongation_simulation/` |
| Residual stresses | `Distributions/Distributions_{F1,F2,W1}/`, `QP_Coefficients/` |

The file name is the foreign key. A curve must be called `<id>.csv` (EBF: `id<id>.csv`) and travel with a record that has this id, or the validator says "Foreign key … not found in primary CSV".

Each curve is the real curve of the template, from the data repo. The script keeps the header as it is, drops the rows that cannot be read, and keeps at most `--max-rows` rows (every k-th row, plus the last one). The second column (force, moment, stress) is multiplied by the row factor, so the curve follows its record. The Lode angle and the triaxiality are not scaled, they have no unit.

When the template has no real file for a folder:

- If the form requires that curve (for example braces `force_displacement`, columns `moment_rotation_strong`), the script writes a synthetic one.
- If the curve is optional, the file stays missing, like in the real test. The run counts them as "not in the real test".
- If the template has no real curve at all, or there is no `--data-dir`, every curve is synthetic.

### Synthetic shapes

The card sparkline plots column 1 against column 2 and normalizes both axes, so two files with the same shape look the same whatever their size. So each kind gets its own shape. The cyclic kinds come from a bilinear kinematic-hardening model over a stepped loading protocol (two cycles per step), so the loops enclose area.

| Kind | Shape |
|---|---|
| Braces, force vs displacement | Not symmetric: tension yields and hardens, compression buckles and keeps fading |
| Columns, axial shortening | Ratchet: rotation cycles on one side, shortening only grows |
| Moment vs rotation, strong axis | Stable nested loops, a small strength loss |
| Moment vs rotation, weak axis | More cycles, loops that shrink |
| Connections, beam and global | Like the strong axis. The `_west` pair degrades faster |
| Panel zone | Pinched: the loop gets thin near the origin |
| Cyclic coupon, stress vs strain | No degradation, strong hardening, loops that grow |
| EBF link, shear vs rotation | Loops cycled to failure, twelve cycles |
| Tensile coupon, stress vs strain | Monotonic tension: elastic rise, plateau, hardening, necking |
| Ductile fracture, force vs elongation or radial | Monotonic pull to fracture. The `_simulation` twin is the same curve with fewer points |
| Ductile fracture, plastic strain, Lode angle, triaxiality | Growth curves and the two stress-state values, simulation only |
| Residual stress distributions | A profile along the section, not a loop. It balances to zero (flanges parabolic, web inverted, F2 tilted) |
| QP coefficients | Four values in one column |

These shapes are smooth, with no noise and no drift. They are enough to test the UI and the validator, not to replace real data.

## Use them in the UI

1. Open `/contribute/new` and pick the matching database. The import matches the headers against the dictionary of this database and refuses a file with no match.
2. Drop the `sample-data/<db>/` folder on the editor (or use "Choose a folder", or drop a zip of it). You get 15 experiment cards with their curves. The "Last drop" report says that `<name>.invalid.csv` also looked like a primary CSV and was left alone.
3. The validation runs about 2 s after you stop editing. Expect range warnings on the last 3 cards, on the fields that the run printed, and nothing else.
4. To see the errors, drop `<name>.invalid.csv` alone on an empty batch.

The UI does not send the file as it is. It reads it into the editor and writes it again on submit, so a few problems look different than with curl:

| Problem | What the UI does |
|---|---|
| Decimal comma without quotes | The import splits `3,5` in two cells. The column gets `3`, and the next values of the row move one column to the right |
| Empty cell, column that accepts NA | Sent as `NR`. No warning |
| Empty cell, mandatory column | The editor warns that it will be sent as `NR`. Then the server reads `NR`: a warning in a text column, an error in a number column |
| Id of an earlier row | A drop merges rows by id, so this row updates the card of the earlier row. One card less, no error |

`NA` in a mandatory column stays `NA` in the editor, so it gives the same error on both paths.

## Use them with curl

```bash
tar czf braces.tar.gz braces/
curl -F file=@braces.tar.gz -u user:$API_PASSWORD "http://127.0.0.1:8000/validate?type=all-braces"
```

The archive must hold the database folder, not a bare CSV. `/validate` takes the machine credential (`API_PASSWORD` from `secrets/.env`, see `docs/src/auth.md`) or a session cookie. Without either, it answers `401`. With data problems it still answers `200` with a structured body, so read `valid` and `results`, not the HTTP status. In a worktree, use `wtx curl backend` for the port.

The backend reads only the exact primary CSV name, so a tar of the folder ignores `<name>.invalid.csv`. To check the invalid file, copy the folder and put the invalid file in place of the primary one. This is what the self-check does.

## Coverage

All nine databases validate. `validate_one_file` in `backend/resslab_hub/data/validator.py` has a branch per type and per curve type, and each entry of `CONTRIBUTION_DATABASES` has `qualityCheckSupported` on. An unknown type still raises `NotImplementedError`. Add it first when a new tab lands, see `docs/src/adding-a-new-tab.md` Step 16. Then add the new database to `DATABASES` and `TIME_SERIES` in `generate.py`.
