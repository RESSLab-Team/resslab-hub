#!/usr/bin/env bash
# One command from branch name to a running, attached dev session:
#   scripts/wt-new.sh <branch> [base=origin/dev]      (or: make new BRANCH=feat/x)
# wt create → .wt.toml hooks (deps, env, ports, detached tmux session) → attach.
# Detach with prefix+d; you land back where you started.
set -euo pipefail
SCRIPTS="$(dirname "$(readlink -f "$0")")"
. "$SCRIPTS/wt-lib.sh"
branch="${1:-}"; base="${2:-origin/dev}"
[ -n "$branch" ] || die "usage: wt-new.sh <branch> [base]"
# Work against the main checkout wherever this runs from — a worktree cwd, or a
# shell whose environment carries a stale ROOT from an old tmux session.
ROOT="$(main_checkout)"
cd "$ROOT"
if [ -z "$(worktree_path_for "$branch")" ]; then
  # A local ref can silently be stale (a branch cut from it then lacks recent
  # fixes); refresh the remote ones so the origin/dev default is current.
  case "$base" in origin/*) git fetch --quiet origin "${base#origin/}" || echo "warning: fetch failed, using cached $base";; esac
  wt create "$branch" "$base"
fi
path="$(worktree_path_for "$branch")"
[ -n "$path" ] || die "wt create did not produce a worktree for $branch"
ROOT="$path" exec "$SCRIPTS/tmux-dev.sh"    # session exists → attach (or switch-client inside tmux)
