# Contributing data

How an experiment goes from a folder on a researcher's laptop to a row in the
database. The app side of it, from the editor to the pull request. The data
repository's own rules (folder layout, headers, units) are in the README of
each database folder there, shown in the editor as well.

Sign-in, roles and the account page are in [auth.md](auth.md). Test batches
to try all this with: [sample-data/README.md](../sample-data/README.md).

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
| `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_APP_INSTALLATION_ID` | The App that opens the pull requests. All three or the feature is off: `POST /contributions` and the curation endpoints answer `503`, the queue says `configured: false`. Not the OAuth pair of [auth.md](auth.md), which is for sign-in. |
| `CONTRIBUTIONS_ENABLED` | `true` by default. `false` switches the whole pipeline off: submit and edit, curation, sign-in and account. The backend answers `404` on those endpoints and the frontend hides every link to them (the routes go to `/`). `GET /auth/me` keeps answering `{"user": null}`, and `/validate` and `/upload` do not change. Read at startup, so restart the pods after a change. `GET /features` tells the frontend the value it acts on: this setting and the GitHub App above. How prod uses it: [releasing.md](releasing.md). |
| `DATA_REPO` | `RESSLab-Team/resslab-hub-data` by default, what dev, stage and prod use. Local setups use the test fork `EPFL-ENAC/resslab-hub-data-test` instead, with the App's EPFL-ENAC `GITHUB_APP_INSTALLATION_ID` (the installation id is per org). `scripts/wt-setup.sh` seeds both into a new worktree's `secrets/.env`. See [Trying it locally](#trying-it-locally). |
| `DATA_REPO_REVIEWERS` | Who is asked to review each pull request the Hub opens (#266). `admins` by default, what dev, stage and prod use: every account with admin on the data repo, read from GitHub at each pull request. `none` asks nobody: new worktrees get it, so a test submit on the fork does not email its admins. A comma list of GitHub logins asks exactly those. |
| `DATA_REPO_BASE_BRANCH` | `main` by default, the only branch the data repo has. Submissions from dev and test land there; close those, never merge them. |

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
- `commit_files` gets the blob shas already at the parent commit and skips
  any file whose content hashes to the same sha, so an edit that changes one
  row uploads one file.

## After the pull request

- The pull request body lists the database, the counts, the contributor, the
  dismissed warnings and, for a new submission, how to update it.
- The data repository's CI (`data-validation.yml`) sends the files the pull
  request adds or changes to `/validate` of the **prod** deployment, with the
  machine credential. It does not turn on the duplicate check: a main CSV
  always holds rows that are already uploaded. Until 2.0 is released, prod
  runs the old validator, so the checks added in 2.0 (the review status
  values, for example) do not run in CI yet. The Hub runs them on a
  submission before it opens the pull request.
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
  its data each night ([backend/README.md](../backend/README.md#upload-data-to-a-deployed-environment-dev-stage-prod)).
  The backend caches responses for an hour per process, so restart the pods if
  it must show at once.

## Trying it locally

A local setup opens its pull requests on the test fork
`EPFL-ENAC/resslab-hub-data-test`, not on the real data repo. Two lines in
`secrets/.env` do it (a new worktree gets them from `scripts/wt-setup.sh`):

```bash
DATA_REPO=EPFL-ENAC/resslab-hub-data-test
GITHUB_APP_INSTALLATION_ID=170990591   # the App's install on EPFL-ENAC
```

Without them, a laptop opens real pull requests on
`RESSLab-Team/resslab-hub-data`, and someone has to close them by hand.

`scripts/wt-setup.sh` also seeds `DATA_REPO_REVIEWERS=none`, so a test submit
does not ask the fork's admins for a review. To test the review request, put
your own GitHub login there (`DATA_REPO_REVIEWERS=your-login`) and restart the
backend. An older worktree has no such line, so it asks every fork admin: add
it by hand.

On the fork you can merge, close or leave pull requests as you like. Its
Actions are off, so no validation runs there. Its `main` is a copy of the real
`main` that drifts: it misses the real merges and keeps your test merges. So a
submission that passes locally can still collide with ids on the real repo.
`make data-fork-reset` puts the fork's `main` back on the real one and lists
the pull requests and `contrib/*` branches left on the fork.

See "Testing the pipeline" in [auth.md](auth.md) for the whole recipe, and
`make sample-data` for a batch that passes with three range warnings and one
that fails.
