# Brief 04: pipeline input

You review what a user can send to the contribution pipeline, and what the backend does with it before anything goes to GitHub. Review only: you find and prove problems, you do not fix them.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 04 in `docs/review/review-plan.md` with the suspicion it names (B8), and `docs/review/findings/README.md`.
2. Read `docs/contributing-data.md`.
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.
4. Look at `sample-data/`: it has valid and invalid batches for each database.

## The routes

- `POST /validate`: a signed-in user or the machine credential, 30 per minute. The editor calls it 2 s after each change.
- `POST /contributions`: contributor, 5 per hour. Opens a pull request.
- `PUT /contributions/{pr_number}`: contributor, 10 per hour. Adds a commit.

All three take a `.tar.gz` built in the browser (`frontend/src/utils/tar.ts`).

## Files

- `backend/resslab_hub/utils/safe_archive.py`: extraction and its caps (50 MB per member, 200 MB in all).
- `backend/resslab_hub/routers/root.py`: `enforce_request_size` (50 MB on `Content-Length`), `reject_oversized`, `/validate`.
- `backend/resslab_hub/routers/contributions.py`.
- `backend/resslab_hub/contributions/submission.py`: `check_paths`, `escape_formula`, `_read_csv`, `normalize_csv_text`, `batch_ids`, `build_primary_csv`, `collect_curve_files`.
- `backend/resslab_hub/data/validator.py`.
- `frontend/src/utils/tar.ts`, `frontend/src/utils/intake.ts`.
- Tests that exist: `backend/tests/test_contributions.py`, `backend/tests/test_contribution_layout.py`.

## Questions

1. Archive. Try members with `../`, an absolute path, a symlink, a hard link, a device file, a name with a NUL or a newline, two members with the same name, a member that is a folder and a file, a gzip bomb, a tar bomb with many small files, a file that is not gzip. Which ones get past `safe_archive.py`?
2. Size. `Content-Length` is checked before the body, and the real size after. What does a chunked body do? Where is the multipart body written while it is parsed, and what bounds it? Is the body read before the auth check, so that a stranger can make the pod write 50 MB to disk? (S8)
3. Paths in the batch. `check_paths` decides where each file goes. Can a file name make the backend write outside the folder of the database in the data repo (for example a curve file named `../../.github/workflows/x.yml`)?
4. CSV. Try: a BOM, CRLF, a quote that never ends, a cell with a newline, a very long cell, 100 000 rows, 1000 columns, a header with spaces or capitals, a duplicate header, an id with a slash or `..`, an id that exists already.
5. Formula cells. `escape_formula` must neutralize cells that start with `=`, `+`, `-`, `@`, a tab or a CR. Check also a cell with spaces before `=`, and a negative number (it must stay a number).
6. The validator. Can a batch make it crash (500), loop, or take more than a few seconds? Measure the time for the largest batch in `sample-data/` and for a batch 10 times larger. While one slow validation runs, does another request wait? (B8)
7. Error text. When validation fails, does the answer echo the user's input without limits (very long, HTML)? Does any path return a Python exception text?
8. Encoding. A file in Latin-1, in UTF-16, with a name in accents or emoji. What does the user see?
9. Frontend side. `tar.ts` and `intake.ts`: what does the browser drop or change before it sends? Can a file pass the frontend and fail the backend, or the reverse, without a clear message?

## Method

1. Build bad archives with a small Python script in `$TMPDIR` (use `tarfile`). Keep the script in your findings file, so Pierre can run it again.
2. For each question, make the smallest proof:
   - First choice: a test in a new file `backend/tests/test_review_04_<topic>.py`, marked `@pytest.mark.xfail(strict=True, reason="review 04: <finding id>")`. `make_batch` in `test_contributions.py` shows how to build one. The tests of `utils/safe_archive.py` need no database.
   - Second choice: Claude in Chrome on `http://127.0.0.1:$FRONTEND_PORT/contribute`, signed in as a contributor. Give the archive to the editor with `file_upload`, and paste what the page and the `/api/validate` answer say. Codes are in `.wt-logs/backend.log`. `wtx curl` and plain `curl` do not reach the servers from the sandbox, do not try them.
3. Use `/validate` for everything you can. It does not write to GitHub. For `POST /contributions`, use the GitHub mocks of `test_contributions.py`. Never submit for real.
4. If the DB tests fail with `OperationalError`, the sandbox hides `secrets/.env`. Write the test anyway, write "not run" in the finding.

## Rules

- Review only. Do not change application code. You add only test files that prove a finding, and your findings file.
- A finding needs a file and line, and a proof.
- Send requests only to your own servers, with Claude in Chrome on the ports of your worktree. Never to stage, prod or any `epfl.ch` host.
- Do not call GitHub for real. Do not post anything on GitHub.
- Do not fill the disk: delete your test archives at the end.
- Give each finding a severity from the scale in `docs/review/README.md`.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/04-pipeline-input.md`, from the template. One section per question.
- The test files, and the script that builds the bad archives.
- Commit on your branch with explicit paths: `docs(review): findings of package 04`. Do not open a pull request. Say when you are done.
