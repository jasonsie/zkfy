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

**Concept-First conformance** (Checks 8–10) enforces the spec defined in `docs/ADR/0001-concept-first-pipeline.md`. **Hybrid Mode conformance** (Checks 8 mode-branching, 9 atom-only, 11 thesis chapter budget, 12 dangling thesis back-link) enforces `docs/ADR/0002-hybrid-atom-thesis-mode.md`. **Clip mode conformance** (Checks 8, 9, 10 skip or branch on `Mode: clip`) follows `docs/ADR/0004-clip-mode-verbatim-notes.md`. Pre-adoption notes (`Date` < 2026-05-28) receive downgraded LOW severity per D10.

## Scoped-vault override (check first)

If the target vault has `docs/knowledge/scope.json`, its corpus policy overrides all legacy inventory/search/backlog/auto-fix procedures below:

- Structural report: `python3 -B <zkfy-root>/scripts/knowledge.py --vault "<vault>" lint` (or `vault-knowledge lint` for the configured canonical vault).
- Obtain candidates/sections only through that CLI's `search` and `read`; do not run the unrestricted note-scanner, whole-vault grep/globs, or source-backlog checks. `raw/` is entirely excluded, including in Check 12.
- Missing `Mode` means an existing legacy profile, not an automatic atom migration. Use the scope's schema compatibility rules for structural checks.
- Model-assisted contradiction/staleness analysis is a review suggestion, not mechanical factual verification. Dates alone do not establish staleness.
- `--fix` never writes logs and cannot bypass the vault's authored-change approval gate. Fixes to authored notes are proposed and applied only after explicit user approval; never run this skill from a query or Git hook.

For unconfigured vaults, the legacy semantic workflow below remains documentation of the old interface; request an explicit scope before scanning. Do not infer permission to inspect excluded sources.

## Input

`$ARGUMENTS` — `<path> [--fix] [--checks 1,2,3] [--vault PATH]`

- **path**: Directory to lint (e.g., `333.ai/`, `.` for entire vault)
- **--fix**: Propose fixes for fixable issues (checks 5, 6, 7, 10); apply only those the user explicitly approves. No log is written. Checks 11 and 12 are NOT auto-fixable.
- **--checks**: Comma-separated check numbers to run (default: all). Valid subsets include the Concept-First trio `--checks 8,9,10` and the Hybrid Mode conformance subset `--checks 8,9,11,12`.
- **--vault**: Vault root (default: `.` — current working directory, i.e., run from inside your vault)

## The 12 Checks

| # | Check | Severity | Auto-fixable |
|---|-------|----------|-------------|
| 1 | **Contradictions** | HIGH | No |
| 2 | **Stale content** | MEDIUM | No |
| 3 | **Orphan pages** | MEDIUM | No |
| 4 | **Missing pages** | HIGH | No |
| 5 | **Weak links** | LOW | Yes |
| 6 | **Concept gaps** | MEDIUM | Yes |
| 7 | **Cross-ref gaps** | LOW | Yes |
| 8 | **Missing required-core section (mode-aware)** | HIGH (post-ADR) / LOW (pre-ADR) | No |
| 9 | **Body over 500-char budget (atom only; skips thesis and clip)** | HIGH (post-ADR) / LOW (pre-ADR) | No |
| 10 | **Legacy `--preserve` artifacts (skips clip)** | MEDIUM | Yes |
| 11 | **Thesis chapter budget** | MEDIUM (post-adoption) / LOW (pre-adoption) | No |
| 12 | **Dangling thesis back-link** | LOW | No |

## Execution

### Constants

```
ADR_ADOPTION_DATE = 2026-05-28
```

This is the threshold for D10's severity gating (see ADR-0001). Notes with `Date < ADR_ADOPTION_DATE` are "pre-ADR" and get downgraded severity for Concept-First violations. Notes with `Date >= ADR_ADOPTION_DATE` are "post-ADR" and get the check's full intrinsic severity.

### Severity gating helper (used by Checks 8, 9, 11, 12)

For checks that enforce the Concept-First and Hybrid Mode specs (Checks 8, 9, 11, 12):

```
if note.frontmatter.Date < ADR_ADOPTION_DATE:
    effective_severity = LOW
else:
    effective_severity = check.intrinsic_severity
```

This implements D10's γ + δ hybrid: pre-ADR notes are reported but not blocking; post-ADR notes are held to the full standard. The same gate covers the ADR-0002 additions (Checks 11 and 12), since pre-Concept-First notes never carried `Mode:` either — a single 2026-05-28 threshold keeps the gating model simple. If a note has no parseable `Date` field, treat it as **post-ADR** (apply intrinsic severity) — missing-Date is itself a defect worth surfacing at full weight.

Check 10 is exempt from gating — legacy `--preserve` artifacts are cleanup signals regardless of Date.

### Step 1: Inventory

Run `note-scanner` on the target path to get full inventory JSON:

```bash
python3 .claude/skills/note-scanner/scripts/note_scanner.py <target_path>
```

Parse the JSON output. Extract `notes[]` array — each entry provides `path`, `filename`, `frontmatter`, `outgoing_links`, and `line_count`.

### Step 2: Run Checks

For each enabled check (1-12), run its method from [references/checks.md](references/checks.md) and collect findings as structured data:

```
{check_id, severity, note_path, detail, fixable}
```

### Step 3: Propose Fixes (if --fix)

Only runs when `--fix` flag is provided. Present each proposed fix to the user and apply only the ones explicitly approved; write no log. Fixable checks: 5, 6, 7, 10. Checks 11 and 12 are NOT auto-fixable; among the Concept-First / Hybrid Mode group, only Check 10 remains auto-fixable.

For each fixable finding:
1. **Check 5 (Weak links)**: Use `vault-knowledge search "<terms>" --limit N` and `read` to find related notes, propose suggested links with rationale to `### Links`
2. **Check 6 (Concept gaps)**: Create stub notes with Train-Case naming, minimal frontmatter, stub Abstract
3. **Check 7 (Cross-ref gaps)**: Add cross-references to `### Links` sections of both notes in the pair
4. **Check 10 (Legacy `--preserve` artifacts)**: Apply the conservative fixes documented under Check 10 — delete `format_mode`/`preserve` frontmatter keys, rename `### Abstract` → `### Definition` only when safe. Never touch `### Content` or preserve-era marker comments automatically.

After approved fixes are applied, re-run the affected checks to confirm resolution.

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
Summary: {H} HIGH | {M} MEDIUM | {L} LOW | {F} fixed (user-approved)
```

## Edge Cases

**Empty directory:** Report "No notes found in {path}" and exit.

**--checks with invalid numbers:** Ignore invalid check numbers, warn the user, run valid ones.

**--fix without fixable issues:** Report "No fixable issues found" in the summary.

**Large vault (whole-vault scan):** Process in batches by top-level directory (111.cs/, 222.web/, etc.) to manage context. Report per-directory then aggregate.

**Notes without frontmatter:** Skip checks that depend on frontmatter fields (2, 7). Still run checks 1, 3, 4, 5. For Checks 8 and 9, a missing/unparseable `Date` is treated as post-ADR per the severity-gating helper — the check still runs at full intrinsic severity. Check 10 inspects frontmatter for `format_mode`/`preserve` keys but degrades gracefully if no frontmatter is present (body-heading and marker-comment scans still apply). For Checks 11 and 12, a missing `Mode` field cannot be branched on — Check 8 flags the missing `Mode` as its own finding, and Checks 11 and 12 skip the note entirely (they only run when `Mode: thesis` is explicit).
