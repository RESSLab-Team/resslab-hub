install:
	npm install
	$(MAKE) -C backend install
	$(MAKE) -C frontend install

dev-all:
	docker compose up -d database
	gnome-terminal --tab -- bash -c '$(MAKE) -C frontend dev'
	$(MAKE) -C backend dev

dev-backend:
	$(MAKE) -C backend dev

dev-frontend:
	$(MAKE) -C frontend dev

dev-database:
	docker compose up -d database

test:
	$(MAKE) -C backend test
	$(MAKE) -C frontend test

lint:
	$(MAKE) -C backend lint
	$(MAKE) -C frontend lint

update:
	$(MAKE) -C backend update

run:
	docker compose build --parallel --pull
	docker compose up -d --remove-orphans --scale backend=4

api:
	cd backend; DATABASE_UPGRADE=false poetry run python api.py ../openapi.json
	$(MAKE) -C frontend api

upload-data:
	$(MAKE) -C backend upload-data

upload-data-test:
	$(MAKE) -C backend upload-data-test
