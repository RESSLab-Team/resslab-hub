#!/usr/bin/env bash
# Reset the test fork's main to the real data repo's main (#382).
# Local setups open their contribution pull requests on the fork, and merging
# them there is fine, so its main drifts from the real one. This puts it back.
# Needs gh signed in with push rights on EPFL-ENAC. Deletes nothing else: it
# only lists the pull requests and contrib/* branches still open on the fork.
set -euo pipefail
REAL=RESSLab-Team/resslab-hub-data
FORK=EPFL-ENAC/resslab-hub-data-test

real_sha="$(gh api "repos/$REAL/commits/main" -q .sha)"
fork_sha="$(gh api "repos/$FORK/commits/main" -q .sha)"
if [ "$real_sha" = "$fork_sha" ]; then
  echo "$FORK main is already at $REAL main ($real_sha)"
else
  gh api -X PATCH "repos/$FORK/git/refs/heads/main" -f sha="$real_sha" -F force=true >/dev/null
  echo "$FORK main: $fork_sha -> $real_sha"
fi

echo
echo "open pull requests on $FORK:"
gh pr list -R "$FORK" --state open --json number,title,headRefName \
  -q '.[] | "  #\(.number) \(.headRefName) \(.title)"'
echo "contrib/* branches on $FORK (delete with: gh api -X DELETE repos/$FORK/git/refs/heads/<branch>):"
gh api --paginate "repos/$FORK/branches" -q '.[].name | select(startswith("contrib/")) | "  " + .'
