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

# Upload data to prod database
# You firstly need to setup the port forwarding
ssh -NL 5432:localhost:5432 root@resslab-hub.epfl.ch

#Then upload locally (forwarded to prod) (with the correct database credential)
make upload-data
```
