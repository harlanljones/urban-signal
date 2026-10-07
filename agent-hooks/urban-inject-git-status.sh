#!/usr/bin/env bash
# urban pre_llm_call injector — injects Git status only for this repository.
set -euo pipefail
payload="$(cat)"
cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty')"
[ -z "$cwd" ] && { echo '{}'; exit 0; }

inside=""
d="$cwd"
while [ "$d" != "/" ]; do
  if git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    remote="$(git -C "$d" remote get-url origin 2>/dev/null || true)"
    if [[ "$remote" == *"github.com/harlanljones/urban-signal"* ]]; then
      inside="$d"
      break
    fi
  fi
  d="$(dirname "$d")"
done
[ -z "$inside" ] && { echo '{}'; exit 0; }

branch="$(git -C "$inside" symbolic-ref --short HEAD 2>/dev/null || git -C "$inside" rev-parse --short HEAD 2>/dev/null || echo unknown)"
status="$(git -C "$inside" status --porcelain 2>/dev/null || true)"
out="repo: $inside | branch: $branch"
if [ -n "$status" ]; then
  status="$(printf '%s\n' "$status" | awk 'NR <= 20')"
  out="$out
dirty files:
$status"
else
  out="$out | working tree clean"
fi
jq -n --arg c "$out" '{context:$c}'
