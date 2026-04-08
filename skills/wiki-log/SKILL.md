---
name: wiki-log
description: Append-only operation log at .claude/log.md tracking vault ingests, queries, and lint runs. Use when you need to log, record, or track ingest/query/lint operations against the vault.
---

# Wiki Log — Append-Only Vault Operation Log

Append structured log entries to `.claude/log.md` (relative to vault root) for ingest, query, and lint operations.

## Input

`$ARGUMENTS` — `<operation> <key=value pairs...> [--vault PATH]`

- **operation**: One of `ingest`, `query`, `lint` (unknown types logged with a warning)
- **key=value pairs**: Metadata fields. Quote values containing spaces: `title="My Note Title"`
- **--vault PATH**: Vault root (default: `/Users/jason/Developer/obsidian/CS`)

### Examples

```
ingest title="AI-LLM-Wiki-Pattern" source="https://example.com/article" output="333.ai/workflow/AI-LLM-Wiki-Pattern.md" mocs="0.7.AI_Map.md" links="AI-Rag-Map,AI-Workflow-Patterns" cross-updates="none"

query question="How does RAG compare to wiki?" searched=5 result="333.ai/workflow/AI-RAG-Vs-Wiki.md"

lint path="333.ai/" scanned=20 contradictions=1 orphans=2 missing-pages=3
```

## Execution

### Step 1: Parse Arguments

Parse `$ARGUMENTS` into:
1. **operation** — first token (e.g., `ingest`, `query`, `lint`)
2. **metadata** — remaining tokens as key=value pairs into a dictionary

If no arguments provided → report error: "Usage: wiki-log <operation> <key=value ...>"

If operation is not one of `ingest`, `query`, `lint` → log it anyway but prepend a warning line:
```
> ⚠ Unknown operation type: {operation}
```

### Step 2: Determine Title

Extract display title from metadata based on operation type:
- `ingest` → use `title` field
- `query` → use `question` field
- `lint` → use `path` field
- Other → use first metadata value, or operation name if no metadata

### Step 3: Get Today's Date

Use ISO format: `YYYY-MM-DD` (e.g., `2026-04-08`)

### Step 4: Read or Create Log File

Read `.claude/log.md` from vault root.

If file does not exist, create it with this initial content:
```markdown
# Vault Log
```

### Step 5: Check for Duplicates

Scan the last entry in the log. If the last entry has the **same date AND same title** in its heading, skip the append and report:
```
⏭ Duplicate entry — already logged: [<date>] <operation> | <title>
```

### Step 6: Format and Append Entry

Build the entry block:

```markdown

## [<date>] <operation> | <title>
- key1: value1
- key2: value2
- key3: value3
```

Rules:
- Skip the key used as title from the bullet list (avoid redundancy)
- Replace empty or `"none"` values with `(none)`
- Preserve key order from the original arguments

Append the block to the end of `.claude/log.md`.

### Step 7: Write File and Report

Write the updated file. Report:

```
✅ Logged: [<date>] <operation> | <title>
📄 File: .claude/log.md
```

## Output

- Updated `.claude/log.md` with the new entry appended
- Confirmation message with date, operation, and title

## Edge Cases

**No arguments provided:**
- Report usage error, do not touch the log file

**Log file doesn't exist:**
- Create `.claude/log.md` with `# Vault Log` header, then append the entry

**Duplicate entry (same date + title):**
- Skip append, report duplicate

**Unknown operation type:**
- Log with warning prefix, do not reject

**Values containing commas or spaces:**
- Values are kept as-is after parsing quoted strings

**Empty metadata (just operation, no key=value):**
- Log the operation with only the heading, no bullet list
