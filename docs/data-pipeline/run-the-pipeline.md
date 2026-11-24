# Run the data pipeline

This page is for the maintainers of the Hub and of the
[data repository][data-repo]. It explains the rules of the data repository,
the three workflows that move the data, the nightly rebuild and the cache. It
ends with the steps to follow when merged data does not show.
[How data gets into the Hub](index.md) shows the full path.

## Branches and commit order

The data repository has one long-lived branch: `main`. It is the only source
of the data for each environment of the Hub. The old `test` branch does not
exist anymore. Other branches are short-lived:

| Branch | Made by | Content |
| --- | --- | --- |
| `contrib/<type>/<first id>-<hex>` | The GitHub App of the Hub, at each submission | New rows and their curve files |
| `verify/<type>/<first id>-<hex>` | The GitHub App, when a curator marks rows as verified | Only the column `data_curation_status` |
| A branch on a fork | A contributor who works without the Hub | Any change |

A submission from the Hub is one commit on its branch. Each edit of the
submission adds one commit on top, with no force push. The merge on `main` is
always a squash, so each pull request becomes one commit on `main`, and the
history stays linear.

Who submitted is written in the commit messages as git trailers
(`Submitted-by`, `Institution`, `ORCID`, `GitHub`, `Dismissed-Warning`). The
first commit of the Hub on a branch decides who owns the submission. The last
commit gives the list of dismissed warnings. The squash commit keeps the
messages of all the commits, so a pull request with one commit keeps the
trailers easy to read on `main`.

## Rules of the data repository

The repository is public. These settings were checked on 2026-11-24:

- The ruleset `data-contribution` protects `main`. It requires a pull request
  with one approval. A new push dismisses an old approval.
- It allows only the squash merge, and it requires a linear history.
- It blocks the deletion of `main` and force pushes.
- It requires the checks `line-endings`, `changes` and `authentification`.
- The pull request template is merged (resslab-hub-data#33).

> Note: The checks `validate` and `validation-passed` are not required. A pull
> request with a failed validation can be merged. Curators must look at
> `validation-passed` before they merge.

## The three workflows

All three are in `.github/workflows/` of the data repository.

| Workflow | When | What it does |
| --- | --- | --- |
| `data-validation.yml` | Each pull request into `main` | Sends the files that the pull request adds or changes, from the base commit to the head, to `POST /api/validate` of the production hub. Fails when the data is not valid. |
| `upload.yml` | Each push on `main` | Sends the `*.csv` and `*/README.md` files that the push added or changed to `POST /api/upload?type=all` of each hub in `UPLOAD_TARGETS`. |
| `build-data-image.yml` | Each push on `main`, or by hand | Builds the image `ghcr.io/resslab-team/resslab-hub-data:main` with all the data. The nightly rebuild reads it. |

`upload.yml` reads the repository variable `UPLOAD_TARGETS`, a JSON list with
one entry for each hub. Each entry has a name, a URL and the name of the
secret that holds the machine password (`API_PASSWORD`) of that hub:

```json
[{"name": "prod", "url": "https://resslab-hub.epfl.ch", "secret": "API_PASSWORD_PROD"},
 {"name": "stage", "url": "https://resslab-hub-test.epfl.ch", "secret": "API_PASSWORD_STAGE"}]
```

The real repository sends to prod and stage. The test fork
`EPFL-ENAC/resslab-hub-data-test` sends to dev. Without the variable, the
workflow does nothing.

## What `/upload` does

`POST /upload` accepts only the machine password, not a session of a signed-in
person. It writes each file in its own transaction.

- `200`: each file went in.
- `422`: some files failed. The answer lists their paths, and the job of
  `upload.yml` shows each path as an error. The other files went in. The error
  text is only in the log of the backend.

When a main CSV is in the upload, the rows that left the file are deleted,
with their curves. A deleted curve file is not sent, so its curve stays in the
database until the next rebuild.

## The nightly rebuild

The CronJob `resslab-hub-upload-data` runs the uploader of the backend image
of the environment on a copy of the data image:

```bash
python -m resslab_hub.data.uploader all /work --rebuild
```

With `--rebuild`, the uploader first empties the main data tables (and their
curve tables) with one `TRUNCATE`. Then it uploads each file again. It never
touches the accounts and the sessions (the `auth_*` tables). It refuses to
start if a main CSV is missing. It exits with code 1 if a file failed.

The CronJob runs at 03:02 UTC. Today it runs each night on dev only. On stage
and prod it is suspended: run it by hand when you need it, from the
deployment tool of the cluster. During a rebuild the tables are partly empty
for some minutes, so the site can show partial data in that window.

## The cache

The backend keeps each data response for `CACHE_MAX_AGE` seconds (3600 by
default). It sends the same value to the browser.

- `POST /upload` changes the data version of the backend at once. The copy of
  the server is then expired, but a browser can keep its own copy until the
  hour ends.
- The nightly rebuild is a different process. It cannot tell the backend that
  the data changed. The new data shows when the cache expires, or when the
  backend restarts.

## The data does not show

If a pull request is merged but the data is not on the dashboards:

1. Open the run of `upload.yml` for the merge commit in the Actions tab of the
   data repository. If the job for the hub failed, read the paths it lists.
2. If the answer was `422`, read the log of the backend at the time of the
   upload. It has the error of each failed file. Fix the file with a new pull
   request.
3. If the answer was a `504`, the proxy stopped waiting. The backend can still
   be uploading. Wait some minutes, then look again.
4. If the job passed, wait up to one hour for the cache, or restart the
   backend of that environment.
5. If a deleted file still shows, run the rebuild CronJob by hand.

To upload from a laptop when the cluster job is not an option, read "Upload
data to a deployed environment" in the [backend README][backend-readme].

## Next step

Before you change the data repository, read its README. The developer
details of the submission code are in
[Contribution internals](../contributing-data.md).

[data-repo]: https://github.com/RESSLab-Team/resslab-hub-data
[backend-readme]: https://github.com/RESSLab-Team/resslab-hub/blob/dev/backend/README.md#upload-data-to-a-deployed-environment-dev-stage-prod
