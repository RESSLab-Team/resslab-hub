# Resslab Hub

## Database Migration

When the data schema changed in the CSV, we need to do a database migration:

- Data Analyzer: update the SQLAlchemy table definitions
- Alembic: create a new revision with the changes and verify it

### Data Analyzer

The utility script `backend/data/analyzer.py` generates the column definition for SQLAlchemy.

Replace the generated definition in the corresponding `backend/resslab_hub/models/database/*.py`.

```base
make analyze-data
```

### Alembic

We use [Alembic](https://alembic.sqlalchemy.org/en/latest/) to autogenerate the revisions and to apply them.

```bash
# Generate new revision
make database-revision name="TODO revision name"

# Manually upgrade database (automatically run at startup)
make database-upgrade

# Downgrade https://alembic.sqlalchemy.org/en/latest/tutorial.html#downgrading
make database-downgrade revision=
```

## Upload data

After migrating the database or if you just need to update the new data without changing the schema, you can upload the new data (this will erase the old data):

```bash
# Upload data to local database
make upload-data

# Upload data to prod database
make upload-data-prod
```
