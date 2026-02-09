# Hooks System

Hooks allow you to intercept and modify Claude Code's behavior at key lifecycle points.

## Hook Types

- **PreToolUse**: Before tool execution (validation, parameter modification)
- **PostToolUse**: After tool execution (auto-format, checks)
- **SessionStart**: When a new session begins
- **PreCompact**: Before context compression
- **Stop**: When session ends (final verification)

## Hook Structure

Each hook requires:
- **matcher**: Pattern to match (e.g., `tool == "Bash"` or `*` for all)
- **command**: Bash script (inline or file path)
- **description**: What the hook does

## Common Patterns

### Input/Output Flow
Hooks receive JSON via stdin and must output JSON to stdout:
```bash
#!/bin/bash
input=$(cat)
# Process input
echo "$input"
```

### Extracting Parameters
```bash
cmd=$(echo "$input" | jq -r '.tool_input.command')
file=$(echo "$input" | jq -r '.tool_input.file_path')
```

### Blocking Execution
Exit with non-zero status to prevent tool execution:
```bash
echo "[Hook] BLOCKED: reason" >&2
exit 1
```

### Logging
Send messages to stderr (shown to user):
```bash
echo "[Hook] Info message" >&2
```

## Example Use Cases

- Validate commands before execution
- Auto-format files after edits
- Block unsafe operations
- Log important events
- Save/restore session state
