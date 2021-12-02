install:
	poetry install

run:
	poetry run dotenv -f ../secrets/.env run uvicorn resslab_tools.main:app --reload

test:
	poetry run pytest
