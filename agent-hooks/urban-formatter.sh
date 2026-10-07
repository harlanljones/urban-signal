#!/usr/bin/env bash
# urban formatter — post_tool_call on write_file|patch.
# Runs only formatters already installed in this checkout; otherwise no-ops.
set -euo pipefail
payload="$(cat)"
file="$(printf '%s' "$payload" | jq -r '.tool_input.path // .tool_input.file_path // empty')"
[ -z "$file" ] || [ ! -f "$file" ] && { echo '{}'; exit 0; }

case "$file" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then ruff format "$file" >/dev/null 2>&1 || true; fi
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.json)
    d="$(dirname "$file")"
    root=""
    while [ "$d" != "/" ]; do
      if [ -f "$d/package.json" ] && [ -d "$d/node_modules" ]; then root="$d"; break; fi
      d="$(dirname "$d")"
    done
    if [ -n "$root" ] && [ -x "$root/node_modules/.bin/prettier" ]; then
      (cd "$root" && node_modules/.bin/prettier --write --log-level warn "$file" >/dev/null 2>&1) || true
    elif [ -n "$root" ] && [ -x "$root/node_modules/.bin/biome" ]; then
      (cd "$root" && node_modules/.bin/biome check --write "$file" >/dev/null 2>&1) || true
    fi
    ;;
esac
echo '{}'
