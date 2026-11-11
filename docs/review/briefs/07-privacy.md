# Brief 07: privacy and leaks

You list every piece of personal data the Hub keeps or sends, and find where it can leak. Review only: you find and prove problems, you do not fix them. Some answers are decisions for Pierre (what to keep, for how long, what to tell users). For those, write the facts and the options, not the decision.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 07 in `docs/review/review-plan.md` with the suspicions it names (S1, S2, S10), and `docs/review/findings/README.md`.
2. Read `docs/auth.md`, `docs/contributing-data.md` and `docs/dashboard-architecture.md` (the part about the response cache).
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

## Files

- `backend/resslab_hub/models/database/auth.py`: what the `auth_*` tables keep.
- `backend/resslab_hub/utils/caching.py`: the response cache and the list of paths it skips (around line 150).
- `backend/resslab_hub/main.py`: middleware, logging, error handlers.
- `backend/resslab_hub/auth/mailer.py`: what each mail says, and what it logs when there is no SMTP.
- `backend/resslab_hub/contributions/submission.py` (`build_pr_body`, `redact_emails`), `contributions/trailers.py`.
- `backend/resslab_hub/routers/root.py` (`/user`), `routers/analytics.py`, `routers/admin.py`.
- `frontend/src/views/ContributeView.vue` (the consent sentence), `frontend/src/utils/cookieConsent.ts`, `frontend/src/plugins/gtag.ts`.
- `frontend/src/locales/en.json`, `frontend/src/locales/fr.json`.

## Questions

1. The list. Make a table of each personal field: what it is (address, name, institution, GitHub login, ORCID iD, IP, user agent, session id), where it is stored (table and column, log, GitHub, browser storage, Google Analytics), who can read it, and how long it stays. This table is the main output of this package.
2. The response cache. It keys on the URL and sends `Cache-Control: public`. Every per-user route must be on the skip list. Read every router and find a route that answers per user (or per role) and is not skipped. Prove it with two `wtx curl` calls as two users, and compare the answers and headers. (S1)
3. `/user`. It is guarded by the machine credential. What does it return? Is it ever cached? The memory of the project says it once was (a "/user cache bypass bug"): check that it is fixed.
4. Logs. What do the backend logs write at each sign-in, submit, edit, admin action and error: addresses, codes, links, tokens, IPs? When `DEPLOYMENT` is set and `SMTP_HOST` is not, does the mailer still write the code to the log? Look at `mailer.py` around line 298 and at uvicorn access logs (they log the full URL, so a sign-in link with a token in the query string would land there).
5. The public data repo. A submission writes the name and the address of the contributor in the commit author, the trailers and the pull request body. The body is public on GitHub before any review. What can a person do to remove it later? Write the facts for Pierre: what GitHub keeps (commits on closed branches, the pull request page, forks), and what `redact_emails` hides only inside the Hub. (S2, S10)
6. Consent. What exactly does the user agree to before submit, and where is it written? Is it a sentence or a tick box? Does it say that the name and the address become public for ever? Compare the English and the French text.
7. Mails. What does each mail contain? Does any mail show the address of another person (for example a mail to an admin about an access request)? Do the mail links carry tokens that go to third parties (link checkers like EPFL Outlook safe links open them)?
8. Admin page. What personal data does an admin see? Can an admin export it? Is it logged when an admin looks at it?
9. Analytics. Which events go to Google Analytics, with which fields? Is any personal data sent (address, user id, a URL with a token or an id)? Does anything load before consent?
10. Retention and deletion. Old sessions, expired challenges, declined access requests, revoked invitations, disabled accounts: does anything delete them? Is there a way for a person to delete their account or get their data? Write the facts and the gaps for Pierre. (S10)
11. Error pages and answers. Does any 4xx or 5xx answer give the address of another user, a stack trace, or a SQL error?

## Method

1. Start with the table of question 1. Read the models, then follow each field through the code with `rg`.
2. For each leak, make the smallest proof:
   - First choice: a `wtx curl backend <path>` transcript on your local server, with headers (`-i`). Codes are in `.wt-logs/backend.log`.
   - Second choice: a test in a new file `backend/tests/test_review_07_<topic>.py`, marked `@pytest.mark.xfail(strict=True, reason="review 07: <finding id>")`.
   - For the logs: quote the lines from `.wt-logs/backend.log` (use `tail -n 50`, never `tail -f`).
3. If the DB tests fail with `OperationalError`, the sandbox hides `secrets/.env`. Write the test anyway, write "not run" in the finding.

## Rules

- Review only. Do not change application code. You add only test files that prove a finding, and your findings file.
- A finding needs a file and line, and a proof.
- Send requests only to your own servers, with `wtx curl`. Never to stage, prod or any `epfl.ch` host.
- Do not call GitHub for real. Do not post anything on GitHub.
- Do not copy a real person's address into the findings. Use `alice@uni.example` and the like.
- Give each finding a severity from the scale in `docs/review/README.md`. A decision for Pierre is a "note", with the options.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/07-privacy.md`, from the template. The table first, then one section per question.
- The test files.
- Commit on your branch with explicit paths: `docs(review): findings of package 07`. Do not open a pull request. Say when you are done.
