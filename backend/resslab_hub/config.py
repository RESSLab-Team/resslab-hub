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
        Validator("root_path", default=""),
        Validator("postgres_host", default="localhost"),
        Validator("postgres_port", default=5432),
        Validator("postgres_user", default="postgres"),
        Validator("postgres_password", must_exist=True),
        Validator("postgres_db", default="postgres"),
        # Where CREATE/DROP DATABASE are issued from (tests). A worktree's own
        # role can only connect to its clone, so wt-db.sh points this at it.
        Validator("postgres_maintenance_db", default="postgres"),
        Validator("database_upgrade", default=True),
        Validator("cache_max_age", default=3600),
        Validator("sql_echo", default=False),
        Validator("db_pool_size", default=5),
        Validator("db_max_overflow", default=10),
        Validator("analytics_property_id", default=None),
        Validator("google_application_credentials", default=None),
        Validator("api_username", default="user"),
        Validator("api_password", must_exist=True),
        # GitHub App used to open contribution PRs on the data repo. All three
        # credentials present = submissions enabled; otherwise POST
        # /contributions answers 503 and the app runs without the feature.
        Validator("github_app_id", default=None),
        Validator("github_app_private_key", default=None),
        Validator("github_app_installation_id", default=None),
        # The deploy-time switch for the whole contribution pipeline (submit,
        # curation, sign-in, account). False in prod until it is released
        # there: the endpoints answer 404 and the frontend hides every link.
        # Read at startup, so a change needs a pod restart.
        Validator("contributions_enabled", default=True),
        Validator("data_repo", default="RESSLab-Team/resslab-hub-data"),
        Validator("data_repo_base_branch", default="main"),
        # --- Sign-in (#247) --------------------------------------------------
        # Absolute URL the app is reached at, without the /api prefix:
        # "https://resslab-hub.epfl.ch" in prod, the Vite dev server locally.
        # Every absolute URL the backend emits (OAuth callback, mail links,
        # redirects) is built from it, because behind Traefik the request URL
        # has already lost the /api prefix and may carry an internal host.
        # 127.0.0.1 rather than localhost: GitHub ignores the port on the
        # loopback address, so one registered callback serves every dev port,
        # and the browser must be on the same host for the cookies to travel.
        Validator("public_base_url", default="http://127.0.0.1:5173"),
        # None = derive from public_base_url's scheme, which is the right
        # answer everywhere: https in the deployments, http locally (a Secure
        # cookie is dropped by the dev server and by the httpx test client).
        # Set it explicitly only to override that.
        Validator("session_cookie_secure", default=None),
        Validator("session_ttl_days", default=30),
        Validator("login_code_ttl_minutes", default=10),
        # Mail: without a host the mailer logs the code instead of sending it,
        # which is how local dev and the tests work. The relay is the EPFL one,
        # with the hub's own service account (docs/auth.md). The sender must be
        # that account's own address:
        # Exchange refuses anything else with 550 5.7.60 "does not have
        # permissions to send as this sender".
        Validator("smtp_host", default=None),
        Validator("smtp_port", default=587),
        Validator("smtp_user", default=None),
        Validator("smtp_password", default=None),
        Validator("smtp_from", default="noreply-resslab-hub@epfl.ch"),
        Validator("smtp_starttls", default=True),
        # The deployment name (dev, stage, prod), set by the k8s ConfigMaps
        # and by nothing local. When it is set, a missing SMTP_HOST is an
        # error, not the log-only mode: the mailer refuses to "send" and the
        # sign-in page says so, instead of telling the person a code is on its
        # way (#247).
        Validator("deployment", default=None),
        # OAuth pair of a GitHub App: the one above in the deployments, a
        # separate dev App locally (docs/auth.md). Both present = "Sign in
        # with GitHub" is offered.
        Validator("github_oauth_client_id", default=None),
        Validator("github_oauth_client_secret", default=None),
        # Comma-separated addresses that get the admin role at first sign-in,
        # so a fresh deployment has an administrator without a CLI.
        Validator("admin_emails", default=""),
        # Comma-separated domains that count as academic on top of the
        # pyswot list, for the research institutes and firms it does not
        # know (empa.ch, aisc.org). A subdomain of one of these matches too.
        Validator("contributor_domains", default=""),
        # --- S3, the enacit4r-cdn that serves the SEM images ----------------
        # Same names as the other ENAC apps (eesd-mast, co2-calculator), so the
        # five public ones come from the resslab-hub-backend ConfigMap and the
        # two keys from Infisical, or from secrets/.env on a laptop. No default
        # here on purpose: the values belong to the deployment, not the code.
        # All unset = no CDN, which is every deployment today; only
        # `make precompute-sem` reads them. See docs/sem-images.md.
        Validator("s3_endpoint_protocol", default=None),
        Validator("s3_endpoint_hostname", default=None),
        Validator("s3_region", default=None),
        Validator("s3_bucket", default=None),
        Validator("s3_path_prefix", default=None),
        Validator("s3_access_key_id", default=None),
        Validator("s3_secret_access_key", default=None),
    ],
)

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
