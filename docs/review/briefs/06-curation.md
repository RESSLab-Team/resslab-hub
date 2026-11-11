# Brief 06: curation and verification

You review the pages where curators read submissions, and the verification flow that marks merged data as checked. Review only: you find and prove problems, you do not fix them.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 06 in `docs/review/review-plan.md` with the suspicion it names (S9), and `docs/review/findings/README.md`.
2. Read `docs/curation.md`.
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

## The routes

- `GET /contributions` (curator): the queue.
- `GET /contributions/{pr}` and `/validation`, `/comments`, `/files`, `/curves` (the owner or a curator).
- `GET /verification`, `GET /verification/{database}/batch`, `/validation`, `/files` (curator).
- `POST /verification` (curator, 10 per hour): opens a pull request that marks rows as verified.

## Files

- `backend/resslab_hub/routers/curation.py`, `backend/resslab_hub/routers/verification.py`.
- `backend/resslab_hub/contributions/verification.py`, `contributions/trailers.py` (`owns_submission`, `provenance_from_commits`, `provenance_from_record`), `contributions/submission.py` (`read_provenance`, `redact_emails`).
- `frontend/src/views/CurationQueueView.vue`, `frontend/src/views/CurationReviewView.vue`, `frontend/src/components/curation/ReviewThread.vue`.
- Tests that exist: `backend/tests/test_curation.py`, `backend/tests/test_verification.py`.

## Questions

1. Owner rule. A submission belongs to the person whose address is in its trailers (or in the old `contributions/*.json` record). Can a contributor read a submission that is not theirs? Try: a pull request opened by hand on GitHub (no trailers), a fork pull request, a pull request with two commits from two people, an old one with a JSON record.
2. What a non-curator owner sees. Does `GET /contributions/{pr}` give the owner anything about other people: reviewer names, comments of curators with addresses, other submissions?
3. Addresses. `redact_emails` removes `(address)` after a name in the body. Does any other route or field still return an address: comments, commit authors, `/files`, the queue?
4. Caches. Curation answers are cached per process. Can one user get another user's cached answer? How long is the cache, and does a closed pull request vanish from the queue in time?
5. GitHub text in the Hub. `ReviewThread.vue` shows comment bodies with `v-html` after DOMPurify. Are links made safe (`rel="noopener noreferrer"`, `target`)? Can a comment load an image from anywhere (a tracking pixel that leaks who reads)? Is the pull request body shown anywhere without DOMPurify?
6. Verification. Can a curator verify rows they submitted themself? Should they? Write what the code does and leave the decision to Pierre. (S9)
7. Verification batch. `POST /verification` opens a pull request. What stops two curators from verifying the same rows at once? What if the rows changed on `main` meanwhile? What does the commit say (`Verified-by` trailer, with the address)?
8. Limits and costs. How many GitHub calls does one queue view make? One review page? What does a curator see when the GitHub limit is reached?
9. Frontend. `CurationReviewView.vue` sends a contributor with `need=curator&reason=not_yours` to the forbidden page. Is the message right? The Approve, Reject and Request changes buttons are off (#254): is that clear to a curator? `CurationQueueView.vue` still says "until curator roles are in place": is it stale?

## Method

1. Read the routes, then the frontend views.
2. For each question, make the smallest proof:
   - First choice: a `wtx curl backend /contributions/...` transcript on your local server. The local backend reads the test fork, so the queue shows real test pull requests. Codes are in `.wt-logs/backend.log`.
   - Second choice: a test in a new file `backend/tests/test_review_06_<topic>.py`, marked `@pytest.mark.xfail(strict=True, reason="review 06: <finding id>")`, with the GitHub mocks of `test_curation.py`.
   - For the frontend: a spec in `frontend/src/components/curation/__tests__/review-06-<topic>.spec.ts`, with `it.fails(...)`.
3. If the DB tests fail with `OperationalError`, the sandbox hides `secrets/.env`. Write the test anyway, write "not run" in the finding.

## Rules

- Review only. Do not change application code. You add only test files that prove a finding, and your findings file.
- A finding needs a file and line, and a proof.
- Send requests only to your own servers, with `wtx curl`. Never to stage, prod or any `epfl.ch` host.
- Do not write on GitHub: no `POST /verification` against the real fork, no comment, no merge. Reading the test fork through your local backend is fine.
- Give each finding a severity from the scale in `docs/review/README.md`.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/06-curation.md`, from the template. One section per question.
- The test files.
- Commit on your branch with explicit paths: `docs(review): findings of package 06`. Do not open a pull request. Say when you are done.
