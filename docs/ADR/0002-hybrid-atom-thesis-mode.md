# ADR-0002 — Hybrid Atom / Thesis Note Modes

**Status:** Accepted
**Date:** 2026-05-29
**Adoption date:** 2026-05-29
**Supplements:** ADR-0001 (amends D3, D4, D5 partial overrides; D2, D6, D7, D8, D9, D10 remain in effect unchanged)
**Superseded by:** None

---

## Context

ADR-0001 landed the Concept-First pipeline on the assumption that **every note maps to a single atomic concept**. Stages 1–4 implemented this faithfully: discover → distill → integrate, with a 500-char hard ceiling and a Concept-First skeleton (`### Definition` / `### Mental Model` / optional `### Why It Matters` / `### Boundary` / `### Code` / `### Links`).

A dry-run on a 12-minute YouTube video using a bubble tea franchise metaphor to argue **"architecture upgrades are forced by traffic bottlenecks, not pre-designed"** surfaced a deep gap. Under the strict-atomicity rules, the natural output was:

- Primary note: one atom (the macro claim)
- Spinoff backlog: 9 sub-concepts (Cache, Docker, CI/CD, Load Balancer, Read Replica, Microservice, CDN, Rate Limiter, Queue)

But the 9 sub-concepts are not independently atomic for this source — they are the *cascade stages* that the macro claim describes. Removing any one of them guts the Mental Model. They belong **in the same note** as the macro claim.

A first patch (Step 4 of the modeler) added a "necessity test" that fixed the false-positive spinoff problem. But the deeper realization is that the source itself is a **thesis with supporting evidence**, not an atomic concept — and the pipeline lacks a way to express that note shape.

User input refined the requirement further by referencing a real Obsidian note (a ~10,000-character multi-chapter synthesis report on Claude Code best practices) as the aspirational template for thesis-style notes. That reference revealed:

- Thesis-style notes are **synthesis dossiers**, not mini-essays
- They use executive summaries, multiple `### <Theme>` chapters, comparison tables, authority quotes, ASCII decision trees, and appendices with templates
- They cannot fit in a 500-char budget — and shouldn't, because their dilution risk is structural (rambling sections), not lexical (verbose prose)

This ADR introduces a **hybrid mode** so the pipeline can produce both atomic concept notes (ADR-0001 style) and thesis-style synthesis notes (new), with the modeler choosing per source.

---

## Decisions

### D1. Hybrid `note_mode`: **atom** or **thesis**

A note is either:

- **atom** — captures a single atomic concept with the Concept-First skeleton from ADR-0001 D5.
- **thesis** — captures a macro thesis with supporting evidence organized into chapters, with a synthesis-dossier skeleton (D4 below).

Both modes coexist in the same vault. Each note declares its mode in frontmatter (`Mode: atom | thesis` — see D8). All downstream tooling (formatter, vault-lint, future spinoff-flush) is mode-aware.

**Rejected:**

- *Hub-and-spoke* (every note is an atom, sub-concepts mandatorily spawn back-links) — fragments coherent arguments and forces readers to traverse 10 notes to understand one thesis.
- *Single superset skeleton* (Definition section overloaded to carry thesis content) — `### Definition` is a declarative speech act; `### 執行摘要` is an argumentative one. Conflating them produces inconsistent reading experience.

### D2. Mode classification is decided by `conceptual-modeler-agent`

The modeler picks `note_mode` based on signals inferred from the source content. No user flag, no upstream pre-classification.

**Atom signals (any one is sufficient):**

- Source primarily *defines* a single concept (e.g., a glossary-style explanation).
- Sub-concepts mentioned in source are vocabulary, not supporting structure.
- Source ≤ ~15 minutes of video / ≤ ~2000 words of text (rough thresholds, not gates).
- Examples: "HTTP GET verb", "React Server Components definition", "Pure function".

**Thesis signals (any one is sufficient):**

- Source has multiple supporting themes that buttress a macro claim.
- Source uses metaphor / argument structure / multi-authority citation / comparison frame.
- Source is organized into chapters or numbered sections.
- Source ≥ ~15 minutes of video / ≥ ~2000 words of text.
- Examples: bubble tea metaphor for scaling (`Demand-Driven Scaling`), design principle videos, comprehensive how-to guides.

**Edge case — long deep-dive defining one concept** (e.g., a 30-min video that defines React Server Components deeply): **content wins over duration**. Pick `atom`. The modeler may still use a richer `### Mental Model` and longer code examples, but the skeleton stays atom-shaped.

**Rejected:**

- *User specifies via CLI flag (`--mode=thesis`)* — kills batch ingestion ergonomics; user usually has not read the source before invoking.
- *zettelkasten-agent (discover layer) decides* — discover stage is sonnet + surface-level classification; insufficient context to judge argument structure.

### D3. **Atom skeleton: unchanged from ADR-0001 D5**

Restated here for completeness only. No semantic change.

**Required:** `### Definition`, `### Mental Model`, `### Links`.
**Optional:** `### Why It Matters`, `### Boundary`, `### Code`.

ADR-0001 D5's inclusion criteria, char-budget rules, and Mental Model fallback chain (D6) apply unchanged when `note_mode = atom`.

### D4. **Thesis skeleton (new)**

```markdown
---
[frontmatter]
Mode: thesis
---

### 執行摘要
<2–3 paragraphs previewing all supporting themes>

> **核心論點：<thesis statement, bold inside blockquote>**

### Mental Model
<top-level diagram showing the structural relationship across themes — ASCII / Mermaid / Image>

### <Theme 1>
<1–3 paragraphs of prose + at least one table or block quote>

#### <Sub-section 1.1 (optional, when theme has natural sub-structure)>

### <Theme 2>
...

### <Theme N>
...

### 附錄 / Appendix (optional)
- A: Reusable templates extracted from source
- B: Quick-decision reference tables
- C: Tool / resource index

### Links
- 延伸閱讀 [[Deep-Note-X]] (when a theme's sub-concept already has a dedicated vault note)
- 來源 [[row/src-...]]
```

**Required sections:** `### 執行摘要`, `### Mental Model`, **at least one** `### <Theme>` chapter, `### Links`.

**Optional sections:** `### 附錄`.

**Removed vs atom:** `### Boundary`. The thesis itself implicitly bounds the argument; competing claims belong as a dedicated `### <Counter-Theme>` chapter, not as a single section.

**Removed vs atom:** `### Code`. Thesis-style notes are macro views; if a source demands code as the primary teaching device, the modeler should classify as `atom` and use atom's `### Code` section.

### D5. **Budget rules per mode**

- **Atom mode:** 500-char hard ceiling (unchanged from ADR-0001 D4). Calculation rule unchanged.
- **Thesis mode:** **no hard ceiling**. Each `### <Theme>` chapter has a **soft target of 200–1500 chars** (counting Chinese characters + English words, excluding code blocks / diagrams / Links — same exclusion rules as ADR-0001 D4).

Why no hard ceiling for thesis: thesis dilution risk is *structural* (rambling chapters, missing tables, missing quotes), not *lexical* (verbose prose). A hard ceiling would force the modeler to strip tables / quotes / decision-trees to fit budget — the opposite of the desired discipline.

When a thesis chapter naturally exceeds ~1500 chars, the modeler must either compress (preferred) or trigger the theme-overflow back-link mechanism (D7).

### D6. **Thesis structural discipline (replacement for char-cap discipline)**

The modeler must enforce three structural rules on thesis-mode chapters:

- **One atom per chapter** — every `### <Theme>` chapter must develop exactly one supporting argument. If a chapter would need to make two distinct claims, split it.
- **Table-first for comparisons** — any comparison / classification / decision tree must use a Markdown table or an ASCII tree. Never list comparisons as bullet prose.
- **Quote-for-authority** — authoritative statements from named experts cited in the source go in `> ` block quotes, not paraphrased prose. The reader sees the original framing.

`vault-lint` Check 11 (new — see D9 / Adoption Checklist) validates per-chapter char range; the structural rules are modeler self-discipline and not lint-enforced (too subjective for automated checks).

### D7. **Theme overflow → inline chapter + back-link (not pure replacement)**

When a `### <Theme>` chapter's natural content would exceed 1500 chars *because the theme itself has become its own thesis-worthy topic* (i.e., the theme has its own Mental Model and multiple supporting sub-themes), the modeler:

1. Keeps the theme as an **inline chapter** in the primary note, containing the *essence* of the theme (the 1–3 paragraphs that buttress the primary thesis).
2. Appends a back-link sentence at the end of the chapter: `完整討論見 [[Deep-Note-X]]` or `For extended treatment, see [[Deep-Note-X]]`.
3. Emits a `spinoff_candidate` in the modeler output payload with `rationale: "thesis chapter overflow — sub-concept has its own thesis-worthy structure"`. This routes to `row/_spinoffs.md` via the same backlog mechanism as ADR-0001 D3.

**Trigger criterion:** char overflow alone is **not** the trigger. The trigger is *"the theme has become an independent thesis"*. If the theme can be compressed to ≤ 1500 chars without losing its supporting role, compress it. Only trigger back-link when compression would strip out the theme's own internal thesis structure.

This unifies thesis chapter overflow with ADR-0001 D3's spinoff mechanism: both feed `row/_spinoffs.md`, both are flushed by the future `/spinoff-flush`.

**Rejected:**

- *Pure back-link (theme replaced by a one-line `See [[...]]`)* — gut thesis completeness; reader must traverse to understand the macro argument.
- *Char-count trigger* — disrespects content density; a tight, well-tabled chapter may sit at 1300 chars without overflowing structurally.

### D8. **Frontmatter: add `Mode: atom | thesis`**

Note frontmatter gains one required field:

```yaml
Mode: atom        # or
Mode: thesis
```

Rationale: `vault-lint` needs an explicit signal to apply the correct required-core check (D3 vs D4) and the correct budget rule (D5). Heuristic detection from body content is unreliable when bodies are mid-migration or partially malformed.

`obsidian-formatter-agent` writes the field based on the modeler's `note_mode` output.

### D9. **vault-lint impact**

ADR-0001's Checks 8, 9, 10 (the Concept-First conformance trio) are revised:

- **Check 8 — Missing required-core section** — gains mode awareness. For `Mode: atom`, requires Definition / Mental Model / Links. For `Mode: thesis`, requires 執行摘要 / Mental Model / at least one `### <Theme>` / Links.
- **Check 9 — Body over budget** — applies only to `Mode: atom` (500-char ceiling). Thesis notes are exempt from this flat check.
- **Check 10 — Legacy `--preserve` artifacts** — unchanged.

Two new checks land in this amendment:

- **Check 11 — Per-chapter char range (thesis only)** — for each `### <Theme>` chapter, count chars (per the D5 calculation rule). Flag chapters < 200 chars (too thin) or > 1500 chars (too dense — should compress or trigger back-link per D7). Severity: MEDIUM for post-adoption notes, LOW pre-adoption.
- **Check 12 — Dangling thesis back-link** — for each `[[...]]` wikilink inside a `### <Theme>` chapter, verify the target exists in the vault **or** appears as an open item in `row/_spinoffs.md`. Flag dangling links. Severity: LOW (back-links pointing to not-yet-promoted spinoffs are expected during a healthy backlog cycle).

The ADR-0001 adoption-date severity-gating (D10 / δ) extends to Checks 11–12: pre-adoption notes get LOW severity for these new checks, post-adoption get the intrinsic severity.

### D10. **Implementation order — B1 redux**

Same inside-out order as ADR-0001 D8:

1. **This ADR lands first**, in its own commit.
2. **CLAUDE.md amendment** — top-level introduce mode concept; show both skeletons; cross-reference ADR-0002.
3. **`agents/conceptual-modeler-agent.md`** — add mode classification step; expand output schema to include `note_mode`; add thesis-mode procedure branch; update spinoff detection to include theme overflow.
4. **`agents/obsidian-formatter-agent.md`** — mode-aware assembly (atom vs thesis skeleton branching); write `Mode:` frontmatter.
5. **`skills/zk-note/SKILL.md`** — propagate `note_mode` between modeler and formatter; report includes the chosen mode.
6. **`commands/*.md`** — pipeline description blocks mention mode classification.
7. **`skills/vault-lint/SKILL.md`** — Check 8 mode branching, Check 9 atom-only restriction, Check 11 new, Check 12 new.

Commit strategy: same PR, separate commits, one per stage.

---

## Inherits unchanged from ADR-0001

The following Decisions from ADR-0001 remain in full effect:

- **D2** — 3-stage pipeline (Discover → Distill → Integrate)
- **D6** — diagram modality routing (Image > ASCII > Mermaid > Structural Bullets), modeler emits `modality_hint`
- **D7** — Layout A responsibility split (sonnet / opus / sonnet across discover / distill / integrate)
- **D8** — Adoption scope and order pattern
- **D9** — CLAUDE.md as developer memory (not end-user docs); single-component specs live in component files
- **D10** — Migration strategy (γ + δ): batch-migration command deferred, severity gating for pre-adoption notes

The ADR-0001 Future Tooling list (video-frame-capture, `/vault-migrate`, `/spinoff-flush`, spinoff backlog source-reference staleness) is also unchanged. `/spinoff-flush` design now must handle both atom-mode spinoffs and thesis-mode theme-overflow spinoffs — but those share the same backlog format, so no design impact yet.

---

## Consequences

### Positive

- Pipeline can now produce both note shapes the user actually wants: atomic concepts AND synthesis dossiers.
- Thesis-mode dilution risk is structurally controlled (1-atom-per-chapter rule + table-first rule) instead of via brittle char count.
- Theme overflow reuses the existing spinoff backlog — no new queue, no new flush command.
- Mode classification is automatic; no user flag burden.
- Atom-mode behavior is unchanged; ADR-0001's Stages 1–4 outputs remain valid for atom-shaped sources.

### Negative / accepted trade-offs

- Modeler agent prompt is meaningfully longer (mode classification + dual procedure branches).
- `vault-lint` complexity increases (mode-aware checks).
- Notes will be visually inconsistent across the vault — some short (atom), some long (thesis). Reader must accept that note length is mode-derived, not a quality signal.
- Existing atom-only notes from Stages 1–4 will need their frontmatter retrofitted with `Mode: atom` (a trivial migration; lint Check 8 will flag missing field).

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Modeler mis-classifies an atom source as thesis (or vice versa) | Mode is part of modeler output and surfaced in completion report; user can re-run with `--force-mode` (future flag) if needed |
| Thesis chapters bloat past 1500 chars routinely | Check 11 LOW severity tells modeler-prompt-tuner where to tighten without false-positive panic |
| Theme overflow spinoffs grow `row/_spinoffs.md` faster than `/spinoff-flush` clears it | Same backlog management problem as ADR-0001 D3; pre-existing |
| Reader confusion about which mode a note is | `Mode: atom \| thesis` frontmatter field is the single source of truth; Obsidian dataview queries can group/filter by mode |

---

## Alternatives considered (rejected)

### A1. Hub-and-spoke for all notes

Every note becomes an atom; supporting sub-concepts mandatorily spawn back-links. Rejected — fragments coherent theses and forces reader traversal to understand one argument. Conflicts with user's intent that "supporting points should illuminate the parent thesis in the same file".

### A2. Single superset skeleton

One skeleton with `### Definition` carrying both atomic definitions and thesis statements. Rejected — declarative vs argumentative speech acts under one heading produces inconsistent reading experience; vault-lint cannot distinguish modes; modeler prompt branches inside one section anyway.

### A3. Two completely separate skeletons (P2 in grilling)

Atom skeleton and thesis skeleton are independent; no shared core. Rejected — duplicates Mental Model and Links section descriptions; thesis budget tuned to 750 chars (arbitrary).

### A4. Single skeleton with mode-overloaded Definition (P3 in grilling)

All notes use atom skeleton; thesis content packed into `### Definition`. Rejected — awkward semantic overload; reader cannot distinguish mode at a glance.

### A5. Hard char ceiling for thesis (500 or 750 or 1000)

Thesis mode inherits a flat char cap. Rejected — kills tables, quotes, ASCII decision trees (the structural elements that make thesis notes valuable). Dilution discipline in thesis comes from structure, not lexical count.

### A6. Theme overflow → pure back-link replacement

When a theme would exceed 1500 chars, replace the inline chapter with a single `See [[Deep-Note]]` line. Rejected — guts the thesis's completeness; the primary note becomes a table of contents.

### A7. Theme overflow trigger by char count

The trigger for back-link is when char count exceeds 1500. Rejected — disrespects content density; a tight, well-tabled chapter can pack ~1300 chars without overflowing structurally.

### A8. User specifies mode via CLI flag

`/source-to-zk <url> --mode=thesis`. Rejected — breaks batch ingestion ergonomics; user often hasn't read the source when invoking.

### A9. ADR-0001 in-place amendment

Append D11+ to ADR-0001, leaving D3/D4/D5 partially superseded inside the same document. Rejected — violates "Accepted ADRs are immutable" convention; future readers must mentally subtract D3/D4/D5 fragments and apply amendments.

### A10. ADR-0002 fully supersedes ADR-0001

ADR-0002 contains a clean rewrite; ADR-0001 marked Superseded. Rejected — D2, D6, D7, D8, D9, D10 are unchanged; copying them verbatim is overkill and buries the original grill context that documented why those decisions were made.

---

## Adoption Checklist (for the implementing PR)

- [ ] CLAUDE.md updated with mode concept overview, both skeleton summaries, and cross-reference to ADR-0002. Spinoff backlog convention extended to cover theme-overflow rationale.
- [ ] `agents/conceptual-modeler-agent.md`:
  - [ ] New Step 1.5 "Classify note_mode" with signal tables and edge-case rule
  - [ ] Output schema gains `note_mode: "atom" | "thesis"` (required)
  - [ ] Thesis branch of Step 2+ procedure (執行摘要 → Mental Model → Theme enumeration → per-theme atom enforcement → 附錄 decision)
  - [ ] Spinoff detection (Step 4) expanded to include theme-overflow trigger per D7
  - [ ] Self-check (Step 5) branches: atom mode counts ≤ 500 chars; thesis mode counts per-chapter 200–1500
- [ ] `agents/obsidian-formatter-agent.md`:
  - [ ] Inputs accept `note_mode`
  - [ ] Step 4 assembly branches by mode
  - [ ] Step 3 frontmatter writes `Mode: atom | thesis`
- [ ] `skills/zk-note/SKILL.md`:
  - [ ] Modeler delegation prompt expects `note_mode` in returned payload
  - [ ] Formatter delegation prompt passes `note_mode` through
  - [ ] Completion report includes the chosen mode
- [ ] `commands/source-to-zk.md`, `commands/query-to-note.md`, `commands/notion-to-zk.md`:
  - [ ] Pipeline description mentions mode classification as part of distill stage
- [ ] `skills/vault-lint/SKILL.md`:
  - [ ] Check 8 mode-aware required-core check
  - [ ] Check 9 restricted to `Mode: atom`
  - [ ] Check 11 new: per-chapter char range (thesis)
  - [ ] Check 12 new: dangling thesis back-link
  - [ ] Existing severity-gating (ADR-0001 D10 / δ) extended to Checks 11–12
- [ ] `README.md` updated to "12 checks" with brief descriptions of 11, 12; mode concept mentioned.
- [ ] Adoption date filled in at top of this ADR on merge.
