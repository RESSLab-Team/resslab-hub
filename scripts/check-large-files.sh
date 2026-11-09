#!/usr/bin/env bash
# Refuse files over MAX_KB (500 kB, the pre-commit default). Called by lefthook
# on staged files and by CI on every tracked file. The few big files we know
# about are allowed below. Skip one commit with LEFTHOOK=0 git commit ...
set -euo pipefail
MAX_KB=500
ALLOWED=(
  backend/uv.lock
  frontend/src/backend/api.ts
  frontend/public/video/steel-mrf-front-page.mp4
)
failed=0
for f in "$@"; do
  [ -f "$f" ] || continue
  for a in "${ALLOWED[@]}"; do [ "$f" = "$a" ] && continue 2; done
  kb=$(( $(wc -c < "$f") / 1024 ))
  if [ "$kb" -gt "$MAX_KB" ]; then
    echo "check-large-files: $f is $kb kB (limit $MAX_KB kB)" >&2
    failed=1
  fi
done
if [ "$failed" -ne 0 ]; then
  echo "check-large-files: add the file to ALLOWED in scripts/check-large-files.sh if it must be committed" >&2
fi
exit "$failed"
