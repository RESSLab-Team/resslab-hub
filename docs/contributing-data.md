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
  card head pinned while scrolling,
- a status bar with the client and server verdict,
- a guide rail on the right (`ContributionGuide.vue`) with the database
  README and a searchable data dictionary,
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
   legacy column the dictionary no longer has gets `NR`),
4. writes one commit on a new branch `contrib/<type>/<first-id-slug>-<hex>`,
   the contributor as git author, the App bot as committer, through the Git
   Data API (blob, tree, commit, ref), then opens the pull request into
   `DATA_REPO_BASE_BRANCH`.

All of it goes through `DataRepoClient` (`contributions/github.py`), a thin
async wrapper over githubkit authenticated as a GitHub App installation. The
App needs `contents: write` and `pull requests: write` on the data repo,
nothing else. The curation queue reads through the same client.

### Settings

| Key | What it is |
|---|---|
| `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_APP_INSTALLATION_ID` | The App that opens the pull requests. All three or the feature is off: `POST /contributions` and the curation endpoints answer `503`, the queue says `configured: false`. Not the OAuth pair of [auth.md](auth.md), which is for sign-in. |
| `DATA_REPO` | `RESSLab-Team/resslab-hub-data` by default. |
| `DATA_REPO_BASE_BRANCH` | `main` by default, the only branch the data repo has. Submissions from dev, test and laptops all land there; close those, never merge them. |

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

Submitting calls `PUT /contributions/<pr number>` with the rebuilt archive
and the `head_sha` the editor loaded. 10 per hour. The backend:

- refuses a closed pull request,
- answers `409` if the branch moved since (`head_sha` differs): reload and
  redo,
- answers `403` if the account does not own the submission (trailer rule
  above; curators get their own way in with #248),
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
- The data repository's CI validates the whole repo against `/validate` of
  the dev deployment with the machine credential, no duplicate check (every
  id there is already uploaded).
- A member of the lab reviews it from the [curation queue](curation.md) and
  merges on GitHub, squash only.
- The data reaches a deployment when someone runs its upload CronJob from
  ArgoCD ([backend/README.md](../backend/README.md)). The backend caches
  responses for an hour per process, so restart the pods if it must show at
  once.

## Trying it locally

The GitHub App installed on the data repo works from anywhere, so a laptop
opens real pull requests into `main`. See "Testing the pipeline" in
[auth.md](auth.md) for the whole recipe, and `make sample-data` for a batch
that passes with three range warnings and one that fails.
