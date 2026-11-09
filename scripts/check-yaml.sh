#!/usr/bin/env bash
# Parse every yaml file given as argument and fail on the first broken one.
# Called by lefthook on staged files and by CI on every tracked yaml file.
# PyYAML comes from the backend dev dependencies, so it runs through uv.
# traefik.yaml is a Go template ({{ env ... }}), not plain yaml, so it is skipped.
set -euo pipefail
SKIP=(traefik.yaml)
root="$(git rev-parse --show-toplevel)"
files=()
for f in "$@"; do
  for s in "${SKIP[@]}"; do [ "$(realpath -m "$f")" = "$root/$s" ] && continue 2; done
  case "$f" in /*) files+=("$f") ;; *) files+=("$PWD/$f") ;; esac
done
[ "${#files[@]}" -gt 0 ] || exit 0
cd "$root/backend"
exec uv run --quiet python -c '
import sys, yaml
failed = 0
for path in sys.argv[1:]:
    try:
        with open(path, encoding="utf-8") as f:
            for _ in yaml.safe_load_all(f):
                pass
    except Exception as e:
        print(f"check-yaml: {path}: {e}", file=sys.stderr)
        failed = 1
sys.exit(failed)
' "${files[@]}"
