# Brief 11: test gaps

You add the tests that the sign-in, account and pipeline code is missing. This package runs in wave 3, after Pierre triaged the findings of packages 01 to 10. Unlike the other packages, you write tests, not findings. You still do not change application code.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 11 in `docs/review/review-plan.md`, and `docs/review/findings/README.md`.
2. Read the triaged findings in `docs/review/findings/` (Pierre merges them before this wave). Each finding with a fix planned or done needs a test that stays.
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

## What exists

- Backend: `backend/tests/test_auth_flow.py`, `test_auth_units.py`, `test_admin.py`, `test_contributions.py`, `test_contribution_layout.py`, `test_curation.py`, `test_verification.py`. Fixtures in `backend/tests/conftest.py`: `client`, `db_session`, `sign_in`, `github_permissions`, `github_refusal`, `write_main_csv`. Most auth tests turn rate limits off with a `_no_rate_limits` fixture.
- Frontend: one view spec, `frontend/src/views/__tests__/ContributeView.spec.ts`. Store specs in `frontend/src/stores/__tests__/`.
- Proof tests from the other packages: `backend/tests/test_review_NN_*.py` and `frontend/src/**/__tests__/review-NN-*.spec.ts`, marked `xfail` or `it.fails`.

## Work

1. Proof tests. For each proof test of a finding that is now fixed, remove the `xfail` or `it.fails`, rename the file to the topic (not the package), and move it next to the tests of the same code. For a finding that Pierre decided not to fix, delete the proof test and say so in your report.
2. Rate limits. One test per limit that checks the 429 (mail start, mail verify, `/validate`, submit, edit, verification). Turn the limits on only for these tests.
3. Cookies. A test that reads the `Set-Cookie` headers of a sign-in and checks `HttpOnly`, `SameSite=Lax`, the path, the lifetime, and `Secure` when the public URL is `https`.
4. OAuth callbacks. One test per branch of the GitHub and ORCID callbacks: success, `error=access_denied`, bad state, state from another browser, identity taken, address taken, link mode, a bare account that joins.
5. Views. A spec for each auth view: `LoginView.vue` (email step, code step, each error key, `next`), `LoginVerifyView.vue` (good link, bad link), `AccountView.vue` (add address, make main, remove, the ORCID add-email step), `ForbiddenView.vue` (each `need`), `AdminView.vue` (each `admin.errors.*` key).
6. Guard. A table test for `resolveGuard`: every route of `router/index.ts` with `meta.auth` or `meta.contributions`, against no user, each role, and the flag off.
7. Errors. Every `auth.errors.*` and `admin.errors.*` key of `en.json` is reached by at least one test. Write a small test that fails if a key is added without a test.

## Method

- Backend: `cd backend && uv run pytest tests/<file>`. If the DB tests fail with `OperationalError`, the sandbox hides `secrets/.env`. Write the tests anyway and say "not run in the sandbox" in your report. Pierre runs `make test`.
- Frontend: `cd frontend && pnpm run test:unit <file>`.
- Keep each test small and named after the behavior: `test_verify_code_refuses_sixth_try`, not `test_case_12`.
- Use the GitHub mocks. Never call GitHub or ORCID for real.

## Rules

- Do not change application code. If a test shows a bug that is not in the findings, mark it `xfail` with a reason and add it to your report.
- Send requests only to your own servers. Never to stage, prod or any `epfl.ch` host.
- Do not post anything on GitHub.
- Write in simple English. No em dash.

## Output

- The tests.
- A short report in `docs/review/findings/11-test-gaps.md`: what you added, what you could not run, new bugs found.
- Commit on your branch with explicit paths: `test(auth): ...` or `test(contributions): ...`, one commit per topic. Do not open a pull request. Say when you are done.
