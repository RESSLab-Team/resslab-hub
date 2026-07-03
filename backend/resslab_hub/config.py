"""
Dynaconf Settings
"""

from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    environments=True,
    envvar_prefix=False,
    load_dotenv=True,
    settings_files=["resslab_hub/settings.toml"],
    validators=[
        Validator("cors_enabled", default=False),
        Validator("root_path", default=""),
        Validator("postgres_host", default="localhost"),
        Validator("postgres_port", default=5432),
        Validator("postgres_user", default="postgres"),
        Validator("postgres_password", must_exist=True),
        Validator("postgres_db", default="postgres"),
        Validator("database_upgrade", default=True),
        Validator("cache_max_age", default=3600),
        Validator("sql_echo", default=False),
        Validator("db_pool_size", default=5),
        Validator("db_max_overflow", default=10),
        Validator("analytics_property_id", default=None),
        Validator("google_application_credentials", default=None),
        Validator("api_username", default="user"),
        Validator("api_password", must_exist=True),
    ],
)

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
