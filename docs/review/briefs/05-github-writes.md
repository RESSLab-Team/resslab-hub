# Brief 05: what we write to GitHub

You review everything the Hub writes on the data repo when a person submits or edits: branch, commit, pull request, reviewers. The data repo is public, so all of it is public for ever. Review only: you find and prove problems, you do not fix them.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 05 in `docs/review/review-plan.md` with the suspicions it names (B3, B4, S2, S7), and `docs/review/findings/README.md`.
2. Read `docs/contributing-data.md` and `docs/curation.md`.
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

Pierre does the GitHub side himself (App permissions, ruleset, branch protection). You do the code.

## What a submission writes

From `contributions/submission.py`:

- A branch `contrib/<database>/<first id>-<8 hex>`.
- One commit, authored as the contributor (name and address), with trailers: `Submitted-by: Name <address>`, `Institution`, `ORCID`, `GitHub: @login`, one `Dismissed-Warning` per warning.
- A pull request with a body from `build_pr_body`: database, counts, `**Contributor**: Name (address), Institution`, ORCID, `@login`, dismissed warnings in code spans, and help to edit the CSV.
- Review requests to the people of `DATA_REPO_REVIEWERS` (default `admins`).

## Files

- `backend/resslab_hub/contributions/github.py`: the githubkit client, timeouts, errors.
- `backend/resslab_hub/contributions/trailers.py`: `build_commit_message`, `_one_line`, `_clean_name`, `parse_trailers`, `owns_submission`.
- `backend/resslab_hub/contributions/submission.py`: `build_pr_body`, `_code_span`, `submit_contribution`, `update_contribution`.
- `backend/resslab_hub/contributions/reviewers.py`.
- `backend/resslab_hub/routers/contributions.py`: `_check_queue_capacity`, error answers.
- `backend/resslab_hub/routers/root.py`: `/upload`.
- The data repo: `../resslab-hub-data/.github/workflows/` (read only).
- Tests that exist: `backend/tests/test_contributions.py`.

## Questions

1. Pull request body. Name and institution go in with no escaping. What can a name like `<img src=x>`, `[click](https://evil.example)`, `@RESSLab-Team/admins`, `**Contributor**: Someone else`, or a name with a newline do? The name can come from GitHub or ORCID, so the person chooses it. (S2)
2. Trailers. `_one_line` and `_clean_name` fold whitespace and remove `<` `>`. Can a value add a fake trailer, break `Name <address>`, or make `parse_trailers` read another owner? Check with `owns_submission`: can a crafted name make a submission look like it belongs to someone else?
3. Branch name. `_slugify(ids[0])`: what does an id with `/`, `..`, `.lock`, spaces, or 300 characters give?
4. Queue cap. `_check_queue_capacity` counts open `contrib/` pull requests. Do pull requests from forks with a `contrib/` head count? What is the message at 503? What happens with 25 open, and two people who submit at the same time? (B3)
5. Reviewers. Who gets a review request, so a mail, on each new pull request? On each edit? (B4)
6. Failure in the middle. If the commit works and the pull request fails, the branch is deleted (`submission.py`, around line 561). What if the delete fails too? What if the edit commit works and something after it fails? List every way to leave a branch or a half pull request behind.
7. GitHub limits. The App has 5000 requests per hour. How many calls does one submit make? One edit? One curation page view? Is there a timeout on each call (githubkit has none by default)? What does the user see when GitHub is slow or down?
8. Error text. Does any answer send back a GitHub error body, a token, a URL with a token, or a Python exception text? (S7, #264 H3)
9. `/upload`. It needs the machine credential. What can it do with a crafted archive? Does it check the same things as `/validate`?
10. Data repo workflows. Read `../resslab-hub-data/.github/workflows/`. Can a pull request from a submission run code with secrets (`pull_request_target`, a script from the branch)? Which validator do they call (prod)? What happens when prod and the Hub that made the submission have different validators?

## Method

1. Read the code. Write down, for each user value, every place it goes on GitHub.
2. Prove with tests that mock the GitHub client, as `test_contributions.py` does. New file `backend/tests/test_review_05_<topic>.py`, marked `@pytest.mark.xfail(strict=True, reason="review 05: <finding id>")`. Assert on the body and the commit message that the mock receives.
3. If the DB tests fail with `OperationalError`, the sandbox hides `secrets/.env`. Write the test anyway, write "not run" in the finding. `build_pr_body` and `build_commit_message` need no database: test them directly.
4. Questions that need the real GitHub (5, 7 in part, 10 in part): write what to check, as "to check by Pierre", with the exact steps.

## Rules

- Review only. Do not change application code. You add only test files that prove a finding, and your findings file.
- A finding needs a file and line, and a proof.
- Send requests only to your own servers, with Claude in Chrome on the ports of your worktree. Never to stage, prod or any `epfl.ch` host.
- Do not call GitHub for real: no submit, no push to the data repo, no issue, no comment. The data repo is public.
- Give each finding a severity from the scale in `docs/review/README.md`.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/05-github-writes.md`, from the template. One section per question.
- The test files.
- Commit on your branch with explicit paths: `docs(review): findings of package 05`. Do not open a pull request. Say when you are done.
