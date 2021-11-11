install:
	$(MAKE) -C backend install
	$(MAKE) -C frontend install

run-backend:
	$(MAKE) -C backend run

run-frontend:
	$(MAKE) -C frontend run

generate-api:
	cd backend; poetry run dotenv -f ../secrets/.env run python cli.py ../openapi.json
	cd frontend; npm run generate:backend
