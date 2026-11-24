#!/usr/bin/env bash
# Make a fresh worktree runnable: seed gitignored dev files from the main checkout,
# allocate ports, isolate its DB settings, write Claude Code's sandbox settings,
# install deps + git hooks, and open its tmux dev session.
# Idempotent on purpose: wt runs it from post_create AND post_checkout (some wt
# builds fire both on create), and you can re-run it by hand to refresh.
#   scripts/wt-setup.sh          from inside a worktree
#   (wt hooks call it with WT_PATH / WT_BRANCH exported)
#   scripts/wt-setup.sh --wtx    from wtx.toml's post_setup: wtx already wrote the
#                                ports, agent settings, deps and tmux session, so
#                                only the seeds, the DB and secrets/.env are done
set -euo pipefail
WTX=""; [ "${1:-}" = "--wtx" ] && WTX=yes
ROOT="${WT_PATH:-$(git rev-parse --show-toplevel)}"
SCRIPTS="$(dirname "$(readlink -f "$0")")"
. "$SCRIPTS/wt-lib.sh"
MAIN="$(main_checkout)"   # not $WT_MAIN: wt points that at whichever worktree holds `dev`
BRANCH="${WT_BRANCH:-$(current_branch)}"
cd "$ROOT"
[ "$ROOT" != "$MAIN" ] || die "run from a worktree, not the main checkout"
# Prefer the branch's own copy of the tooling; fall back to the main checkout's for
# branches that predate it.
tooling() { [ -f "$ROOT/scripts/$1" ] && echo "$ROOT/scripts/$1" || echo "$MAIN/scripts/$1"; }

echo "==> worktree $ROOT ($BRANCH)"

# 0. Tracking. `wt create <branch> origin/dev` cuts the branch from a
#    remote-tracking ref, and git's default autoSetupMerge then points the new
#    branch's upstream at origin/dev. `git pull` there rebases the branch onto
#    dev instead of fetching its own commits, the next push is refused as
#    non-fast-forward, and `git pull` still answers "up to date" because it is
#    comparing against dev. That happened on perf/improve-github-contribution
#    and left its HEAD detached. `simple` only tracks a remote branch of the
#    same name, and push.autoSetupRemote sets the upstream on the first push,
#    so a new branch gets the right one or none at all. Repo-wide config, but
#    written here so every checkout of this repo gets it.
git config branch.autoSetupMerge simple || echo "note: could not set branch.autoSetupMerge"
git config push.autoSetupRemote true || echo "note: could not set push.autoSetupRemote"
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  git branch --set-upstream-to="origin/$BRANCH" "$BRANCH" >/dev/null 2>&1 ||
    echo "note: could not track origin/$BRANCH"
elif [ "$(git config --get "branch.$BRANCH.merge" || true)" != "refs/heads/$BRANCH" ]; then
  # Not pushed yet: no upstream at all beats one pointing at another branch.
  git branch --unset-upstream "$BRANCH" >/dev/null 2>&1 || true
fi

# 1. Gitignored dev files aren't in the branch; the main checkout's copies on disk
#    are the right source whatever it has checked out. Never overwrite.
for f in secrets/.env docker-compose.override.yml frontend/.env.development.local; do
  if [ ! -e "$f" ] && [ -e "$MAIN/$f" ]; then
    mkdir -p "$(dirname "$f")"; cp "$MAIN/$f" "$f"; echo "seeded $f"
  fi
done
[ -f secrets/.env ] || die "no secrets/.env in $MAIN to seed from — create it first (README > Secrets)"

# 1b. Sample contribution batches. The CSVs are generated and untracked
#     (sample-data/.gitignore), but the contribution flow wants drop-in test
#     data, so a worktree without them is less useful. Copy only the generated batch folders: the top-level files
#     (generate.py, README.md) are tracked and belong to the branch.
if ! find sample-data -name '*.csv' -print -quit 2>/dev/null | grep -q .; then
  found=""
  for d in "$MAIN"/sample-data/*/; do
    if [ -d "$d" ]; then cp -r "$d" sample-data/; found=yes; fi
  done
  if [ -n "$found" ]; then
    echo "seeded sample-data/ from $MAIN"
  else
    echo "note: no generated sample-data in $MAIN; run 'make sample-data' (here or there) if you need it"
  fi
fi

# 2. Ports and names. A previous run may have picked ports (the servers in the
#    session listen on them, and the hash input has changed once already) and
#    cloned a branch DB: keep both. A fresh worktree gets the hashed pair, or
#    the next free one (branch_ports in wt-lib.sh).
prev_backend=""; prev_frontend=""; prev_db=""
if [ -f .env.worktree ]; then
  prev_backend="$(sed -n 's/^BACKEND_PORT=//p' .env.worktree | head -1)"
  prev_frontend="$(sed -n 's/^FRONTEND_PORT=//p' .env.worktree | head -1)"
  prev_db="$(sed -n 's/^DB_NAME=//p' .env.worktree | head -1)"
fi
if [ -n "$WTX" ]; then
  BACKEND_PORT="$prev_backend"; FRONTEND_PORT="$prev_frontend"   # wtx picked them
elif [ -n "$prev_backend" ] && [ -n "$prev_frontend" ]; then
  BACKEND_PORT="$prev_backend"; FRONTEND_PORT="$prev_frontend"
else
  branch_ports "$BRANCH"
fi
SLUG="$(slug "$BRANCH")"
DB_NAME="${prev_db:-$SHARED_DB}"
DATA_DIR="$(readlink -f "$MAIN/../resslab-hub-data" 2>/dev/null || echo "$MAIN/../resslab-hub-data")"
if [ -n "$WTX" ]; then
  # wtx owns this file: add our keys, never rewrite it.
  set_env_var .env.worktree WT_SLUG "$SLUG"
  set_env_var .env.worktree DB_NAME "$DB_NAME"
  set_env_var .env.worktree POSTGRES_TEST_DB "resslab_hub_test_$SLUG"
  set_env_var .env.worktree RESSLAB_DATA_DIR "$DATA_DIR"
else
cat > .env.worktree <<ENV
# Generated by scripts/wt-setup.sh — this worktree's private settings (gitignored).
# tmux-dev.sh exports these in every window; re-run wt-setup.sh to refresh.
WT_BRANCH=$BRANCH
WT_SLUG=$SLUG
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
DB_NAME=$DB_NAME
POSTGRES_TEST_DB=resslab_hub_test_$SLUG
RESSLAB_DATA_DIR=$DATA_DIR
ENV
fi
echo "ports: backend $BACKEND_PORT, frontend $FRONTEND_PORT; database: $DB_NAME"

# 3. This frontend talks to this backend through the Vite proxy, which reads
#    BACKEND_PORT from .env.worktree (same-origin, no CORS layer: the session
#    cookie must be first-party, see docs/src/auth.md). An absolute
#    VITE_APP_BACKEND_URL seeded from an older main checkout would send the
#    browser to the backend port directly and break sign-in, so drop it.
if [ -f frontend/.env.development.local ]; then
  sed -i '/^VITE_APP_BACKEND_URL=/d' frontend/.env.development.local
fi
#    This backend talks to the right DB and never migrates the shared one
#    (wt-db.sh create flips DATABASE_UPGRADE on).
set_env_var secrets/.env POSTGRES_DB "$DB_NAME"
set_env_var secrets/.env POSTGRES_MAINTENANCE_DB "$DB_NAME"
set_env_var secrets/.env POSTGRES_TEST_DB "resslab_hub_test_$SLUG"
if [ "$DB_NAME" = "$SHARED_DB" ]; then set_env_var secrets/.env DATABASE_UPGRADE false
else set_env_var secrets/.env DATABASE_UPGRADE true; fi

# 3c. Local submissions go to the test fork, never the real data repo (#382):
#     every test pull request on the real one had to be closed by hand. The App
#     installation id is per org, and the one seeded from the main checkout is
#     the RESSLab-Team one, so the fork needs its own (the App's install on
#     EPFL-ENAC). It is a plain number, useless without the private key, so it
#     can live here. DATA_REPO is only set when absent, so a human can point a
#     checkout elsewhere; the id follows only when DATA_REPO is the fork.
TEST_DATA_REPO=EPFL-ENAC/resslab-hub-data-test
TEST_DATA_REPO_INSTALLATION_ID=170990591
set_env_default secrets/.env DATA_REPO "$TEST_DATA_REPO"
if grep -qxE "DATA_REPO=\"?$TEST_DATA_REPO\"?" secrets/.env; then
  set_env_var secrets/.env GITHUB_APP_INSTALLATION_ID "$TEST_DATA_REPO_INSTALLATION_ID"
  # Each PR asks the repo admins for a review (#266). On the fork that is
  # nine EPFL-ENAC people for every test submit, so ask nobody by default.
  # Put your own login there to test the review request.
  set_env_default secrets/.env DATA_REPO_REVIEWERS none
  echo "contributions: pull requests go to $TEST_DATA_REPO"
else
  echo "note: DATA_REPO in secrets/.env is not the test fork, kept as is"
fi

# 3b. Own throwaway database: clone the ~20 MB light template (sub-second) so
#     this worktree can migrate, upload, or break its DB without touching the
#     shared dataset. The clone comes with its own Postgres role, whose login
#     replaces the admin one seeded from the main checkout above, so nothing in
#     this worktree can reach another database. Best-effort: without the
#     container or a template we stay on the shared DB as the admin user and say
#     so; `make db-branch` retries later.
if [ "$DB_NAME" = "$SHARED_DB" ]; then
  if ROOT="$ROOT" "$(tooling wt-db.sh)" create; then :
  else echo "note: staying on the shared $SHARED_DB — build the light template once with 'make db-template-light', then run 'make db-branch' here"
  fi
fi

# Under wtx, steps 4 to 6 are its own (agent settings, deps, session).
[ -z "$WTX" ] || exit 0

# 4. Claude Code runs sandboxed here with the ask/deny rules from the template.
#    .claude/ is gitignored, so the worktree's copy never reaches a commit.
#    Always read the template from the main checkout, not the branch: a branch
#    forked before a template fix would otherwise write the old rules back (that
#    is how two worktrees got the `python3 -` ask rule after it was removed),
#    and a feature branch should not be able to change Claude's permissions.
#    Not fatal: a re-run from inside a sandboxed agent cannot write this file
#    (Claude blocks an agent editing its own permissions), and in that case the
#    file is already there. Rendered to a temp file first so a refused write
#    cannot leave a truncated one behind.
mkdir -p .claude
if sed "s|__RESSLAB_DATA_DIR__|$DATA_DIR|g" "$MAIN/scripts/claude-worktree-settings.json" > .claude/settings.local.json.tmp 2>/dev/null &&
   mv .claude/settings.local.json.tmp .claude/settings.local.json 2>/dev/null; then
  echo "wrote .claude/settings.local.json"
else
  rm -f .claude/settings.local.json.tmp
  echo "note: could not write .claude/settings.local.json (kept the existing one; re-run wt-setup.sh from a terminal to refresh it)"
fi

# 5. Dependencies (skipped when already present) and lefthook, which refuses
#    commits from a checkout where it isn't installed.
if [ ! -d node_modules ] || [ ! -d frontend/node_modules ] || [ ! -d backend/.venv ]; then make install; fi
make hooks

# 6. Detached tmux session "<repo>/<branch>"; switch to it with prefix+s.
ROOT="$ROOT" "$(tooling tmux-dev.sh)" --no-attach   # ROOT: the script may be the main checkout's copy
