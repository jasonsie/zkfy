#!/usr/bin/env bash
# signal-index-update.sh
# PostToolUse hook: detect if a .md file was written inside a zkfied vault,
# and emit a reminder signal to update the vault index.
#
# A "zkfied vault" is detected by walking up the file path looking for a
# .claude/ sibling directory — structure-based, not path-based.
#
# Input (stdin): Claude Code PostToolUse event JSON
# Output: JSON signal if in a zkfied vault, or empty (no-op) otherwise

set -euo pipefail

# Read the tool event from stdin
EVENT=$(cat)

# Extract the file path from the tool input
FILE_PATH=$(echo "$EVENT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null)

# Only proceed if we got a file path and it's a .md file
if [[ -z "$FILE_PATH" || "${FILE_PATH##*.}" != "md" ]]; then
    exit 0
fi

# Walk up the directory tree looking for a .claude/ sibling
# This detects a zkfied vault without hardcoding any paths
SEARCH_DIR=$(dirname "$FILE_PATH")
VAULT_ROOT=""

while [[ "$SEARCH_DIR" != "/" && "$SEARCH_DIR" != "." ]]; do
    if [[ -d "$SEARCH_DIR/.claude" ]]; then
        VAULT_ROOT="$SEARCH_DIR"
        break
    fi
    SEARCH_DIR=$(dirname "$SEARCH_DIR")
done

# Also check root-level .claude
if [[ -z "$VAULT_ROOT" && -d "$SEARCH_DIR/.claude" ]]; then
    VAULT_ROOT="$SEARCH_DIR"
fi

# If no zkfied vault found, exit silently (no-op)
if [[ -z "$VAULT_ROOT" ]]; then
    exit 0
fi

# Skip files in excluded directories (not actual notes)
EXCLUDED_PATTERNS="y.template|/row/|/x.temp/|/docs/|/.obsidian/|/.claude/|/.agents/|/.prompts/|/.github/|/.instructions/|000.Index"
if echo "$FILE_PATH" | grep -qE "$EXCLUDED_PATTERNS"; then
    exit 0
fi

# Emit a reminder signal for the LLM to update the vault index
python3 -c "
import json, sys
signal = {
    'index_update_needed': True,
    'note_path': sys.argv[1],
    'vault_root': sys.argv[2],
    'reminder': 'Run vault-index --append <note_path> to keep .claude/index.md current'
}
print(json.dumps(signal))
" "$FILE_PATH" "$VAULT_ROOT"
