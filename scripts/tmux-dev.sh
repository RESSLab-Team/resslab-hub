#!/usr/bin/env bash
# One tmux session per checkout, named "<repo>/<branch>", one window with four
# titled panes: claude (left half), backend (uvicorn), frontend (vite), shell
# stacked on the right. Ports come from .env.worktree
# (written by wt-setup.sh); the main checkout keeps 8000/5173.
#   scripts/tmux-dev.sh              create the session for this checkout, or attach if it exists
#   scripts/tmux-dev.sh --no-attach  create it detached (what the wt hook does)
set -euo pipefail
SCRIPTS="$(dirname "$(readlink -f "$0")")"
. "$SCRIPTS/wt-lib.sh"
# ROOT arrives exported from wt-new.sh / wt-setup.sh; wt-lib has read it, so drop
# the export before any tmux command. If this command is the one that starts the
# tmux server, an exported ROOT becomes part of the server's environment, every
# shell in every pane inherits it, and any wt script run from those shells then
# targets this checkout no matter what directory it is run from. The
# set-environment call scrubs a server that an earlier version already poisoned.
export -n ROOT || true
tmux set-environment -gu ROOT 2>/dev/null || true
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

# Every pane exports .env.worktree so pytest (POSTGRES_TEST_DB), the Makefiles
# (BACKEND_PORT, RESSLAB_DATA_DIR) and vite (FRONTEND_PORT) all see the same values.
LOAD='set -a; [ -f "$(git rev-parse --show-toplevel)/.env.worktree" ] && . "$(git rev-parse --show-toplevel)/.env.worktree"; set +a'
# Mirror the server panes' output to plain files: the claude pane's agent runs
# sandboxed with no access to the tmux socket, so log files inside the checkout
# are the only way it can see why a server misbehaves. Fresh per session.
LOGS="$ROOT/.wt-logs"; mkdir -p "$LOGS"
pipe_log() { : > "$LOGS/$1.log"; tmux pipe-pane -t "$2" -o "exec cat >> '$LOGS/$1.log'"; }

# One window, four titled panes: claude fills the left half; the right half
# stacks backend / frontend / shell. prefix+arrows move between panes, prefix+z
# zooms one to full screen, and the prefix+s / prefix+w previews show the whole
# layout at a glance. claude has focus when you attach.
tmux new-session -d -s "$SESSION" -n dev -c "$ROOT"
P_CLAUDE="$(tmux display-message -p -t "=$SESSION:dev" '#{pane_id}')"
P_BACKEND="$(tmux split-window -h -l 50% -P -F '#{pane_id}' -t "$P_CLAUDE" -c "$ROOT/backend")"
P_FRONTEND="$(tmux split-window -v -l 67% -P -F '#{pane_id}' -t "$P_BACKEND" -c "$ROOT/frontend")"
P_SHELL="$(tmux split-window -v -l 50% -P -F '#{pane_id}' -t "$P_FRONTEND" -c "$ROOT")"
tmux select-pane -t "$P_CLAUDE" -T claude
tmux select-pane -t "$P_BACKEND" -T backend
tmux select-pane -t "$P_FRONTEND" -T frontend
tmux select-pane -t "$P_SHELL" -T shell
tmux set-option -w -t "=$SESSION:dev" pane-border-status top

tmux send-keys -t "$P_BACKEND" "$LOAD; make dev" C-m
pipe_log backend "$P_BACKEND"
tmux send-keys -t "$P_FRONTEND" "$LOAD; make dev" C-m
pipe_log frontend "$P_FRONTEND"
# Resume the checkout's last agent conversation when there is one (a recreated
# session picks up where its agent left off); a fresh worktree has none, the
# flag exits nonzero, and a new conversation starts instead.
tmux send-keys -t "$P_CLAUDE" "$LOAD; claude --continue || claude" C-m
tmux send-keys -t "$P_SHELL" "$LOAD; clear" C-m
tmux select-pane -t "$P_CLAUDE"

print_urls
attach
