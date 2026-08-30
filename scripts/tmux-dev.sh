#!/usr/bin/env bash
# One tmux session per checkout, named "<repo>/<branch>", with four windows:
# backend (uvicorn), frontend (vite), claude, shell. Ports come from .env.worktree
# (written by wt-setup.sh); the main checkout keeps 8000/5173.
#   scripts/tmux-dev.sh              create the session for this checkout, or attach if it exists
#   scripts/tmux-dev.sh --no-attach  create it detached (what the wt hook does)
set -euo pipefail
SCRIPTS="$(dirname "$(readlink -f "$0")")"
. "$SCRIPTS/wt-lib.sh"
load_env_worktree
BRANCH="$(current_branch)"
SESSION="$(session_name "$BRANCH")"
MAIN="$(main_checkout)"
ATTACH=1; [ "${1:-}" = "--no-attach" ] && ATTACH=0

attach() {
  [ "$ATTACH" = 1 ] || return 0
  if [ -n "${TMUX:-}" ]; then tmux switch-client -t "=$SESSION"; else tmux attach-session -t "=$SESSION"; fi
}
print_urls() {
  cat <<URLS
session : $SESSION   (prefix+s to switch)
frontend: http://localhost:$FRONTEND_PORT/
backend : http://127.0.0.1:$BACKEND_PORT/docs
database: $DB_CONTAINER / ${DB_NAME:-$SHARED_DB}
URLS
}

if tmux has-session -t "=$SESSION" 2>/dev/null; then print_urls; attach; exit 0; fi

# One shared Postgres container for every checkout. Always start it from the main
# checkout: compose names its project after the directory, so running it from a
# worktree would create a second project fighting for the same host port.
docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER" || (cd "$MAIN" && docker compose up -d database)

# Every window exports .env.worktree so pytest (POSTGRES_TEST_DB), the Makefiles
# (BACKEND_PORT, RESSLAB_DATA_DIR) and vite (FRONTEND_PORT) all see the same values.
LOAD='set -a; [ -f "$(git rev-parse --show-toplevel)/.env.worktree" ] && . "$(git rev-parse --show-toplevel)/.env.worktree"; set +a'
tmux new-session -d -s "$SESSION" -n backend -c "$ROOT/backend"
tmux send-keys -t "=$SESSION:backend" "$LOAD; make dev" C-m
tmux new-window -t "=$SESSION" -n frontend -c "$ROOT/frontend"
tmux send-keys -t "=$SESSION:frontend" "$LOAD; make dev" C-m
tmux new-window -t "=$SESSION" -n claude -c "$ROOT"
tmux send-keys -t "=$SESSION:claude" "$LOAD; claude" C-m
tmux new-window -t "=$SESSION" -n shell -c "$ROOT"
tmux send-keys -t "=$SESSION:shell" "$LOAD; clear" C-m
tmux select-window -t "=$SESSION:shell"

print_urls
attach
