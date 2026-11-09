#!/usr/bin/env bash
# PostToolUse: after a note is written in a zkfied vault, remind the agent to keep the generated
# catalog current. A configured vault (docs/knowledge/scope.json above the note) decides through
# scripts/knowledge-hook.py; elsewhere a vault is a folder with a .claude/ sibling, found by
# walking up from the file. Nothing is written here.
#
# Two input shapes on stdin, told apart by the toolCall key:
#   Claude Code, Codex and Pi's extension (extensions/zkfy.ts): {tool_input: {file_path}}.
#     Output: Claude Code's PostToolUse JSON (hookSpecificOutput.additionalContext) or nothing.
#   Antigravity: {toolCall: {args: {TargetFile}}}. Output: {}, the only answer its PostToolUse
#     takes, so the reminder goes to stderr; validate-zk-structure.sh carries it to the agent on
#     the preceding PreToolUse instead.
set -euo pipefail

EVENT=$(cat)
HERE=$(cd "$(dirname "$0")" && pwd)

if printf '%s' "$EVENT" | jq -e '.toolCall' >/dev/null 2>&1; then
  CLI=agy
  FILE_PATH=$(printf '%s' "$EVENT" | jq -r '.toolCall.args.TargetFile // empty')
else
  CLI=claude
  FILE_PATH=$(printf '%s' "$EVENT" | jq -r '.tool_input.file_path // empty')
fi

finish() {  # $1: the signal JSON (index_update_needed, note_path, reminder), or nothing
  if [[ -n "${1:-}" ]]; then
    text=$(printf '%s' "$1" | jq -r '[(.reminder // empty), (.note_path // empty | "Note: " + .)] | join(" ")')
    if [[ "$CLI" == agy ]]; then
      printf 'zkfy: %s\n' "$text" >&2
    else
      jq -n -c --arg text "zkfy: $text" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $text}}'
    fi
  fi
  [[ "$CLI" == agy ]] && echo '{}'
  exit 0
}

[[ -n "$FILE_PATH" && "${FILE_PATH##*.}" == "md" ]] || finish

# Scoped vaults use the shared positive allowlist, including maps. No source scans.
if SIGNAL=$(python3 -B "$HERE/../scripts/knowledge-hook.py" index "$FILE_PATH"); then
  finish "$SIGNAL"
else
  status=$?
  if [[ "$status" != 3 ]]; then
    printf '%s\n' 'zkfy: scoped hook runtime unavailable; reminder skipped.' >&2
    finish
  fi
fi

# Walk up the directory tree looking for a .claude/ sibling: a zkfied vault, without any hardcoded path
SEARCH_DIR=$(dirname "$FILE_PATH")
VAULT_ROOT=""
while [[ "$SEARCH_DIR" != "/" && "$SEARCH_DIR" != "." ]]; do
  if [[ -d "$SEARCH_DIR/.claude" ]]; then
    VAULT_ROOT="$SEARCH_DIR"
    break
  fi
  SEARCH_DIR=$(dirname "$SEARCH_DIR")
done
if [[ -z "$VAULT_ROOT" && -d "$SEARCH_DIR/.claude" ]]; then
  VAULT_ROOT="$SEARCH_DIR"
fi
[[ -n "$VAULT_ROOT" ]] || finish

# Files in excluded directories are not notes
EXCLUDED_PATTERNS="y.template|/raw/|/row/|/x.temp/|/docs/|/.obsidian/|/.claude/|/.agents/|/.prompts/|/.github/|/.instructions/|000.Index"
if printf '%s' "$FILE_PATH" | grep -qE "$EXCLUDED_PATTERNS"; then
  finish
fi

finish "$(jq -n -c --arg path "$FILE_PATH" --arg root "$VAULT_ROOT" \
  '{index_update_needed: true, note_path: $path, vault_root: $root, reminder: "Run vault-knowledge lint, then vault-knowledge build, to keep the generated catalog current"}')"
