# Findings of package 05: what we write to GitHub

- Branch: `review/05-github-writes`
- Commit reviewed: `0e15c031` (from `dev`, with ORCID)
- Date: 2026-11-12
- Tests run: yes. `cd backend && python3 ../scripts/with-db.py uv run pytest tests/test_review_05_*.py -q` gives `17 xfailed`. Each test was also run with `--runxfail` to check that it fails on its own assertion and not on a setup error. No GitHub call: every test uses a fake client.

## Where each user value goes on GitHub

All of it is public, for good, on the data repo.

| Value | From | Commit author | Commit title | Trailers | PR title | PR body | Branch | File path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Name | account (GitHub profile, ORCID, or the mail local part) | raw (`github.py:412`) | | `Submitted-by`, folded on one line, `<>` removed | | raw (`submission.py:293`) | | |
| Address | account | raw | | `Submitted-by` | | raw | | |
| Institution | account | | | `Institution`, folded | | raw (`submission.py:294`) | | |
| ORCID | sign-in | | | `ORCID` | | raw (`submission.py:297`) | | |
| GitHub login | sign-in | | | `GitHub: @login` | | `@login` (`submission.py:301`), a real mention | | |
| Specimen id | CSV cell | | first id (`submission.py:496`) | | same as commit title | | `_slugify` of the first id (`submission.py:537`) | curve file name |
| Dismissed warning | form | | | `Dismissed-Warning`, folded | | in a code span (`_code_span`) | | |
| CSV cells | archive | | | | | | | blob content |

The id rule (`data/common.py:72`) allows spaces, `'`, `` ` ``, `@`, `#` and any letter, after a first letter or digit. It has no length limit.

## Summary

| Id    | Severity | Title | Suspicion | Proof |
| ----- | -------- | ----- | --------- | ----- |
| 05-1  | medium | The contributor's name is live markdown in the PR body | S2 | test |
| 05-2  | low | A name with a newline adds fields that the curation queue reads | S2 | test |
| 05-3  | medium | Trailers in any commit are trusted, also a fork's commit | | test |
| 05-4  | low | No length limit on an id, so the branch name has none either | | test |
| 05-5  | high | Pull requests from forks fill the queue and block every submission | B3 | test |
| 05-6  | medium | A pull request that exists can be closed by the cleanup | | test |
| 05-7  | low | A failed branch cleanup leaves no trace | | test |
| 05-8  | medium | Any error on the edit commit is answered "its branch moved" | | test |
| 05-9  | low | A GitHub timeout gives an empty reason: "(...repository ())" | S7 | test |
| 05-10 | low | An edit with no file change still rewrites the body | | test |
| 05-11 | medium | One request per file: a big batch passes GitHub's content limit | | test |
| 05-12 | medium | A rate limit makes the request sleep up to an hour | | test |
| 05-13 | low | Data repo CI breaks on an id with a space or a quote | | local transcript |
| 05-14 | note | Each new PR mails every admin of the data repo | B4 | code |
| 05-15 | note | The doc still says prod runs the old validator | | doc line |
| 05-16 | note | The queue cap docstring says the rate limit is per account | | code |

## Question 1. Pull request body

The name and the institution go into the body as they are (`submission.py:293-294`). GitHub renders the body as markdown with some HTML. So a name can ping a person or a team, add a link or an image, or close an issue of the data repo when the pull request is merged (`fixes #1`). The name comes from the GitHub profile or from ORCID, so the person picks it. A newline in the name adds lines that `_parse_pr_body` reads back. Dismissed warnings are safe, they are in code spans.

### 05-1 The contributor's name is live markdown in the PR body

- Severity: medium
- Suspicion: S2 (confirmed)
- Where: `backend/resslab_hub/contributions/submission.py:293`
- Status: new

A name like `Ada @RESSLab-Team/admins`, `Ada [read me](https://evil.example)`, `Ada <img src=...>` or `Ada, fixes #1` goes into the body with no escaping. The mention sends a notification to that person or team. The link and the image show on a public page under the Hub's App, so they look trusted. The closing keyword closes an issue at merge. Nothing here leaks data, but it uses the Hub to send mails and to post content in our name.

Proof: `backend/tests/test_review_05_pr_body.py::test_the_name_is_not_markdown_in_the_body` (4 cases), marked `xfail(strict=True)`.

Fix: put the name and the institution in a code span, like the dismissed warnings, or escape markdown, `@` and `#` before writing them.

To check by Pierre: the institution has no writer in the app today (no form sets it, from what I read), so only the name is open. Confirm that.

### 05-2 A name with a newline adds fields that the curation queue reads

- Severity: low
- Suspicion: S2 (confirmed at the sink)
- Where: `backend/resslab_hub/contributions/submission.py:293`, `backend/resslab_hub/routers/curation.py:179`
- Status: new

The body is plain lines. A name with `\n- **GitHub**: @someone-else` writes a second field line. `_parse_pr_body` uses `^` with `re.M`, so it reads the lines the name added. In the test, the queue gets no contributor at all (the Contributor line breaks), and would read the fake GitHub and ORCID lines. Low because I could not prove that a GitHub or ORCID name can hold a newline.

Proof: `backend/tests/test_review_05_pr_body.py::test_a_newline_in_the_name_cannot_add_fields_the_queue_reads`, marked `xfail(strict=True)`.

Fix: fold the name on one line before the body, as `_one_line` does for the trailers. The fix of 05-1 also covers it.

To check by Pierre: on a test GitHub account, try to save a profile name with a newline (through the API, `PATCH /user` with `"name": "A\nB"`), and the same on an ORCID sandbox account. If one of them keeps it, raise 05-2 to medium.

## Question 2. Trailers

The Hub's own fields cannot forge a trailer. `_one_line` (`trailers.py:51`) folds every kind of line break, so a value cannot start a new trailer line. `_clean_name` (`trailers.py:56`) removes `<` and `>`, so a name cannot break `Name <address>`. The address comes from a verified sign-in. But `provenance_from_commits` (`trailers.py:130`) trusts the trailers of any commit in the pull request, not only the commits the App made.

### 05-3 Trailers in any commit are trusted, also a fork's commit

- Severity: medium
- Where: `backend/resslab_hub/contributions/trailers.py:141-150`
- Status: new

The data repo is public. Anyone can open a pull request from a fork with a commit message that copies the Hub's trailers, with the name and address of a real researcher. The Hub then shows this researcher as the submitter, and `owns_submission` says the submission is theirs. The queue shows a fork badge (`CurationQueueView.vue:181`), but the review page does not. A curator can trust and merge data that the named person never sent. The edit route refuses forks (`submission.py:622`), so nobody can take over a real submission this way.

Proof: `backend/tests/test_review_05_trailers.py` (2 tests), marked `xfail(strict=True)`.

Fix: read the trailers only from commits whose committer is the App (or check the commit sha against the one the Hub created), and ignore pull requests from forks in the provenance.

## Question 3. Branch name

`_slugify` (`submission.py:182`) keeps only `[a-z0-9-]`. So `/`, `..`, `.lock` and spaces never reach the branch name: `a/../b.lock` gives `a-b-lock`. An id with no ASCII letter or digit gives `batch`. The length has no limit anywhere.

### 05-4 No length limit on an id, so the branch name has none either

- Severity: low
- Where: `backend/resslab_hub/data/common.py:72`, `backend/resslab_hub/contributions/submission.py:537`
- Status: new

An id of 250 characters gives a branch segment of 259 bytes. Git refs are files on many systems, and most file systems refuse a name over 255 bytes. The id also goes into the commit and PR titles. The Hub sends every blob, the tree and the commit before GitHub can refuse the ref or the title, so the person waits, then gets a 502 with GitHub's reason.

Proof: `backend/tests/test_review_05_branch_name.py` (2 tests), marked `xfail(strict=True)`.

Fix: limit the id length in the validator (an error, for example 100 characters), and cut the slug to a fixed length.

To check by Pierre: on the test fork, what GitHub answers to a ref of 300 characters and to a PR title over 256 characters.

## Question 4. Queue cap

`_check_queue_capacity` (`routers/contributions.py:102`) lists the open pull requests and counts the ones whose head branch starts with `contrib/` (line 117). It does not look at `head_repo`, so pull requests from forks count. At the cap it answers 503 "The review queue is full. Try again once the open submissions are reviewed." It runs before validation (line 241). When GitHub fails, it lets the submission pass.

### 05-5 Pull requests from forks fill the queue and block every submission

- Severity: high
- Suspicion: B3 (confirmed)
- Where: `backend/resslab_hub/routers/contributions.py:117`
- Status: new

Anyone with a GitHub account can fork the public data repo and open 25 pull requests from branches named `contrib/x`. From then on, every researcher gets 503 on submit, until a maintainer closes them. Nothing in the message says why. During the workshop, this stops everybody. The helper `from_fork` (`projection.py:114`) exists but is not used here.

Proof: `backend/tests/test_review_05_queue_cap.py::test_pull_requests_from_forks_do_not_fill_the_queue`, marked `xfail(strict=True)`. 30 fork pull requests give the 503.

Fix: count only pull requests whose head repo is the data repo (`from_fork` is false), or only the ones the App opened.

Two smaller points, not proven by a test:

- Check then act: the count is read, then the submission takes seconds. Two people at 24 both pass, so the queue can go over the cap by a few. Harmless.
- The 503 comes before validation, so a person at the cap does not learn if the batch is valid. A "try later" with a valid batch would be kinder.

## Question 5. Reviewers

With the default `DATA_REPO_REVIEWERS=admins` (`config.py:55`), each new pull request asks a review from every account that `list_collaborators(affiliation="all", permission="admin")` returns (`github.py:331`), minus the person who opened it (`reviewers.py:40-47`). GitHub sends each one a mail. It happens on a new submission (`submission.py:568`) and on a verification pull request (`verification.py:311`). An edit asks nobody. It reads one page of 100.

### 05-14 Each new PR mails every admin of the data repo

- Severity: note
- Suspicion: B4 (confirmed, as designed)
- Where: `backend/resslab_hub/contributions/reviewers.py:40`
- Status: new

This is what `docs/contributing-data.md:187` says. With `affiliation="all"`, owners of the organisation have admin on every repo, so they are in the list too. With 30 people in a workshop, each admin gets 30 mails in an hour.

Proof: code read only (`reviewers.py:40-47`, `github.py:326-334`).

Fix: a decision, not a bug. Use a short fixed list or a team for the workshop.

To check by Pierre:

1. `gh api 'repos/EPFL-ENAC/resslab-hub-data/collaborators?affiliation=all&permission=admin' --jq '.[].login'` and look for organisation owners who should not get the mails.
2. Same call with `affiliation=direct`, to see who would stay with a narrower filter.
3. Decide the `DATA_REPO_REVIEWERS` value for stage and prod before the workshop.

## Question 6. Failure in the middle

A new submission does blobs, tree, commit, branch (`commit_files`), then the pull request. If the pull request fails, the Hub deletes the branch (`submission.py:560`). An edit does blobs, tree, commit, a ref update, then a body update that is best effort (`submission.py:725-739`). The ways to leave something behind:

1. Blobs, tree and commit with no ref: they stay in GitHub's object store but no branch points to them. Not visible to people. Fine.
2. The branch is created but its answer is lost: the Hub sees an error, raises 502, and does not delete the branch (the delete is only around the pull request). A branch with the name and address stays. Not tested, same family as 05-7.
3. The pull request fails and the delete fails too: 05-7.
4. The pull request is created but the answer is lost: 05-6.
5. Review requests fail: only logged, the submission succeeds (`reviewers.py:60-66`). Fine.
6. The edit commit fails for a reason that is not a moved branch: 05-8.
7. The edit commit works and the body update fails: the body keeps the old counts. Only logged. The review page reads the counts from the body, so it is wrong until the next edit.
8. An edit with no file change: 05-10.
9. The ingress or the browser gives up before the Hub ends. The Hub goes on and opens the pull request. The person sees an error and submits again: a second pull request with the same ids. `reject_clashes` checks only `main`, not the open pull requests. Not tested here (needs the real ingress).

### 05-6 A pull request that exists can be closed by the cleanup

- Severity: medium
- Where: `backend/resslab_hub/contributions/submission.py:560-561`
- Status: new

The Hub deletes the branch on any error of `create_pull_request`. But the pull request can exist when the error comes: githubkit retries a 5xx on POST up to three times, so a POST that GitHub ran but answered 502 comes back as 422 "A pull request already exists". A timeout after GitHub got the request does the same. Deleting the branch closes the pull request. The person gets a 502 and submits again. The closed pull request, with the name, the address and the data, stays public.

Proof: `backend/tests/test_review_05_failures.py::test_a_pull_request_that_exists_is_not_closed_by_the_cleanup`, marked `xfail(strict=True)`.

Fix: before the delete, look for an open pull request from this branch. When it exists, use it and answer success.

### 05-7 A failed branch cleanup leaves no trace

- Severity: low
- Where: `backend/resslab_hub/contributions/github.py:491-498`
- Status: new

`delete_branch` catches every error and does nothing, not even a log line. When the delete fails (no permission, GitHub down), a branch with a name and an address stays on the public repo, and nobody knows it is there.

Proof: `backend/tests/test_review_05_failures.py::test_a_failed_branch_cleanup_is_logged`, marked `xfail(strict=True)`.

Fix: log a warning with the branch name, so someone can delete it by hand.

### 05-8 Any error on the edit commit is answered "its branch moved"

- Severity: medium
- Where: `backend/resslab_hub/contributions/submission.py:716-722`
- Status: new

Every error of `commit_on_branch` gives 409 "its branch moved on GitHub. Reload the page and make your changes again." A timeout, a 5xx, a rate limit or a refused permission all give this text. The person reloads, redoes the work, and fails again for the same reason. They lose their changes each time.

Proof: `backend/tests/test_review_05_failures.py::test_a_timeout_on_the_edit_commit_is_not_called_a_moved_branch`, marked `xfail(strict=True)`.

Fix: answer 409 only when GitHub says the update is not a fast-forward (422 on the ref update). Answer 502 with `describe_error` for the rest.

### 05-10 An edit with no file change still rewrites the body

- Severity: low
- Where: `backend/resslab_hub/contributions/github.py:464`, `backend/resslab_hub/contributions/submission.py:725`
- Status: new

When the files are the same, `commit_on_branch` makes no commit. But the body is rewritten with the new dismissed warnings. The trailers, read at merge, keep the old ones. So the body and the trailers say different things, and the new dismissed warnings are lost after the squash merge.

Proof: `backend/tests/test_review_05_failures.py::test_an_edit_with_no_file_change_keeps_body_and_trailers_in_step`, marked `xfail(strict=True)`.

Fix: when no commit is made, either refuse the edit ("nothing changed"), or make an empty commit that carries the new trailers.

## Question 7. GitHub limits

Calls, counted in the code:

- One submit: about 9 calls plus one per file. Base sha, read the main CSV on `main`, one blob per changed file (the merged main CSV and each curve file, 8 at a time, `github.py:377`), tree, commit, ref, pull request, list admins, request reviewers. 40 specimens with 3 curves each: about 130 calls. 200 specimens with 3 curves: about 610, so 8 such submits use the App's 5000 per hour.
- One edit: get the pull request, list its commits, read the head tree and the main CSV, one blob per changed file, tree, commit, ref update, body update. About 9 plus the changed files.
- One curation page: the list costs 1 call (cached 60 s) plus 1 per open pull request for the files (cached 600 s). A review page costs about 6 cold calls (pull request, commits, files, two CSV reads, comments) plus one per curve shown. Caches are per pod.

Timeout: `REQUEST_TIMEOUT = 30.0` (`github.py:37`) on the githubkit client. It is per httpx phase (connect, read, write), not per submission. The retries come on top. When GitHub is slow or down, the person waits, then gets a 502 from the Hub, or the ingress gives up first (5 minutes, per S8). The frontend has no axios timeout.

### 05-11 One request per file: a big batch passes GitHub's content limit

- Severity: medium
- Where: `backend/resslab_hub/contributions/github.py:377-381`
- Status: new

GitHub's secondary limit for requests that create content is 80 per minute and 500 per hour. One blob per file means a batch of 40 specimens with 3 curves sends 124 content requests in a few seconds. GitHub answers 403 with a secondary rate limit. With githubkit's retry (05-12), the person waits, then fails. The hour limit is shared by every person who submits.

Proof: `backend/tests/test_review_05_github_limits.py::test_a_large_batch_stays_under_the_per_minute_content_limit`, marked `xfail(strict=True)`. It counts 124.

Fix: send the file contents inline in the tree (`content` instead of `sha`), which needs one request for all the text files. Or pace the blobs.

To check by Pierre: on the test fork, submit a batch with more than 80 curve files from a local Hub (`DATA_REPO` already points at the fork) and read the backend log for a 403 "secondary rate limit".

### 05-12 A rate limit makes the request sleep up to an hour

- Severity: medium
- Where: `backend/resslab_hub/contributions/github.py:137-150`
- Status: new

The Hub keeps githubkit's default retry. On a rate limit answer, it sleeps `retry-after` (or until the reset) and tries once more, inside the request. For the primary limit, the reset can be an hour away. Meanwhile the person waits, the ingress gives up after 5 minutes, and the work goes on in the backend with no one to answer. It also retries 5xx on POST three times, which is what makes 05-6 possible.

Proof: `backend/tests/test_review_05_github_limits.py::test_the_hub_does_not_sleep_for_an_hour_inside_a_request`, marked `xfail(strict=True)`. The retry rule asks to wait 3600 s.

Fix: give githubkit a retry rule with a short cap (a few seconds) for rate limits and no retry for POST on 5xx, and answer the person "GitHub is busy, try in N minutes".

## Question 8. Error text

No answer sends a token or a URL with a token. The handler for `RequestFailed` (`main.py:162-166`) sends GitHub's message, cut to 300 characters, never the body or the headers. `/upload` and `/contributions` send a fixed sentence for unknown errors (#264 H3). But `describe_error` (`github.py:68-69`) returns `str(exc)` for any error that is not `RequestFailed`. It goes into the 502 of a submit (`submission.py:565`), of a verification (`verification.py:308`) and into curation answers (`curation.py:285, 612, 693, 832`). Today those texts are httpx or githubkit messages, so no secret, but any exception text can reach the person.

### 05-9 A GitHub timeout gives an empty reason

- Severity: low
- Suspicion: S7 (partly confirmed: Python exception text reaches the caller, but here it is empty, not secret)
- Where: `backend/resslab_hub/contributions/github.py:68-69`
- Status: new

A real httpx read timeout in async code has an empty message (httpcore maps anyio's bare `TimeoutError`). So a submit that times out answers "The pull request could not be opened on the data repository ()." The person cannot know it was GitHub being slow.

Proof: `backend/tests/test_review_05_failures.py::test_a_github_timeout_is_described_in_words`, marked `xfail(strict=True)`. The test opens a local socket that never answers, so the timeout is the real one.

Fix: give `describe_error` a sentence for timeouts and other network errors ("GitHub did not answer in time"), and use the class name when the text is empty. Never use `str(exc)` for unknown errors.

## Question 9. `/upload`

`/upload` (`routers/root.py:120`) needs the machine credential. It extracts the archive with `safe_extract_targz` (links, member count, sizes, paths), then runs `upload_all`. It does not run `validate_all` or `check_paths`, as `/validate` does. For each main CSV, it deletes the rows that are not in the file, with their curves (`data/uploader.py:370-380`). So a crafted archive with a main CSV of one row empties that table. Errors answer with the failed paths only, not the text (#264 H3). This is by design: the credential is for the data repo's workflow and the CronJob, which send the full main CSV. No finding, no test (it needs the database). The risk is the credential itself, and it leaked before (it was public 17 months, rotated 2026-09-01).

No finding.

## Question 10. Data repo workflows

Read at `origin/main` of the data repo (`5b3ee6c`). `data-validation.yml` runs on `pull_request`, not `pull_request_target`. It runs no script from the branch: only `git diff`, `xargs tar` and `curl`. The file names go to `tar` through `xargs` with no shell, and they all start with the folder name, so they cannot become a `tar` option. So a pull request cannot run code with the secret. It calls `https://resslab-hub.epfl.ch` (prod) with `API_PASSWORD_PROD`. A pull request from a fork gets no secrets, so its `authentification` job fails.

The Hub validates the submission with its own validator before it opens the pull request. CI then validates the same files with prod's validator. When the Hub that made the submission (dev or stage) is newer than prod, CI can refuse a file the Hub accepted, or the other way. The pull request then has a red check that the person cannot fix.

### 05-13 Data repo CI breaks on an id with a space or a quote

- Severity: low
- Where: data repo `.github/workflows/data-validation.yml:88`, `backend/resslab_hub/data/common.py:72`
- Status: new

The Hub accepts ids with a space (a warning only, `validator.py:534`) and with a `'`. CI packs the files with `git diff --name-only | xargs tar`. `xargs` splits on spaces and stops on a single quote. So the step fails and the pull request gets a red check, with an error that has nothing to do with the data. Accented letters pass (git quotes them, tar unquotes them).

Proof, in a throwaway repo in `$TMPDIR`, with curve files `B 9.csv`, `O'Neil-1.csv`, `Bé9.csv`, `B10.csv`:

```text
$ git diff --diff-filter=AM --name-only $BASE HEAD braces/ | xargs tar --exclude-vcs -czf braces.tar.gz
xargs: unmatched single quote; by default quotes are special to xargs unless you use the -0 option
tar: braces/force_displacement/B: Cannot stat: No such file or directory
tar: 9.csv: Cannot stat: No such file or directory
tar: Exiting with failure status due to previous errors
exit: 123
$ tar -tzf braces.tar.gz
braces/force_displacement/B10.csv
braces/force_displacement/Bé9.csv
```

Fix: use `git diff -z --name-only ... | xargs -0 tar ...` in the workflow, and refuse `'` in ids in the Hub (or make the space an error).

### 05-15 The doc still says prod runs the old validator

- Severity: note
- Where: `docs/contributing-data.md:184`
- Status: new

"Until 2.0 is released, prod runs the old validator". Prod runs 2.1.0 since October 2026. The real point to write is the one above: CI uses prod's validator, which can differ from the Hub that made the submission.

Proof: the doc line.

Fix: replace the sentence with "CI validates with prod's version; a submission made on dev or stage can get a different answer".

To check by Pierre:

1. In the data repo settings, Actions, General: is "Require approval for fork pull request workflows" set to all outside contributors?
2. In the ruleset or branch protection of `main`: is the `validation-passed` check required? If yes, a fork pull request can never be merged (no secret, so `authentification` fails). If no, a red check does not block a merge.
3. The `changes` and `validate` jobs check out `ref: github.event.pull_request.head.ref` from the base repo. For a fork pull request, that branch is not in the base repo, so the checkout fails, or, worse, checks out a base repo branch with the same name and validates other files. Open a fork pull request on the test fork from a branch named like an existing `contrib/` branch and look at which files the job packs.
4. Compare the validator version of prod with stage and dev (`/api/healthz` or the image tag), and keep it in mind when a submission made on stage gets a red CI.

## Other

### 05-16 The queue cap docstring says the rate limit is per account

- Severity: note
- Where: `backend/resslab_hub/routers/contributions.py:105`
- Status: new

The docstring says "The rate limit is per account and per pod". The limiter uses `get_remote_address` (`utils/rate_limit.py:13`), so it is per IP address and per pod. In a workshop room behind one NAT, everybody shares the `5/hour` of submit, and failed tries (422, 503) count too. This belongs to package 10, I only note the wrong comment.

Proof: the two lines.

Fix: fix the docstring. Package 10 decides on the key.

## Rejected suspicions

| Suspicion | Why it is not a problem | Where |
| --------- | ----------------------- | ----- |
| A Hub field forges a trailer | `_one_line` folds every line break that `splitlines()` knows, `_clean_name` removes `<` `>`. A value cannot add a trailer line or break `Name <address>` | `backend/resslab_hub/contributions/trailers.py:51-60` |
| An id puts `/`, `..` or `.lock` in the branch | `_slugify` keeps only `[a-z0-9-]` | `backend/resslab_hub/contributions/submission.py:182` |
| A data repo workflow runs code from the branch with a secret | `pull_request` only, and the steps run no file from the branch. File names reach `tar` through `xargs`, with no shell, and start with the folder name | data repo `.github/workflows/data-validation.yml:4,88` |
| An error answer sends a token or a GitHub body | `describe_error` keeps only `message` and `errors`, cut to 300 characters. The token is never in a message or a URL path | `backend/resslab_hub/contributions/github.py:70-85` |
| A later push takes over a submission | The owner comes from the first commit with `Submitted-by`, and the edit route refuses forks. But see 05-3 for a fork that writes the first commit | `backend/resslab_hub/contributions/trailers.py:148`, `submission.py:622` |

## Not proven

- An id like `B fixes #1` (allowed, with a space warning) goes into the commit title (`submission.py:496`). The squash merge keeps it on `main`, and GitHub closes issue #1 of the data repo for a closing keyword in a commit on the default branch. Proof: merge such a pull request on the test fork and look at issue #1.
- A branch is left when the ref is created but its answer is lost (`github.py:432`, `submission.py:544`). The delete covers only the pull request call. A test like 05-6 with `commit_files` raising after the ref would prove it.
- A second submission after an ingress timeout opens a duplicate pull request (`reject_clashes` reads only `main`). Needs the real ingress; a test with a fake client that keeps the first pull request open would prove the Hub accepts the second.
- The raw name in the git author field (`github.py:412`): GitHub may refuse a name with a newline or `<` with 422. Needs the real GitHub (see 05-2).
- Two submissions at 24 open both pass the cap (check then act). A test with two concurrent calls and a slow `open_pulls` would prove it.

## Not checked

- Question 5 and parts of 7 and 10 on the real GitHub: listed under "To check by Pierre", as the brief asks. I made no GitHub call.
- How the frontend shows a 502, 503 and 409 of submit and edit: not opened in Claude in Chrome, since a real submit would write on the test fork.
- The ingress values (5 minute read timeout, 50 MB body) come from S8 in `review-plan.md`. I did not find them again in the k8s config checkout.
