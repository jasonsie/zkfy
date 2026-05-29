---
description: "Promote a query answer or synthesis into a permanent Zettelkasten note. Files valuable explorations back into the vault."
---

# Query to Note

Promote a query answer, synthesis, or comparison into a permanent Zettelkasten note so explorations compound in the vault instead of vanishing into chat history.

## Input

$ARGUMENTS — a question or topic to research and file as a permanent note. Examples:

- `"How does RAG compare to the LLM Wiki pattern?"`
- `"What are the trade-offs between SSR and CSR?"`
- `"Summarize all backtracking algorithm patterns in the vault"`

## Execution

You are an orchestrator that runs a multi-step pipeline with **progress tracking**. Read each agent/skill before delegating to it.

### Step 0: Initialize Task List

Create a task list to track pipeline progress. Use TaskCreate to create these tasks:

1. **Search vault for relevant notes**
   - Subject: "Search vault for relevant notes"
   - Description: "Use vault-search skill to find notes related to the query"
   - ActiveForm: "Searching vault"

2. **Synthesize answer from vault knowledge**
   - Subject: "Synthesize answer from vault knowledge"
   - Description: "Read top results and synthesize a comprehensive answer"
   - ActiveForm: "Synthesizing answer"

3. **Create permanent ZK note from synthesis**
   - Subject: "Create permanent ZK note from synthesis"
   - Description: "Write synthesis to temp file and process through zk-note pipeline"
   - ActiveForm: "Creating permanent note"

4. **Cross-pollinate related notes**
   - Subject: "Cross-pollinate related notes"
   - Description: "Add backlinks from existing notes to the new synthesis"
   - ActiveForm: "Cross-pollinating notes"

5. **Log and index the new note**
   - Subject: "Log and index the new note"
   - Description: "Record the query and result in wiki-log and vault-index"
   - ActiveForm: "Logging and indexing"

6. **Report completion**
   - Subject: "Report completion"
   - Description: "Output final location, sources, and cross-updates"
   - ActiveForm: "Reporting completion"

**Important**: Update each task's status (`in_progress` → `completed`) as you progress through the pipeline.

### Step 0.5: Check for Existing Synthesis

Before running the full pipeline, do a quick `vault-search` with `--limit 5` using the question as the query.

Scan the results for any note flagged `[SYNTHESIS]` (i.e., `Type: permanent` in its frontmatter). If one is found and its abstract substantially covers the question:

1. Read the synthesis note fully and display it to the user:
   ```
   📋 Found existing synthesis: [[<Note-Name>]]
   Created: <Date from frontmatter>
   Abstract: <abstract excerpt>

   Options:
   (a) Use this answer — display the note and stop
   (b) Create a fresh synthesis — continue with Steps 1-6
   (c) Update the existing note — proceed but write to the existing path
   ```
2. Wait for user choice before proceeding
3. If (a): show the note content, mark all pipeline tasks `deleted`, report done
4. If (b): proceed normally through Step 1
5. If (c): proceed through Step 1, but in Step 3 write to the existing note path instead of creating new

If no synthesis match found, proceed directly to Step 1 without prompting.

### Step 1: Vault Search

**Update task**: Mark "Search vault for relevant notes" as `in_progress`

Use the `vault-search` skill with the question as query, `--limit 10`.

Read the top results to gather context — these are the source notes for the synthesis.

**Update task**: Mark "Search vault for relevant notes" as `completed`

### Step 2: Synthesize

**Update task**: Mark "Synthesize answer from vault knowledge" as `in_progress`

Read each relevant note found in Step 1. Synthesize a comprehensive answer that:

- Draws from multiple vault notes
- Identifies patterns, contrasts, and connections
- Includes code examples where relevant
- Cites source notes with `[[WikiLinks]]`

The synthesis is raw material handed to `zk-note` in Step 3 — do not pre-format it for the Concept-First skeleton (that's the modeler's job). Just produce a clear, dense answer.

Display the synthesis to the user in chat before proceeding.

**Update task**: Mark "Synthesize answer from vault knowledge" as `completed`

### Step 3: Create Permanent Note

**Update task**: Mark "Create permanent ZK note from synthesis" as `in_progress`

Write the synthesis to a temporary file at `row/synthesis-<topic-kebab>.md`.

Use the `zk-note` skill to process it through the 4-agent Hybrid Atom/Thesis pipeline (see `docs/ADR/0001-concept-first-pipeline.md` for the 3-stage shape and `docs/ADR/0002-hybrid-atom-thesis-mode.md` for mode branching):

1. `zettelkasten-agent` (sonnet) — Discover: atomic concept, domain, metadata, related notes
2. `conceptual-modeler-agent` (opus) — Distill: classifies `note_mode` (atom vs thesis) at the start of distillation per ADR-0002 D2, then branches output. Synthesized answers from `/query-to-note` are mode-agnostic: a synthesis that defines a single concept naturally becomes atom; a synthesis that compares 3 approaches, weighs trade-offs, or carries multiple supporting themes is naturally thesis-shaped. Modeler emits mental model, spinoff candidates (atom-spinoffs and thesis-chapter-overflow spinoffs share the queue), and a mode-aware char-budget self-check.
3. `diagram-agent` (sonnet) — Render: Image > ASCII > Mermaid > Structural Bullets
4. `obsidian-formatter-agent` (sonnet) — Integrate: consumes `note_mode` and branches skeleton assembly (atom Concept-First vs thesis synthesis-dossier); writes `Mode: atom | thesis` into frontmatter (ADR-0002 D8); updates neighbors and MOCs

The skill also appends any spinoff candidates to `row/_spinoffs.md`.

**Important**: The note `Type` should be `permanent` (original synthesis), NOT `literature`. This is orthogonal to `Mode:` — a permanent synthesis can still be either atom or thesis; the modeler picks `Mode:` from the synthesis content regardless of `Type:`.

**Update task**: Mark "Create permanent ZK note from synthesis" as `completed`

### Step 4: Cross-Pollinate

**Update task**: Mark "Cross-pollinate related notes" as `in_progress`

Delegate to `cross-pollinator-agent`:

- New note path from Step 3
- Candidate notes from Step 1
- This adds backlinks from existing notes to the new synthesis

**Update task**: Mark "Cross-pollinate related notes" as `completed`

### Step 5: Log and Index

**Update task**: Mark "Log and index the new note" as `in_progress`

Use `wiki-log` skill: `query question="<original question>" searched=<N> result="<note-path>"`

Use `vault-index` skill: `--append <note-path>`

**Update task**: Mark "Log and index the new note" as `completed`

### Step 6: Report

**Update task**: Mark "Report completion" as `in_progress`

Output:

```
✅ Query filed as permanent note
📄 Location: <domain>/<filename>.md
🧬 Mode: <atom | thesis>                        ← from zk-note skill report
❓ Question: "<original question>"
📚 Sources: <N> vault notes consulted
🔗 Cross-updates: <N> existing notes enriched
📑 MOC updates: <MOCs modified>
```

**Update task**: Mark "Report completion" as `completed`

## Error Handling

| Step | Error                    | Action                                             |
| ---- | ------------------------ | -------------------------------------------------- |
| 1    | No relevant notes found  | Warn user, proceed with general knowledge synthesis |
| 2    | Synthesis too broad      | Ask user to narrow the question                    |
| 3    | Domain unclear           | Ask user to specify domain                         |
| 4    | Cross-pollination fails  | Warn, note is still created                        |
| 5    | Log/index fails          | Warn, note is still created                        |
