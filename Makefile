install:
	npm install
	$(MAKE) -C backend install
	$(MAKE) -C frontend install

run-backend:
	$(MAKE) -C backend run

run-frontend:
	$(MAKE) -C frontend run

run-database:
	docker-compose up -d database

test:
	$(MAKE) -C backend test
	$(MAKE) -C frontend test

lint:
	$(MAKE) -C backend lint
	$(MAKE) -C frontend lint

update:
	$(MAKE) -C backend update

deploy:
	docker-compose build --parallel --pull
	docker-compose up --remove-orphans

api:
	cd backend; DATABASE_UPGRADE=false poetry run python api.py ../openapi.json
	$(MAKE) -C frontend api

upload-data:
	$(MAKE) -C backend upload-data

upload-data-prod:
	$(MAKE) -C backend upload-data-prod

upload-data-test:
	$(MAKE) -C backend upload-data-test
