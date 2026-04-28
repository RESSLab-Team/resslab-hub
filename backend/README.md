# Resslab Hub

## Database Migration

When the data schema changed in the CSV, we need to do a database migration:

- Data Analyzer: update the SQLAlchemy table definitions
- Alembic: create a new revision with the changes and verify it

### Data Model Generator

The utility script `backend/data/generate_model.py` generates the column definition for SQLAlchemy.

Replace automatically the generated definition in the corresponding `backend/resslab_hub/models/database/*.py`.

```base
make generate-model
```

You then need to check the generated code for any potential issues. And then you must run `make database-revision` to create a new revision with the proper changes.

And don't forget to align the types in resslab-hub/backend/resslab_hub/models/api.py


### Alembic

We use [Alembic](https://alembic.sqlalchemy.org/en/latest/) to autogenerate the revisions and to apply them.

```bash
# Generate new revision
make database-revision name="TODO revision name"

# Manually upgrade database (automatically run at startup)
make database-upgrade

# Downgrade to last revision (runs downgrade -1)
make database-downgrade
```

## Upload data

After migrating the database or if you just need to update the new data without changing the schema, you can upload the new data (this will erase the old data):

```bash
# Upload data to local database
make upload-data

# Upload data to test database
make upload-data-test
```

### Upload data to the dev cluster

`dev` runs on the EPFL ENAC Kubernetes cluster (`prod` / `test` are still on the old Ansible-managed VM — keep using SSH for those). The dev DB isn't exposed publicly, so port-forward it first:

```bash
kubectl -n epfl-resslab-resslab-hub-dev port-forward svc/resslab-hub-db-dev 5432:5432
```

Set `secrets/.env` (at the **repo root**, not under `backend/` — the Makefile loads `../secrets/.env`) with the dev creds from Infisical (`/epfl-resslab/resslab-hub/db`, env slug `dev`):

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=<DB_USER>
POSTGRES_PASSWORD=<DB_PASSWORD>
API_PASSWORD=<any non-empty value>
```

If your local machine already runs a Postgres on 5432, port-forward to a different port (e.g. `5433:5432`) and set `POSTGRES_PORT=5433` in the `.env`.

Then from `backend/`, run `make upload-data`. Note: it **erases** existing data in the tables it touches.
