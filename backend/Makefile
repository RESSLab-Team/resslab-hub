install:
	poetry install
	poetry run pre-commit install

run:
	poetry run dotenv -f ../secrets/.env run uvicorn resslab_tools.main:app --reload

test:
	poetry run pytest

lint:
	poetry run pre-commit run --all-files

upload-data:
	poetry run dotenv -f ../secrets/.env run python data.py connection ../../resslab-tools-data/connections/connections.csv
	poetry run dotenv -f ../secrets/.env run python data.py connection-global ../../resslab-tools-data/connections/Global/*.csv
	poetry run dotenv -f ../secrets/.env run python data.py connection-global-west ../../resslab-tools-data/connections/Global_west/*.csv
	poetry run dotenv -f ../secrets/.env run python data.py connection-panel-zone ../../resslab-tools-data/connections/Panel_zone/*.csv
