#!/usr/bin/env bash
# One command from branch name to a running, attached dev session:
#   scripts/wt-new.sh <branch> [base=stage]      (or: make new BRANCH=feat/x)
# wt create → .wt.toml hooks (deps, env, ports, detached tmux session) → attach.
# Detach with prefix+d; you land back where you started.
set -euo pipefail
SCRIPTS="$(dirname "$(readlink -f "$0")")"
. "$SCRIPTS/wt-lib.sh"
branch="${1:-}"; base="${2:-stage}"
[ -n "$branch" ] || die "usage: wt-new.sh <branch> [base]"
in_worktree && die "run wt-new from the main checkout: $(main_checkout)"
cd "$ROOT"
if [ -z "$(worktree_path_for "$branch")" ]; then
  wt create "$branch" "$base"
fi
path="$(worktree_path_for "$branch")"
[ -n "$path" ] || die "wt create did not produce a worktree for $branch"
ROOT="$path" exec "$SCRIPTS/tmux-dev.sh"    # session exists → attach (or switch-client inside tmux)
