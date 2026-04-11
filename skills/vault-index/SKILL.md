---
name: vault-index
description: Auto-maintained vault catalog at .claude/index.md grouping all notes by domain with enriched metadata and a Keyword Index for fast retrieval. Use when you need to rebuild index, update index, or generate a vault catalog.
---

# Vault Index — Auto-Maintained Note Catalog

Generate and maintain `.claude/index.md` (relative to vault root) — a structured catalog of all Zettelkasten notes grouped by domain, with enriched metadata and a Keyword Index for fast Tier 0 lookup by vault-search.

## Input

`$ARGUMENTS` — `[--full | --append <note-path>] [--vault PATH]`

- **--full**: Full rebuild by scanning the entire vault
- **--append \<path\>**: Incremental — add or update a single note entry
- **--vault PATH**: Vault root (default: `.` — current working directory, i.e., run from inside your vault)

If no flag provided, default to `--full`.

## Output Format

`.claude/index.md` follows this structure:

```markdown
# Vault Index
Generated: 2026-04-08 | Notes: 317 | Domains: 7

## cs (142 notes)
- [[CS-Algorithm-Backtracking]] — Backtracking pattern for constraint satisfaction | cats:CS sub:algorithm,backtracking tags:design-pattern aka:Backtracking,回溯法
- [[CS-Binary-Search-Tree]] — BST operations and balancing | cats:CS sub:data-structure,tree tags:reference aka:BST,Binary Search Tree,二元搜尋樹

## web (89 notes)
- [[Web-React-Hooks]] — React hook patterns and lifecycle | cats:Web sub:react,hooks tags:state-management aka:React Hooks,useState,useEffect

## ai (45 notes)
- [[AI-Multi-Agent-Patterns]] — Multi-agent orchestration strategies | cats:AI sub:multi-agent,workflow tags:architecture aka:Multi-Agent,多代理

## principle (20 notes)
...

## Keyword Index
- algorithm: [[CS-Algorithm-Backtracking]], [[CS-Algorithm-DP]], [[CS-Algorithm-BFS]]
- react: [[Web-React-Hooks]], [[Web-React-Server-Components]], [[Web-React-Performance]]
- 前端: [[Web-Frontend-Career-Path]], [[Web-React-Hooks]]
- security: [[Web-XSS-Prevention]], [[CS-Auth-JWT-Patterns]]
```

Each entry format: `- [[Filename-Without-Extension]] — <abstract excerpt> | cats:<categories> sub:<sub-categories> tags:<tags> aka:<aliases>`

- `cats:` — primary + secondary categories (Title Case, comma-separated)
- `sub:` — topic-level sub-categories (lowercase-kebab, comma-separated)
- `tags:` — cross-cutting controlled vocab tags (comma-separated)
- `aka:` — aliases including CJK translations (comma-separated)
- Omit any field whose value is empty

---

## Execution: --full Rebuild

### Step 0: Discover Domains

Scan top-level directories under vault root:

1. Glob `*/` under vault root to list all top-level directories
2. **Exclude**: `y.template/`, `row/`, `x.temp/`, `docs/`, `zz.original-source/`, `.obsidian/`, `.claude/`, `.agents/`, `.prompts/`, `.github/`, `.instructions/`, `000.Index/`
3. For each remaining directory, derive its **domain label** by stripping any leading numeric prefix:
   - `111.cs/` → `cs`, `222.web/` → `web`, `333.ai/` → `ai`
   - `notes/` → `notes`, `journal/` → `journal` (no prefix to strip)
   - Pattern: strip `^\d+\.` if present
4. Build a map: `{folder_name → domain_label}`. Sort domains alphabetically.

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
2. **Domain** — match the note's parent folder against the domain map from Step 0; if no match → `other`
3. **Abstract excerpt** — first non-empty line under `### Abstract` (truncate to 80 chars). If Abstract section is missing, use the first content line after frontmatter closes (`---`).
4. **Categories** — from frontmatter `Categories:` field, comma-separated Title Case
5. **Sub-Categories** — from frontmatter `Sub-Categories:` field, comma-separated lowercase-kebab
6. **tags** — from frontmatter `tags:` field, comma-separated
7. **Aliases** — from frontmatter `Aliases:` field, comma-separated (preserve CJK characters)

### Step 3: Group and Sort

1. Group notes by domain
2. Sort alphabetically by filename within each domain
3. Sort domain sections alphabetically (no fixed order — domains are vault-specific)

### Step 4: Build Domain Sections

1. **Header**: `# Vault Index` with generated date, total note count, and domain count (domains with >0 notes)
2. **Domain sections**: `## <domain> (<N> notes)` followed by sorted entries
3. Each entry: `- [[<Filename>]] — <abstract excerpt> | cats:<categories> sub:<sub-categories> tags:<tags> aka:<aliases>`
   - If no abstract: use `(no abstract)`
   - Omit any `cats:`/`sub:`/`tags:`/`aka:` field that is empty

### Step 5: Build Keyword Index

After all domain sections, generate a `## Keyword Index` section:

1. **Collect all keywords** across every note:
   - All values from `tags` (e.g., `security`, `interview-prep`)
   - All values from `Sub-Categories` (e.g., `xss`, `algorithm`)
   - All values from `Aliases` — including CJK terms (e.g., `XSS`, `跨站腳本攻擊`)
   - All values from `Categories` (lowercased, e.g., `web`, `cs`)

2. **Build inverted index**: `keyword → [list of note filenames]`

3. **Filter**: Only include keywords that appear in **2 or more notes** (single-note keywords are discoverable via entry scan)

4. **Sort**: Alphabetically by keyword. CJK keywords sort after ASCII.

5. **Format** each line:
   ```
   - <keyword>: [[Note-A]], [[Note-B]], [[Note-C]]
   ```

6. **Cap**: If a keyword maps to >20 notes, truncate to top 20 alphabetically and append ` (and N more)`

### Step 6: Write Index

Concatenate: header + domain sections + Keyword Index section.

Write the complete content to `.claude/index.md`.

Report:
```
✅ Vault index rebuilt
📄 File: .claude/index.md
📊 Notes: <total> | Domains: <count> | Keywords: <keyword-count>
```

---

## Execution: --append \<note-path\>

### Step 1: Validate Note

Read the note at the given path. If the file doesn't exist → error:
```
❌ Note not found: <path>
```

### Step 2: Extract Metadata

Same extraction as full rebuild Step 2 — filename, domain (via Step 0 domain discovery), abstract, categories, sub-categories, tags, aliases.

### Step 3: Read Existing Index

Read `.claude/index.md`. If it doesn't exist → run `--full` rebuild instead and report:
```
📋 Index not found — running full rebuild instead
```

### Step 4: Insert or Update Domain Entry

1. Find the correct domain section (`## <domain>`)
2. If the note already exists in the index → replace its line with the updated enriched format
3. If new → insert in alphabetical order within the domain section
4. If domain section doesn't exist → create it in alphabetical order among existing sections

### Step 5: Update Keyword Index

1. Read the existing `## Keyword Index` section
2. For the appended note's keywords (tags, sub-categories, aliases, categories):
   - If keyword already exists in index → add `[[Filename]]` to its list if not already present
   - If keyword is new and will appear in 2+ notes after this note → add a new line
3. Re-sort the Keyword Index alphabetically

### Step 6: Update Header Counts

Recount notes per domain and total. Update the header line:
```
Generated: <today> | Notes: <new-total> | Domains: <new-count> | Keywords: <keyword-count>
```

### Step 7: Write and Report

Write the updated `.claude/index.md`.

Report:
```
✅ Index updated: [[<Filename>]] added to <domain>
📄 File: .claude/index.md
📊 Notes: <total> | Domains: <count> | Keywords: <keyword-count>
```

---

## Edge Cases

**Index doesn't exist (--append mode):**
- Fall back to `--full` rebuild

**Note path invalid or file missing:**
- Report error with the attempted path

**Domain not recognized (folder not in domain map):**
- Assign to `other` section

**Note scanner script not found:**
- Fall back to manual glob-based scanning

**Empty vault (no notes found):**
- Create index with header showing 0 notes
- Report: "No notes found in vault"

**Duplicate entry (--append with existing note):**
- Update the existing line in place (re-extract metadata to catch changes)

**No Aliases / CJK terms:**
- Omit `aka:` field from entry; skip in Keyword Index
