# resslab_hub

## Database Migration

```bash
# Generate new revision
DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run alembic revision --autogenerate -m ""

# Manually upgrade database (automatically run at startup)
DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run alembic upgrade head

# Downgrade https://alembic.sqlalchemy.org/en/latest/tutorial.html#downgrading
DOTENV_PATH_FOR_DYNACONF="../secrets/.env" poetry run alembic downgrade
```

## Upload data

```bash
make upload-data
```

## SSH Port Forwarding

```bash
# local_port:localhost:remote_port
ssh -NL 5432:localhost:5432 root@enacvm0074.xaas.epfl.ch
```
