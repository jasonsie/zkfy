---
name: zk-note
description: Transform markdown files into fully integrated Zettelkasten notes using the Hybrid Atom/Thesis pipeline (Discover → Distill → Render → Integrate). Use when you need to (1) Create atomic notes or thesis-dossier notes from existing markdown, (2) Let the modeler classify note_mode and distill the appropriate artifact (atom: ≤500-char body; thesis: per-chapter 200–1500-char themes), (3) Propose backlinks and MOC entries for the new note.
---

# ZK-Note

Transform markdown into a fully integrated Zettelkasten note using the Hybrid
Atom/Thesis pipeline. Per ADR-0001 (3-stage shape) and ADR-0002 (hybrid mode), the
pipeline runs four agents — `zettelkasten-agent` (Discover) → `conceptual-modeler-agent`
(Distill, classifies `note_mode` and emits mode-discriminated payload) → `diagram-agent`
(Render) → `obsidian-formatter-agent` (Integrate, branches assembly on `note_mode`) —
followed by a cross-pollination pass that only proposes edits. Spinoff candidates (both
atom-spinoffs and thesis-chapter-overflow spinoffs) are listed in the final report and
never saved to a file.

## Input

$ARGUMENTS — `<path-to-markdown-file> [domain]`

Optional positional `domain`: `cs` | `web` | `ai` | `principle` | `devops` | `math`
(or any other domain folder auto-discovered from the vault root).

No mode flags. `note_mode` is classified by `conceptual-modeler-agent` from the source
content per ADR-0002 D2 — never by a CLI flag. `--preserve` was removed per ADR-0001 /
D5 (incompatible with the atom 500-char budget — raw-content preservation belongs in a
separate future command).

## Execution Order

This skill orchestrates four agents in sequence, then proposes cross-pollination edits
for existing notes (applied only after user approval):

```
Source File
    │
    ▼
┌────────────────────────────────┐
│  zettelkasten-agent (sonnet)   │  Discover layer
│  (atomic concept + metadata)   │
│                                │
│  → domain                      │
│  → concept                     │
│  → key_insights                │
│  → source_url                  │
│  → related_notes               │
│  → categories / sub_categories │
│  → aliases / tags              │
└──────────┬─────────────────────┘
           │ discover_output
           ▼
┌────────────────────────────────┐
│  conceptual-modeler-agent      │  Distill layer
│  (opus — deep reasoning)       │
│                                │
│  → note_mode: atom | thesis    │ ◄── classified per ADR-0002 D2
│                                │
│  Atom-mode payload:            │
│  → one_line_definition (≤50ch) │
│  → why_it_matters?  (nullable) │
│  → boundary?        (nullable) │
│  → code_example?    (nullable) │
│                                │
│  Thesis-mode payload:          │
│  → executive_summary           │
│  → themes[] {heading, body,    │
│      overflow_backlink,        │
│      char_count}               │
│  → appendix?        (nullable) │
│                                │
│  Shared:                       │
│  → mental_model { modality,    │
│      description, image }      │
│  → spinoff_candidates[]        │
│  → char_budget (mode-aware)    │
└──────────┬─────────────────────┘
           │ note_mode + mode-payload
           ▼
┌────────────────────────────────┐
│  diagram-agent (sonnet)        │  Render utility
│  (Image > ASCII > Mermaid >    │
│   Structural Bullets)          │
│                                │
│  → rendered_diagram_block      │
└──────────┬─────────────────────┘
           │ markdown block for ### Mental Model
           ▼
┌────────────────────────────────┐
│  obsidian-formatter-agent      │  Integrate layer
│  (sonnet — mechanical)         │
│                                │
│  consumes note_mode (REQUIRED) │ ◄── branches skeleton on mode
│  → Train-Case filename         │
│  → minimal frontmatter + Mode  │
│      (no Before/Next)          │
│  → assemble atom skeleton      │
│      OR thesis skeleton        │
│  → suggest MOC entries         │
└──────────┬─────────────────────┘
           │ final note path + mode
           │ + suggested MOC entries
           ▼
┌────────────────────────────────┐
│  cross-pollinator-agent        │  Graph enrichment
│  (sonnet — Dry run: true)      │
│  → proposed backlinks, shown   │
│    to the user for approval    │
└──────────┬─────────────────────┘
           │
           ▼
       Cleanup & Report (incl. Mode)
```

### Step 1: Read Source

Read the markdown file from the provided path. Extract the source URL if present in
the file. There is no flag parsing — `$ARGUMENTS` is just `<path> [domain]`.

### Step 2: Delegate to zettelkasten-agent (Discover)

Use the Task tool to delegate to a `general-purpose` subagent:

```
Prompt: "You are delegated to act as the zettelkasten-agent agent.

Read the agent instructions at: ~/.claude/agents/zettelkasten-agent.md

Then run the Discover layer on this source:
Source file: <path>
Vault root: <vault_root>
[Domain: <domain> — if provided by user]

Return the discover_output payload:
- domain
- concept (atomic concept name)
- key_insights (raw bullets, NOT distilled prose)
- source_url
- related_notes (list of [[Note]] — rationale pairs)
- categories
- sub_categories
- aliases
- tags"
```

If the zettelkasten-agent asks about domain ambiguity, relay the question to the user
and re-invoke with the chosen domain. Do not pick heuristically.

### Step 3: Delegate to conceptual-modeler-agent (Distill)

Use the Task tool to delegate to a `general-purpose` subagent. The modeler classifies
`note_mode` (atom vs thesis) at the start of distillation per ADR-0002 D2, then branches
its output skeleton accordingly. The skill must propagate the returned `note_mode` to
Steps 4 and 5 — never re-derive it.

```
Prompt: "You are delegated to act as the conceptual-modeler-agent agent.

Read the agent instructions at: ~/.claude/agents/conceptual-modeler-agent.md

Then run the Distill layer:
discover_output: <full payload from Step 2>
Source file: <path>
Vault root: <vault_root>

The modeler will first classify note_mode (atom vs thesis) per ADR-0002 D2, then emit
the mode-discriminated payload below. Atom-mode fields are non-null only when
note_mode = atom; thesis-mode fields are non-null only when note_mode = thesis.

Return the conceptual_artifact payload:
- note_mode: 'atom' | 'thesis'                   # REQUIRED
- mental_model { modality_hint, description, source_image }   # shared
- spinoff_candidates (list, may be empty)        # shared (atom-spinoffs + thesis-overflow)
- char_budget { mode, atom_total | null, thesis_chapter_counts | null }   # shared

Atom-mode fields (populated when note_mode = atom; null when thesis):
- one_line_definition (≤50 chars)
- why_it_matters (list or null)
- boundary (list or null)
- code_example (string or null)

Thesis-mode fields (populated when note_mode = thesis; null when atom):
- executive_summary (2-3 paragraphs + trailing `> **核心論點：…**` blockquote)
- themes: list of {heading, body, overflow_backlink, char_count} — at least 1 entry
- appendix (string or null)"
```

If the modeler aborts, **abort the entire pipeline**. The abort reason is mode-specific:

- **Atom mode** — concept un-distillable to ≤50 chars, or body budget > 500 after
  compression and optional-section demotion.
- **Thesis mode** — no coherent macro thesis identifiable, zero themes pass the
  one-atom-per-chapter rule, or every chapter < 200 chars after authoring.

Report the modeler's error verbatim (including which mode-specific failure occurred).
Do not proceed to diagram-agent or formatter — the discover output is not lost (the user
can refine the source selection or concept name and retry).

If the modeler return is missing `note_mode`, abort with a malformed-delegation error
(the modeler always returns `note_mode` per ADR-0002 D2; a missing field indicates the
delegation envelope was corrupted, not a modeling failure).

### Step 4: Delegate to diagram-agent (Render)

Use the Task tool to delegate to a `general-purpose` subagent:

```
Prompt: "You are delegated to act as the diagram-agent agent.

Read the agent instructions at: ~/.claude/agents/diagram-agent.md

Then render the Mental Model diagram for this concept:
modality_hint: <conceptual_artifact.mental_model.modality_hint>
description: <conceptual_artifact.mental_model.description>
source_image: <conceptual_artifact.mental_model.source_image>  # currently always null
context: <one_line_definition + concept name, for context-aware rendering>

Honor the CLAUDE.md priority chain: Image > ASCII > Mermaid > Structural Bullets.

Return:
- rendered_diagram_block: the exact markdown block to drop under ### Mental Model
  (an image embed, a fenced ASCII block, a fenced Mermaid block, or a Structural
  Bullets list)"
```

Structural Bullets is the guaranteed floor — diagram-agent should always succeed. If
it nonetheless fails to produce any output, abort and report.

### Step 5: Delegate to obsidian-formatter-agent (Integrate)

Use the Task tool to delegate to a `general-purpose` subagent. Pass `note_mode`
(REQUIRED — the formatter aborts if missing per its Error Handling table) along with the
mode-discriminated payload. Only the payload fields relevant to the active mode will be
non-null; the formatter ignores the others. The skill passes the modeler's `note_mode`
through verbatim — never re-derive it from payload shape.

```
Prompt: "You are delegated to act as the obsidian-formatter-agent agent.

Read the agent instructions at: ~/.claude/agents/obsidian-formatter-agent.md
Read the formatting rules at: ~/.claude/prompts/obsidian-note.prompt.md

Then assemble the mode-appropriate note (atom skeleton per ADR-0001 D5 or thesis
synthesis-dossier skeleton per ADR-0002 D4, branched on note_mode):

Shared inputs (always required):
- note_mode: <conceptual_artifact.note_mode>              # REQUIRED — 'atom' | 'thesis'
- Mental Model (rendered): <rendered_diagram_block from Step 4>
- Domain: <discover_output.domain>
- Concept: <discover_output.concept>
- Related notes: <discover_output.related_notes>
- Source URL: <discover_output.source_url>
- Source file: <source_file>
- Categories: <discover_output.categories>
- Sub-Categories: <discover_output.sub_categories>
- Aliases: <discover_output.aliases>
- tags: <discover_output.tags>
- Today's date: <today YYYY-MM-DD>
- Vault root: <vault_root>

Atom-mode payload (non-null only when note_mode = atom):
- One-line definition: <conceptual_artifact.one_line_definition>
- Why It Matters:      <conceptual_artifact.why_it_matters>    # may be null — omit section
- Boundary:            <conceptual_artifact.boundary>          # may be null — omit section
- Code example:        <conceptual_artifact.code_example>      # may be null — omit section

Thesis-mode payload (non-null only when note_mode = thesis):
- Executive summary:   <conceptual_artifact.executive_summary> # already includes the trailing
                                                               #   `> **核心論點：…**` blockquote
- Themes: <conceptual_artifact.themes>                         # list of {heading, body,
                                                               #   overflow_backlink}; at least 1
- Appendix:            <conceptual_artifact.appendix>          # may be null — omit ### 附錄

The Mental Model block is already rendered — paste it under ### Mental Model verbatim.
Do not regenerate the diagram. Do not rewrite or expand the modeler's prose. Write
`Mode: <note_mode>` into frontmatter per ADR-0002 D8. Omit `Before`/`Next`, `Sub-Categories`, and `Link`.

Return:
- note path and filename
- mode (atom | thesis)
- suggested MOC entries (MOC path + line); do not edit or create any MOC or neighbor file"
```

If the formatter fails, abort. The conceptual_artifact and rendered_diagram_block are
not lost — the user can re-run from Step 5 once the formatter issue is resolved.

### Step 6: Cross-Pollinate

Delegate to `cross-pollinator-agent` to propose backlinks in existing related notes
to the new note:

```
Prompt: "You are delegated to act as the cross-pollinator-agent agent.

Read the agent instructions at: ~/.claude/agents/cross-pollinator-agent.md

Then cross-pollinate this newly created note:
New note path: <note path from Step 5>
Vault root: <vault_root>
Candidates: <discover_output.related_notes>
Dry run: true

Return the proposed backlink edits."
```

Present the proposed edits plus the formatter's suggested MOC entries (MOC path + line)
to the user. Apply only the ones the user explicitly approves; never create a new MOC
automatically.

If cross-pollination fails, warn but do not abort — the note is already created.

### Step 7: Cleanup & Report

Delete only intermediate files this run created (`raw/src-*.md`, fetched transcripts). Never delete a source the user dropped into `raw/`, nor a clip written by the `web-clipper` skill (`raw/<Page Title>.md` and its attachment folder); they stay as provenance.

Report completion (the `🧬 Mode` line is always present and reflects the modeler's
classification; the `🪴 Spinoff candidates (not saved)` line is conditional on N > 0 and
lists both atom-spinoffs and thesis-overflow spinoffs together):

```
✅ Zettelkasten note created
📄 Location: <domain>/<filename>.md
🧬 Mode: <atom | thesis>
🔗 Backlinks: <N> notes linked
📑 Suggested MOC entries: <MOC path + line>
🔄 Cross-updates: <N> existing notes enriched (user-approved only)
🪴 Spinoff candidates (not saved): <concept — rationale list>   # only line if N > 0
```

## Output

The pipeline produces:

- **Final note** at `<vault_root>/<domain>/<Domain-Concept-In-Train-Case>.md` using the
  mode-appropriate skeleton:
  - **`Mode: atom`** — Concept-First skeleton per ADR-0001 D5: required `### Definition`
    / `### Mental Model` / `### Links`, optional `### Why It Matters` / `### Boundary` /
    `### Code` (presence determined by the modeler).
  - **`Mode: thesis`** — synthesis-dossier skeleton per ADR-0002 D4: required
    `### 執行摘要` / `### Mental Model` / ≥ 1 `### <Theme>` chapter / `### Links`,
    optional `### 附錄`.
  The mode is written to frontmatter as `Mode: atom | thesis` by the formatter.
- **Rendered diagram** composed into the `### Mental Model` section. Modality chosen
  per the Image > ASCII > Mermaid > Structural Bullets priority chain.
- **Spinoff candidates** listed in the final report only (atom-mode atom-spinoffs and
  thesis-mode chapter-overflow spinoffs together; only `rationale` distinguishes them).
  Nothing is written to a file.
- **Navigation**: the new note has no `Before`/`Next`; no neighbor files are edited.
- **Suggested MOC entries**: the formatter returns MOC path + line proposals; no MOC is
  edited or created without explicit user approval.
- **Cross-pollination**: up to 10 proposed backlinks in existing related notes'
  `### Links` sections, applied only after explicit user approval.

## Error Handling

**Source file not found:**
- Report the path that was tried; ask the user to verify the path.

**Domain unclear (from zettelkasten-agent):**
- Relay the agent's question — present available domains and ask the user to choose.
- Do not heuristically pick a domain.

**zettelkasten-agent failure:**
- Abort the pipeline. Report the agent's error verbatim.

**conceptual-modeler-agent abort** — the modeler can abort for mode-specific reasons:
- **Atom mode**: concept un-distillable to ≤50 chars, or body budget > 500 after
  compression and optional-section demotion.
- **Thesis mode**: no coherent macro thesis identifiable, zero themes pass the
  one-atom-per-chapter rule, or every chapter < 200 chars after authoring.

Either case → abort the entire pipeline. Report the modeler's error verbatim, including
which mode-specific failure occurred. The discover_output is not lost — the user can
refine the source selection or concept name in the source file and retry. No note is
written.

**Missing `note_mode` in modeler return:**
- Caller-side abort. The modeler always returns `note_mode` per ADR-0002 D2; a missing
  field indicates a malformed delegation response, not a modeling failure. Report and
  retry Step 3 (do not silently default the mode — the formatter would reject the
  payload at the next step anyway).

**diagram-agent failure:**
- Should be impossible — Structural Bullets is the guaranteed floor. If it nonetheless
  fails, abort and report. No note is written.

**obsidian-formatter-agent failure:**
- Abort. The conceptual_artifact and rendered_diagram_block from Steps 3–4 are not
  lost — the user can re-run Step 5 once the underlying issue is resolved.

**cross-pollinator-agent failure:**
- Warn but do not abort — the note is already created.

**No related notes found:**
- Proceed. The `### Links` section may be empty (cross-pollination will then be a no-op).

**MOC missing:**
- The formatter returns no suggested MOC entry. Never create a new MOC automatically; tell
  the user and let them decide.
