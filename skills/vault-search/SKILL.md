---
name: vault-search
description: Search the Obsidian Zettelkasten vault for notes matching a natural language query. Searches Aliases, Categories, Sub-Categories, tags, and filenames across the vault. Works from any working directory. Use when you need to find related notes, check what exists on a topic, or gather context before creating new notes.
---

# Vault Search — Find Relevant Zettelkasten Notes

Search the Obsidian ZK vault for notes matching a natural language query. Returns ranked results with paths, matched metadata, and abstract excerpts.

## Input

`$ARGUMENTS` — `<query> [--limit N] [--vault PATH]`

- **query**: Natural language search prompt (English or Chinese)
  - Examples: `"front-end career developing suggestion"`, `"XSS 攻擊防禦"`, `"React performance optimization"`
- **--limit N**: Max results to return (default: 10)
- **--vault PATH**: Vault root (default: `/Users/jason/Developer/obsidian/CS`)

## Execution

### Step 0: Query Analysis

Analyze the query and produce a flat list of search terms to drive all three tiers:

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

### Tier 0: Index Lookup (Fast Path)

Before running grep-based tiers, check if `.claude/index.md` exists in the vault root. If it does:

1. Read `.claude/index.md`
2. Search entries for matches against primary keywords (case-insensitive substring match on note name, abstract excerpt, and sub-categories)
3. Collect matched entries as Tier 0 results (score: 35 pts each)

If Tier 0 yields ≥ limit results → skip to Step 4.
If Tier 0 yields some results → proceed to Tier 1 but merge with Tier 0 results.
If `.claude/index.md` doesn't exist → skip directly to Tier 1.

---

### Tier 1: Alias + Filename Match (Highest Signal)

These are the strongest matches — curated synonyms and note names.

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

**Merge** Tier 1 results. Record matched field as `Aliases` or `Filename` per note.

If Tier 1 yields ≥ limit results → skip to Step 4.

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

Add new matches (not already in Tier 1) with matched field recorded.

If Tier 1 + Tier 2 ≥ limit → skip to Step 4.

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
Add new matches with field = `Body`.

---

### Step 4: Rank and Deduplicate

1. **Deduplicate** — if a note appears in multiple tiers, keep the highest-tier entry
2. **Score each note:**
   - Tier 0 = 35 pts (index match)
   - Tier 1 = 30 pts
   - Tier 2 = 20 pts
   - Tier 3 = 10 pts
   - +5 pts per additional matched search term
3. **Sort** by score descending
4. **Truncate** to limit (default 10)

---

### Step 5: Read Abstracts and Metadata

For each result note (up to limit), use the Read tool to extract the first 25 lines and parse:

1. **Frontmatter block** — extract: `Categories`, `Sub-Categories`, `Aliases`, `tags`
2. **Abstract section** — content under `### Abstract` or `## Abstract` until next heading or 10 lines, whichever comes first

---

### Step 6: Format Output

```
## Vault Search: "{original query}"

Found {N} notes ({X} metadata matches, {Y} content matches):

### 1. {Note-Filename.md}
- **Path**: {relative path from vault root}
- **Match**: {field}: {matched term}
- **Categories**: {categories}  **Tags**: {tags}
- **Aliases**: {aliases}
- **Abstract**:
  > {abstract excerpt, max 5 lines}

### 2. ...

---
Vault: {vault_root} | Terms searched: {terms list}
```

---

## Edge Cases

**No results found:**
- Report which terms were tried
- Suggest checking `000.Index/` MOC files for topic discovery
- Suggest broadening the query or trying Chinese/English alternative

**Chinese-only query:**
- Generate English equivalents as additional search terms
- The vault's `Aliases` field contains Chinese — this is the primary Chinese match surface

**Single-word or ambiguous query:**
- Expand synonyms aggressively
- Run all three tiers regardless of intermediate result count

**`--vault` override:**
- Use the provided path as vault root for all Grep/Glob calls
- Useful for searching a different vault or a subdirectory

## Metadata Reference

The vault uses this frontmatter schema (enriched 2026-04-07):

```yaml
Categories: [Web, Security]          # Title Case domain + secondary
Sub-Categories: [xss, injection]     # lowercase-kebab topics
Aliases: [XSS, Cross-Site Scripting, 跨站腳本攻擊]  # 3-5 search terms
tags: [security, interview-prep]     # cross-cutting controlled vocab
```

**Primary Categories:** CS, Web, AI, Principles, Tools, Study Plan, Interview
**Tags vocabulary (18):** interview-prep, career, learning-strategy, performance, security, testing, debugging, design-pattern, architecture, api-design, concurrency, state-management, type-system, beginner, advanced, reference, cheatsheet, stub
