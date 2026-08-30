# Per-checkout overrides (git worktrees export these from .env.worktree, see
# docs/worktree-dev-environment.md); the main checkout keeps the defaults.
BACKEND_PORT ?= 8000
RESSLAB_DATA_DIR ?= ../../resslab-hub-data

# `benchmark` collides with the benchmark/ directory; mark targets phony so make
# always runs the recipe instead of treating the directory as an up-to-date file.
.PHONY: install dev test test-cov benchmark lint update sample-data

install:
	uv sync

# --log-level info: debug puts the root logger at DEBUG, which makes
# SQLAlchemy log every statement and adds real per-request latency.
dev:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run uvicorn resslab_hub.main:app --reload --log-level info --port $(BACKEND_PORT)

test:
	uv run pytest

# Coverage: terminal summary + browsable HTML report in backend/htmlcov/index.html
test-cov:
	uv run pytest --cov --cov-report=term-missing --cov-report=html

# Performance benchmark against a throwaway DB (needs `make dev-database`).
# Override defaults with ROWS/ROUNDS, e.g. `make benchmark ROWS=20000 ROUNDS=100`.
ROWS ?= 5000
ROUNDS ?= 50
benchmark:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python -m benchmark.benchmark --rows $(ROWS) --rounds $(ROUNDS)

lint:
	uv run pre-commit run --all-files

# Sample contribution batches for /contribute/new. Needs the database: the
# in-range values are drawn from it. Override with EXPERIMENTS/OUTLIERS.
EXPERIMENTS ?= 15
OUTLIERS ?= 3
sample-data:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python ../sample-data/generate.py \
		--experiments $(EXPERIMENTS) --outliers $(OUTLIERS)

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
	@echo "Looking for files in: $(RESSLAB_DATA_DIR)/$(DIRECTORY)"
	@ls $(RESSLAB_DATA_DIR)/$(DIRECTORY) || (echo "Directory not found or empty" && exit 1)
	@echo "Creating archive $(TAR_NAME)..."
#	tar --exclude-vcs -czf $(TAR_NAME) -C $(RESSLAB_DATA_DIR) $(DIRECTORY)
	@echo ""
	@echo "Executing validation..."
	$(eval API_PASSWORD=$(shell DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python -c "from resslab_hub.config import settings; print(settings.api_password)"))
	curl -s -F "file=@$(TAR_NAME)" -u user:$(API_PASSWORD) http://localhost:$(BACKEND_PORT)/validate?type=all-$* | \
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
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py brace $(RESSLAB_DATA_DIR)/braces/steel_braces.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py brace-displacement $(RESSLAB_DATA_DIR)/braces/force_displacement/*.csv

upload-column:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py column $(RESSLAB_DATA_DIR)/columns/steel_columns.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py column-axial-shortening $(RESSLAB_DATA_DIR)/columns/axial_shortening_rotation/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py column-moment-strong $(RESSLAB_DATA_DIR)/columns/moment_rotation_strong/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py column-moment-weak $(RESSLAB_DATA_DIR)/columns/moment_rotation_weak/*.csv

upload-connection:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection $(RESSLAB_DATA_DIR)/connections/connections.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-global $(RESSLAB_DATA_DIR)/connections/Global/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-global-west $(RESSLAB_DATA_DIR)/connections/Global_west/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-panel-zone $(RESSLAB_DATA_DIR)/connections/Panel_zone/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-beam $(RESSLAB_DATA_DIR)/connections/Beam_moment_rotation/*.csv
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py connection-beam-west $(RESSLAB_DATA_DIR)/connections/Beam_moment_rotation_west/*.csv

upload-material:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-material $(RESSLAB_DATA_DIR)

upload-residual-stress:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-residual-stresses $(RESSLAB_DATA_DIR)

upload-hss-column:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-hss-columns $(RESSLAB_DATA_DIR)

upload-eccentric-braced-frame:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-eccentric-braced-frames $(RESSLAB_DATA_DIR)

upload-tensile-coupon:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-tensile-coupons $(RESSLAB_DATA_DIR)

upload-ductile-fracture:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all-ductile-fractures $(RESSLAB_DATA_DIR)

precompute-sem:
	uv run --group sem python data/precompute_sem.py $(RESSLAB_DATA_DIR)

upload-data:
	DOTENV_PATH_FOR_DYNACONF="../secrets/.env" uv run python data/uploader.py all $(RESSLAB_DATA_DIR)

upload-data-test:
	ENV_FOR_DYNACONF=test $(MAKE) upload-data

transform-data:
	uv run python data/csv_transformer.py aisc $(RESSLAB_DATA_DIR)/connections/component/aisc.csv ../frontend/src/assets/connection/aisc-sections.csv
	uv run python data/csv_transformer.py european $(RESSLAB_DATA_DIR)/connections/component/european.csv ../frontend/src/assets/connection/european-sections.csv
	uv run python data/csv_transformer.py japanese $(RESSLAB_DATA_DIR)/connections/component/japanese.csv ../frontend/src/assets/connection/japanese-sections.csv
	uv run python data/hss_csv_transformer.py aisc $(RESSLAB_DATA_DIR)/hss_columns/sections/aisc.csv ../frontend/src/assets/hss/hss-aisc-sections.csv
	uv run python data/hss_csv_transformer.py european $(RESSLAB_DATA_DIR)/hss_columns/sections/european.csv ../frontend/src/assets/hss/hss-european-sections.csv
	uv run python data/hss_csv_transformer.py japanese $(RESSLAB_DATA_DIR)/hss_columns/sections/japanese.csv ../frontend/src/assets/hss/hss-japanese-sections.csv

#This is outdated now that we use the data dictionnaries
#We keep it for local testing purposes
analyze-data:
	uv run python -m data.analyzer $(RESSLAB_DATA_DIR)/connections/connections.csv $(RESSLAB_DATA_DIR)/material/cyclic_coupons/steel_material.csv $(RESSLAB_DATA_DIR)/columns/steel_columns.csv $(RESSLAB_DATA_DIR)/braces/steel_braces.csv $(RESSLAB_DATA_DIR)/residual_stresses/residual_stresses.csv $(RESSLAB_DATA_DIR)/hss_columns/hss_columns.csv

generate-model:
	uv run python data/generate_model.py \
		$(RESSLAB_DATA_DIR)/braces/steel_braces_data_dictionary.csv \
		resslab_hub/models/database/brace.py \
		resslab_hub/models/api.py brace
	uv run python data/generate_model.py \
		$(RESSLAB_DATA_DIR)/columns/steel_columns_data_dictionary.csv \
		resslab_hub/models/database/column.py \
		resslab_hub/models/api.py column
	uv run python data/generate_model.py \
		$(RESSLAB_DATA_DIR)/connections/connections_data_dictionary.csv \
		resslab_hub/models/database/connection.py \
		resslab_hub/models/api.py connection
	uv run python data/generate_model.py \
		$(RESSLAB_DATA_DIR)/hss_columns/hss_columns_data_dictionary.csv \
		resslab_hub/models/database/hss_column.py \
		resslab_hub/models/api.py hss_column
	uv run python data/generate_model.py \
		$(RESSLAB_DATA_DIR)/material/cyclic_coupons/steel_material_data_dictionary.csv \
		resslab_hub/models/database/material.py \
		resslab_hub/models/api.py material
	uv run python data/generate_model.py \
		$(RESSLAB_DATA_DIR)/residual_stresses/residual_stresses_data_dictionary.csv \
		resslab_hub/models/database/residual_stress.py \
		resslab_hub/models/api.py residual_stress
	uv run python data/generate_model.py \
		$(RESSLAB_DATA_DIR)/eccentric_braced_frames/eccentric_braced_frames_data_dictionary.csv \
		resslab_hub/models/database/eccentric_braced_frame.py \
		resslab_hub/models/api.py eccentric_braced_frame
	uv run python data/generate_model.py \
		$(RESSLAB_DATA_DIR)/material/tensile_coupons/tensile_coupons_data_dictionary.csv \
		resslab_hub/models/database/tensile_coupon.py \
		resslab_hub/models/api.py tensile_coupon
	uv run python data/generate_model.py \
		$(RESSLAB_DATA_DIR)/material/ductile_fracture/ductile_fracture_data_dictionary.csv \
		resslab_hub/models/database/ductile_fracture.py \
		resslab_hub/models/api.py ductile_fracture
