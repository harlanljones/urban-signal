#!/usr/bin/env bash
# urban evidence recorder — post_tool_call on terminal.
# Appends compact command/cwd JSONL for later session context.
set -euo pipefail
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
payload="$(cat)"
printf '%s' "$payload" | jq -c '{ts:(now|todateiso8601),cmd:(.tool_input.command // ""),cwd:.cwd}' \
  >> "$HERMES_HOME/agent-hooks/urban-evidence.jsonl" 2>/dev/null || true
echo '{}'
