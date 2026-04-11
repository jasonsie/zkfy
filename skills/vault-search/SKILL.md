---
name: vault-search
description: Search the Obsidian Zettelkasten vault for notes matching a natural language query. Uses a tiered retrieval system: fast index lookup (Tier 0) → synthesis dedup (Tier 0.5) → grep-based fallback (Tiers 1-3). Works from any working directory. Use when you need to find related notes, check what exists on a topic, or gather context before creating new notes.
---

# Vault Search — Find Relevant Zettelkasten Notes

Search the ZK vault for notes matching a natural language query. Returns ranked results with paths, matched metadata, and abstract excerpts.

## Input

`$ARGUMENTS` — `<query> [--limit N] [--vault PATH]`

- **query**: Natural language search prompt (English or Chinese)
  - Examples: `"front-end career developing suggestion"`, `"XSS 攻擊防禦"`, `"React performance optimization"`
- **--limit N**: Max results to return (default: 10)
- **--vault PATH**: Vault root (default: `.` — current working directory, i.e., run from inside your vault)

## Execution

### Step 0: Query Analysis

Analyze the query and produce a flat list of search terms to drive all tiers:

1. **Extract primary keywords** from the query
   - `"front-end career developing suggestion"` → `frontend`, `career`, `development`
2. **Generate synonyms and variants** including:
   - English variations: `frontend` / `front-end` / `web`
   - Traditional Chinese translations (e.g., `前端`, `職涯`, `學習路徑`)
   - English translations if query is in Chinese
   - Common abbreviations (e.g., `XSS`, `CORS`, `DP`, `DSA`)
   - Kebab-case variants for Sub-Categories matching: `interview-prep`, `career`, `learning-strategy`
3. **Map to controlled tag vocabulary** — check which of these apply and add as search terms:
   `interview-prep`, `career`, `learning-strategy`, `performance`, `security`,
   `testing`, `debugging`, `design-pattern`, `architecture`, `api-design`,
   `concurrency`, `state-management`, `type-system`, `beginner`, `advanced`,
   `reference`, `cheatsheet`, `stub`

Produce a **deduplicated flat list** of all search terms. Track which terms come from the original query vs. generated synonyms.

---

### Tier 0: Index Fast Path

Before running grep-based tiers, check if `.claude/index.md` exists in the vault root.

**If index.md does NOT exist:**
- Emit warning: `⚠ No index found. Run /vault-index --full to build it.`
- Skip to Tier 1.

**If index.md exists**, run two phases:

#### Phase A: Keyword Index Lookup

1. Read `.claude/index.md`
2. Jump to the `## Keyword Index` section
3. For each primary keyword and synonym from Step 0:
   - Search for a line starting with `- <term>:` (case-insensitive)
   - Collect all `[[NoteNames]]` from matching lines
4. Deduplicate collected notes. Score: **35 pts** per note, +5 per additional keyword that matched it
5. If Phase A yields ≥ limit results → skip Phase B and all grep tiers, jump to Tier 0.5

#### Phase B: Full Entry Scan

If Phase A yielded < limit results, scan enriched entry lines:

1. Scan all lines in the domain sections (lines starting with `- [[`)
2. For each line, match against primary keywords in these inline fields (case-insensitive substring):
   - Note name (between `[[` and `]]`)
   - Abstract excerpt (between `—` and `|`)
   - `cats:`, `sub:`, `tags:`, `aka:` field values
3. Add new matches not already in Phase A results. Score: **30 pts** per note, +5 per additional field match
4. Merge with Phase A results

**Early exit**: If Phase A + Phase B yields ≥ limit results → skip all grep tiers, jump to Tier 0.5.
If some results but < limit → proceed to Tier 1 but merge with Tier 0 results.

---

### Tier 0.5: Synthesis Dedup Check

After Tier 0 (and before grep tiers), check the current result set for prior synthesis notes:

1. For each result so far, check if its entry contains `Type: permanent` in the note (read first 10 lines if needed)
2. If a permanent note's abstract or title strongly relates to the query (primary keywords appear), flag it as `[SYNTHESIS]`
3. Boost synthesis matches to **40 pts** (highest tier)
4. These will surface first in the final ranked output

Synthesis notes are created by `/query-to-note` — finding one means this question may have already been answered and filed.

---

### Tier 1: Alias + Filename Match (Highest Signal — grep fallback)

Only reached if Tier 0 yielded < limit results or index.md is missing.

**1a. Search Aliases** — for each primary keyword and synonym:

```
Grep pattern: ^Aliases:.*{term}
Path: {vault_root}
Glob: **/*.md
Case-insensitive: true
```

**1b. Search Filenames** — for each primary keyword:

```
Glob pattern: **/*{term}*.md
Path: {vault_root}
```

**Exclude from all searches:**
`y.template/`, `row/`, `row/assets/`, `x.temp/`, `docs/`,
`.obsidian/`, `.claude/`, `.agents/`, `.prompts/`, `.github/`, `.instructions/`

**Merge** Tier 1 results. Score: **25 pts** per note, +5 per additional matched term.

If Tier 0 + Tier 1 yields ≥ limit → skip Tier 2 and Tier 3.

---

### Tier 2: Metadata Match (Categories, Sub-Categories, Tags)

Catches topical matches not covered by exact aliases.

For each remaining search term:

```
Grep pattern: ^(Categories|Sub-Categories|tags):.*{term}
Path: {vault_root}
Glob: **/*.md
Case-insensitive: true
```

Add new matches (not already found). Score: **20 pts** per note, +5 per additional matched term.

If Tier 0 + Tier 1 + Tier 2 ≥ limit → skip Tier 3.

---

### Tier 3: Body Content Match (Fallback)

For queries with few results after Tier 2, search note bodies:

```
Grep pattern: {term}
Path: {vault_root}
Glob: **/*.md
Case-insensitive: true
```

Restrict to primary keywords only (not all synonyms) to avoid noise.
Add new matches. Score: **10 pts** per note, +5 per additional term.

---

### Step 4: Rank and Deduplicate

1. **Deduplicate** — if a note appears in multiple tiers, keep the highest-tier entry (highest base score)
2. **Score each note** (final):
   - Synthesis match (Tier 0.5 boost) = 40 pts
   - Keyword Index match (Tier 0A) = 35 pts
   - Entry Scan match (Tier 0B) = 30 pts
   - Alias + Filename grep (Tier 1) = 25 pts
   - Metadata grep (Tier 2) = 20 pts
   - Body grep (Tier 3) = 10 pts
   - +5 pts per additional matched search term (any tier)
3. **Sort** by score descending
4. **Truncate** to limit (default 10)

---

### Step 5: Read Abstracts and Metadata

For each result note (up to limit), use the Read tool to extract the first 25 lines and parse:

1. **Frontmatter block** — extract: `Type`, `Categories`, `Sub-Categories`, `Aliases`, `tags`
2. **Abstract section** — content under `### Abstract` or `## Abstract` until next heading or 10 lines

---

### Step 6: Format Output

```
## Vault Search: "{original query}"

Found {N} notes ({X} index matches, {Y} grep matches):

### 1. {Note-Filename.md} {[SYNTHESIS] if applicable}
- **Path**: {relative path from vault root}
- **Match**: {tier}: {matched term}
- **Categories**: {categories}  **Tags**: {tags}
- **Aliases**: {aliases}
- **Abstract**:
  > {abstract excerpt, max 5 lines}

### 2. ...

---
Vault: {vault_root} | Index: {used/missing} | Terms searched: {terms list}
```

---

## Edge Cases

**No results found:**
- Report which terms were tried
- Suggest checking `000.Index/` MOC files for topic discovery
- Suggest broadening the query or trying Chinese/English alternative
- If index was missing, remind: `Run /vault-index --full to enable fast search`

**Chinese-only query:**
- Generate English equivalents as additional search terms
- The vault's `Aliases` field and Keyword Index both contain CJK — these are the primary Chinese match surfaces

**Single-word or ambiguous query:**
- Expand synonyms aggressively
- Run all tiers regardless of intermediate result count

**`--vault` override:**
- Use the provided path as vault root for all Read/Grep/Glob calls
- Useful for searching a different vault or a subdirectory

**Synthesis note found (Tier 0.5):**
- Always surface it in output with `[SYNTHESIS]` label
- The caller (e.g., `/query-to-note`) can use this to offer dedup options

## Metadata Reference

The vault uses this frontmatter schema:

```yaml
Type: literature          # or: permanent (synthesis from /query-to-note)
Categories: [Web, Security]          # Title Case domain + secondary
Sub-Categories: [xss, injection]     # lowercase-kebab topics
Aliases: [XSS, Cross-Site Scripting, 跨站腳本攻擊]  # 3-5 search terms incl. CJK
tags: [security, interview-prep]     # cross-cutting controlled vocab
```

**Tags vocabulary (18):** interview-prep, career, learning-strategy, performance, security, testing, debugging, design-pattern, architecture, api-design, concurrency, state-management, type-system, beginner, advanced, reference, cheatsheet, stub

---

## Future: qmd Integration

When [qmd](https://github.com/tobi/qmd) is installed, vault-search gains a **Tier -1** that supersedes all other tiers:

### Tier -1: qmd Hybrid Search (if available)

1. Check: `which qmd` — if not found, skip to Tier 0
2. Run: `qmd search "<query>" --path <vault_root> --limit <limit>`
3. Parse results (BM25 + vector hybrid, pre-ranked by qmd)
4. Score: **50 pts** per result
5. If Tier -1 yields ≥ limit → skip all other tiers entirely

### Installation

```bash
# macOS via Homebrew
brew install tobi/tap/qmd
# or from source
go install github.com/tobi/qmd@latest
```

### MCP Alternative

qmd also provides an MCP server. If configured in `.mcp.json`, use the `mcp__qmd__search` tool instead of shelling out — no CLI install needed.

Use qmd when the vault exceeds ~5000 notes and the index-based Tier 0 becomes the bottleneck.
