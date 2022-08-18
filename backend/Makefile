install:
	poetry install

run:
	poetry run dotenv -f ../secrets/.env run uvicorn resslab_hub.main:app --reload

test:
	poetry run pytest

lint:
	poetry run pre-commit run --all-files

update:
	pre-commit autoupdate

upload-data: upload-brace upload-column upload-connection

upload-brace:
	poetry run dotenv -f ../secrets/.env run py data/uploader.py brace ../../resslab-hub-data/braces/steel_braces.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py brace-displacement ../../resslab-hub-data/braces/force_displacement/*.csv

upload-column:
	poetry run dotenv -f ../secrets/.env run py data/uploader.py column ../../resslab-hub-data/columns/steel_columns.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py column-axial-shortening ../../resslab-hub-data/columns/axial_shortening_rotation/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py column-moment-strong ../../resslab-hub-data/columns/moment_rotation_strong/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py column-moment-weak ../../resslab-hub-data/columns/moment_rotation_weak/*.csv

upload-connection:
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection ../../resslab-hub-data/connections/connections.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-global ../../resslab-hub-data/connections/Global/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-global-west ../../resslab-hub-data/connections/Global_west/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-panel-zone ../../resslab-hub-data/connections/Panel_zone/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-beam ../../resslab-hub-data/connections/Beam_moment_rotation/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-beam-west ../../resslab-hub-data/connections/Beam_moment_rotation_west/*.csv

transform-data:
	poetry run python data/csv_transformer.py aisc ../../resslab-hub-data/connections/component/aisc.csv ../frontend/src/assets/connection/aisc-sections.csv
	poetry run python data/csv_transformer.py european ../../resslab-hub-data/connections/component/european.csv ../frontend/src/assets/connection/european-sections.csv
	poetry run python data/csv_transformer.py japanese ../../resslab-hub-data/connections/component/japanese.csv ../frontend/src/assets/connection/japanese-sections.csv

upgrade-database:
	poetry run dotenv -f ../secrets/.env run alembic upgrade head

upgrade-database-prod:
	ENV_FOR_DYNACONF=production $(MAKE) upgrade-database
