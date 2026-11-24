# Curation

The review queue of the lab: the open pull requests of the data repository,
read back into a screen that shows a submission the way the database will,
next to the data already there. Reviewing is reading; approving, asking for
changes and merging stay on GitHub.

This page is the developer reference. The steps for a curator are in
[Review data](contribute/review-and-verify.md). How a submission gets there:
[contributing-data.md](contributing-data.md).

## Who can open it

`/curation` (the queue) needs the `curator` role. A curator is someone with
write or maintain on the data repository, through their linked GitHub
account, or someone an admin made curator ([auth.md](auth.md#roles)). So the
people who can merge on GitHub are the ones who review here.

`/curation/<pr number>` (one submission) is open to curators and to the
person who made it: the `Submitted-by` trailer of its first Hub commit
matches their verified address. That second way in is what lets a
contributor follow their own submission and load it into the editor. Anyone
else gets a 403, and the page sends them to the "not open to your account"
page. The check is `_check_access` in `backend/resslab_hub/routers/curation.py`;
it needs the pull request, so it runs in each handler, not as a dependency.

With `CONTRIBUTIONS_ENABLED=false` nobody can: the endpoints answer `404` and
the sidebar has no Curation section ([contributing-data.md](contributing-data.md#settings)).

## Nothing is stored

The app keeps no copy of a submission. Every endpoint rebuilds the batch from
the pull request: the rows of the head CSV whose id is not in the base CSV,
matched by column name (`contributions/projection.py`), so column order, line
endings and legacy columns do not matter.

To keep that cheap there is a small in-process cache per replica
(`_TTLCache`): the pull request list for a minute, the detail and the
validation for ten minutes keyed by head sha (a new commit expires them),
the comments for thirty seconds. An edit made from the app invalidates the
pull request at once.

## The endpoints

| Endpoint | What it answers |
|---|---|
| `GET /contributions` | every open pull request into `DATA_REPO_BASE_BRANCH`, newest first, up to 100, drafts and forks included. Each one has a `kind`, see [What is in the queue](#what-is-in-the-queue). Cached one minute; `?fresh=true` skips the cache (the Refresh button). With no GitHub App configured: `configured: false`, not an error, and a warning in the backend log. |
| `GET /contributions/{pr}` | everything the review page needs: summary, provenance (from the trailers, else the legacy JSON record, else none and a warning; the contributor parsed from the pull request body only fills the summary), the reconstructed rows, the classified files, and `mine`, whether the signed-in account owns it. |
| `GET /contributions/{pr}/validation` | `validate_all` re-run on the reconstructed batch in a temporary repo-shaped folder. Up to `MAX_CURVE_FILES` (100) curve files are downloaded, with size caps; the skipped ones get an explicit warning ("too large, review on GitHub"). |
| `GET /contributions/{pr}/comments` | the pull request thread, oldest first, the pull request body as the first entry. Read only. |
| `GET /contributions/{pr}/files?path=` | the text of one file the pull request added, primary CSV or curve only. Used for the curve preview. |
| `GET /contributions/{pr}/curves` | every curve the pull request added, with its text, in one answer (#336). The editor loads a submission with it. The files are read from GitHub in parallel, cached per head sha when the batch is 1 MB or less. The answer is complete or it is a 502, never partial: a save deletes the curves the editor does not send back. |

`GET /contributions` needs the `curator` role. The other routes need a
signed-in account that is a curator or owns the submission (`_check_access`).
Rate limits per client: 30 per minute for the queue, the detail, the comments
and the curves, 10 per minute for the validation, 60 per minute for the files.

Response shapes: `backend/resslab_hub/models/curation.py`.

## What is in the queue

Every open pull request into the base branch shows up, not only the ones the
Hub opened (#267). A contributor who reads a database README can fork the data
repository and open a pull request by hand, and the lab must see it.

| `kind` | How it is found | In the queue |
|---|---|---|
| `submission` | head branch `contrib/<type slug>/...`, opened by the Hub | review page, as before |
| `manual` | any other branch, and its changed files are all in one database folder (`type_for_files` in `projection.py`) | review page, with a warning: there are no trailers, so only the rows it adds to the main CSV are shown |
| `unrecognised` | its files touch no database folder, or several (`braces/` and `columns/`, or two of the `material/` folders) | `reason` says why. GitHub link only, the review page answers `404` with the reason |
| verification | head branch `verify/<type slug>/...` (#253) | not here, it is on the **To verify** tab. The backend log has one `Review queue: skipped #N` line for each one |

Files outside every database folder (`.github/`, `contributions/`, the root
README) do not count. A data dictionary or a README alone counts for its
folder. The changed files are read only for branches that are not `contrib/`
or `verify/`, and cached by head sha. If GitHub fails to give them, the pull
request is still listed as `unrecognised`, with a warning in the log.

Drafts are listed, with a **Draft** tag. A pull request from a fork has
`from_fork: true` and a **Fork** tag. The review page reads it like any other
(GitHub serves a fork's head commit from the base repository), but the Hub
cannot push to the fork's branch, so **Edit on the Hub** answers `409`: edit
it on GitHub.

## The queue page

`frontend/src/views/CurationQueueView.vue` has two tabs. **To accept** lists
the summaries: number, database (or the **Unrecognised** tag and its reason),
**Draft** and **Fork** tags, title, branch, dates, and what can be parsed from
the pull request body (experiment count, contributor). **To verify**
(`?tab=verify`) is the second step, see [Verification](#verification).

## The review page

`frontend/src/views/CurationReviewView.vue`, with the panels of
`components/curation/`:

- **Metadata** (`MetadataPanel.vue`): the selected experiment's cells,
  grouped by scientific category like the drawer and the editor
  ([variable-categories.md](variable-categories.md)).
- **Cohort** (`CohortPanel.vue`, `ghost.ts`): specimens of the existing
  database that resemble the selected one, from a filter derived from its
  own cells on the chosen similarity fields. A brush on the parallel chart
  narrows the same cohort. The point is to judge a value against its peers,
  not against the whole database.
- **Derived columns** (#322): a submitted CSV never carries the columns the
  ORM computes (`column_property`), so `withDerivedCells` in
  `utils/curation.ts` computes them the same way, for example the cyclic
  coupon `type` from `grade` and `spec`, or `h_over_b` for residual
  stresses. Cohort chips and curves can then match on them.
- **Data preview** (`DataPreviewPanel.vue`, `curves.ts`): every attached
  curve, with ghosts of the cohort's curves behind it.
  The submission is red and the ghosts are faded and thinner: the same
  convention as the parallel plot, the metadata ranges and the
  contribution preview (#268, `--data-submitted` and `--data-existing`,
  named by `DataLegend.vue`). For cyclic coupons'
  `stress_strain` files, the UVC material model is drawn dashed over the
  test, computed in the browser from the row's calibrated parameters run
  over the submitted strain history (#316), the same code as the Materials
  model tab. When it cannot: `uvcMissing` names the parameter columns the
  row lacks (no model calibrated, or a renamed column), `uvcFailed` says the
  parameters exist but the integration produced nothing. Both are shown,
  not hidden.
- **Quality flags** (`QualityFlagsRail.vue`): the validation response per
  experiment, same shape as the editor's.
- **Discussion** (`ReviewThread.vue`): the pull request comments, read only.

**Edit on the Hub** appears when `mine` is true (the signed-in account's
verified address matches the `Submitted-by` trailer of the first Hub commit,
see provenance in [contributing-data.md](contributing-data.md)), and for every
curator. It opens `/contribute/edit/<pr number>`. A curator's edit is a commit
authored by the curator; the trailers keep naming the person who submitted.
It works on `contrib/` branches only (`404` otherwise), never on a fork
(`409`), and a curator gets `403` when no commit of the branch says who
submitted.


## Verification

Accepting and verifying are two steps (#253). Accepting is quick: the
curator checks that the submission is sane and merges it. The rows then go
live with `data_curation_status` set to `unverified`, and the site says so.
Verifying comes later, with no rush: a curator checks the values against the
publication, then marks the rows as verified.

The column is managed by the Hub, like the `*_count` flags
(`backend/resslab_hub/data/curation_status.py`):

- a contributor never fills it, the editor and the starter kit leave it out;
- the submission code writes `unverified` on every new row, whatever the
  batch says, on a first submit and on an edit;
- the validator does not require it, and refuses a value other than
  `verified` or `unverified`;
- the uploader reads a missing header, an empty cell or an unknown value as
  `unverified`;
- the migration added it with `verified` as the default, so every row that
  was there before #253 is verified.

The data repository CSV is the source of truth: the status survives a
re-upload, and every change to it is a pull request.

**Mark as verified** is the button that opens that pull request. It is in
three places, for curators only: the **To verify** tab, one button per
database and reference; the review page of a reference (below); and the
warning at the top of the specimen drawer, for one row. The backend reads the main CSV at the head commit of the base branch, changes only
the status cells of those ids (line endings and everything else kept),
commits on `verify/<type slug>/<first id>-<hex>` as the curator, with a
`Verified-by` trailer, and opens a pull request titled like
`data(braces): verify 3 experiments (…)`. The ids are listed in an `ids`
fenced block of its body. It is merged on GitHub like any other, squash only.

| Endpoint | What it answers |
|---|---|
| `GET /verification` | the unverified rows of every database, from the database, grouped by database and `reference`. Each group has its ids and the open verification pull request that covers them, if any. Curators only. |
| `POST /verification` | `{database, ids}` opens the pull request, up to `MAX_IDS` (500) ids. `409` for an id the CSV does not have, one already verified, or one already in an open verification pull request. `10/hour` per client address. Curators only. |
| `GET /verification/{database}/batch?reference=` | the unverified rows of one reference, read from the data repository's base branch: the same `columns`, `experiments` and `files` as a submission's detail, plus `base_sha`, `missing_ids` and the pending pull request of each id. `404` when the reference has no unverified row. Curators only. |
| `GET /verification/{database}/validation?reference=` | the same checks as a submission's validation, re-run on those rows and their curves. Curators only. |
| `GET /verification/{database}/files?path=&ref=` | the raw text of one curve at `ref` (the batch's `base_sha`). Only `<curve folder>/<id>.csv` of that database is served. Curators only. |

**The review page of a reference** (`/curation/verify/<database>?reference=`)
is where most of the scientific check happens, so it has the same panels as
a submission's review: the metadata with the existing ranges, the cohort of
similar experiments, the curves with their cohort overlays, and the quality
flags. The rows come from the database (the unverified ids of that
reference), their cells and curves from the data repository at one base
commit, since that is what a verification changes. A curve is
`<curve folder>/<id>.csv`, the way the uploader links a file to its row. The
cohort only takes verified rows (`data_curation_status:verified,` is added to
its query), or the rows under review would be compared with themselves. The
quality flags follow the same rule: they are the submission checks with
`live_rows` on (`build_validation`), so there is no "id already exists"
error, and the range warnings compare with the verified rows only. Without
that, an outlier would set the range itself and never be flagged. The rail
has **Mark all as verified** and, for a batch of several, a button that
marks only the selected row. A row already in a pull request is greyed in
the picker and left out of the button. An id unverified on the site but missing from the CSV, or
already verified in the CSV, gets a note at the top: both mean the site waits
for the next upload. `?id=` opens the page on one row.

Nothing is stored here either: an open pull request on a `verify/` branch is
what "pending" means. The list comes from the database, so a merged
verification stays in the **To verify** tab until the next upload. The
button then answers `409`, since it reads the data repository. Verification
pull requests are not in the **To accept** tab: the list skips `verify/`
branches, and logs each one it skips.

On the dashboards, an unverified row has an orange rule on its checkbox cell
and the drawer warning. **Verified only** in the toolbar hides those rows.
It is off by default and writes `data_curation_status==verified` in the URL,
so a shared link keeps it. The code: `utils/curationStatus.ts`,
`stores/verification.ts`, `components/commons/UnverifiedNotice.vue`,
`components/curation/VerificationQueue.vue` and the verify mode of
`views/CurationReviewView.vue`; on the backend `routers/verification.py` and
`contributions/verification.py`.

## What curation does not do yet

- No approve, request changes or merge here (#254). Do those on GitHub, and
  merge with squash only: the ruleset allows nothing else, and one commit per
  pull request keeps the trailers readable on `main`.
- The merge gate is on GitHub: the ruleset `data-contribution` on the data
  repository `main` needs one approving review, three checks, and a squash
  merge ([Run the pipeline](run-the-pipeline.md#rules-of-the-data-repository)).
  There is no CODEOWNERS file. Instead, the Hub asks every
  admin of the data repository to review each submission and verification
  it opens (#266, `DATA_REPO_REVIEWERS` in
  [contributing-data.md](contributing-data.md#settings)).
- No embargo: an unverified row is public like any other (the data
  repository is public too). It is a separate issue.

## Trying it locally

Submit a sample batch from the app ([contributing-data.md](contributing-data.md),
"Trying it locally"), open `/curation`, and close the pull request on GitHub
when done.

For the **To verify** tab, mark a few rows as unverified in your local
database (never a shared one), for
example `UPDATE brace SET data_curation_status = 'unverified' WHERE id IN
(...)`. The tab shows them at once (`/verification` is not cached), the
dashboards only after a backend restart (the response cache lasts an hour).
Pressing the button opens a real pull request into `main`: close it on
GitHub, never merge a test one.
