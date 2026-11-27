# Contributing data

How an experiment goes from a folder on a researcher's laptop to a row in the
database. The app side of it, from the editor to the pull request. The data
repository's own rules (folder layout, headers, units) are in the README of
each database folder there, shown in the editor as well.

This page is the developer reference. For the steps of each reader (submit,
review, run), start at [How data gets into the Hub](contribute/index.md).
Sign-in, roles and the account page are in [auth.md](auth.md). Test batches
to try all this with: [sample-data/README.md](https://github.com/RESSLab-Team/resslab-hub/blob/dev/sample-data/README.md).

## What a contributor sees

`/contribute` needs the `contributor` role, which an academic address gets at
sign-in (`auth/roles.py`). The route sends to `/contribute/new`, the editor
(`frontend/src/views/ContributeView.vue`):

- a database picker (changing it with unsaved rows asks once),
- the experiment cards (`components/contribute/ExperimentCards.vue`), one
  card per row of the primary CSV, fields folded by scientific category, the
  card head pinned while scrolling. Their toolbar is for files only: the
  starter kit, the template CSV and the dictionary CSV, all downloads,
- a status bar with the client and server verdict,
- a guide rail on the right (`ContributionGuide.vue`), for reading: the
  database README and a searchable data dictionary, each with a link to its
  file in the data repository. Both leave out the columns the Hub fills
  itself (`MANAGED_COLUMNS` in `utils/curationStatus.ts`, today only
  `data_curation_status`),
- a submit dialog that shows who is submitting, from the session.

Files get in by drop or by the folder picker: a whole folder, a zip, or loose
files. Nothing is refused up front. `utils/intake.ts` sorts them locally into
the primary CSV (recognised by its headers against the selected database),
curve files (recognised by folder name and headers, `utils/timeseries.ts`)
and leftovers, and reports what it did. A second drop merges by id, so the
attachments stay. `NA` in a cell means no value.

## Validation while editing

Every edit restarts a 2 s timer (`AUTO_VALIDATE_DELAY_MS` in
`stores/contribution.ts`); when it fires, the editor rebuilds the archive and
posts it to `POST /validate?type=<type>&check_duplicates=true`. A row added by
hand is a draft for 30 s (`DRAFT_SETTLE_MS`): its empty required fields show
as hints, not errors, until the person had time to fill them.

Submit is allowed when (`canSubmit`): at least one id, no client error, no
file error, no experiment still waiting for its test data, a server verdict
of pass or warn, nothing in flight. Warnings never block. The ones the
contributor dismissed are listed in the pull request body, so the reviewer
sees them.

The archive is a gzipped tar built in the browser (`utils/tar.ts`, a small
ustar writer, no dependency). It holds the primary CSV (blank cells become
`NR`) and one file per attached curve at `<directory>/<id>.csv`, the same
layout the uploader expects (`get_args_all` in
`backend/resslab_hub/data/uploader.py`). The same archive is what
`/validate` and `/contributions` receive.

## What `POST /validate` does

`backend/resslab_hub/routers/root.py`. Two ways in: a signed-in account of
any role, or the machine credential (`API_USERNAME` / `API_PASSWORD`), which
is what the data repository's CI uses. 30 requests per minute per client.

1. The archive is extracted with `safe_extract_targz` (no path escapes, size
   caps) and validated inline, one process: a worker pool would import the
   app once per worker and blow the memory limit of a pod.
2. `validate_all` (`data/validator.py`) checks headers, types, nullability,
   dates, booleans, the curve files' required columns, and the rules the
   database README promises (#319).
3. Range warnings: a numeric value more than one full span outside the
   `[min, max]` of the existing data for that column, only when the column
   has at least `RANGE_MIN_COUNT` (20) values in the database
   (`TableValidator._check_range`).
4. With `check_duplicates` (the editor sets it, the CI does not), an id that
   already exists in the database is an error on the id cell. If the GitHub
   App is configured, ids at the head of the data repo are checked too, best
   effort, to catch a specimen merged but not yet uploaded.

Data problems come back as `200` with `valid: false` and a `results` list per
file and row. `4xx` is for transport only: bad archive, too big, too many
requests.

## Formatting with an AI agent

Most researchers have their data in another format. Converting it by hand
takes days. So the guide rail of the form has a block "Format your data with
an AI agent": a short prompt the researcher copies into their own agent
(Claude, ChatGPT, Copilot...). We don't run a chatbot. The agent works on the
researcher's machine, and stops at a folder: the researcher drops it on the
form and submits under their own name, like any other submission.

The prompt (`frontend/src/utils/agentPrompt.ts`) only points to the agent
guide. Everything else is in `backend/resslab_hub/routers/agent.py`, behind
`CONTRIBUTIONS_ENABLED` like the rest of the pipeline:

| Route | What |
| --- | --- |
| `GET /agent/guide` | Markdown: the method, the CSV rules, the list of databases. |
| `GET /agent/guide/{database}` | Markdown: the method, the folder layout, the README and the data dictionary of one database, on one page. |
| `POST /agent/validate?database=` | The same checks as `/validate`, without an account. |

- The method is the only hand-written part: `backend/resslab_hub/agent/guide.md`.
  Edit it when you see an agent go wrong. It tells the agent to show its
  column mapping first, never invent a value, fix format errors alone, and
  ask the researcher about every warning instead of changing a measured value.
- The rest of the page is built from what the hub already uses, in
  `agent/guide.py`: the folder layout and the response headers from
  `get_args_all` and `validate_one_file`, the README and the dictionary from
  the database. A new column or a renamed header shows up with no edit.
- "In the hub now" in the dictionary table: for numbers, the range the range
  warning compares with; for text, the values in use (30 at most, no numbers,
  no `NA`/`NR` words), so the agent reuses the same vocabulary. Kept in memory
  per data version, like the response cache.
- `/agent/validate` is open to anybody, so it is smaller than `/validate`:
  10 MB, 10 a minute per address, one check at a time for the whole process
  (a second caller gets a `429` with `Retry-After`), the check in a thread,
  ids already in the database are errors, and no call to GitHub. The answer
  has no legacy arrays. An archive where nothing is found at the expected path
  (`output/braces/...` instead of `braces/...`) is an error, not an empty pass.
- `frontend/public/llms.txt` points agents that land on the site to the guide.

## From submission to pull request

`POST /contributions` (`routers/contributions.py`), `contributor` role, an
account with a name and a verified email, 5 per hour. It:

1. validates the archive again server side (errors block, warnings do not),
2. checks every path against the allowlist derived from the uploader's type
   map, and refuses ids that already exist at the head of the data repo,
3. appends the rows to the repo's primary CSV, aligned by column name (a
   legacy column the dictionary no longer has gets `NR`), with
   `data_curation_status` set to `unverified` whatever the batch says (#253,
   see [curation.md](curation.md#verification)),
4. writes one commit on a new branch `contrib/<type>/<first-id-slug>-<hex>`,
   the contributor as git author, the App bot as committer, through the Git
   Data API (blob, tree, commit, ref), then opens the pull request into
   `DATA_REPO_BASE_BRANCH`.

All of it goes through `DataRepoClient` (`contributions/github.py`), a thin
async wrapper over githubkit authenticated as a GitHub App installation. The
App needs `contents: write` and `pull requests: write` on the data repo,
nothing else (the Metadata read every App has covers the list of admins). The curation queue reads through the same client.

### Settings

| Key | What it is |
|---|---|
| `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_APP_INSTALLATION_ID` | The App that opens the pull requests. All three or the feature is off: `POST /contributions`, the detail routes of curation and the verification routes answer `503`. The queue and the `GET /verification` list answer `configured: false` instead. Not the OAuth pair of [auth.md](auth.md), which is for sign-in. |
| `CONTRIBUTIONS_ENABLED` | `true` by default. `false` switches the whole pipeline off: submit and edit, curation, verification, sign-in and account. The backend answers `404` on those endpoints and the frontend hides every link to them (the routes go to `/`). `GET /auth/me` keeps answering `{"user": null}`, and `/validate` and `/upload` do not change. Read at startup, so restart the pods after a change. `GET /features` tells the frontend the value it acts on: this setting and the GitHub App above. How to switch it in one environment: [releasing.md](releasing.md#switching-the-contribution-pipeline-off). |
| `DATA_REPO` | `RESSLab-Team/resslab-hub-data` by default, what stage and prod use. Dev and local setups use the test fork `EPFL-ENAC/resslab-hub-data-test` instead, with the `GITHUB_APP_INSTALLATION_ID` of the App on EPFL-ENAC (the installation id is per org). See [Trying it locally](#trying-it-locally). |
| `DATA_REPO_REVIEWERS` | Who is asked to review each pull request the Hub opens (#266). `admins` by default, what dev, stage and prod use: every account with admin on the data repo, read from GitHub at each pull request. `none` asks nobody: local setups use it, so a test submit on the fork does not email its admins. A comma list of GitHub logins asks exactly those. |
| `DATA_REPO_BASE_BRANCH` | `main` by default, the only long-lived branch of the data repo. Submissions from stage (the test site) land there too: close those, never merge them. |
| `MAX_OPEN_CONTRIBUTIONS` | `25` by default. When that many `contrib/` pull requests are open, `POST /contributions` answers `503` ("The review queue is full"). The rate limit is per client and per process, so this is the cap that holds across many accounts. |

Defaults in `backend/resslab_hub/config.py`.

### Provenance: commit trailers

Who submitted, and what they dismissed, is in the commit message, as git
trailers (`contributions/trailers.py`), the same mechanism as
`Signed-off-by`:

```
Submitted-by: Ada Lovelace <ada@somewhere.edu>
Institution: Somewhere University
ORCID: 0000-0002-1825-0097
GitHub: @ada
Dismissed-Warning: DEMO-BRC-013: area=68050.53 far outside the existing range
```

Why trailers and not a file: the data repo squash-merges, GitHub makes the App
the author of the squash commit, and the merge keeps the commit messages. So
on `main` the trailers are the only trace of the contributor. Ownership reads
the `Submitted-by` of the **first** Hub commit of the branch, so a later push
cannot take a submission over; the latest `Dismissed-Warning` list comes from
the last commit. Pull requests older than the trailers fall back to a JSON
record under `contributions/` in the data repo.

## Editing an open submission (#321, #325)

`/contribute/edit/<pr number>` opens the same editor on a pull request. The
store loads the pull request through the curation endpoints, checks `mine`
before doing any work, and refills the cards from the files the pull request
added (`editableFiles` in `utils/curation.ts` decides which files the editor
can hold; the others stay on the branch untouched).

A new submission lands on this page too, as soon as its pull request is open
(#403). The store takes the pull request as its edit target and the URL is
replaced with `/contribute/edit/<pr number>`, without a reload. So the page
after a submit can be refreshed, linked and shared: a refresh rebuilds it from
the pull request like any edit. Submitting again from there updates the same
pull request, it never opens a second one.

Submitting calls `PUT /contributions/<pr number>` with the rebuilt archive
and the `head_sha` the editor loaded. 10 per hour. The backend:

- refuses a closed pull request,
- answers `409` if the branch moved since (`head_sha` differs): reload and
  redo,
- answers `403` if the account does not own the submission (trailer rule
  above) and is not a curator. A curator's commit is authored by the
  curator, the trailers keep naming the person who submitted,
- validates again, rewrites the primary CSV keeping every row this
  submission does not own, and commits on top of the branch.

## Why a submit is fast (#337)

Two things in `contributions/github.py`:

- one `httpx.AsyncClient` per process, kept open, instead of a new TCP and
  TLS handshake for each of the dozens of calls a commit makes (this was most
  of a 30 s submit),
- on an edit, `commit_on_branch` gets the blob shas already at the head of
  the branch and skips any file whose content hashes to the same sha, so an
  edit that changes one row uploads one file. A first submit uploads every
  file.

## After the pull request

- The pull request body lists the database, the counts, the contributor, the
  dismissed warnings and, for a new submission, how to update it.
- The data repository's CI (`data-validation.yml`) sends the files the pull
  request adds or changes to `/validate` of the **prod** deployment, with the
  machine credential. It does not turn on the duplicate check: a main CSV
  always holds rows that are already uploaded. Since the CI calls prod, a
  check added to the validator runs in CI only once it is released. The Hub
  runs the checks of its own version on a submission before it opens the pull
  request.
- The Hub asks every admin of the data repo to review it (#266), so GitHub
  sends each one a "review requested" email and a notification. The person
  who submitted is left out, since nobody reviews their own pull request.
  To make someone a reviewer, make them admin on the data repo: it is the
  same list as the Hub admins ([auth.md](auth.md)). If the request fails,
  the backend logs `Reviewers not requested on #...` and the submit still
  succeeds. Verification pull requests get the same request.
- A member of the lab reviews it from the [curation queue](curation.md) and
  merges on GitHub, squash only.
- The rows go live as **unverified**: the dashboards flag them and the
  drawer says the data was not checked by the lab yet. A curator verifies
  them later from the "To verify" tab, which opens a second, small pull
  request ([curation.md](curation.md#verification)).
- The data reaches the deployments when the pull request is merged: the data
  repo sends the changed files to `/upload` of each hub, and dev also rebuilds
  its data each night ([Run the pipeline](run-the-pipeline.md)).
  `/upload` expires the response cache of the backend at once, but a browser
  keeps its copy for up to an hour (`CACHE_MAX_AGE`). The nightly rebuild
  cannot expire the cache: restart the backend if its data must show at once.

## Trying it locally

A local setup opens its pull requests on the test fork
`EPFL-ENAC/resslab-hub-data-test`, not on the real data repo. Two lines in
`secrets/.env` do it:

```bash
DATA_REPO=EPFL-ENAC/resslab-hub-data-test
GITHUB_APP_INSTALLATION_ID=<the id of the App on EPFL-ENAC>
```

Without them, a laptop opens real pull requests on
`RESSLab-Team/resslab-hub-data`, and someone has to close them by hand.

Also set `DATA_REPO_REVIEWERS=none`, so a test submit does not ask the
fork's admins for a review. To test the review request, put your own GitHub
login there (`DATA_REPO_REVIEWERS=your-login`) and restart the backend.

On the fork you can merge, close or leave pull requests as you like. A merge
on its `main` goes to the dev hub, through the `upload.yml` of the fork. Its `main` is a copy of the real
`main` that drifts: it misses the real merges and keeps your test merges. So a
submission that passes locally can still collide with ids on the real repo.
`make data-fork-reset` puts the fork's `main` back on the real one and lists
the pull requests and `contrib/*` branches left on the fork.

See "Testing the pipeline" in [auth.md](auth.md) for the whole recipe, and
`make sample-data` for a batch that passes with three range warnings and one
that fails.
