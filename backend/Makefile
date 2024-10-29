install:
	poetry install

dev:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run uvicorn resslab_hub.main:app --reload --log-level debug

test:
	poetry run pytest

lint:
	poetry run pre-commit run --all-files

update:
	pre-commit autoupdate

database-upgrade:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run alembic upgrade head

database-upgrade-prod:
	ENV_FOR_DYNACONF=production $(MAKE) database-upgrade

database-downgrade:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run alembic downgrade -1

database-revision:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run alembic revision --autogenerate -m "$(name)"

upload-brace:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py brace ../../resslab-hub-data/braces/steel_braces.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py brace-displacement ../../resslab-hub-data/braces/force_displacement/*.csv

upload-column:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py column ../../resslab-hub-data/columns/steel_columns.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py column-axial-shortening ../../resslab-hub-data/columns/axial_shortening_rotation/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py column-moment-strong ../../resslab-hub-data/columns/moment_rotation_strong/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py column-moment-weak ../../resslab-hub-data/columns/moment_rotation_weak/*.csv

upload-connection:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py connection ../../resslab-hub-data/connections/connections.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py connection-global ../../resslab-hub-data/connections/Global/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py connection-global-west ../../resslab-hub-data/connections/Global_west/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py connection-panel-zone ../../resslab-hub-data/connections/Panel_zone/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py connection-beam ../../resslab-hub-data/connections/Beam_moment_rotation/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py connection-beam-west ../../resslab-hub-data/connections/Beam_moment_rotation_west/*.csv

upload-material:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py all-materials ../../resslab-hub-data

upload-residual-stress:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py all-residual-stress ../../resslab-hub-data

upload-hss-column:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py all-hss-columns ../../resslab-hub-data

upload-data:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run python data/uploader.py all ../../resslab-hub-data

upload-data-test:
	ENV_FOR_DYNACONF=test $(MAKE) upload-data

transform-data:
	poetry run python data/csv_transformer.py aisc ../../resslab-hub-data/connections/component/aisc.csv ../frontend/src/assets/connection/aisc-sections.csv
	poetry run python data/csv_transformer.py european ../../resslab-hub-data/connections/component/european.csv ../frontend/src/assets/connection/european-sections.csv
	poetry run python data/csv_transformer.py japanese ../../resslab-hub-data/connections/component/japanese.csv ../frontend/src/assets/connection/japanese-sections.csv

analyze-data:
	poetry run python -m data.analyzer ../../resslab-hub-data/connections/connections.csv ../../resslab-hub-data/material/steel_material.csv ../../resslab-hub-data/columns/steel_columns.csv ../../resslab-hub-data/braces/steel_braces.csv ../../resslab-hub-data/residual_stresses/residual_stresses.csv ../../resslab-hub-data/hss_columns/hss_columns.csv
