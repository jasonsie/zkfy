---
name: vault-index
description: Auto-maintained vault catalog at .claude/index.md grouping all notes by domain with abstracts and tags. Use when you need to rebuild index, update index, or generate a vault catalog.
---

# Vault Index — Auto-Maintained Note Catalog

Generate and maintain `.claude/index.md` (relative to vault root) — a structured catalog of all Zettelkasten notes grouped by domain.

## Input

`$ARGUMENTS` — `[--full | --append <note-path>] [--vault PATH]`

- **--full**: Full rebuild by scanning the entire vault
- **--append \<path\>**: Incremental — add or update a single note entry
- **--vault PATH**: Vault root (default: `/Users/jason/Developer/obsidian/CS`)

If no flag provided, default to `--full`.

## Output Format

`.claude/index.md` follows this structure:

```markdown
# Vault Index
Generated: 2026-04-08 | Notes: 317 | Domains: 7

## cs (142 notes)
- [[CS-Algorithm-Backtracking]] — Backtracking pattern for constraint satisfaction (algorithm, backtracking)
- [[CS-Binary-Search-Tree]] — BST operations and balancing (data-structure, tree)

## web (89 notes)
- [[Web-React-Hooks]] — React hook patterns and lifecycle (react, hooks)

## ai (45 notes)
- [[AI-Multi-Agent-Patterns]] — Multi-agent orchestration strategies (multi-agent, workflow)

## principle (20 notes)
...

## tools (8 notes)
...

## study-plan (7 notes)
...

## interview (6 notes)
...

## other (0 notes)
```

Each entry format: `- [[Filename-Without-Extension]] — <abstract excerpt> (<sub-categories>)`

---

## Execution: --full Rebuild

### Step 1: Run Note Scanner

Execute the note-scanner script to get structured vault data:

```bash
python3 .claude/skills/note-scanner/scripts/note_scanner.py .
```

Working directory: vault root. Parse the JSON output.

If the script is not found or fails, fall back to manual scanning (Step 1b).

### Step 1b: Manual Fallback Scan

If the scanner script is unavailable, scan manually:

1. Glob for `**/*.md` under vault root
2. **Exclude**: `y.template/`, `row/`, `x.temp/`, `docs/`, `zz.original-source/`, `.obsidian/`, `.claude/`, `.agents/`, `.prompts/`, `.github/`, `.instructions/`, `000.Index/`
3. Collect all matching note paths

### Step 2: Extract Note Metadata

For each note, Read the first 30 lines and extract:

1. **Filename** — without `.md` extension
2. **Domain** — derived from parent folder:
   - `111.cs/` → `cs`
   - `222.web/` → `web`
   - `333.ai/` → `ai`
   - `444.principle/` → `principle`
   - `555.tools/` → `tools`
   - `888.study-plan/` → `study-plan`
   - `999.interview/` → `interview`
   - Anything else → `other`
3. **Abstract excerpt** — first non-empty line under `### Abstract` (truncate to 80 chars)
4. **Sub-Categories** — from frontmatter `Sub-Categories:` field, formatted as comma-separated lowercase

If Abstract section is missing, use the first content line after frontmatter closes (`---`).

### Step 3: Group and Sort

1. Group notes by domain
2. Sort alphabetically by filename within each domain
3. Sort domain sections in this fixed order: `cs`, `web`, `ai`, `principle`, `tools`, `study-plan`, `interview`, `other`

### Step 4: Build Index Content

1. **Header**: `# Vault Index` with generated date, total note count, and domain count (domains with >0 notes)
2. **Domain sections**: `## <domain> (<N> notes)` followed by sorted entries
3. Each entry: `- [[<Filename>]] — <abstract excerpt> (<sub-categories>)`
   - If no abstract: use `(no abstract)`
   - If no sub-categories: omit the parenthetical

### Step 5: Write Index

Write the complete content to `.claude/index.md`.

Report:
```
✅ Vault index rebuilt
📄 File: .claude/index.md
📊 Notes: <total> | Domains: <count>
```

---

## Execution: --append \<note-path\>

### Step 1: Validate Note

Read the note at the given path. If the file doesn't exist → error:
```
❌ Note not found: <path>
```

### Step 2: Extract Metadata

Same extraction as full rebuild Step 2 — filename, domain, abstract, sub-categories.

### Step 3: Read Existing Index

Read `.claude/index.md`. If it doesn't exist → run `--full` rebuild instead and report:
```
📋 Index not found — running full rebuild instead
```

### Step 4: Insert or Update Entry

1. Find the correct domain section (`## <domain>`)
2. If the note already exists in the index → replace its line
3. If new → insert in alphabetical order within the domain section
4. If domain section doesn't exist → create it in the correct position

### Step 5: Update Header Counts

Recount notes per domain and total. Update the header line:
```
Generated: <today> | Notes: <new-total> | Domains: <new-count>
```

### Step 6: Write and Report

Write the updated `.claude/index.md`.

Report:
```
✅ Index updated: [[<Filename>]] added to <domain>
📄 File: .claude/index.md
📊 Notes: <total> | Domains: <count>
```

---

## Edge Cases

**Index doesn't exist (--append mode):**
- Fall back to `--full` rebuild

**Note path invalid or file missing:**
- Report error with the attempted path

**Domain not recognized:**
- Assign to `other` section

**Note scanner script not found:**
- Fall back to manual glob-based scanning

**Empty vault (no notes found):**
- Create index with header showing 0 notes
- Report: "No notes found in vault"

**Duplicate entry (--append with existing note):**
- Update the existing line in place (re-extract metadata to catch changes)
