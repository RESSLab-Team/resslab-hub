install:
	poetry install

run:
	poetry run dotenv -f ../secrets/.env run uvicorn resslab_tools.main:app --reload

test:
	poetry run pytest

lint:
	poetry run pre-commit run --all-files

update:
	pre-commit autoupdate

upload-data: upload-brace upload-column upload-connection

upload-brace:
	poetry run dotenv -f ../secrets/.env run py data/uploader.py brace ../../resslab-tools-data/braces/steel_braces.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py brace-displacement ../../resslab-tools-data/braces/force_displacement/*.csv

upload-column:
	poetry run dotenv -f ../secrets/.env run py data/uploader.py column ../../resslab-tools-data/columns/steel_columns.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py column-axial-shortening ../../resslab-tools-data/columns/axial_shortening_rotation/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py column-moment-strong ../../resslab-tools-data/columns/moment_rotation_strong/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py column-moment-weak ../../resslab-tools-data/columns/moment_rotation_weak/*.csv

upload-connection:
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection ../../resslab-tools-data/connections/connections.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-global ../../resslab-tools-data/connections/Global/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-global-west ../../resslab-tools-data/connections/Global_west/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-panel-zone ../../resslab-tools-data/connections/Panel_zone/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-beam ../../resslab-tools-data/connections/Beam_moment_rotation/*.csv
	poetry run dotenv -f ../secrets/.env run py data/uploader.py connection-beam-west ../../resslab-tools-data/connections/Beam_moment_rotation_west/*.csv

transform-data:
	poetry run python data/csv_transformer.py aisc ../../resslab-tools-data/connections/component/aisc.csv ../frontend/src/assets/connection/aisc-sections.csv
	poetry run python data/csv_transformer.py european ../../resslab-tools-data/connections/component/european.csv ../frontend/src/assets/connection/european-sections.csv
	poetry run python data/csv_transformer.py japanese ../../resslab-tools-data/connections/component/japanese.csv ../frontend/src/assets/connection/japanese-sections.csv
