.PHONY: install hooks go dev-all tmux-dev-all dev-backend dev-frontend dev-database test test-cov benchmark lint run api sample-data upload-data backup-dump data-fork-reset new db-template-light db-template db-branch db-branch-full db-branch-drop db-status wt-land wt-done wt-open docs docs-serve

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'


install:                ## pnpm + uv sync + frontend deps, then the git hooks
	pnpm install
	$(MAKE) -C backend install
	$(MAKE) -C frontend install

hooks:                  ## install the Lefthook git hooks (done by make install)
	pnpm exec lefthook install

dev-all: dev-database   ## database + backend + frontend in this terminal, Ctrl-C stops both servers (in a worktree: set -a; . .env.worktree; set +a first)
	$(MAKE) -j2 --no-print-directory dev-backend dev-frontend

tmux-dev-all:           ## same, as the tmux session resslab-hub/<branch> with claude, backend, frontend and shell panes (main checkout and worktrees)
	scripts/tmux-dev.sh

dev-backend:            ## FastAPI on http://127.0.0.1:8000 (BACKEND_PORT in a worktree)
	$(MAKE) -C backend dev

dev-frontend:           ## Vite on http://127.0.0.1:5173 (FRONTEND_PORT in a worktree)
	$(MAKE) -C frontend dev

dev-database:           ## PostgreSQL in Docker, host port 5433 (5432 without docker-compose.override.yml)
	docker compose up -d database

test:                   ## backend pytest + frontend vitest
	$(MAKE) -C backend test
	$(MAKE) -C frontend test

test-cov:               ## same with coverage reports (backend/htmlcov, frontend/coverage)
	$(MAKE) -C backend test-cov
	$(MAKE) -C frontend test-coverage

benchmark:              ## backend performance benchmark against a throwaway DB
	$(MAKE) -C backend benchmark

lint:                   ## backend ruff + frontend ESLint
	$(MAKE) -C backend lint
	$(MAKE) -C frontend lint

run:                    ## Docker build + full stack (traefik, frontend, 7 backends, db); needs SSL_CERT_CRT/KEY
	docker compose build --parallel --pull
	docker compose up -d --remove-orphans --scale backend=7

api:                    ## regenerate openapi.json, database-columns.json and frontend/src/backend/
	cd backend; DATABASE_UPGRADE=false uv run python api.py ../openapi.json
	cd backend; uv run python -m resslab_hub.data.columns ../database-columns.json
	$(MAKE) -C frontend api

sample-data:            ## test batches into sample-data/, from real records, self-checked (EXPERIMENTS=15 OUTLIERS=3)
	$(MAKE) -C backend sample-data

upload-data:            ## upload every CSV of the data repo into the local DB (REBUILD=1 empties the tables first)
	$(MAKE) -C backend upload-data

backup-dump:            ## make backup-dump DEST_FOLDER=path, pg_dumpall of the dev database
	@docker compose exec database sh -c 'pg_dumpall -U postgres' > ${DEST_FOLDER}/all-databases.sql

# --- docs site (zensical.toml, docs/). Zensical comes from the docs group of backend/pyproject.toml.
DOCS_PORT ?= 8100
ZENSICAL = cd backend && uv run --only-group docs zensical

docs:                   ## build the docs site into site/ in strict mode, then check links and orphan files
	$(ZENSICAL) build --config-file ../zensical.toml --clean --strict
	python3 scripts/docs-check-links.py site
	python3 scripts/docs-check-orphans.py

docs-serve:             ## preview the docs site with live reload on http://127.0.0.1:8100 (DOCS_PORT in a worktree)
	$(ZENSICAL) serve --config-file ../zensical.toml --dev-addr 127.0.0.1:$(DOCS_PORT)

data-fork-reset:        ## reset the test fork's main (where local submissions go) to the real data repo's main; needs gh with push on EPFL-ENAC
	scripts/data-fork-reset.sh

# --- git worktrees (docs/worktree-dev-environment.md)
new:                    ## make new BRANCH=feat/x [BASE=origin/dev] [PROMPT=brief.md]: worktree + deps + session, attached
	scripts/wt-new.sh $(BRANCH) $(BASE) $(if $(PROMPT),--prompt '$(PROMPT)')

go: new                 ## make go BRANCH=feat/x: same thing, truthful verb: jump to the branch's session, creating branch/worktree/session as needed (tab completion: wtgo, scripts/wt-go.bash)

db-template-light:      ## build the ~20 MB resslab_hub_light template from the data repo (main CSVs + 1 series file per type, ~30 s)
	scripts/wt-db.sh template-light

db-template:            ## copy the shared dev DB into resslab_hub_template (full 3.4 GB, for branches that need real data volumes)
	scripts/wt-db.sh template

db-branch:              ## clone a template (light if it exists) into this worktree's own DB and turn migrations on
	scripts/wt-db.sh create

db-branch-full:         ## same, but force the full 3.4 GB template
	scripts/wt-db.sh create full

db-branch-drop:         ## drop this worktree's DB and go back to the shared one
	scripts/wt-db.sh drop

db-status:              ## which database this checkout uses
	scripts/wt-db.sh status

wt-land:                ## make wt-land BRANCH=feat/x [MODE=--local]: rebase, PR + squash-merge into dev, clean up
	scripts/wt-land.sh $(BRANCH) $(MODE)

wt-done:                ## make wt-done BRANCH=feat/x: kill the session + remove the worktree, keep the branch
	scripts/wt-done.sh $(BRANCH)

wt-open:                ## make wt-open [TARGET=frontend|backend] [BRANCH=feat/x]
	scripts/wt-open.sh $(or $(TARGET),frontend) $(BRANCH)
