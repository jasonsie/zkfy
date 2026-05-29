# ADR-0001 — Concept-First Pipeline for Zettelkasten Note Synthesis

**Status:** Accepted
**Date:** 2026-05-28
**Adoption date:** 2026-05-28
**Supersedes:** None
**Superseded by:** None

---

## Context

The current `zk-note` pipeline (zettelkasten-agent → obsidian-formatter-agent) produces notes that suffer from two coupled defects:

1. **Concept dilution** — the atomic concept is identified but immediately diluted in Feynman-style prose, bad/good code patterns, and free-form synthesis. The resulting note teaches the concept but does not _crystallize_ it.
2. **No conceptual model layer** — there is no intermediate artifact between "atomic concept name" and "written content sections" that captures the concept's minimal mental model. As a direct consequence, diagrams never get generated: `diagram-agent` exists but has no structured input to consume from the pipeline, so notes ship without visual representation.

Symptomatically, this manifests as:

- Notes regularly exceed 500 characters of prose, often 2–3×.
- Diagrams are absent in the vast majority of generated notes.
- Multi-concept source material is squeezed into a single note, violating Zettelkasten atomicity.

This ADR resolves all three symptoms with a single coordinated refactor.

---

## Decisions

### D1. Diagnose as **concept dilution + missing conceptual model layer**

The two failure modes share a common root: the original `zettelkasten-agent` collapses _distillation_ and _synthesis_ into one step. We treat them as two distinct cognitive activities and separate them.

### D2. Three-stage pipeline: **Discover → Distill → Integrate**

```
┌───────────────────────┐    ┌──────────────────────────┐    ┌──────────────────────────┐
│  zettelkasten-agent   │ →  │  conceptual-modeler-agent│ →  │ obsidian-formatter-agent │
│  (Discover, sonnet)   │    │  (Distill, opus)         │    │  (Integrate, sonnet)     │
└───────────────────────┘    └──────────────────────────┘    └──────────────────────────┘
```

A new agent `conceptual-modeler-agent` is introduced. Distillation responsibilities move out of `zettelkasten-agent`. `obsidian-formatter-agent` is unchanged in role, lightly adjusted in inputs.

See **D7** for the precise responsibility split.

### D3. Multi-atom strategy: **primary note + spinoff backlog**

When source material contains multiple atomic concepts, the pipeline:

1. Produces _one_ primary note immediately (the most prominent concept).
2. Records all other **independently atomic** concepts in a backlog file (`row/_spinoffs.md`; see CLAUDE.md "Spinoff backlog convention").
3. User reviews the backlog and chooses which spinoffs to promote into full notes via a future flush command.

**Rejected:** automatic fan-out (corrupts vault on misclassification), interactive prompt per source (kills batch ingestion ergonomics).

**Spinoff candidate criterion (necessity test).** Not every concept the source mentions is a spinoff. A concept earns spinoff status only if the source treats it as its own atom AND removing it from the primary note would not damage the primary concept's exposition. Stages of a cascade, supporting evidence, and passing vocabulary all stay embedded in the primary note's `### Mental Model` / `### Why It Matters` / `### Boundary`. The full test (with worked example using a bubble-tea-metaphor scaling video) is documented in `agents/conceptual-modeler-agent.md` Step 4. Most notes should yield 0–2 spinoffs; payloads of 5+ are a smell.

### D4. **500-character hard limit** per note body

Measured as: Chinese characters + English words, **excluding** frontmatter, fenced code blocks, embedded diagrams (Mermaid/ASCII/Image), and the `### Links` section.

This budget covers `### Definition`, `### Why It Matters`, `### Boundary`, and any prose surrounding diagrams or code.

`conceptual-modeler-agent` self-checks the budget and reports `char_budget.total` in its output. `vault-lint` enforces the limit as an external gate (see D8).

### D5. **Concept-First note skeleton** — required core + agent-discretion optionals

The skeleton below is the **maximal template**. `conceptual-modeler-agent` decides which optional sections to include based on concept complexity. The 500-char budget (D4) applies regardless of which sections are present.

**Required sections** (always present in every note):

- `### Definition` — one-line definition, ≤ 50 chars, no word larger than the concept itself.
- `### Mental Model` — diagram (Image / Mermaid / ASCII) or Structural Bullets fallback. **Not counted** toward the 500-char budget.
- `### Links` — relationship list. **Not counted** toward budget.

**Optional sections** (modeler's discretion, criteria below):

| Section | Include when … | Skip when … |
|---|---|---|
| `### Why It Matters` | The concept's motivation is non-obvious or commonly misunderstood (e.g., "React Server Components", "Eventual Consistency") | The motivation is self-evident from the Definition (e.g., "HTTP GET verb", "Array.length") |
| `### Boundary` | The concept is frequently confused with a related one and the boundary needs explicit reinforcement (e.g., "Process vs Thread", "Map vs WeakMap") | No common confusion exists; Boundary would be padding |
| `### Code` | The concept is implementation-level and a minimal runnable example sharpens understanding | The concept is abstract (a principle, a system property) or non-programming |

The agent must justify inclusion implicitly via the content itself — if a Boundary section reads like a stretch, the modeler should have skipped it. `vault-lint` will not enforce a minimum section count; it only enforces the 500-char ceiling and the required-core presence.

**Minimal note example** (atomic concept with no need for elaboration):

```markdown
---
[frontmatter]
---

### Definition
<one line, ≤ 50 chars>

### Mental Model
<diagram or Structural Bullets>

### Links
- Related to [[X]] because ...
```

**Maximal note example** (concept benefiting from full elaboration):

```markdown
---
[frontmatter]
---

### Definition
<one line>

### Mental Model
<diagram>

### Why It Matters
- <bullet 1, ≤ 30 chars>
- <bullet 2>

### Boundary
- This is NOT <X>

### Code
<minimal runnable example>

### Links
- ...
```

**`--preserve` mode is removed.** Preserve semantics is incompatible with the 500-char budget. If raw-content storage remains useful, it belongs in a separate command (e.g., a future `/source-to-raw`), not in `zk-note`.

### D6. Diagram routing: **β + β1 + C1**

- **β — best-effort with structured fallback.** Always attempt to render a diagram. If all three modalities fail, fall back to a **Structural Bullets** list (≤ 5 component lines) under `### Mental Model`. Never fall back to free prose.
- **β1 — CLAUDE.md priority order is authoritative.** Order: **Image > ASCII > Mermaid > Structural Bullets**. `agents/diagram-agent.md` currently asserts "use Mermaid for Obsidian" — this assertion is wrong and must be updated to align with CLAUDE.md as part of this refactor.
- **C1 — `conceptual-modeler-agent` decides modality, `diagram-agent` executes.** The modeler emits `mental_model.modality_hint` based on its understanding of the concept. The diagram agent consumes the hint and renders. This keeps modality decisions at the layer that has full conceptual context.

### D7. **Layout A** — responsibility split

| Stage | Agent | Model | Responsibilities |
|---|---|---|---|
| Discover | `zettelkasten-agent` | sonnet (downgraded from opus) | Atomic concept name; domain selection; metadata classification (Categories / Sub-Categories / Aliases / tags); related-notes discovery |
| Distill | `conceptual-modeler-agent` (NEW) | opus | `one_line_definition`; `mental_model` (modality_hint + description + source_image); `why_it_matters`; `boundary`; `code_example`; `spinoff_candidates`; `char_budget` self-check |
| Integrate | `obsidian-formatter-agent` | sonnet | Filename; frontmatter; neighbor wiring (Before/Next); MOC updates; file write |

`zettelkasten-agent`'s opus → sonnet downgrade is justified because: (a) the heavy reasoning work (Feynman synthesis, code patterns) moves out; (b) controlled-vocabulary metadata classification is a mapping task, not a reasoning task; (c) related-notes discovery is dominated by Grep/Glob lookups with light semantic ranking — sonnet is sufficient.

### D8. **Scope A1 + order B1 + ADR-first**

**Scope (A1):** full surface in one refactor — agents (new `conceptual-modeler-agent`, slimmed `zettelkasten-agent`, lightly adjusted `obsidian-formatter-agent`) + `zk-note` skill (3-stage orchestration) + 3 commands (`source-to-zk`, `query-to-note`, `notion-to-zk` description blocks updated) + `vault-lint` (new checks for Concept-First conformance).

**Order (B1, inside-out):**

1. This ADR lands first (Proposed → Accepted on user approval).
2. CLAUDE.md updates in a sibling commit, same PR (see D9).
3. Agents implemented bottom-up.
4. `zk-note` skill rewired.
5. Commands' description blocks updated.
6. `vault-lint` checks added.

**Commit strategy:** same PR, separate commits. At minimum:

- `docs(adr): add ADR-0001 concept-first pipeline`
- `docs(claude): align CLAUDE.md with ADR-0001`
- Followed by implementation commits, one logical unit per commit.

### D9. **CLAUDE.md updates** (atomic with this ADR)

**Scope clarification.** CLAUDE.md is the **developer memory for maintaining the zkfy plugin codebase**. It is _not_ end-user documentation about "how to use zkfy in your vault" — that surface belongs in `README.md` and the individual skill/agent files. Updates below are therefore framed as developer invariants future contributors must preserve, not as user-facing rules.

The following lines/sections in CLAUDE.md must change in lockstep with this ADR:

- **Pipeline description: 2-stage → 3-stage** (zettelkasten / modeler / formatter). Maintainers need to know the pipeline shape before adding or modifying agents.
- **Spinoff backlog convention** — list the backlog path alongside `log.md` and `index.md` as "auto-generated, do not hand-edit", so contributors do not accidentally corrupt it during routine work.
- **500-character hard constraint and calculation rule** — a single source of truth for the invariant that future agent authors and `vault-lint` maintainers can point at.
- **Diagram rule extended**: append "→ Structural Bullets" as final fallback to the existing Image → ASCII → Mermaid chain.
- **`--preserve` mode removed** — so new code does not reference the deprecated flag.
- **Cross-reference**: `See ADR-0001 for rationale.`

**Boundary between CLAUDE.md and other docs:**

- CLAUDE.md carries **cross-cutting invariants** that span multiple files and that any contributor needs to know.
- The **authoritative spec for any single component** (e.g., the modeler's full output schema, the formatter's frontmatter assembly logic) lives in that component's own SKILL.md / agent file. CLAUDE.md does not duplicate it.
- ADR-0001 remains the immutable rationale. CLAUDE.md captures the resulting rules in rule-book form.

### D10. Migration of pre-existing notes: **γ + δ hybrid, opt-in**

- **δ (severity gating, lands in this refactor):** `vault-lint` reports Concept-First violations as **LOW severity** for notes whose `Date` predates ADR-0001 adoption. The same violations on post-adoption notes are reported at **MEDIUM/HIGH**.
- **γ (batch migration, deferred):** a future `/vault-migrate` command will provide opt-in batch migration with a review queue (`_migration_review/`). Never auto-overwrites unless `--auto-accept` is explicitly passed. **Deferred to a separate session** (see TODO.md).

**Explicitly rejected:** lazy migration on edit (β in the original grill). Touching a note for an unrelated reason must never trigger content rewrite — this destroys user trust and creates a category of bugs (silent migration corruption) that we are unwilling to accept.

---

## Consequences

### Positive

- Notes ship with structured Mental Model, eliminating "no diagrams" complaint.
- 500-char enforcement at three layers (modeler self-check, formatter rejection, vault-lint gate) makes concept dilution structurally impossible.
- Spinoff backlog preserves atomicity without sacrificing batch ingestion ergonomics.
- Agent specialization enables independent model selection per stage (cost down ~30–40% for the discover stage with sonnet).
- Clear extension surfaces: future commands like `/vault-migrate`, `/spinoff-flush` slot into existing pipeline without re-architecting.

### Negative / accepted trade-offs

- One additional Task round-trip per note (modeler is a new agent invocation). Latency increases by roughly the cost of one opus call.
- `--preserve` mode is deleted. Users who relied on raw-content storage must migrate to a future `/source-to-raw` or store raw materials outside the vault.
- Pre-ADR notes look stylistically different from post-ADR notes until manually migrated. Vault visual inconsistency is the price of forward progress.
- `diagram-agent.md` carries a known contradiction with CLAUDE.md until the modality-priority commit lands. The contradiction is documented here so future readers do not mistake it for ambiguity.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Modeler hallucinates a forced "Mental Model" for inherently non-spatial concepts | Structural Bullets fallback (D6); diagrammable-ness is graceful, not mandatory |
| 500-char budget too tight for some legitimate notes | Re-evaluate after 30 days of usage; budget is a starting point, ADR-0002 can revise |
| Spinoff backlog grows unbounded | TODO follow-up: `/spinoff-flush` command with aging / expiry policy |
| Sonnet on `zettelkasten-agent` misclassifies metadata | `vault-lint`'s metadata check catches this; opus escalation is cheap to re-enable |

---

## Alternatives considered

### A1. Insert Step 2.5 inside the existing `zettelkasten-agent` (no new agent)

Rejected. The agent is already overloaded; piling on more responsibilities continues the trajectory that caused the dilution problem in the first place. Separation makes each prompt simpler and lets each stage be model-tuned independently.

### A2. Four-stage pipeline (split classification & relationship into their own agents)

Rejected as over-engineering for current vault size. Reconsider if (a) `related_notes` discovery becomes a latency bottleneck or (b) `metadata` classification accuracy regresses below an acceptable bar with sonnet.

### A3. Atomic-Card skeleton (mandatory diagram, no prose)

Rejected. Some legitimate atomic concepts (e.g., "database atomicity", "structural typing") are rule-like, not spatial. Forcing a diagram would either fail-loud needlessly or produce nonsense visualizations. Concept-First with graceful Structural-Bullets fallback is the better default.

### A4. Hybrid digest/preserve dual-mode

Rejected. The 500-char budget and verbatim source preservation are fundamentally incompatible. Trying to keep both modes in `zk-note` would force one to constantly compromise the other. Preserve semantics belongs in a separate, single-purpose command.

### A5. Automatic fan-out for multi-atom sources

Rejected. Misclassification corrupts the vault. Atomicity boundaries are exactly the kind of decision that benefits from a human review gate; the spinoff backlog provides that gate without blocking ingestion throughput.

### A6. Lazy migration on touch (β in migration grill)

Rejected. Silent content rewrites destroy user trust. Migration must be explicitly invoked, with diff preview, with the original preserved until accepted.

### A7. β2 modality order (Mermaid > ASCII to match `diagram-agent.md`)

Rejected by user preference for ASCII portability across rendering contexts (terminal, plain-text export, non-Obsidian readers). `diagram-agent.md` is the document that must yield, not CLAUDE.md.

---

## Future Tooling (not implemented in this ADR, captured here for traceability)

The following items are deferred to subsequent sessions but are part of the long-term shape of this design. They live in `TODO.md` with full acceptance criteria:

1. **`video-frame-capture` → `source_image`** — populate `mental_model.source_image` from video sources via frame extraction at semantically meaningful timestamps.
2. **`/vault-migrate <path>`** — opt-in batch migration command for pre-ADR notes, with `_migration_review/` queue and explicit `--auto-accept` gating.
3. **`/spinoff-flush`** — promote spinoff backlog entries into full notes interactively.
4. **Aging / expiry policy for spinoff backlog** — prevent unbounded growth.

---

## Adoption checklist (for the implementing PR)

- [ ] CLAUDE.md updated per D9 in a sibling commit.
- [ ] `agents/conceptual-modeler-agent.md` created with the schema in D7.
- [ ] `agents/zettelkasten-agent.md` slimmed per D7; model frontmatter changed to `sonnet`.
- [ ] `agents/obsidian-formatter-agent.md` adjusted to consume the new modeler output (Definition / Mental Model / Why / Boundary sections) and to drop `--preserve` branching.
- [ ] `agents/diagram-agent.md` modality priority aligned with CLAUDE.md (Image > ASCII > Mermaid > Structural Bullets).
- [ ] `skills/zk-note/SKILL.md` rewired to 3-stage pipeline; `--preserve` flag removed.
- [ ] `commands/source-to-zk.md`, `commands/query-to-note.md`, `commands/notion-to-zk.md` pipeline-description blocks updated.
- [ ] `skills/vault-lint/SKILL.md` extended with checks for the **required-core** sections only (`### Definition`, `### Mental Model`, `### Links` — per D5), body > 500 chars (per D4), and presence of legacy `--preserve` artifacts. **Do not** check for `### Why It Matters`, `### Boundary`, or `### Code` — these are optional by D5 and lint must not flag their absence.
- [ ] `vault-lint` severity-gates Concept-First violations by `Date` vs adoption date (D10 / δ).
- [ ] Adoption date filled in at the top of this ADR on merge.
