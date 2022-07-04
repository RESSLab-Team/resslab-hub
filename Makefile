install:
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

deploy-local:
	docker-compose build --parallel --pull
	docker-compose up --remove-orphans

install-server:
	ansible-galaxy install -r ansible/requirements.yml
	ansible-playbook ansible/install.yml -i ansible/inventory.ini

deploy-prod:
	ansible-playbook ansible/deploy.yml -i ansible/inventory.ini

api:
	cd backend; poetry run dotenv -f ../secrets/.env run python api.py ../openapi.json
	cd frontend; npm run generate:backend

upload-data:
	$(MAKE) -C backend upload-data

upload-data-prod:
	ENV_FOR_DYNACONF=production $(MAKE) upload-data
