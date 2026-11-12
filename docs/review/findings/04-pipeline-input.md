# Findings of package 04: pipeline input

- Branch: `review/04-pipeline-input`
- Commit reviewed: `0e15c031` (from `dev`, with ORCID)
- Date: 2026-11-12
- Tests run: yes, all 21 proof tests run and are `xfailed`. They need no database: the validator's database checks answer "nothing found" when Postgres is not reachable, and the sandbox hides `secrets/.env`. So the checks against existing ids were not part of these runs.

Run them with:

```sh
cd backend && uv run pytest tests/test_review_04_archive.py tests/test_review_04_submission.py tests/test_review_04_validator.py tests/test_review_04_http.py -rx
```

## Summary

| Id    | Severity | Title                                                                  | Suspicion | Proof      |
| ----- | -------- | ---------------------------------------------------------------------- | --------- | ---------- |
| 04-2  | high     | A 64 kB archive makes the backend use 320 MB of memory                 |           | test       |
| 04-4  | high     | A validation stops every other request of the server                   | B8        | test       |
| 04-3  | medium   | The upload is read in full before the caller is checked                | S8        | test       |
| 04-5  | medium   | No limit on the number of errors in a validation answer                | B8        | test       |
| 04-8  | medium   | A Latin-1 or UTF-16 file passes `/validate`, then submit gives a 500   |           | test       |
| 04-1  | low      | Some broken archives give a 500 instead of a 400                       |           | test       |
| 04-6  | low      | Errors show the server's temp path and Python error text               | S7        | test       |
| 04-7  | low      | A file name that is not UTF-8 gives a 500                              |           | test       |
| 04-9  | low      | A CSV with two `id` columns: one is checked, the other is written      |           | test       |
| 04-10 | low      | An unknown column is a warning at validate, then a 502 at submit       |           | test       |
| 04-11 | low      | The validator reads `1_000`, Arabic digits and full-width digits       |           | test       |
| 04-12 | note     | The backend id pattern is looser than the frontend one                 |           | code read  |
| 04-13 | note     | The "too large" message says "validate" also on submit                 |           | code read  |

## Question 1. Archive

`safe_extract_targz` refuses what the brief asks about: `..`, links, devices, fifos, a file that is not gzip, a corrupt gzip. An absolute path is made relative and stays in the temp folder. A newline in a name is extracted, then `check_paths` refuses it at submit. Two members with the same name: the last one wins, in the temp folder only. 2000 small files pass in well under a second. 4 members of 50 MB of zeros (a 204 kB upload) pass the caps and write 200 MB in about 1 s, which is what the caps allow. Two real problems: some broken archives fall through to the generic 500, and a tar header that `tarfile` reads before any cap.

### 04-1 Some broken archives give a 500 instead of a 400

- Severity: low
- Where: `backend/resslab_hub/utils/safe_archive.py:77`
- Status: new

`safe_extract_targz` turns only `tarfile.TarError` into `ArchiveError` (400). A cut gzip raises `EOFError`. A member name over 255 bytes raises `OSError` (ENAMETOOLONG). A name that is a file and then a folder raises `NotADirectoryError` or `IsADirectoryError`. All of them reach the `except Exception` of `/validate` and of `_run_on_archive`, so the user sees "The validation failed on the server". The editor cannot build these archives (`tar.ts:47` refuses names over 100 bytes), so it hurts API callers and the log only.

Proof: `backend/tests/test_review_04_archive.py::test_broken_archive_is_refused_as_a_bad_archive` (4 cases), marked `xfail(strict=True)`.

Fix: also catch `EOFError`, `zlib.error`, `OSError` and `ValueError` around the read and the extraction, and raise `ArchiveError`.

### 04-2 A 64 kB archive makes the backend use 320 MB of memory

- Severity: high
- Where: `backend/resslab_hub/utils/safe_archive.py:49`
- Status: new

The caps (member count, member size, total size) apply to the members that `tarfile` returns. A GNU long-name header (type `L`, also a PAX header) is not a member: `tarfile` reads its whole payload into memory to build the name of the next member, before the loop sees anything. A payload of 64 MB of the same byte gzips to 64 kB. Measured: a 64 kB upload gives a 320 MB peak, a 204 kB upload gives +256 MB of RSS for 200 MB of name. The ratio is about 1000 to 5. So about 1 MB sent can ask for several GB. The backend has one replica with a 4 Gi limit: one request from any signed-in account can kill the pod, and everybody in the workshop loses the server until it restarts. Then it fails with `OSError` (see 04-1).

Proof: `backend/tests/test_review_04_archive.py::test_long_name_header_is_not_read_into_memory`, marked `xfail(strict=True)`.

```text
$ uv run pytest tests/test_review_04_archive.py --runxfail -k long_name --tb=line
AssertionError: peak 320 MB for a 65354 B upload
```

Fix: cap the size of the compressed and the decompressed stream before `tarfile` reads it (a reader that counts bytes and stops at the total cap), or refuse GNU and PAX long-name headers over a few kB. The browser only writes ustar headers (`tar.ts`), so the editor loses nothing.

## Question 2. Size

The ingress gives 50 MB to `/validate` and `/contributions` (enack8s-app-config#414). Inside the app, the body is read in full before anything else: FastAPI 0.162 calls `await request.form()` before it solves the dependencies, so before `require_user_or_service`, before `enforce_request_size` and before the rate limit. Starlette parses the multipart body into a `SpooledTemporaryFile`, kept in memory up to 1 MB, then written to the pod's temp folder. A chunked body has no `Content-Length`, so `enforce_request_size` checks nothing, and `reject_oversized` runs after the whole file is on disk. Only the ingress bounds it.

### 04-3 The upload is read in full before the caller is checked

- Severity: medium
- Suspicion: S8 (confirmed, its last sentence)
- Where: `backend/resslab_hub/routers/root.py:258` (and `enforce_request_size` at `:55`)
- Status: new

A stranger with no cookie and no credential sends a chunked 20 MB body to `/validate`. The answer is 401, but only after the app has read all 20 MB and written it to disk. The rate limit does not count it either. With the 50 MB ingress limit and several connections at once, a stranger can fill the pod's temp folder and use its CPU, with no account. It needs no other bug, but the ingress limit and the end of each request (the temp file is deleted) keep it bounded, so medium.

Proof: `backend/tests/test_review_04_http.py::test_body_is_not_read_before_the_auth_check`, marked `xfail(strict=True)`.

```text
$ uv run pytest tests/test_review_04_http.py --runxfail -k auth_check --tb=line
AssertionError: 20 MB read before the 401
```

Fix: check the session or credential and the rate limit in a middleware (or a route that reads `request.stream()` itself) before the body is parsed, and stop reading at 50 MB also when there is no `Content-Length`.

## Question 3. Paths in the batch

No finding. `filter="data"` in `extractall` refuses `..`, absolute paths and links, and `check_paths` (`submission.py:99`) accepts only the primary CSV, the dictionaries, and `<curve folder>/<safe id>.csv`. A name like `../../.github/workflows/x.yml` is refused twice. I also checked whether a batch can carry the curve file of a specimen it does not add (to replace an existing curve in the data repo): it cannot, see "Rejected suspicions".

## Question 4. CSV

A BOM and CRLF are handled. A newline in a cell is kept, and a newline in an id is refused by the id rule. An id that exists already is refused (in the database by the validator, in the repo by `flag_repo_duplicates`), not tested here because it needs the database. A header in capitals gives "Missing required columns: id" plus a warning "Unexpected columns: ID", which is clear enough. A quote that never ends, an empty file and a cell over 131 072 characters give one error with Python's text (04-6). 100 000 rows and 1000 columns: no cap, the cost is in 04-4 and 04-5. A duplicate header and an unknown column are accepted by the validator and break later (04-9, 04-10). The id rule of the backend is looser than the frontend one (04-12).

### 04-9 A CSV with two `id` columns: one is checked, the other is written

- Severity: low
- Where: `backend/resslab_hub/contributions/submission.py:159` (`batch_ids`), `:466` (`batch_index`)
- Status: new

The validator has no check for a repeated header name. At submit, `batch_ids` reads the first `id` column, so the clash check against the data repo sees `B9`. `build_primary_csv` builds `batch_index` from the header, so the last `id` column wins, and the commit writes `B1`. A contributor can add a second `B1` row to the repo CSV past the repo clash check. The curator still sees the diff in the pull request, and only an API caller can do it (the editor builds the header from the dictionary).

Proof: `backend/tests/test_review_04_submission.py::test_validator_refuses_a_duplicated_header` and `::test_the_id_written_is_the_id_checked`, marked `xfail(strict=True)`.

```text
AssertionError: checked B9, wrote B1
```

Fix: refuse a CSV whose header repeats a name, in `TableValidator` and in `_read_csv`.

### 04-10 An unknown column is a warning at validate, then a 502 at submit

- Severity: low
- Where: `backend/resslab_hub/contributions/submission.py:459`
- Status: new

A primary CSV with a column that is not in the dictionary (`colour`) passes `/validate` with the warning "Unexpected columns". At submit, `build_primary_csv` raises a 502 that says the data dictionary may have changed and asks to contact the maintainers. The user did nothing wrong in their eyes, and the maintainers get a mail for a typo in a header.

Proof: `backend/tests/test_review_04_submission.py::test_a_column_the_validator_only_warns_about_is_not_a_server_error`, marked `xfail(strict=True)`.

Fix: make an unknown column an error in the validator (so the user sees it in the editor), or drop it at submit with a 400 that names it.

### 04-12 The backend id pattern is looser than the frontend one

- Severity: note
- Where: `backend/resslab_hub/data/common.py:72` and `frontend/src/utils/validation.ts:25`
- Status: new

Both refuse the characters Windows forbids and the C0 controls. The backend also accepts the C1 controls (U+0080 to U+009F), a final dot or space (`B9.`, `B9 `, which Windows strips from a file name), `a..b`, and ids of any length. The frontend refuses the C1 controls. Two ids that differ only by case both pass on both sides. No harm found on Linux, but a clone of the data repo on Windows or macOS can get two curve files that clash.

Fix: one rule on both sides, also refusing a final dot or space, the C1 controls, and ids over a fixed length (for example 64).

## Question 5. Formula cells

`escape_formula` escapes `=`, `+`, `-`, `@`, a tab and a CR, and `-2+3+cmd|...`. A cell with spaces before `=` is stripped first (`build_primary_csv` calls `escape_formula(value.strip() or "NR")`), so it is escaped too. A negative number stays a number. Curve files are committed without escape, but the validator refuses any cell that is not a number there ("Must be a number."), so no formula reaches the repo through them. `|calc` and a full-width `＝1+1` are not escaped. Excel and LibreOffice do not run them as formulas from a CSV, so no finding. One problem with numbers, below.

### 04-11 The validator reads `1_000`, Arabic digits and full-width digits

- Severity: low
- Where: `backend/resslab_hub/data/validator.py:188` (`parse_number`)
- Status: new

`parse_number` uses `Decimal(text)`, which accepts underscores (`-1_000`), any Unicode digit (`١٢٣`, `１２`) and huge exponents (`+1E+999999999`). These cells pass the validator and are written to the repo as they are, but the editor's own number rule (`DECIMAL` in `utils/validation.ts`) refuses them, and PostgreSQL 14 `numeric` most likely refuses them at upload (not tested, see "Not proven"). So a row can be valid at submit and fail the nightly upload.

Proof: `backend/tests/test_review_04_submission.py::test_parse_number_refuses_what_the_database_and_the_editor_refuse` (4 cases), marked `xfail(strict=True)`.

Fix: match the cell against an ASCII number pattern (the same as the frontend `DECIMAL`) before `Decimal`, and cap the exponent.

## Question 6. The validator

Times of `validate_all` alone, one CPU, no database:

| Batch                                                     | Files | Size   | Time   |
| --------------------------------------------------------- | ----- | ------ | ------ |
| `sample-data/connections` (largest)                       | 76    | 0.8 MB | 0.18 s |
| the same, 10 times (new ids)                              | 751   | 8 MB   | 1.21 s |
| one connections curve file of 2 MB                        | 2     | 2 MB   | 1.93 s |
| one connections curve file of 8 MB                        | 2     | 8 MB   | 7.32 s |
| a braces primary of 2 MB, every cell bad (1452 rows)      | 1     | 2 MB   | 5.0 s  |
| a braces primary of 8 MB, every cell bad (5809 rows)      | 1     | 8 MB   | 19.3 s |

The time grows with the size, about 0.9 s per MB of curve data. The caps allow 200 MB, so about 3 minutes for one archive of 200 kB gzipped. Stage measured 2.2 s for a 4 MB batch (B8). I found no loop and no crash, apart from the 500s of 04-1 and 04-7.

### 04-4 A validation stops every other request of the server

- Severity: high
- Suspicion: B8 (confirmed)
- Where: `backend/resslab_hub/routers/root.py:263-271`, `backend/resslab_hub/contributions/submission.py:396`, `backend/resslab_hub/routers/contributions.py:175`
- Status: new

`/validate` is an `async def`, and it calls `safe_extract_targz` and `validate_all` directly, with no `run_in_threadpool` (`/upload` at `root.py:132` uses it). Submit and edit do the same. So while one validation runs, the event loop of the only backend pod does nothing else: page loads, sign-ins, other validations, health checks all wait. In the workshop, 30 people each change a cell, the editor calls `/validate` 2 s later, and each call of a few seconds adds to the wait of all the others. A single archive of 200 kB gzipped holds the whole server about 3 minutes. The backend runs one uvicorn worker, and its liveness probe on `/healthz` keeps the Kubernetes defaults (1 s timeout, 3 failures, every 10 s, `enack8s-app-config/epfl-resslab/resslab-hub/base/backend-deployment.yaml:53`). So a loop blocked for about 30 s makes Kubernetes restart the pod in the middle of the work of everybody.

Proof: `backend/tests/test_review_04_http.py::test_event_loop_keeps_running_during_a_validation`, marked `xfail(strict=True)`. A task that ticks every 10 ms runs during a `/validate` of an 8 MB brace curve file (a 22 kB upload).

```text
$ uv run pytest tests/test_review_04_http.py --runxfail -k event_loop --tb=line
AssertionError: the loop stopped for 0.7 s (21930 B uploaded)
```

Fix: run the extraction, `validate_all` and the CSV reads of submit in `run_in_threadpool` (or a small process pool with a time limit), and cap the total size of the curve data well below 200 MB.

To check by Pierre: whether a restart was already seen on stage during a big validation (pod restarts count).

## Question 7. Error text

The answer echoes cell values, header names and file names with no length limit, and every error is written twice (structured `results`, then the legacy arrays). The frontend shows these messages as text (the only `v-html` are the guide, unit labels and sliders, none of them for validation messages), so no HTML injection was found. The size of the answer and Python's error text are the problems.

### 04-5 No limit on the number of errors in a validation answer

- Severity: medium
- Suspicion: B8 (it adds to the time)
- Where: `backend/resslab_hub/routers/root.py:194` and `:208` (each error twice), `backend/resslab_hub/data/validator.py:434-455`
- Status: new

A primary CSV where every cell is bad gives one error per cell. 195 kB gives 13 200 errors and a 1.8 MB answer. 8 MB gives 778 406 errors, a 110 MB answer, 19 s, and about 1 GB of memory (measured with `ru_maxrss`). The browser then has to parse and draw it. A user who pastes a sheet in the wrong order gets this, no attack needed.

Proof: `backend/tests/test_review_04_validator.py::test_report_size_is_bounded`, marked `xfail(strict=True)`.

```text
AssertionError: 13200 errors, answer 1785398 B for 194940 B
```

Fix: stop a file after a fixed number of errors (for example 200, with a last line "and N more"), and send each error once.

### 04-6 Errors show the server's temp path and Python error text

- Severity: low
- Suspicion: S7 (confirmed for the validation report)
- Where: `backend/resslab_hub/data/validator.py:505` and `:856`
- Status: new

When the CSV reader fails, the error is `Failed to process file: {e}` and its value is the absolute path of the file in the server's temp folder (`/tmp/tmpXXXX/braces/steel_braces.csv`). The routes hide exception text in their own 500 (#264 H3), but this one is inside a 200 report. Cases: a quote that never ends, an empty file (the message is empty), a cell over 131 072 characters (`field larger than field limit (131072)`). The user does not know what to fix, and the server shows its paths.

Proof: `backend/tests/test_review_04_validator.py::test_report_has_no_server_path_and_no_python_text` (3 cases), marked `xfail(strict=True)`.

Fix: send the path relative to the batch, and a sentence per known `csv.Error` ("a quote is never closed", "the file is empty", "a cell is too long").

## Question 8. Encoding

The validator guesses the encoding with `chardet` and accepts a Latin-1 or UTF-16 file with a warning only ("File is not UTF-8"). The code after it reads the same files as UTF-8.

### 04-8 A Latin-1 or UTF-16 file passes `/validate`, then submit gives a 500

- Severity: medium
- Where: `backend/resslab_hub/contributions/submission.py:415` (`read_batch`), `:365` (`flag_repo_duplicates`), `:491` (`collect_curve_files`)
- Status: new

The primary CSV in Latin-1 (`Müller`) or UTF-16 is valid for `validate_all`. At submit, `read_batch` opens it as UTF-8 and raises `UnicodeDecodeError`, which `_run_on_archive` turns into "The submission failed on the server". In `/validate`, `flag_repo_duplicates` hits the same error, and `root.py:278` only logs it: the check of the ids against the data repo is skipped and the user is not told. Curve files go through `collect_curve_files`, which reads them the same way. Excel's "CSV" and "Unicode text" exports give these encodings.

Through the editor, the browser reads each file with `file.text()` (`frontend/src/utils/intake.ts:50`), which decodes as UTF-8 and puts "�" in place of each bad byte with no message. So the primary CSV the editor rebuilds is UTF-8, but the accents are lost (not proven, see below).

Proof: `backend/tests/test_review_04_submission.py::test_a_batch_validate_accepts_can_be_read_at_submit` (latin-1 and utf-16), marked `xfail(strict=True, raises=UnicodeDecodeError)`.

Fix: refuse a file that is not UTF-8 in the validator (an error, not a warning, with the encoding it found), or convert it to UTF-8 once after extraction so every later step reads the same text. In the browser, decode with `TextDecoder('utf-8', { fatal: true })` and show a message.

### 04-7 A file name that is not UTF-8 gives a 500

- Severity: low
- Where: `backend/resslab_hub/routers/root.py:284` (`_build_response`), the name comes from `safe_archive.py:74`
- Status: new

A GNU tar member named with a byte that is not UTF-8 (`\xff.csv`) is extracted with a surrogate in its name. The validator reports it, then the JSON answer cannot be encoded, and the user gets the generic 500. The browser cannot build such a name (JS strings are encoded as UTF-8 by `tar.ts`), so only API callers hit it. Names with accents or emoji in UTF-8 are fine on the backend. In the browser, an emoji or accented id longer than 100 bytes makes `tar.ts:47` throw `Path "..." does not fit a ustar header`, which the user sees as is.

Proof: `backend/tests/test_review_04_http.py::test_member_name_not_utf8_is_a_report_not_a_500`, marked `xfail(strict=True)`.

Fix: refuse a member name that is not valid UTF-8 in `safe_extract_targz` (an `ArchiveError`, so a 400).

## Question 9. Frontend side

What the browser drops or changes before it sends: hidden files, `__MACOSX`, `Thumbs.db` and similar are dropped without a word (`intake.ts:31`), which is fine. Files are decoded as UTF-8 with replacement characters (04-8). `tar.ts` refuses paths that do not fit a ustar header (04-7). The browser has no size or count cap, so the first limit the user meets is the 413 of the ingress or of the backend. A file passes the frontend and fails the backend in 04-10 (unknown column) and 04-8. The reverse (the frontend refuses, the backend accepts) is 04-11 and 04-12, which only matter for API callers.

### 04-13 The "too large" message says "validate" also on submit

- Severity: note
- Where: `frontend/src/stores/contribution.ts:52`
- Status: new

`transportError` is written for `/validate` and also used for the submit and edit calls (`:952`). On submit, a 413 shows "The contribution is too large to validate in one request." The user validated fine a moment ago, so this confuses. The other branches of the function are neutral.

Fix: pass the action ("validate", "submit") to `transportError`, or say "too large to send".

## Rejected suspicions

| Suspicion                                                              | Why it is not a problem                                                                                                                                       | Where                                                       |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Path traversal, absolute paths, links, devices (question 1 and 3)       | `filter="data"` refuses them or makes them relative, and `check_paths` allows only the layout's folders and a safe id                                          | `safe_archive.py:74`, `submission.py:99`                    |
| A batch carries the curve file of another specimen and replaces it      | A submission must have a primary CSV (`read_batch` gives 400 without it), and when a primary is in the batch, a curve id must be in it                        | `submission.py:414`, `validator.py:812`                     |
| A formula in a curve file reaches the repo                              | The validator refuses any curve cell that is not a number ("Must be a number.")                                                                                | `validator.py` (curve rows), checked with a probe          |
| A header in capitals gives a confusing message                          | "Missing required columns: id" plus "Unexpected columns: ID" is clear                                                                                          | `validator.py:419`                                          |
| A tar bomb of small files                                               | 2000 small files extract in under a second, and the member cap applies                                                                                         | `safe_archive.py:49`                                        |
| Two members with the same name                                          | The last one wins, in the temp folder, and the result is still validated                                                                                       | `safe_archive.py:74`                                        |
| A cell with spaces before `=` is not escaped                            | `build_primary_csv` strips the cell before `escape_formula`                                                                                                    | `submission.py:477`                                         |

## Not proven

- The subsidiary run of `validate_all` has no `try` (`validator.py:1340`), and the primary run's `try` only logs (`:1333`): an exception there drops the primary results and could make an invalid batch look valid. I found no input that raises there.
- PostgreSQL 14 `numeric` refuses `1_000` and non-ASCII digits at upload (04-11). Proof: upload a CSV with such a cell to a branch database (needs the DB tunnel and `secrets/.env`).
- The editor turns Latin-1 accents into "�" with no message (04-8). Proof: a vitest on `intake.ts` with a Latin-1 `File`, or Claude in Chrome with `file_upload`.
- A single 200 MB archive of curve data takes about 3 minutes (04-4): computed from the measured 0.9 s per MB, not run in full.

## Not checked

- Claude in Chrome on `http://127.0.0.1:19076/contribute` (plan step 6). I did not sign in and did not run the `fetch` checks: the HTTP tests over ASGI prove 04-3, 04-4 and 04-7 on the real app, and I kept the time for the tests. So what the page itself shows for 04-8 and 04-13 is read from the code, not seen.
- The checks against existing ids (database and data repo). They need the database or GitHub, and the brief forbids real GitHub calls.
- 30 users at once (B8). The test proves that one validation blocks the others, not the full queue.
- Memory limit of my own runs: the 8 MB "every cell bad" run of 04-5 reached about 1 GB of RSS, over the 256 MB I planned. The laptop had 11 GB free. The proof test of 04-5 uses a 195 kB file instead.

<details>
<summary>Script that builds the bad archives</summary>

Run from `backend/`: `uv run python make_archives.py "" [case ...]`. An empty first argument keeps the archives in memory. A folder as first argument also writes them there. Each case prints the size sent, the time, the extra RSS and what `safe_extract_targz` did. `zeros_4x50MB` writes 200 MB to a temp folder and `gnu_longname_200MB` uses about 260 MB of RAM: run them alone.

```python
import gzip
import io
import os
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from resslab_hub.utils.safe_archive import safe_extract_targz

PRIMARY = "braces/steel_braces.csv"
CURVE = "braces/force_displacement/B9.csv"


def _info(name, data=b"", kind=tarfile.REGTYPE, **extra):
    info = tarfile.TarInfo(name)
    info.type = kind
    info.size = len(data) if kind == tarfile.REGTYPE else 0
    for key, value in extra.items():
        setattr(info, key, value)
    return info, (io.BytesIO(data) if kind == tarfile.REGTYPE else None)


def build(members, fmt=tarfile.PAX_FORMAT):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=fmt) as tar:
        for info, data in members:
            tar.addfile(info, data)
    return buf.getvalue()


def zeros_member(name, size):
    """A member of `size` zero bytes, streamed (no big buffer in memory)."""

    class Zeros(io.RawIOBase):
        def __init__(self, n):
            self.left = n

        def readable(self):
            return True

        def readinto(self, b):
            n = min(len(b), self.left)
            b[:n] = bytes(n)
            self.left -= n
            return n

    info = tarfile.TarInfo(name)
    info.size = size
    return info, io.BufferedReader(Zeros(size), 1 << 20)


def gnu_longname_bomb(size):
    """A GNU 'L' header whose payload is `size` bytes, read into memory by tarfile."""
    header = tarfile.TarInfo("././@LongLink")
    header.type = tarfile.GNUTYPE_LONGNAME
    header.size = size
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=9) as gz:
        gz.write(header.tobuf(format=tarfile.GNU_FORMAT))
        chunk = b"a" * (1 << 20)
        left = size
        while left:
            n = min(left, len(chunk))
            gz.write(chunk[:n])
            left -= n
        gz.write(b"\0" * (tarfile.BLOCKSIZE - size % tarfile.BLOCKSIZE or 0))
        gz.write(tarfile.TarInfo("x.csv").tobuf(format=tarfile.GNU_FORMAT))
        gz.write(b"\0" * 1024)
    return out.getvalue()


CASES = {
    "dotdot": lambda: build([_info("../evil.csv", b"x")]),
    "absolute": lambda: build([_info("/tmp/evil.csv", b"x")]),
    "symlink": lambda: build([_info("braces/l.csv", kind=tarfile.SYMTYPE, linkname="/etc/passwd")]),
    "hardlink": lambda: build([_info("a.csv", b"x"), _info("b.csv", kind=tarfile.LNKTYPE, linkname="a.csv")]),
    "chardev": lambda: build([_info("dev.csv", kind=tarfile.CHRTYPE, devmajor=1, devminor=3)]),
    "fifo": lambda: build([_info("fifo.csv", kind=tarfile.FIFOTYPE)]),
    "newline_name": lambda: build([_info("braces/force_displacement/B\n9.csv", b"x")]),
    "nul_in_pax_name": lambda: build([_info("braces/force_displacement/B\x009.csv", b"x")]),
    "long_name_300": lambda: build([_info("braces/force_displacement/" + "B" * 300 + ".csv", b"x")]),
    "non_utf8_name": lambda: build(
        [_info(b"braces/force_displacement/\xff.csv".decode("utf-8", "surrogateescape"), b"x")],
        fmt=tarfile.GNU_FORMAT,
    ),
    "duplicate_name": lambda: build([_info(CURVE, b"first"), _info(CURVE, b"second")]),
    "file_then_dir": lambda: build([_info("braces", b"x"), _info(PRIMARY, b"id\n")]),
    "dir_then_file": lambda: build([_info("braces", kind=tarfile.DIRTYPE), _info("braces", b"x")]),
    "not_gzip": lambda: b"id,f_y\nB9,400\n",
    "truncated_gzip": lambda: (lambda b: b[: len(b) // 2])(
        build([_info(PRIMARY, os.urandom(30000).hex().encode())])
    ),
    "corrupt_gzip": lambda: (lambda b: b[:40] + bytes(x ^ 0xFF for x in b[40:80]) + b[80:])(
        build([_info(PRIMARY, b"id\n" * 50000)])
    ),
    "many_small_2000": lambda: build(
        [_info(f"braces/force_displacement/S{i}.csv", b"x") for i in range(2000)]
    ),
    "zeros_4x50MB": lambda: build(
        [zeros_member(f"braces/force_displacement/Z{i}.csv", 50 * 2**20) for i in range(4)]
    ),
    "gnu_longname_200MB": lambda: gnu_longname_bomb(200 * 2**20),
}


def run(case, data):
    import resource

    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with tempfile.TemporaryDirectory() as dest:
        start = time.monotonic()
        try:
            safe_extract_targz(io.BytesIO(data), dest)
            files = sorted(p for p in Path(dest).rglob("*") if p.is_file())
            outcome = "EXTRACTED: " + ", ".join(repr(str(p.relative_to(dest))) for p in files)[:200]
        except Exception as exc:  # noqa: BLE001
            outcome = f"{type(exc).__module__}.{type(exc).__name__}: {str(exc)[:120]!r}"
        took = time.monotonic() - start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"{case:22} {len(data):>10} B gz  {took:6.2f} s  peak RSS +{(peak - before) // 1024} MB  {outcome}")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else None
    for name in sys.argv[2:] or list(CASES):
        data = CASES[name]()
        if out:
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}.tar.gz").write_bytes(data)
        run(name, data)
```

Results at `0e15c031`:

| Case                 | What happens                                                         |
| -------------------- | -------------------------------------------------------------------- |
| dotdot, symlink, hardlink, chardev, fifo, not_gzip, corrupt_gzip | `ArchiveError` (400)                         |
| absolute             | extracted as `tmp/evil.csv`, inside the temp folder                  |
| newline_name         | extracted, refused later by `check_paths`                            |
| nul_in_pax_name      | name cut at the NUL (`B`)                                            |
| non_utf8_name        | extracted as `\udcff.csv`, then a 500 (04-7)                         |
| duplicate_name       | the last one wins                                                    |
| long_name_300        | `OSError` ENAMETOOLONG, a 500 (04-1)                                 |
| file_then_dir        | `NotADirectoryError`, a 500 (04-1)                                   |
| dir_then_file        | `IsADirectoryError`, a 500 (04-1)                                    |
| truncated_gzip       | `EOFError`, a 500 (04-1)                                             |
| many_small_2000      | extracted                                                            |
| zeros_4x50MB         | 204 kB sent, 200 MB written in about 1 s                             |
| gnu_longname_200MB   | 204 kB sent, +256 MB of RSS (04-2)                                   |

</details>
