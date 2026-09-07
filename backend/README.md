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
make upload-data
```

The uploader is a module of the package, so it also runs from the backend image:

```bash
python -m resslab_hub.data.uploader all <path to resslab-hub-data>
```

### Upload data to a deployed environment (dev, stage, prod)

Do not tunnel and upload from your laptop. Each environment has a suspended
CronJob `resslab-hub-upload-data-<env>` that does the same upload from inside
the cluster, next to the database. In the ArgoCD UI, open the environment's
application, find that CronJob and use the `create-job` action. It runs the
same backend image the environment serves, on the CSV data image built by the
resslab-hub-data repo (`main` for dev and prod, `test` for stage).

Two things to know:

- The job replaces the rows it owns, table by table. The site keeps serving
  during the run.
- The backend caches responses per process for one hour, so the new data can
  take up to an hour to show. Restart the backend pods from ArgoCD if you need
  it right away.

Fallback if the cluster job is not an option (the data image is not built yet,
or you need to upload something that is not in the data repo): port-forward the
database and upload from your machine.

```bash
kubectl -n epfl-resslab-resslab-hub-dev port-forward svc/resslab-hub-db-dev 5432:5432
```

Set `secrets/.env` (at the **repo root**, not under `backend/` — the Makefile loads `../secrets/.env`) with the creds from Infisical (`/epfl-resslab/resslab-hub/db`, env slug `dev`, `staging` or `prod`):

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=<DB_USER>
POSTGRES_PASSWORD=<DB_PASSWORD>
API_PASSWORD=<any non-empty value>   # machine credential, see docs/auth.md
```

To send real sign-in mails instead of logging them, add the `SMTP_*` block
from `docs/auth.md`. Watch the quoting of `SMTP_USER`: double quotes turn the
backslash into a newline.

If your local machine already runs a Postgres on 5432, port-forward to a different port (e.g. `5433:5432`) and set `POSTGRES_PORT=5433` in the `.env`.

Then from `backend/`, run `make upload-data`. Note: it **erases** existing data in the tables it touches.
