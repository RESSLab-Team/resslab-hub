# Brief 03: roles and access matrix

You check that every route of the Hub lets in exactly the people it must, and nobody else. Review only: you find and prove problems, you do not fix them.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 03 in `docs/review/review-plan.md` with the suspicions it names (B6, S4), and `docs/review/findings/README.md`.
2. Read `docs/auth.md`, the part about roles.
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

## How a role is decided

`derive_role` in `backend/resslab_hub/auth/roles.py`, first match wins:

1. An address in `ADMIN_EMAILS`: admin.
2. Admin permission on the data repo on GitHub: admin.
3. `role_override`, set by an admin.
4. Write permission on the data repo: curator.
5. An academic address (swot list or `CONTRIBUTOR_DOMAINS`): contributor.
6. Else viewer.

The routes use `require_user`, `require_role(...)`, `require_service`, `require_user_or_service` and `require_contributions_enabled` from `backend/resslab_hub/auth/deps.py`.

## Files

- `backend/resslab_hub/auth/roles.py`, `deps.py`, `access.py`, `github_sync.py`.
- Every file of `backend/resslab_hub/routers/`.
- `frontend/src/router/index.ts` (`meta.auth`, `meta.contributions`), `frontend/src/router/guards.ts`.
- Tests that exist: `backend/tests/test_auth_flow.py`, `test_admin.py`, `test_curation.py`, `test_verification.py`, `test_contributions.py`.

## Questions

1. The matrix. Make a table: every backend route (method and path) against anonymous, viewer, contributor, curator, admin, machine credential (`API_PASSWORD`), and contributions switched off. Write the status code in each cell. Mark the cells where the code and the intent disagree. Do it by reading the code, then prove the surprising cells.
2. Is any route that changes data, or returns personal data, open to anonymous or viewer by mistake? Look also at the data routers (`braces`, `columns`, ...): do they return anything personal?
3. The owner rule. `GET /contributions/{pr}` and its sub-routes are for the owner or a curator. How is the owner decided (`owns_submission` in `contributions/trailers.py`)? Can a contributor open someone else's submission by adding the other person's address to their own account, or with an address that differs only in case?
4. Role precedence. Can an admin lower a GitHub admin, or an `ADMIN_EMAILS` admin (`locked_admin`)? Can an admin change their own role (`cannot_change_self`)? Can the last admin who is not locked remove themself, by a role change, a disable or a merge?
5. GitHub sync (`github_sync.py`). When is the permission read again? What if the GitHub login is renamed and someone else takes the old name? What if GitHub answers an error or a rate limit: does the role stay, drop, or go up? (S4)
6. Academic addresses. Check `is_academic` with: `x@epfl.ch`, `x@ethz.ch`, `x@gmail.com`, `x@student.epfl.ch`, `x@sub.uni.edu`, `x@nus.edu.sg`, an address with a capital, an address with a trailing dot. Is a role from an academic address removed when that address is removed? (B6)
7. Invitations and access requests. An invitation is redeemed at sign-in by the address. Can it be redeemed by an account that adds the address later? By a GitHub sign-in with that primary address? What role does it give, and can it be higher than intended? Can an access request be approved twice by two admins at once?
8. Feature flag. With `CONTRIBUTIONS_ENABLED=false`, every pipeline route must answer 404, and `/auth/me` must still answer. Is any route missing the dependency? (Read the code. Do not restart the server to test it. If you need to, use a test with `monkeypatch`.)
9. Frontend guard. `resolveGuard` decides from the role in `/auth/me`. Find routes where the frontend shows a page that the backend then refuses, or the reverse. Look at `/curation/:prNumber`, which lets a contributor in on purpose.
10. The 401 and 403 answers. Do they say more than needed (role names, address of the owner)?

## Method

1. Make the matrix of question 1 first. It is the main output of this package. Get the route list by reading the routers, and write it in the findings file.
2. For each surprising cell, prove it:
   - First choice: a `wtx curl backend <path>` transcript on your local server, signed in as the role you need. Codes are in `.wt-logs/backend.log`. You can give a role to a local account from the admin page or the API, signed in as admin.
   - Second choice: a test in a new file `backend/tests/test_review_03_<topic>.py`, marked `@pytest.mark.xfail(strict=True, reason="review 03: <finding id>")`.
3. If the DB tests fail with `OperationalError`, the sandbox hides `secrets/.env`. Write the test anyway, write "not run" in the finding.

## Rules

- Review only. Do not change application code. You add only test files that prove a finding, and your findings file.
- A finding needs a file and line, and a proof.
- Send requests only to your own servers, with `wtx curl`. Never to stage, prod or any `epfl.ch` host.
- Do not call GitHub for real. Use the `github_permissions` fixture of `conftest.py`. Do not post anything on GitHub.
- Give each finding a severity from the scale in `docs/review/README.md`.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/03-roles.md`, from the template. The matrix first, then one section per question.
- The test files.
- Commit on your branch with explicit paths: `docs(review): findings of package 03`. Do not open a pull request. Say when you are done.
