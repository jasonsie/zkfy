---
name: vault-lint
description: >-
  Semantic health checks for the Obsidian ZK vault. Detects contradictions between notes,
  stale content, orphan pages, missing pages, weak links, concept gaps, and cross-reference gaps.
  Use when the user asks to "lint the vault", "check vault health", "find contradictions",
  "find orphans", or "what's missing". Goes beyond structural compliance (vault-audit) to
  check semantic coherence.
---

# Vault Lint — Semantic Health Checks

Detect contradictions, staleness, orphan pages, missing pages, weak links, concept gaps, and cross-reference gaps across the Obsidian ZK vault. Complements `vault-audit` (structural compliance) with semantic coherence checks.

## Input

`$ARGUMENTS` — `<path> [--fix] [--checks 1,2,3] [--vault PATH]`

- **path**: Directory to lint (e.g., `333.ai/`, `.` for entire vault)
- **--fix**: Auto-remediate fixable issues (checks 5, 6, 7)
- **--checks**: Comma-separated check numbers to run (default: all)
- **--vault**: Vault root (default: `/Users/jason/Developer/obsidian/CS`)

## The 7 Checks

| # | Check | Severity | Auto-fixable |
|---|-------|----------|-------------|
| 1 | **Contradictions** | HIGH | No |
| 2 | **Stale content** | MEDIUM | No |
| 3 | **Orphan pages** | MEDIUM | No |
| 4 | **Missing pages** | HIGH | No |
| 5 | **Weak links** | LOW | Yes |
| 6 | **Concept gaps** | MEDIUM | Yes |
| 7 | **Cross-ref gaps** | LOW | Yes |

## Execution

### Step 1: Inventory

Run `note-scanner` on the target path to get full inventory JSON:

```bash
python3 .claude/skills/note-scanner/scripts/note_scanner.py <target_path>
```

Parse the JSON output. Extract `notes[]` array — each entry provides `path`, `filename`, `frontmatter`, `outgoing_links`, and `line_count`.

### Step 2: Run Checks

For each enabled check (1-7), execute the check method and collect findings as structured data:

```
{check_id, severity, note_path, detail, fixable}
```

---

#### Check 1: Contradictions (HIGH)

For each note, read the `### Abstract` and key claims in `### Content`. Compare against notes referenced in its `### Links` section and notes sharing the same `Sub-Categories`.

Flag conflicting statements about the same concept — e.g., one note claims "SSR improves SEO" while a linked note claims "SSR has no SEO benefit".

**Method:**
1. For each note, extract key claims (statements of fact, definitions, comparisons)
2. For notes that share `Sub-Categories` or appear in each other's `### Links`, compare claims
3. Use semantic understanding to detect contradictions (not just textual differences)
4. Report the specific conflicting statements

**Not auto-fixable** — requires human judgment to resolve which claim is correct.

---

#### Check 2: Stale Content (MEDIUM)

Notes with `Date` older than 6 months AND newer notes exist with overlapping `Sub-Categories`.

**Method:**
1. Parse `Date` from each note's frontmatter
2. Calculate age from current date
3. For notes older than 6 months, check if other notes with overlapping `Sub-Categories` have a newer `Date`
4. Flag the older note for review — it may contain outdated information

**Not auto-fixable** — staleness requires human review to determine if content is still accurate.

---

#### Check 3: Orphan Pages (MEDIUM)

Notes with 0 incoming links — no other note in the vault references them.

**Method:**
1. For each note's filename (without `.md` extension), grep the entire vault for `[[Filename-Without-Extension]]`
2. Exclude self-references (the note itself)
3. If zero other notes reference it, it's an orphan

```bash
# For each note, check incoming links:
Grep pattern: \[\[{Note-Name}\]\]
Path: {vault_root}
Glob: **/*.md
```

**Not auto-fixable** — orphans may need to be linked, merged, or deleted depending on content.

---

#### Check 4: Missing Pages (HIGH)

WikiLink targets that don't exist as files in the vault.

**Method:**
1. Collect all `[[WikiLinks]]` from note bodies across scanned notes
2. **Exclude** links found in frontmatter `Before`, `Next`, and `Src` fields — these are navigational
3. For each target, check if `{target}.md` exists anywhere in the vault
4. List non-existent targets with the notes that reference them

```bash
# For each collected target:
Glob pattern: **/{target}.md
Path: {vault_root}
```

**Not auto-fixable** — missing pages may be typos, planned notes, or intentional references to external concepts.

---

#### Check 5: Weak Links (LOW)

Notes with fewer than 2 outgoing links in their `### Links` section (not counting Before/Next/Src frontmatter links).

**Method:**
1. Read the `### Links` section of each note
2. Count outgoing `[[links]]` that have rationale text nearby (e.g., "Related to [[X]] because...")
3. Flag notes with < 2 such links

**Auto-fixable with `--fix`:**
- Use `vault-search` skill to find related notes based on the note's `Sub-Categories` and `### Abstract`
- Suggest links with rationale text and append to `### Links` section

---

#### Check 6: Concept Gaps (MEDIUM)

Concepts referenced frequently across notes but with no dedicated note file.

**Method:**
1. Aggregate all `[[WikiLink]]` targets across scanned notes
2. Count occurrences of each target
3. Filter targets that appear >= 3 times but have no corresponding `.md` file in the vault
4. These represent concepts important enough to be frequently referenced but lacking a dedicated note

**Auto-fixable with `--fix`:**
- Create stub notes with Train-Case naming in the appropriate domain folder
- Minimal frontmatter with `Type: literature`, current `Date`, inferred `Categories` and `Sub-Categories`
- `### Abstract` section containing: "Stub -- needs dedicated note. Referenced by N notes."
- `### Content` section left empty
- `### Links` section with backlinks to the top 3 referencing notes

---

#### Check 7: Cross-Reference Gaps (LOW)

Notes sharing the same `Sub-Category` that don't link to each other.

**Method:**
1. Group notes by `Sub-Categories` values
2. Within each group, check if notes reference each other via `[[WikiLinks]]`
3. Flag pairs that share a `Sub-Category` but have no cross-reference

**Auto-fixable with `--fix`:**
- Add cross-references to the `### Links` section of both notes
- Include rationale: "Related to [[Note]] — shares Sub-Category: {sub-category}"

---

### Step 3: Auto-fix (if --fix)

Only runs when `--fix` flag is provided. Only checks 5, 6, and 7 are auto-fixable.

For each fixable finding:
1. **Check 5 (Weak links)**: Use `vault-search` to find related notes, add suggested links with rationale to `### Links`
2. **Check 6 (Concept gaps)**: Create stub notes with Train-Case naming, minimal frontmatter, stub Abstract
3. **Check 7 (Cross-ref gaps)**: Add cross-references to `### Links` sections of both notes in the pair

After auto-fixes, re-run the affected checks to confirm resolution.

### Step 4: Report

Output grouped by severity:

```
## Vault Lint: {path}
Scanned: {N} notes | Checks run: {check_ids}

### HIGH
[Check 1] Contradiction: CS-SSR-Basics.md vs Web-CSR-Performance.md
   CS-SSR-Basics.md claims "SSR always improves TTI"
   Web-CSR-Performance.md claims "CSR with code-splitting matches SSR TTI"

[Check 4] Missing page: [[React-Suspense]] referenced by 3 notes
   - Web-React-Server-Components.md
   - Web-React-Performance.md
   - Web-React-Streaming-SSR.md

### MEDIUM
[Check 2] Stale: Web-jQuery-Patterns.md (Date: 2024-03-15, superseded by Web-Modern-DOM-API.md)
[Check 3] Orphan: CS-Assembly-Basics.md (0 incoming links)
[Check 6] Concept gap: [[Event-Loop]] referenced 5 times, no dedicated note

### LOW
[Check 5] Weak links: AI-Transformer-Architecture.md (1 outgoing link in Links section)
[Check 7] Cross-ref gap: CS-Binary-Search.md <-> CS-Algorithm-Complexity.md (shared: algorithm-analysis)

---
Summary: {H} HIGH | {M} MEDIUM | {L} LOW | {F} auto-fixed
```

## Edge Cases

**Empty directory:** Report "No notes found in {path}" and exit.

**--checks with invalid numbers:** Ignore invalid check numbers, warn the user, run valid ones.

**--fix without fixable issues:** Report "No auto-fixable issues found" in the summary.

**Large vault (whole-vault scan):** Process in batches by top-level directory (111.cs/, 222.web/, etc.) to manage context. Report per-directory then aggregate.

**Notes without frontmatter:** Skip checks that depend on frontmatter fields (2, 7). Still run checks 1, 3, 4, 5.
