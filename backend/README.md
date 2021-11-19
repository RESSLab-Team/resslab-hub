# resslab_tools

## Database Migration

```shell
# Generate new revision
poetry run dotenv -f ..\secrets\.env run alembic revision --autogenerate -m ""

# Manually upgrade database (automatically run at startup)
poetry run dotenv -f ..\secrets\.env run alembic upgrade head
```
