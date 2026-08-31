# resslab-hub

## Related Repositories

- [resslab-hub-data](https://github.com/RESSLab-Team/resslab-hub-data) contains the csv to populate the database
- [resslab-hub-scripts](https://github.com/RESSLab-Team/resslab-hub-scripts) contains the MATLAB scripts translated for component models and fraglity curves

## Development

### Prerequisites

Prerequisites:

- [uv](https://docs.astral.sh/uv/) (manages Python automatically)
- [Make](https://www.gnu.org/software/make/)
- [Node.js](https://nodejs.org/) ≥ 18 (CI uses the current LTS)
- [Docker](https://www.docker.com/) with the [Compose v2 plugin](https://docs.docker.com/compose/)

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

#### for MAC OS

1. Use brew to install openssl and postgresql
2. if you encounter any problem, clear your uv cache (`uv cache clean`)

https://github.com/psycopg/psycopg2/issues/1200#issuecomment-776159466

```
$ brew install postgresql ## need to be done first

$ brew link openssl
Warning: Refusing to link macOS provided/shadowed software: openssl@1.1
If you need to have openssl@1.1 first in your PATH, run:
  echo 'export PATH="/opt/homebrew/opt/openssl@1.1/bin:$PATH"' >> ~/.zshrc

For compilers to find openssl@1.1 you may need to set:
  export LDFLAGS="-L/opt/homebrew/opt/openssl@1.1/lib"
  export CPPFLAGS="-I/opt/homebrew/opt/openssl@1.1/include"

For pkg-config to find openssl@1.1 you may need to set:
  export PKG_CONFIG_PATH="/opt/homebrew/opt/openssl@1.1/lib/pkgconfig"
```

### Run for development

#### CLI

```bash
make dev-database
# postgresql://127.0.0.1:5432

make dev-backend
# http://127.0.0.1:8000

make dev-frontend
# http://127.0.0.1:5173
```

#### Parallel worktrees (one branch = its own servers + Claude Code session)

```bash
make new BRANCH=feat/my-thing      # worktree + deps + secrets + ports + tmux session, attached (wt create + attach)
make wt-open BRANCH=feat/my-thing  # open that branch's frontend
make wt-land BRANCH=feat/my-thing  # rebase, PR, squash-merge into dev, remove the worktree
```

Everything about it — ports, the shared vs per-branch database, what Claude may and may not do in a worktree — is in [docs/worktree-dev-environment.md](docs/worktree-dev-environment.md).

#### Visual Studio Code

Run configurations are in `.vscode`: https://code.visualstudio.com/docs/editor/debugging

## Upload Data

Upload data to database.
See [backend](./backend/README.md)

## Generate API for frontend

Folder `frontend/src/backend` is generated from backend API. It should be updated when the backend api changes.

```bash
make api
```

## Deployment

### Locally with Docker Compose

```bash
make run
```
