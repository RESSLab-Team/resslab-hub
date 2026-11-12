# Brief 02: identity and account life

You review how an account is made, joined, changed and closed, and every way one person could get into another person's account. Review only: you find and prove problems, you do not fix them.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 02 in `docs/review/review-plan.md` with the suspicions it names (B5, S6), and `docs/review/findings/README.md`.
2. Read `docs/auth.md`, the parts about addresses, identities, bare accounts and merge.
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

## The rules the code says it follows

Check that the code really does this:

- Two accounts are never joined because they report the same address. A GitHub or ORCID sign-in whose address belongs to another account is refused (`email_in_use`). The person signs in by email and links from the account page.
- A GitHub or ORCID account whose address is new makes a new, separate account.
- An account can have several addresses. Each one signs in by code and counts for the role. One is the main one: it signs submissions and gets the mails.
- A bare account (no address, one GitHub or ORCID identity) joins the account that proves an address or identity of it (`absorb_bare_account`).
- Only an admin merges two accounts that are not bare (`merge_users`).
- The last way to sign in and the main address cannot be removed (`CannotUnlink`).

## Files

- `backend/resslab_hub/auth/users.py`: `sign_in_with_email`, `sign_in_with_provider`, `attach_identity`, `add_email`, `set_main_email`, `remove_identity`, `is_bare`, `absorb_bare_account`, `merge_users`.
- `backend/resslab_hub/routers/auth.py`: `/auth/identities`, `/auth/emails`, `/auth/emails/verify`, the GitHub and ORCID callbacks.
- `backend/resslab_hub/routers/admin.py`: `PATCH /admin/users/{id}`, `POST /admin/users/{id}/merge`.
- `backend/resslab_hub/models/database/auth.py`: unique keys, cascades, column lengths.
- `backend/resslab_hub/auth/access.py`: invitations redeemed at sign-in.
- Tests that exist: `backend/tests/test_auth_flow.py`, `backend/tests/test_admin.py`.

## Questions

1. Takeover by address. Can someone get a session on an account by proving an address they do not own? Try: add address B to account A while B is in the middle of its own sign-in; two tabs that add the same address; an address with capitals or spaces, or a `+tag`.
2. Takeover by identity. Can a GitHub or ORCID identity land on the wrong account? Look at the link flow, the bare join, and what happens when the same GitHub account signs in after its primary address changed on GitHub.
3. Bare join. `absorb_bare_account` deletes the bare account. Can a bare account have anything that is lost: a session in another browser, an access request, an invitation, a submission? The docstring says it cannot. Prove it or break it.
4. Admin merge. What moves, what is lost, what if both sides have an ORCID iD, what if `keep` is disabled, what if the admin merges an account into itself or merges their own account away. What happens to the sessions of the account that goes?
5. Disable. Does it end all sessions at once? Can the person come back by another identity, by a bare account, or by an invitation?
6. Remove an identity or an address. Can it leave an account with no way in? Can it leave the role too high (the academic address is gone, but the role stays)?
7. Profile. Is there any way to set `display_name` or `institution` (API, admin page, provider)? What do they become for each way of making an account? What goes into a submission when they are empty? (B5)
8. Bad input. Long GitHub login, long ORCID name, an ORCID name with HTML or newlines, an address over the column length. 500 or 4xx? (S6)
9. Database rules. Which unique keys and foreign keys protect these rules, and which rules live only in Python? A rule only in Python can break under two requests at the same time.

## Method

1. Read `auth/users.py` first, then the routes that call each function.
2. For each question, make the smallest proof:
   - First choice: a Claude in Chrome transcript on your local server: open `http://127.0.0.1:$FRONTEND_PORT/`, sign in, then call `fetch('/api/auth/...')` from the page with `javascript_tool`, and paste the status, the headers and the body. `wtx curl` and plain `curl` do not reach the servers from the sandbox, do not try them. Codes are in `.wt-logs/backend.log` (no SMTP in dev). Read it with `tail -n 50`. Sign in as admin with an address of `ADMIN_EMAILS` (ask Pierre which one if you cannot see it).
   - Second choice: a test in a new file `backend/tests/test_review_02_<topic>.py`, marked `@pytest.mark.xfail(strict=True, reason="review 02: <finding id>")`. Copy the helpers of `test_admin.py` (`_user`, `_identity`, `_two_accounts`, `_sign_in_by_mail`).
3. If the DB tests fail with `OperationalError`, the sandbox hides `secrets/.env`. Write the test anyway, write "not run" in the finding.

## Rules

- Review only. Do not change application code. You add only test files that prove a finding, and your findings file.
- A finding needs a file and line, and a proof.
- Send requests only to your own servers, with Claude in Chrome on the ports of your worktree. Never to stage, prod or any `epfl.ch` host.
- Do not call GitHub or ORCID for real. Do not post anything on GitHub.
- Give each finding a severity from the scale in `docs/review/README.md`.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/02-identity.md`, from the template. One section per question.
- The test files.
- Commit on your branch with explicit paths: `docs(review): findings of package 02`. Do not open a pull request. Say when you are done.
