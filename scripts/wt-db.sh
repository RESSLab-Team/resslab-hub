#!/usr/bin/env bash
# Per-branch database for a worktree, cloned from an idle template, owned by a
# per-branch Postgres role that can reach nothing else on the server.
# Two templates exist:
#   resslab_hub_light    (default) ~20 MB rebuilt from the data repo: every main
#                        CSV, dictionary and README, one measurement file per
#                        series type — enough for almost all feature work, and a
#                        clone costs well under a second, so every worktree gets
#                        its own and migrations stay ON.
#   resslab_hub_template full idle copy of the shared 3.4 GB dev dataset, for
#                        branches that need real data volumes or every curve.
# Commands:
#   wt-db.sh template-light  (re)build resslab_hub_light from the data repo — alembic + uploader, ~30 s
#   wt-db.sh template        (re)build resslab_hub_template from the shared DB — pg_dump | psql, minutes, 3.4 GB
#   wt-db.sh create [full]   clone a template into resslab_hub_<slug> owned by role wt_<slug>,
#                            point this worktree at it with that role's credentials, migrations ON
#   wt-db.sh drop            drop this worktree's clone, its test DB and its role, point it back
#                            at the shared DB as the admin user, migrations OFF
#   wt-db.sh status          which DB and role this worktree uses, and the clones that exist
# Why a template and not `TEMPLATE postgres` directly: Postgres refuses to clone a
# database that has open connections, and the shared one always has some.
# Why a role per branch: the backend, alembic, the uploader and pytest all log in
# with what secrets/.env says. As the admin superuser, a worktree could read or
# drop the shared dataset, the templates or another branch's clone, whatever its
# POSTGRES_DB says. As wt_<slug>, owner of its clone only, it cannot connect
# anywhere else (CONNECT is revoked from PUBLIC on every database this script
# manages). The admin commands here keep running as the superuser through
# `docker exec`, which uses the container's local trust login and no password.
set -euo pipefail
SCRIPTS="$(dirname "$(readlink -f "$0")")"
. "$SCRIPTS/wt-lib.sh"
load_env_worktree
cd "$ROOT"
BRANCH="$(current_branch)"
SLUG="$(slug "$BRANCH")"
CLONE="resslab_hub_$SLUG"
TEST_CLONE="resslab_hub_test_$SLUG"
ROLE="$(db_role "$BRANCH")"

db_exists() { [ "$(psql_db -Atc "select 1 from pg_database where datname='$1'")" = 1 ]; }
role_exists() { [ "$(psql_db -Atc "select 1 from pg_roles where rolname='$1'")" = 1 ]; }
container_up() { docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER" || die "$DB_CONTAINER is not running (make dev-database)"; }
# Point this worktree at DBNAME with migrations UPGRADE (true/false), logging in
# as USER with PASSWORD. The maintenance DB is where pytest issues CREATE/DROP
# DATABASE from: a branch role can only connect to its own clone, so that is it.
point_at() {
  local db=$1 upgrade=$2 user=$3 password=$4
  set_env_var .env.worktree DB_NAME "$db"
  set_env_var secrets/.env POSTGRES_DB "$db"
  set_env_var secrets/.env POSTGRES_MAINTENANCE_DB "$db"
  set_env_var secrets/.env POSTGRES_USER "$user"
  set_env_var secrets/.env POSTGRES_PASSWORD "$password"
  set_env_var secrets/.env DATABASE_UPGRADE "$upgrade"
}
# The admin login the shared DB is used with: the main checkout's credentials.
admin_password() { sed -n 's/^POSTGRES_PASSWORD=//p' "$(main_checkout)/secrets/.env" | head -1; }
# Nobody but the superuser and an explicit owner connects to the databases this
# script manages. Idempotent; skips databases that do not exist yet.
protect_shared() {
  local d
  for d in "$SHARED_DB" "$TEMPLATE_DB" "$LIGHT_TEMPLATE_DB" template1; do
    db_exists "$d" && psql_db -c "revoke connect on database $d from public" >/dev/null
  done
}
# Hand every object of the clone's public schema to the role. A clone copies its
# template's objects with their owner (the superuser), and alembic needs to own a
# table to ALTER it. REASSIGN OWNED cannot move objects away from the bootstrap
# superuser, hence the explicit loop.
chown_clone() {
  local db=$1 role=$2
  psql_db -d "$db" <<SQL >/dev/null
alter schema public owner to $role;
do \$\$
declare r record;
begin
  for r in
    select format('alter %s %I.%I owner to %I',
                  case c.relkind when 'S' then 'sequence' when 'v' then 'view'
                                 when 'm' then 'materialized view' else 'table' end,
                  n.nspname, c.relname, '$role') as q
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relkind in ('r', 'p', 'S', 'v', 'm')
      -- a serial's sequence follows its table and refuses its own ALTER
      and not exists (select 1 from pg_depend d where d.objid = c.oid and d.deptype = 'a')
  loop execute r.q; end loop;
  for r in
    select format('alter type %I.%I owner to %I', n.nspname, t.typname, '$role') as q
    from pg_type t join pg_namespace n on n.oid = t.typnamespace
    where n.nspname = 'public' and t.typtype in ('e', 'd')
  loop execute r.q; end loop;
  for r in
    select format('alter function %I.%I(%s) owner to %I',
                  n.nspname, p.proname, pg_get_function_identity_arguments(p.oid), '$role') as q
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
  loop execute r.q; end loop;
end \$\$;
SQL
}
restart_backend() {
  local s; s="$(session_name "$BRANCH")"
  tmux has-session -t "=$s" 2>/dev/null || return 0
  tmux send-keys -t "=$s:backend" C-c; sleep 1
  tmux send-keys -t "=$s:backend" 'set -a; . "$(git rev-parse --show-toplevel)/.env.worktree"; set +a; make dev' C-m
  echo "restarted backend window of $s"
}

case "${1:-status}" in
  template)
    container_up
    echo "==> rebuilding $TEMPLATE_DB from $SHARED_DB (copies ~3.4 GB — several minutes)"
    psql_db -c "drop database if exists $TEMPLATE_DB" -c "create database $TEMPLATE_DB"
    docker exec -i "$DB_CONTAINER" sh -c "pg_dump -U postgres $SHARED_DB | psql -q -v ON_ERROR_STOP=1 -U postgres $TEMPLATE_DB" >/dev/null
    protect_shared
    echo "template ready: $TEMPLATE_DB ($(psql_db -Atc "select pg_size_pretty(pg_database_size('$TEMPLATE_DB'))"))"
    ;;
  template-light)
    container_up
    [ -d "${RESSLAB_DATA_DIR:-$ROOT/../resslab-hub-data}" ] || die "no data repo at ${RESSLAB_DATA_DIR:-$ROOT/../resslab-hub-data}"
    echo "==> rebuilding $LIGHT_TEMPLATE_DB from the data repo (main CSVs + 1 measurement file per series type)"
    psql_db -c "select pg_terminate_backend(pid) from pg_stat_activity where datname='$LIGHT_TEMPLATE_DB'" \
            -c "drop database if exists $LIGHT_TEMPLATE_DB" \
            -c "create database $LIGHT_TEMPLATE_DB" >/dev/null
    # Exported env beats secrets/.env (dotenv never overrides the environment),
    # so the schema and upload land in the template, not this checkout's DB.
    # The template is built as the admin user: a worktree's own role could not
    # even connect to it.
    POSTGRES_DB="$LIGHT_TEMPLATE_DB" POSTGRES_USER=postgres POSTGRES_PASSWORD="$(admin_password)" make -C backend database-upgrade
    POSTGRES_DB="$LIGHT_TEMPLATE_DB" POSTGRES_USER=postgres POSTGRES_PASSWORD="$(admin_password)" make -C backend upload-data-light
    protect_shared
    echo "light template ready: $LIGHT_TEMPLATE_DB ($(psql_db -Atc "select pg_size_pretty(pg_database_size('$LIGHT_TEMPLATE_DB'))"))"
    ;;
  create)
    container_up
    in_worktree || die "clone a branch DB from a worktree, not the main checkout"
    if [ "${2:-}" = "full" ]; then
      SRC="$TEMPLATE_DB"
      db_exists "$SRC" || die "no $TEMPLATE_DB yet — run 'make db-template' once from the main checkout"
    elif db_exists "$LIGHT_TEMPLATE_DB"; then SRC="$LIGHT_TEMPLATE_DB"
    elif db_exists "$TEMPLATE_DB"; then SRC="$TEMPLATE_DB"
    else die "no template yet — run 'make db-template-light' once (or 'make db-template' for the full copy)"
    fi
    # A fresh password every time: it lives only in this worktree's secrets/.env,
    # and re-running `create` is how an older clone (owned by the superuser,
    # used with the admin login) is moved onto its own role.
    PASSWORD="$(random_password)"
    if role_exists "$ROLE"; then psql_db -c "alter role $ROLE with login createdb password '$PASSWORD'" >/dev/null
    else psql_db -c "create role $ROLE with login createdb password '$PASSWORD'" >/dev/null; echo "created role $ROLE"
    fi
    if db_exists "$CLONE"; then
      echo "$CLONE already exists"
      psql_db -c "alter database $CLONE owner to $ROLE" >/dev/null
    else
      psql_db -c "create database $CLONE template $SRC owner $ROLE" >/dev/null; echo "created $CLONE from $SRC"
    fi
    psql_db -c "revoke connect on database $CLONE from public" >/dev/null
    chown_clone "$CLONE" "$ROLE"
    protect_shared
    point_at "$CLONE" true "$ROLE" "$PASSWORD"
    restart_backend
    echo "this worktree now uses $CLONE as $ROLE; alembic upgrade runs when its backend starts"
    ;;
  drop)
    container_up
    { [ "$CLONE" != "$SHARED_DB" ] && [ "$CLONE" != "$TEMPLATE_DB" ] && [ "$CLONE" != "$LIGHT_TEMPLATE_DB" ]; } || die "refusing to drop $CLONE"
    for d in "$CLONE" "$TEST_CLONE"; do
      if db_exists "$d"; then
        psql_db -c "select pg_terminate_backend(pid) from pg_stat_activity where datname='$d'" -c "drop database $d" >/dev/null
        echo "dropped $d"
      fi
    done
    if role_exists "$ROLE"; then psql_db -c "drop role $ROLE" >/dev/null; echo "dropped role $ROLE"; fi
    point_at "$SHARED_DB" false postgres "$(admin_password)"
    restart_backend
    echo "this worktree is back on the shared $SHARED_DB as postgres (migrations off)"
    ;;
  status)
    echo "checkout: $ROOT ($BRANCH)"
    echo "database: ${DB_NAME:-$SHARED_DB} as $(sed -n 's/^POSTGRES_USER=//p' secrets/.env 2>/dev/null | head -1)"
    echo "clones:"
    psql_db -Atc "select d.datname || '  ' || pg_size_pretty(pg_database_size(d.datname)) || '  owner ' || r.rolname from pg_database d join pg_roles r on r.oid = d.datdba where d.datname like 'resslab_hub_%' order by 1" | sed 's/^/  /'
    ;;
  *) die "usage: wt-db.sh template-light|template|create [full]|drop|status" ;;
esac
