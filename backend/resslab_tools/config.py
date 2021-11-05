
from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    envvar_prefix=False,
    settings_files=['resslab_tools/settings.toml'],
    validators=[
        Validator('cors_enabled', default=False),
        Validator('root_path', default=''),
    ],
)

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
