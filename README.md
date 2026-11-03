# resslab-hub

RESSLab Hub is the research database of the Resilient Steel Structures
Laboratory at EPFL. It holds test data for nine kinds of structural steel
components: braces, columns, connections, HSS columns, EBF links, cyclic and
tensile coupons, ductile fracture specimens and residual stresses. Each one has
a dashboard, a data table and detail curves. Anyone can browse. With an
account, a researcher submits new experiments from the app; the submission
becomes a pull request on the data repository, and the lab reviews it from a
curation queue.

Backend: FastAPI REST API on PostgreSQL. Frontend: Vue 3 single page app.
Production: https://resslab-hub.epfl.ch.

## Where to read next

- [backend/README.md](backend/README.md): migrations, model generation, uploading data locally and to a deployment
- [frontend/README.md](frontend/README.md): scripts, source layout, environment files
- [docs/README.md](docs/README.md): the index of every guide. The most used ones:
  - [docs/whats-new-in-2.0.md](docs/whats-new-in-2.0.md): what changed between the old app and this one
  - [docs/worktree-dev-environment.md](docs/worktree-dev-environment.md): one branch, its own servers and Claude session
  - [docs/auth.md](docs/auth.md): sign-in, roles, the settings a deployment needs
  - [docs/contributing-data.md](docs/contributing-data.md): the submission pipeline
  - [docs/sem-images.md](docs/sem-images.md): the SEM images, the script that converts and uploads them
- `CLAUDE.md`: the map of the repo written for coding agents, also a good quick reference

## Related repositories

- [resslab-hub-data](https://github.com/RESSLab-Team/resslab-hub-data): the CSV files and data dictionaries that populate the database and drive the schema
- [resslab-hub-scripts](https://github.com/RESSLab-Team/resslab-hub-scripts): the MATLAB scripts translated for component models and fragility curves

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python automatically)
- [Make](https://www.gnu.org/software/make/)
- [Node.js](https://nodejs.org/) ≥ 18 (CI uses the current LTS)
- [pnpm](https://pnpm.io) 11 (`npm install -g pnpm`), one shared store for every checkout and worktree
- [Docker](https://www.docker.com/) with the [Compose v2 plugin](https://docs.docker.com/compose/)
- [Git LFS](https://git-lfs.com/) only if you want the SEM images of the data repo (see below)

### Secrets

An environment file should be created (see all available keys in `backend/resslab_hub/config.py`).

```bash
mkdir -p secrets && echo POSTGRES_PASSWORD=changeit > secrets/.env
```

### Installation

```bash
make install
```

Git hooks (commitlint + lint/format) are managed by [Lefthook](https://lefthook.dev) and installed automatically by `make install`. Skip with `LEFTHOOK=0`.

### Run for development

```bash
make dev-database
# postgresql://127.0.0.1:5433

make dev-backend
# http://127.0.0.1:8000

make dev-frontend
# http://127.0.0.1:5173
```

`make dev-all` runs the three in one terminal, `make tmux-dev-all` as a tmux
session. `make help` lists every target, here and in `backend/`.

About the database port: `docker-compose.yml` maps 5432, but each checkout
carries a gitignored `docker-compose.override.yml` that moves it to 5433
(`scripts/wt-setup.sh` seeds it, so every worktree shares the same container).
Put `POSTGRES_PORT=5433` in `secrets/.env` to match.

Open the app on the Vite port only. It proxies `/api` to the backend, which is
what makes the session cookie first-party. The backend port alone signs nobody
in.

### Populate the database

The data lives in [resslab-hub-data](https://github.com/RESSLab-Team/resslab-hub-data).

1. Clone it next to this repo. `backend/Makefile` looks for it at
   `../../resslab-hub-data` relative to `backend/`, that is a sibling of this
   checkout:

   ```bash
   git clone https://github.com/RESSLab-Team/resslab-hub-data.git ../resslab-hub-data
   ```

   Anywhere else works too: `export RESSLAB_DATA_DIR=/path/to/resslab-hub-data`,
   or a symlink at `../resslab-hub-data`. Worktrees get the absolute path in
   their `.env.worktree`.

2. Git LFS. Only the SEM microscope images (`material/ductile_fracture/sem/`,
   about 700 TIF files, 1.7 GB) are in LFS. The CSV files are plain git, so
   the upload works without LFS installed. If `git lfs` is installed and you
   do not want the images, clone with `GIT_LFS_SKIP_SMUDGE=1`. To get them
   later: `git lfs install` then `git lfs pull`. The images are only needed
   for `make precompute-sem` ([docs/sem-images.md](docs/sem-images.md)).

3. Upload:

   ```bash
   make dev-database
   make upload-data                  # changed files only (FORCE=1: all, ~1 min)
   make -C backend upload-data-light # one measurement file per series type, ~30 s
   ```

   Both read `RESSLAB_DATA_DIR`. The light one is enough for most UI work.
   Rerun after pulling the data repo. In a worktree, `make db-template-light`
   once, then `make db-branch` clones that template into the branch's own
   database in under a second (details in
   [docs/worktree-dev-environment.md](docs/worktree-dev-environment.md)).

4. The backend caches responses for `CACHE_MAX_AGE` seconds (one hour by
   default). Set `CACHE_MAX_AGE=0` in `secrets/.env` while you work on data,
   so an upload shows at once.

Test batches for the contribution editor come from `make sample-data`, see
[sample-data/README.md](sample-data/README.md).

#### Parallel worktrees (one branch = its own servers + Claude Code session)

```bash
make new BRANCH=feat/my-thing      # worktree + deps + secrets + ports + tmux session, attached (wt create + attach)
make wt-open BRANCH=feat/my-thing  # open that branch's frontend
make wt-land BRANCH=feat/my-thing  # rebase, PR, squash-merge into dev, remove the worktree
```

Everything about it (ports, the shared vs per-branch database, what Claude may and may not do in a worktree) is in [docs/worktree-dev-environment.md](docs/worktree-dev-environment.md).

#### Visual Studio Code

Run configurations are in `.vscode`: https://code.visualstudio.com/docs/editor/debugging

## Generate API for frontend

Folder `frontend/src/backend` is generated from backend API. It should be updated when the backend api changes.

```bash
make api
```

## Deployment

### Environments

| Branch or tag | Deploys to |
|---|---|
| `dev` | https://resslab-hub-dev.epfl.ch |
| `stage` | https://resslab-hub-test.epfl.ch |
| tag `v*.*.*` | https://resslab-hub.epfl.ch |

Promotion goes `dev` -> `stage` -> `main`, and Release Please tags `main`. The
steps, and the rules that make them work, are in
[docs/releasing.md](docs/releasing.md).

### Locally with Docker Compose

```bash
make run
```

Builds the images and starts the full stack (Traefik, frontend, seven backend
replicas, PostgreSQL). It needs `SSL_CERT_CRT` and `SSL_CERT_KEY` in the
environment and the `/etc/ssl` mounts of `docker-compose.yml`.
