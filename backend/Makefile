install:
	uv sync

dev:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run uvicorn resslab_hub.main:app --reload --log-level debug

test:
	uv run pytest

lint:
	uv run pre-commit run --all-files

update:
	pre-commit autoupdate

validate-data:
	@echo "Choose a data type to validate: braces, columns, connections, material, residual-stresses, or hss-columns"
	@echo "Example: make validate-braces"

# Add to your Makefile or replace the existing validate-% rule
validate-%:
	@echo "Preparing archive for validating $*..."
	$(eval DIRECTORY=$(subst -,_,$*))
	$(eval TAR_NAME=$(DIRECTORY).tar.gz)
	@echo "Looking for files in: ../../resslab-hub-data/$(DIRECTORY)"
	@ls ../../resslab-hub-data/$(DIRECTORY) || (echo "Directory not found or empty" && exit 1)
	@echo "Creating archive $(TAR_NAME)..."
#	tar --exclude-vcs -czf $(TAR_NAME) -C ../../resslab-hub-data $(DIRECTORY)
	@echo ""
	@echo "Executing validation..."
	$(eval API_PASSWORD=$(shell DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python -c "from resslab_hub.config import settings; print(settings.api_password)"))
	curl -s -F "file=@$(TAR_NAME)" -u user:$(API_PASSWORD) http://localhost:8000/validate?type=all-$* | \
	jq -r
	@echo ""
	@echo "Cleaning up temporary file..."

database-upgrade:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run alembic upgrade head

database-upgrade-prod:
	ENV_FOR_DYNACONF=production $(MAKE) database-upgrade

database-downgrade:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run alembic downgrade -1

database-revision:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run alembic revision --autogenerate -m "$(name)"

upload-brace:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py brace ../../resslab-hub-data/braces/steel_braces.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py brace-displacement ../../resslab-hub-data/braces/force_displacement/*.csv

upload-column:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py column ../../resslab-hub-data/columns/steel_columns.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py column-axial-shortening ../../resslab-hub-data/columns/axial_shortening_rotation/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py column-moment-strong ../../resslab-hub-data/columns/moment_rotation_strong/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py column-moment-weak ../../resslab-hub-data/columns/moment_rotation_weak/*.csv

upload-connection:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection ../../resslab-hub-data/connections/connections.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-global ../../resslab-hub-data/connections/Global/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-global-west ../../resslab-hub-data/connections/Global_west/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-panel-zone ../../resslab-hub-data/connections/Panel_zone/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-beam ../../resslab-hub-data/connections/Beam_moment_rotation/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-beam-west ../../resslab-hub-data/connections/Beam_moment_rotation_west/*.csv

upload-material:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-material ../../resslab-hub-data

upload-residual-stress:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-residual-stresses ../../resslab-hub-data

upload-hss-column:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-hss-columns ../../resslab-hub-data

upload-eccentric-braced-frame:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-eccentric-braced-frames ../../resslab-hub-data

upload-tensile-coupon:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-tensile-coupons ../../resslab-hub-data

upload-ductile-fracture:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-ductile-fractures ../../resslab-hub-data

upload-data:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all ../../resslab-hub-data

upload-data-test:
	ENV_FOR_DYNACONF=test $(MAKE) upload-data

transform-data:
	uv run python data/csv_transformer.py aisc ../../resslab-hub-data/connections/component/aisc.csv ../frontend/src/assets/connection/aisc-sections.csv
	uv run python data/csv_transformer.py european ../../resslab-hub-data/connections/component/european.csv ../frontend/src/assets/connection/european-sections.csv
	uv run python data/csv_transformer.py japanese ../../resslab-hub-data/connections/component/japanese.csv ../frontend/src/assets/connection/japanese-sections.csv
	uv run python data/hss_csv_transformer.py aisc ../../resslab-hub-data/hss_columns/sections/aisc.csv ../frontend/src/assets/hss/hss-aisc-sections.csv
	uv run python data/hss_csv_transformer.py european ../../resslab-hub-data/hss_columns/sections/european.csv ../frontend/src/assets/hss/hss-european-sections.csv
	uv run python data/hss_csv_transformer.py japanese ../../resslab-hub-data/hss_columns/sections/japanese.csv ../frontend/src/assets/hss/hss-japanese-sections.csv

#This is outdated now that we use the data dictionnaries
#We keep it for local testing purposes
analyze-data:
	uv run python -m data.analyzer ../../resslab-hub-data/connections/connections.csv ../../resslab-hub-data/material/steel_material.csv ../../resslab-hub-data/columns/steel_columns.csv ../../resslab-hub-data/braces/steel_braces.csv ../../resslab-hub-data/residual_stresses/residual_stresses.csv ../../resslab-hub-data/hss_columns/hss_columns.csv

generate-model:
	uv run python data/generate_model.py \
		../../resslab-hub-data/braces/steel_braces_data_dictionary.csv \
		resslab_hub/models/database/brace.py \
		resslab_hub/models/api.py brace
	uv run python data/generate_model.py \
		../../resslab-hub-data/columns/steel_columns_data_dictionary.csv \
		resslab_hub/models/database/column.py \
		resslab_hub/models/api.py column
	uv run python data/generate_model.py \
		../../resslab-hub-data/connections/connections_data_dictionary.csv \
		resslab_hub/models/database/connection.py \
		resslab_hub/models/api.py connection
	uv run python data/generate_model.py \
		../../resslab-hub-data/hss_columns/hss_columns_data_dictionary.csv \
		resslab_hub/models/database/hss_column.py \
		resslab_hub/models/api.py hss_column
	uv run python data/generate_model.py \
		../../resslab-hub-data/material/steel_material_data_dictionary.csv \
		resslab_hub/models/database/material.py \
		resslab_hub/models/api.py material
	uv run python data/generate_model.py \
		../../resslab-hub-data/residual_stresses/residual_stresses_data_dictionary.csv \
		resslab_hub/models/database/residual_stress.py \
		resslab_hub/models/api.py residual_stress
	uv run python data/generate_model.py \
		../../resslab-hub-data/eccentric_braced_frames/eccentric_braced_frames_data_dictionary.csv \
		resslab_hub/models/database/eccentric_braced_frame.py \
		resslab_hub/models/api.py eccentric_braced_frame
	uv run python data/generate_model.py \
		../../resslab-hub-data/tensile_coupons/tensile_coupons_data_dictionary.csv \
		resslab_hub/models/database/tensile_coupon.py \
		resslab_hub/models/api.py tensile_coupon
	uv run python data/generate_model.py \
		../../resslab-hub-data/ductile_fracture/ductile_fracture_data_dictionary.csv \
		resslab_hub/models/database/ductile_fracture.py \
		resslab_hub/models/api.py ductile_fracture
