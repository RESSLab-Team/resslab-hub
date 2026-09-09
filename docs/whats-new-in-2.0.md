# What's new in 2.0

`main` has not moved since April 2026 (v1.1.0, what https://resslab-hub.epfl.ch
serves today). `dev` and `stage` carry the rewrite of the whole app: about 430
commits and 650 files since then. This page is the human summary; the commit
list lands in `CHANGELOG.md` when Release Please cuts the 2.0.0 tag
([releasing.md](releasing.md)).

## What the old app was

Nine databases behind a Vuetify 3 UI: a paginated table per database,
charts fed by aggregate endpoints (`/counts`, `/range`, `/matrix`) on every
filter change, a detail view with the curves, the overview map,
the component model and fragility tools. No accounts. Data reached the
database by hand: someone tarred a folder and posted it to `/upload` with the
API password, or ran the uploader over a tunnel.

## Sign-in and accounts (#247, #248)

Browsing stays open. An account is needed to submit data or to open the review
queue. Sign in with an email code or with GitHub. Roles are `viewer`,
`contributor`, `curator`, `admin`; an academic address grants `contributor`
at sign-in, `ADMIN_EMAILS` grants `admin`, an override in the database wins.
`API_PASSWORD` is now the machine credential only. Details: [auth.md](auth.md).

## Contribution pipeline

Submit from the app (`/contribute/new`): drop a folder, a zip or loose files,
the editor sorts them, validates every two seconds against the backend, shows
range warnings against the existing data, and turns the batch into a branch
and a pull request on the data repo. Provenance lives in commit trailers. An
open submission can be edited from the app by its owner. Submits reuse one
GitHub connection and upload only what changed. Details:
[contributing-data.md](contributing-data.md).

## Curation

`/curation` lists the open pull requests of the data repo. The review page
shows the batch by field group, a cohort of similar specimens from the
database, the curves with ghosts of that cohort, the UVC model drawn over
submitted cyclic coupons, the quality flags and the pull request discussion.
Merging still happens on GitHub. Details: [curation.md](curation.md).

## Dashboard engine and design system

Each database loads once and every filter runs in the browser: one filter
state shared by the table, the charts, the histograms and the brushes, live
while dragging. Filters are derived from the data dictionary and grouped by
scientific category. Category colours are stable across filters. The table
uses virtual rows. The detail view is a drawer with every property of the
specimen, grouped by category. The look is the EPFL system: Suisse Int'l, square corners, no
shadows, the red braced-bay mark. Details:
[dashboard-architecture.md](dashboard-architecture.md).

## New tabs and data

- Tensile coupons and ductile fracture, as sub-tabs of Materials. Ductile
  fracture specimens have SEM images (WebP on the EPFL CDN, TIFs in Git LFS,
  [sem-images.md](sem-images.md)) and a drawn figure of their own geometry.
- EBF links, with the confirmed link geometry on the icon.
- The data dictionaries carry a `group` column; the categories come from the
  data ([variable-categories.md](variable-categories.md)).
- Every database folder of the data repo has a README for contributors,
  uploaded with the data and shown in the submission form.
- Material: `uvc_e` is in GPa, the `file` column is gone, tensile curves are
  engineering values (#308).

## Platform

- Kubernetes deploys (dev, test, prod) through the EPFL enac action;
  in-cluster upload CronJobs instead of tunnels.
- Licence AGPL-3.0. pnpm instead of npm. ruff instead of black, flake8 and
  isort. Pydantic v2, FastAPI 0.115, Vite 6, TypeScript 5.9, Vitest 4.
- Upload is 3.7x faster (`COPY FROM STDIN`, biggest files first). Responses
  are cached per process with an ETag and warmed at startup.
- A backend test suite (18 files, about 380 tests) run in CI against
  Postgres.
- Per-branch dev environments: a git worktree, its own ports, its own
  database clone and a tmux session
  ([worktree-dev-environment.md](worktree-dev-environment.md)).
- The release pipeline works again (Release Please with its own token,
  `include-component-in-tag: false`).

## Schema changes

Nine migrations run at backend startup on a v1.1.0 database, in this order:

```
7428c25e3b9f  add tensile coupon model
d6db08cd309d  add ductile fracture model
816d65afefa6  add has_sem
630367b7b682  add dictionary column table
2a42de2d3438  materialize count flags
b7c1e2d4f5a6  add database readme table
c3f7a91b2e08  rename uvc_e to GPa, drop material file, fix fy_e type
fd4c75d51fa4  add group to dictionary columns
a4e91c73b0d2  add auth tables
```

The `uvc_e` rename keeps the values (they were always GPa, only the name said
MPa). Dump the database before the first prod deploy
(`make backup-dump DEST_FOLDER=...`).

## What a deployment must set before 2.0 goes live

Without these the site runs and browses, but nobody can sign in or submit:

- `PUBLIC_BASE_URL` (the public host, without `/api`)
- the `SMTP_*` block, else sign-in codes only go to the log
- `GITHUB_OAUTH_CLIENT_ID` / `GITHUB_OAUTH_CLIENT_SECRET`, with the
  environment's callback registered on the GitHub App
- `GITHUB_APP_ID` / `GITHUB_APP_PRIVATE_KEY` / `GITHUB_APP_INSTALLATION_ID`
  for the contribution pipeline
- the backend and frontend image tags of the overlay, and the data image
  `resslab-hub-data:main`

The full list and where each one lives: [auth.md](auth.md) and
[releasing.md](releasing.md).
