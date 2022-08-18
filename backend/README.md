# resslab_hub

## Database Migration

```bash
# Generate new revision
poetry run dotenv -f ../secrets/.env run alembic revision --autogenerate -m ""

# Manually upgrade database (automatically run at startup)
poetry run dotenv -f ../secrets/.env run alembic upgrade head

# Downgrade https://alembic.sqlalchemy.org/en/latest/tutorial.html#downgrading
poetry run dotenv -f ../secrets/.env run alembic downgrade
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
