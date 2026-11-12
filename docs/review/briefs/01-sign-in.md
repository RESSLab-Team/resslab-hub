# Brief 01: sign-in and sessions

You review how people sign in to the RESSLab Hub and how their session lives. Review only: you find and prove problems, you do not fix them.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 01 in `docs/review/review-plan.md` with the suspicions it names (S3, S5, S6), and `docs/review/findings/README.md`.
2. Read `docs/auth.md`.
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

## Files

- `backend/resslab_hub/routers/auth.py`: every `/auth/*` route.
- `backend/resslab_hub/auth/email_login.py`: code and link, attempts, hourly caps.
- `backend/resslab_hub/auth/oauth_state.py`, `github_oauth.py`, `orcid_oauth.py`: OAuth start and callback.
- `backend/resslab_hub/auth/sessions.py`, `csrf.py`, `urls.py` (`safe_redirect`, `cookie_secure`), `tokens.py`, `challenges.py`.
- `backend/resslab_hub/utils/rate_limit.py`.
- Tests that exist: `backend/tests/test_auth_flow.py`, `backend/tests/test_auth_units.py`.
- Frontend side: `frontend/src/views/LoginView.vue`, `frontend/src/views/LoginVerifyView.vue`, `frontend/src/stores/auth.ts`.

## Questions

Answer each one with "problem" (a finding) or "no problem" (and why).

1. Email code. Ten minutes, five tries, one use. Can a code be used twice by two requests at the same time (`verify_code` sets `consumed_at` after the check, no `SELECT ... FOR UPDATE`)? Can the attempt counter be passed by parallel requests? (S5)
2. Email link. The token is checked without the `resslab_login` cookie, on purpose. Can a link sent for address A sign in somebody else? What happens to the redirect stored in the challenge?
3. A challenge made to add an address (`link_user_id` set) must never sign in, and a sign-in challenge must never add an address. Prove both ways.
4. Hourly caps: 5 mails per address, 20 per IP, counted in SQL. Does the answer of `/auth/email/start` tell a stranger that an address has an account, or that a cap is reached? Does the time of the answer tell it?
5. OAuth state (GitHub and ORCID). Is the state bound to the browser (the `resslab_login` cookie)? Is it one use, and is the use atomic? What happens on a callback with a state from another browser? (S5)
6. Link flow. The callback attaches the identity to `link_user_id` from the stored state. Does it check that the session of the browser is still that user? Build the case: user A starts "Link GitHub", signs out, user B signs in on the same browser, the callback arrives. Where does the GitHub identity go? (S3)
7. `next` and `redirect_to`. `safe_redirect` must refuse another site. Try `//evil.example`, `/\evil.example`, `https:evil.example`, `/%2F%2Fevil.example`, a tab or a newline, a very long value. Check the backend and `LoginView.vue` (it accepts `next` only if it starts with `/` and not `//`).
8. Cookies. `resslab_session` and `resslab_login`: `HttpOnly`, `Secure` (when?), `SameSite=Lax`, path, lifetime. Is the session id rotated at sign-in? Does logout delete the server row, or only the cookie?
9. CSRF. Which routes check it and how (`auth/csrf.py`)? Can a form on another site sign someone in to the attacker's account (login CSRF), or sign them out?
10. Bad input that gives a 500 instead of a 4xx: a session cookie that is not a UUID, a challenge id that is not a UUID, a code with letters or spaces, a huge body, an ORCID or GitHub name over the column length. (S6)
11. Rate limits. List the decorator of every `/auth/*` route. Which key do they use? What does a user see on 429 (the frontend message)?
12. A disabled account: can it still sign in by any way (code, link, GitHub, ORCID)? Does it lose its sessions at once?
13. ORCID (#250): the first sign-in with no address sends to `/account?add_email=1&next=...`. Is `next` checked there too?

## Method

1. Read the code of each route, top to bottom. Write down every check and its order.
2. For each question, make the smallest proof:
   - First choice: a Claude in Chrome transcript on your local server: open `http://127.0.0.1:$FRONTEND_PORT/`, sign in, then call `fetch('/api/auth/...')` from the page with `javascript_tool`, and paste the status, the headers and the body. `wtx curl` and plain `curl` do not reach the servers from the sandbox, do not try them. The sign-in code and link go to `.wt-logs/backend.log`, because dev has no SMTP. Read it with `tail -n 50 .wt-logs/backend.log`.
   - Second choice: a test in a new file `backend/tests/test_review_01_<topic>.py`, marked `@pytest.mark.xfail(strict=True, reason="review 01: <finding id>")`. Copy the helpers of `test_auth_flow.py` (`_start`, `_github_state`, the `sign_in` fixture of `conftest.py`).
3. If the DB tests fail with `OperationalError`, the sandbox hides `secrets/.env`. Write the test anyway, write "not run" in the finding, and give a Claude in Chrome transcript if you can.
4. For the OAuth callbacks you cannot reach GitHub or ORCID. Use the monkeypatch pattern of `test_auth_flow.py`.

## Rules

- Review only. Do not change application code. You add only test files that prove a finding, and your findings file.
- A finding needs a file and line, and a proof.
- Send requests only to your own servers, with Claude in Chrome on the ports of your worktree. Never to stage, prod or any `epfl.ch` host.
- Do not call GitHub or ORCID for real. Do not post anything on GitHub.
- Give each finding a severity from the scale in `docs/review/README.md`. Pierre decides the final one.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/01-sign-in.md`, from the template. One section per question, in the order above.
- The test files.
- Commit on your branch with explicit paths: `docs(review): findings of package 01`. Do not open a pull request. Say when you are done.
