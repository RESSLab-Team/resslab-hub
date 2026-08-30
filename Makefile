.PHONY: install hooks dev-all dev-backend dev-frontend dev-database test test-cov benchmark lint update run api sample-data upload-data upload-data-test backup-dump new db-template db-branch db-branch-drop db-status wt-land wt-open

install:
	npm install
	$(MAKE) -C backend install
	$(MAKE) -C frontend install

hooks:
	npx lefthook install

# tmux session "resslab-hub/<branch>" with backend, frontend, claude and shell
# windows; starts the database if needed. Works in the main checkout and in
# every git worktree (see docs/worktree-dev-environment.md).
dev-all:
	scripts/tmux-dev.sh

dev-backend:
	$(MAKE) -C backend dev

dev-frontend:
	$(MAKE) -C frontend dev

dev-database:
	docker compose up -d database

test:
	$(MAKE) -C backend test
	$(MAKE) -C frontend test

test-cov:
	$(MAKE) -C backend test-cov
	$(MAKE) -C frontend test-coverage

benchmark:
	$(MAKE) -C backend benchmark

lint:
	$(MAKE) -C backend lint
	$(MAKE) -C frontend lint

update:
	$(MAKE) -C backend update

run:
	docker compose build --parallel --pull
	docker compose up -d --remove-orphans --scale backend=7

api:
	cd backend; DATABASE_UPGRADE=false uv run python api.py ../openapi.json
	$(MAKE) -C frontend api

sample-data:
	$(MAKE) -C backend sample-data

upload-data:
	$(MAKE) -C backend upload-data

upload-data-test:
	$(MAKE) -C backend upload-data-test

backup-dump:
	@docker compose exec database sh -c 'pg_dumpall -U postgres' > ${DEST_FOLDER}/all-databases.sql

# --- git worktrees (docs/worktree-dev-environment.md)
new:                    ## make new BRANCH=feat/x [BASE=stage]  — worktree + deps + session, attached
	scripts/wt-new.sh $(BRANCH) $(or $(BASE),stage)

db-template:            ## copy the shared dev DB into resslab_hub_template (once, from the main checkout)
	scripts/wt-db.sh template

db-branch:              ## clone the template into this worktree's own DB and turn migrations on
	scripts/wt-db.sh create

db-branch-drop:         ## drop this worktree's DB and go back to the shared one
	scripts/wt-db.sh drop

db-status:
	scripts/wt-db.sh status

wt-land:                ## make wt-land BRANCH=feat/x [MODE=--local]  — rebase, PR + squash-merge into dev, clean up
	scripts/wt-land.sh $(BRANCH) $(MODE)

wt-open:                ## make wt-open [TARGET=frontend|backend] [BRANCH=feat/x]
	scripts/wt-open.sh $(or $(TARGET),frontend) $(BRANCH)
