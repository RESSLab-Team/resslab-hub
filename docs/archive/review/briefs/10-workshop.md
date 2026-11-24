# Brief 10: workshop readiness

You check that the Hub holds a room of about 30 people who all sign in and submit in the same hour, from the same network. You measure on your local server, and you list the gaps in the user flow that will hurt on the day. Review only: you find and prove problems, you do not fix them.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 10 in `docs/review/review-plan.md` with the suspicions it names (B1, B3, B5, B8, B10), and `docs/review/findings/README.md`.
2. Read `docs/contributing-data.md`.
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

## The day

About 30 attendees in one room, on the EPFL network or eduroam, so probably one public IP. Each one signs in (mail code, GitHub or ORCID), opens the editor, drops a small batch, fixes errors, submits, maybe edits once. All in about one hour. Prod runs one backend replica.

## Files

- `backend/resslab_hub/utils/rate_limit.py`, `backend/resslab_hub/auth/email_login.py` (hourly caps in SQL).
- `backend/resslab_hub/routers/contributions.py` (`_check_queue_capacity`, the limits on submit and edit), `routers/root.py` (`/validate`).
- `backend/resslab_hub/config.py` (`max_open_contributions`).
- `frontend/src/stores/contribution.ts`, `frontend/src/views/ContributeView.vue` (when `/validate` is called, the debounce).

## Questions

1. Limits on one IP. For each limit (mail per IP per hour, `/auth/email/start`, `/auth/email/verify`, `/validate`, submit, edit), how many requests does the room make in one hour? Count how often the editor calls `/validate` during a normal edit (read `ContributeView.vue` and the store). Which limit is hit first, and after how many minutes? (B1)
2. Measure. Write a small Python script in `$TMPDIR` that plays N users on your local backend: sign in by mail (read the codes from `.wt-logs/backend.log`), then call `/validate` with a batch from `sample-data/` at the rate of the editor. Run it with N = 5, 15, 30. Report the first 429, the time per `/validate` (median and worst), and errors. Do not call `POST /contributions`: it opens real pull requests on the test fork.
3. One slow request blocks the others? While one user validates the largest batch of `sample-data/`, measure the time of a small `GET` from another user. One replica, so a blocking validation blocks everyone. (B8)
4. Queue cap. With 30 submissions, the 26th gets a 503 (25 open `contrib/` pull requests). What message does the user see? Can they save their work? (B3)
5. The profile. A new account by mail has a name made from the address and no institution. A new GitHub account has the GitHub name. What will the commits and pull requests of the room look like? Can the user fix it before submit? (B5)
6. Lost work. What survives a reload, a closed tab, a session that ends, a sign-out, a 429 or a 503 during submit? Is there a "my submissions" list, so a person can find their pull request again? (B10)
7. Mail. 30 mails in a few minutes from the EPFL relay to many domains. What happens when a mail is late or lands in spam? Can the person ask again without hitting the cap? What is the fallback (GitHub, ORCID, an admin invitation)?
8. Roles at the door. Attendees with a non-academic address are viewers. How long does it take an admin to give 10 people the contributor role from the admin page, one by one? Is there a faster way (invitations before the day, `CONTRIBUTOR_DOMAINS`)?
9. The plan for the day. From all of the above, write the list of settings to change for the day and back after (limits, cap, reviewers, domains), with the place to change each one (code, config, overlay).

## Method

1. Read the code and count first (questions 1, 4 to 8). Then measure (2, 3).
2. Keep the load script in your findings file, so Pierre can run it again on stage, with his agreement and outside working hours.
3. For the frontend parts, use Claude in Chrome on `http://localhost:$FRONTEND_PORT/` when you need to see what the user sees. Sign in with the code from `.wt-logs/backend.log` (use `tail -n 50`).
4. If you write a test, put it in a new file `backend/tests/test_review_10_<topic>.py`, marked `@pytest.mark.xfail(strict=True, reason="review 10: <finding id>")`. If the DB tests fail with `OperationalError`, the sandbox hides `secrets/.env`: write "not run" in the finding.

## Rules

- Review only. Do not change application code.
- Load only your own local backend. A script cannot reach it from the sandbox: write the script, say "not run", and Pierre runs it. For a single request, use `fetch` from Claude in Chrome. Never stage, prod or any `epfl.ch` host.
- Do not submit for real, do not call GitHub for real, do not post anything on GitHub.
- Your local backend writes the mail codes to the log because dev has no SMTP. Do not set `SMTP_HOST`.
- Give each finding a severity from the scale in `docs/review/README.md`.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/10-workshop.md`, from the template. One section per question. The measures as a table.
- The load script.
- Commit on your branch with explicit paths: `docs(review): findings of package 10`. Do not open a pull request. Say when you are done.
