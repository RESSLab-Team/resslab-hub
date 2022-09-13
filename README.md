# resslab-hub

## Related Repositories

- [resslab-hub-data](https://github.com/RESSLab-Team/resslab-hub-data) contains the csv to populate the database
- [resslab-hub-scripts](https://github.com/RESSLab-Team/resslab-hub-scripts) contains the MATLAB scripts translated for component models and fraglity curves

## Development

### Prerequisites

Prerequisites:

- [Python](https://www.python.org/) 3.9
- [Make](https://www.gnu.org/software/make/)
- [Poetry](https://python-poetry.org/)
- [Node.js](https://nodejs.org/) 16.x
- [Docker](https://www.docker.com/)
  - [Docker Compose](https://docs.docker.com/compose/) 1.27.0+

### Secrets

An environment file should be created (see all available keys in `backend/resslab_hub/config.py`).

```bash
mkdir -p secrets && echo POSTGRES_PASSWORD=changeit > secrets/.env
```

### Installation

```bash
make install
```

#### for MAC OS

1. Do not hesitate to use pyenv to setup python3.9.6 at least
2. Use brew to install openssl and postgresql
3. if you encounter any problem, clear your poetry cache

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
make run-database
# postgresql://127.0.0.1:5432

make run-backend
# http://127.0.0.1:8000

make run-frontend
# http://127.0.0.1:8080
```

#### Visual Studio Code

Run configurations are in `.vscode`: https://code.visualstudio.com/docs/editor/debugging

### Data

Populate data to database

```bash
make upload-data
```

## Generate API for frontend

Folder frontend/src/backend is generated from backend API. It should be updated when the backend api changes.

```bash
# update generated files (requires Java installed)
make generate-api
```

## Deployment

### Locally with Docker Compose

```bash
make deploy-local
```
