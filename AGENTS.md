# CLAUDE.md

zkfy is a Claude Code plugin that turns URLs, videos, and raw text into Zettelkasten literature notes for an Obsidian vault. Three commands drive everything: `/source-to-zk` (ingest), `/query-to-note` (synthesize from existing notes), `/vault-lint` (semantic health check). Agent definitions live in `agents/`, skill modules in `skills/` — read those files for specifics rather than relying on this document.

## Scope clarification

CLAUDE.md is the **developer memory for maintaining the zkfy plugin codebase**. It is _not_ end-user documentation about "how to use zkfy in your vault" — that surface lives in `README.md` and the individual skill/agent files. The rules below are cross-cutting invariants future contributors must preserve. Authoritative single-component specs (modeler output schema, formatter assembly logic, etc.) live in the relevant agent/skill files; CLAUDE.md does not duplicate them.

See `docs/ADR/0001-concept-first-pipeline.md` and `docs/ADR/0002-hybrid-atom-thesis-mode.md` for rationale.

## Pipeline shape (3-stage)

Note synthesis runs through three agents in order: **Discover → Distill → Integrate**.

```
zettelkasten-agent (Discover, sonnet)
  → conceptual-modeler-agent (Distill, opus)
    → obsidian-formatter-agent (Integrate, sonnet)
```

- **zettelkasten-agent** identifies the atomic concept, picks the domain, classifies metadata (Categories / Sub-Categories / Aliases / tags), and discovers related notes. No distillation.
- **conceptual-modeler-agent** classifies `note_mode` (atom vs thesis) at the start of Distill, then branches its output skeleton accordingly: atom-mode produces `one_line_definition` + optional `why_it_matters` / `boundary` / `code_example`; thesis-mode produces `executive_summary` + a list of `themes` + optional `appendix`. Both modes emit `mental_model` (with `modality_hint` for `diagram-agent`), `spinoff_candidates`, and a mode-aware char-budget self-check.
- **obsidian-formatter-agent** branches skeleton assembly on `note_mode`, writes the file with `Mode:` frontmatter (`Before: ''`, `Next: ''`), and returns suggested MOC entries. It never edits neighbors or MOCs.

The 3-stage architecture itself is unchanged from ADR-0001 — only the modeler's internal branching and the formatter's assembly logic are mode-aware.

`--preserve` mode is **removed**. Preserve semantics is incompatible with the 500-char budget; if raw-content storage is needed it belongs in a separate command, not in `zk-note`.

## Non-obvious dependencies

Two prompt files must exist outside this repo or the relevant agents abort:

- `~/.claude/prompts/crawler.prompt.md` — markdown extraction rules
- `~/.claude/prompts/obsidian-note.prompt.md` — note structure rules

Agents reference each other via `~/.claude/agents/<name>.md` at runtime. Those paths only resolve once the plugin is installed (symlinked from this repo), so reading the files directly during development means using the in-repo `agents/` path instead.

## Vault contract

Scoped knowledge retrieval and maintenance use `scripts/knowledge.py` and require an explicit `--vault` plus `docs/knowledge/scope.json`. The `query` skill is read-only; `query-to-note` is a separate explicitly requested write workflow. The shared CLI runs in Pi or Claude Code without Claude-only APIs. See `docs/ADR/0003-scoped-knowledge-record.md`.

Do not infer a knowledge vault from the current project directory. The installed `vault-knowledge` launcher supplies a machine-local binding. All scoped reads, link expansion, indexing, and health reports share the allowlist, exclude `raw/` completely, and reject symlink/traversal paths. Do not add per-skill exclusion lists or whole-vault fallback scans. MOCs are optional navigation, not coverage gates.

`.claude/index.md` and related catalog files (`.claude/index/`, `.claude/QUALITY.md`, manifest) are generated only by `vault-knowledge build`. Never hand-edit them. `.claude/log.md` is frozen history and is no longer written. Existing notes, MOCs, and neighbor navigation are never edited automatically; ingest prompts return proposals (including `cross-pollinator-agent` with `Dry run: true`) that the user approves.

## Spinoff candidates

When `conceptual-modeler-agent` detects atomic concepts in source material beyond the primary one, it emits them as `spinoff_candidates`. No file is written: the orchestrator lists them in the final report under "🪴 Spinoff candidates (not saved)" (`<concept-name> — <rationale>`) for the user to decide on.

**Thesis chapter overflow uses the same list.** Per ADR-0002 D7, when a thesis-mode `### <Theme>` chapter has its own thesis-worthy internal structure, the modeler keeps the chapter inline (with a `完整討論見 [[Deep-Note]]` back-link) AND emits a spinoff candidate with `rationale: "thesis chapter overflow — sub-concept has its own thesis-worthy structure"`.

## Note modes

Every note declares `Mode: atom | thesis` in frontmatter (per ADR-0002 D8). The modeler picks the mode; the formatter writes it; `vault-lint` reads it to apply the right required-core check and the right budget rule. ADR-0002 D2 lists the signal tables (atom: defines one concept, ≤ ~15 min / ~2000 words, sub-concepts are vocabulary; thesis: multiple supporting themes, metaphor / argument / multi-authority, ≥ ~15 min / ~2000 words). Edge case: a long deep-dive defining one concept stays atom — content wins over duration.

Authoritative skeleton definitions live in `agents/conceptual-modeler-agent.md` (output) and `agents/obsidian-formatter-agent.md` (assembly). Do not duplicate them here.

| Mode | Required core sections | Body budget rule |
|---|---|---|
| atom | `### Definition` / `### Mental Model` / `### Links` | 500-char hard ceiling across body prose |
| thesis | `### 執行摘要` / `### Mental Model` / ≥ 1 `### <Theme>` chapter / `### Links` | Per-chapter soft target 200–1500 chars; no flat ceiling |

Atom-mode optional sections: `### Why It Matters`, `### Boundary`, `### Code`. Thesis-mode optional section: `### 附錄`. Thesis mode does **not** carry `### Boundary` or `### Code` — the thesis bounds the argument structurally, and code-heavy sources should classify as atom.

## Note conventions (enforced, will fail validation if violated)

Filename: `Domain-Concept-Name-In-Train-Case.md` (e.g. `Web-React-Server-Components.md`).

Frontmatter schema:

```yaml
Date: YYYY-MM-DD
Type: literature
Mode: atom        # REQUIRED: atom | thesis — written by obsidian-formatter-agent from modeler's note_mode
Categories: []
Sub-Categories: []
Aliases: []
tags: []          # controlled vocabulary — see zettelkasten-agent for the list
Before: ''       # new notes start empty; never auto-wired
Next: ''
Link: '<source-url>'
Src: '[[raw/src-file]]'
```

New notes get `Before: ''` and `Next: ''`. Neighbor navigation is not rewired automatically; any change to it is a proposal the user approves.

## Agent delegation pattern

<important if="writing or modifying an agent">
Agents do not call each other directly. They use the Task tool with `subagent_type: general-purpose` and a prompt that tells the subagent to read `~/.claude/agents/<name>.md`. The indirection is intentional — it lets the same agent file work both as a plugin agent and as an ad-hoc delegation target. Don't refactor it into direct calls.
</important>

## Error handling decisions (not negotiable)

- **Video transcription failure → abort the whole workflow.** No fallback to summary, no partial content. A hallucinated transcript poisons every downstream note; we'd rather fail loudly than file a wrong note.
- **Markdown extraction failure → report and stop, don't guess.** User retries with a different source.
- **Domain ambiguity → ask the user.** Don't pick heuristically.

## Body budget per mode

The budget rule depends on `Mode:` (per ADR-0002 D5). Both rules share the same calculation method below.

### Atom mode — 500-character hard ceiling

`Mode: atom` notes carry a **500-character hard ceiling** across the body prose. `conceptual-modeler-agent` self-checks it; `vault-lint` Check 9 enforces it as an external gate. The budget covers `### Definition`, `### Why It Matters`, `### Boundary`, and any prose surrounding diagrams or code. If an atom concept cannot fit, the modeler aborts and recommends splitting via a spinoff candidate — do not silently truncate.

### Thesis mode — per-chapter soft target

`Mode: thesis` notes are **exempt from the flat 500-char ceiling**. Instead, each `### <Theme>` chapter has a **soft target of 200–1500 chars** (counted per the same calculation rule below). Total body length across all chapters is unbounded. Dilution discipline in thesis mode is structural (one-atom-per-chapter, table-first for comparisons, quote-for-authority), not lexical — see ADR-0002 D6. When a chapter naturally exceeds 1500 chars *because it has become its own thesis-worthy topic*, the modeler triggers the D7 back-link mechanism (inline essence + `完整討論見 [[Deep-Note]]` + a spinoff candidate in the report). `vault-lint` Check 11 (new) flags chapters outside the 200–1500 range; Check 9 is restricted to atom mode.

### Calculation rule (shared)

Count is **Chinese characters + English words**. The following are **excluded** from the count in both modes:

- Frontmatter (the YAML block between `---` fences)
- Fenced code blocks (` ``` ` … ` ``` `)
- Embedded diagrams (Mermaid, ASCII, Image embeds — anything under `### Mental Model`)
- The `### Links` section

## Diagrams

Default to Image, then `ascii-diagram-agent` if that fails, resort to Mermaid, and if all three fail fall back to **Structural Bullets** (≤ 5 component lines under `### Mental Model`). The priority order is **Image > ASCII > Mermaid > Structural Bullets** and applies even for Obsidian targets — `diagram-agent` must honor this order, not its own legacy "use Mermaid for Obsidian" rule.
