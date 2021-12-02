# resslab-tools

## Development

### Installation

Prerequisites:

- [Make](https://www.gnu.org/software/make/)
- [Poetry](https://python-poetry.org/)
- [Node.js](https://nodejs.org/)
- Copy `secrets` folder from `//enac1files.epfl.ch/common/IT4R/github/resslab-tools` to this repository root

```bash
make install
```

### Run for development

#### CLI

```bash
make run-database
# postgresql://127.0.0.1:5432

make run-backend
# http://127.0.0.1:8080

make run-frontend
# http://127.0.0.1:8000
```

#### Visual Studio Code

Run configurations are in `.vscode`: https://code.visualstudio.com/docs/editor/debugging

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

### Server

Deployed on http://enacvm0070.xaas.epfl.ch/

Prerequisites:

- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)

```bash
# Install on new server
make install-server

# Deploy
make deploy-prod
```
