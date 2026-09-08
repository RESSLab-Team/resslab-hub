# Curation

The review queue of the lab: the open pull requests of the data repository,
read back into a screen that shows a submission the way the database will,
next to the data already there. Reviewing is reading; approving, asking for
changes and merging stay on GitHub.

How a submission gets there: [contributing-data.md](contributing-data.md).

## Who can open it

`/curation` (the queue) and `/curation/<pr number>` (the review) need a
signed-in account, any role (`require_user` on every endpoint of
`backend/resslab_hub/routers/curation.py`). Not the `curator` role yet: the
endpoints reveal nothing the public pull request does not, but the queue is
the lab's work list, not a public page. #248 will tie `curator` to the GitHub
permission on the data repo, so the app and the merge gate read the same
source ([auth.md](auth.md), "Later").

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
| `GET /contributions` | the open pull requests into `DATA_REPO_BASE_BRANCH`, newest first, up to 100. With no GitHub App configured: `configured: false`, not an error. |
| `GET /contributions/{pr}` | everything the review page needs: summary, provenance (from the trailers, else the pull request body, else the legacy JSON record), the reconstructed rows, the classified files, and `mine`, whether the signed-in account owns it. |
| `GET /contributions/{pr}/validation` | `validate_all` re-run on the reconstructed batch in a temporary repo-shaped folder. Up to `MAX_CURVE_FILES` (100) curve files are downloaded, with size caps; the skipped ones get an explicit warning ("too large, review on GitHub"). |
| `GET /contributions/{pr}/comments` | the pull request thread, oldest first, the pull request body as the first entry. Read only. |
| `GET /contributions/{pr}/files?path=` | the text of one file the pull request added, primary CSV or curve only. Used for the curve preview and by the editor when it loads a submission to edit. |

Response shapes: `backend/resslab_hub/models/curation.py`.

## The queue page

`frontend/src/views/CurationQueueView.vue` lists the summaries: number,
title, branch, type, draft flag, dates, and what can be parsed from the pull
request body (experiment count, contributor).

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
  curve, with ghosts of the cohort's curves behind it. For cyclic coupons'
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

**Edit on the Hub** appears only when `mine` is true: the signed-in account's
verified address matches the `Submitted-by` trailer of the first Hub commit
(see provenance in [contributing-data.md](contributing-data.md)). It opens
`/contribute/edit/<pr number>`.

## What curation does not do yet

- No approve, request changes or merge here. Do those on GitHub, and merge
  with squash only (the data repo CI validates `HEAD~1..HEAD`).
- The `curator` role exists in the hierarchy but is not enforced, and there
  is no admin screen to grant it (#248).
- A curator cannot edit someone else's submission from the app; only the
  owner can (#248 as well).

## Trying it locally

Submit a sample batch from the app ([contributing-data.md](contributing-data.md),
"Trying it locally"), open `/curation`, and close the pull request on GitHub
when done.
