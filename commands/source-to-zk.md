---
description: "Complete pipeline from any source (URL, text, file) to an integrated Zettelkasten literature note"
---

# Source to Zettelkasten

Create a well-formed Zettelkasten literature note from an external source.

## Input

$ARGUMENTS — a URL (web page or video), raw text, or file path to transform into a Zettelkasten note.

The Concept-First pipeline (see `docs/ADR/0001-concept-first-pipeline.md`) is the only mode. `--preserve` and `--digest` flags are removed.

## Execution

You are an orchestrator that runs a multi-phase pipeline with **progress tracking**. Read each agent file before delegating to it.

### Step 0: Initialize Task List

Create a task list to track pipeline progress. Use TaskCreate to create these tasks:

1. **Detect input type (video/web/text)**
   - Subject: "Detect input type"
   - Description: "Classify the input as VIDEO_URL, WEB_URL, or TEXT"
   - ActiveForm: "Detecting input type"

2. **[Conditional] Extract video transcript** (only if VIDEO_URL detected)
   - Subject: "Extract video transcript"
   - Description: "Use video-agent agent to fetch transcript from video URL"
   - ActiveForm: "Extracting video transcript"

3. **Generate structured Markdown**
   - Subject: "Generate structured Markdown"
   - Description: "Use markdown-file-agent agent to convert source to clean Markdown"
   - ActiveForm: "Generating structured Markdown"

4. **Integrate into Zettelkasten**
   - Subject: "Integrate into Zettelkasten"
   - Description: "Run 4-agent Hybrid Atom/Thesis pipeline (zettelkasten → conceptual-modeler classifies note_mode → diagram → obsidian-formatter writes Mode: frontmatter) with spinoff candidates reported only"
   - ActiveForm: "Integrating into Zettelkasten"

5. **Cross-pollinate related notes**
   - Subject: "Cross-pollinate related notes"
   - Description: "Use cross-pollinator-agent (dry run) to propose backlinks to existing related notes; apply only user-approved edits"
   - ActiveForm: "Cross-pollinating related notes"

6. **Validate**
   - Subject: "Validate"
   - Description: "Run vault-knowledge lint, then vault-knowledge build to regenerate the catalog"
   - ActiveForm: "Validating"

7. **Report completion**
   - Subject: "Report completion"
   - Description: "Output final location, backlinks, suggested MOC entries, cross-updates, spinoff candidates, and lint result"
   - ActiveForm: "Reporting completion"

**Important**: Update each task's status (`in_progress` → `completed`) as you progress through the pipeline.

### Step 1: Detect Input Type

**Update task**: Mark "Detect input type" as `in_progress`

Classify the input:

- **VIDEO_URL**: matches youtube.com, youtu.be, vimeo.com, or other video platforms
- **WEB_URL**: any other http/https URL
- **TEXT**: raw text or local file path

**Update task**: Mark "Detect input type" as `completed`

### Step 2: Run Pipeline

**Pipeline flow**:
```
if VIDEO_URL → Phase 0 → Phase 1 → Phase 2
else          → Phase 1 → Phase 2
```

If VIDEO_URL: Create task #2 (Extract video transcript)
Otherwise: Mark task #2 as `deleted` (not needed)

### Phase 0: Video Transcription (conditional)

**Update task**: Mark "Extract video transcript" as `in_progress`

**Read agent**: `~/.claude/agents/video-agent.md`

Use the Task tool to delegate to `general-purpose` subagent with:

```
Prompt: "You are delegated to act as the video-agent agent.

Read the agent instructions at: ~/.claude/agents/video-agent.md

Then extract the transcript from this video URL: <video_url>

Mode: STRICT — abort on any failure. No fallbacks. No partial results.

Output location: raw/<video-title>.md

Return the path to the created transcript file."
```

**On success**: Update task to `completed`, store transcript file path
**On failure**: STOP entire workflow — update all remaining tasks to `deleted`, report error to user

**If transcript extraction fails → STOP the entire workflow. No fallback.**

### Phase 1: Content Crawling & Extraction

**Update task**: Mark "Generate structured Markdown" as `in_progress`

**Read agent**: `~/.claude/agents/markdown-file-agent.md`
**Read prompt**: `~/.claude/prompts/crawler.prompt.md`

Use the Task tool to delegate to `general-purpose` subagent with:

```
Prompt: "You are delegated to act as the markdown-file-agent agent.

Read the agent instructions at: ~/.claude/agents/markdown-file-agent.md
Read the formatting rules at: ~/.claude/prompts/crawler.prompt.md

Then convert this source to structured Markdown:
<source> = <URL | text | transcript file path>

Requirements:
- Zero data loss policy
- Preserve tables/code/SVGs
- Web URL: clip it with the global web-clipper skill (python3 ~/.claude/skills/web-clipper/scripts/clip.py "<url>" --out raw --json); the clip lands at raw/<Page Title>.md with its images under the vault attachment folder and is a durable source, never an intermediate
- Text / transcript: output to raw/src-<title-kebab>.md
- If the clipper exits 2 (bot challenge, login wall, paywall), stop and ask the user to save the page from their browser and rerun with --html <file>; do not substitute WebFetch or any scraper
- For complex diagrams, you may sub-delegate to ~/.claude/agents/diagram-agent.md

Return the path to the created Markdown file."
```

**On success**: Update task to `completed`, store source file path
**On clipper exit 2**: Ask the user for the saved page HTML, then rerun Phase 1 with `--html <file>`
**On other failure**: Report error, suggest alternatives to user

### Phase 2: Zettelkasten Integration

**Update task**: Mark "Integrate into Zettelkasten" as `in_progress`

Use the `zk-note` skill to orchestrate the integration:
- Pass the source file path from Phase 1
- The skill drives the 4-agent Hybrid Atom/Thesis pipeline internally (see `docs/ADR/0001-concept-first-pipeline.md` for the 3-stage shape and `docs/ADR/0002-hybrid-atom-thesis-mode.md` for the mode branching):
  1. `zettelkasten-agent` (sonnet, Discover) — atomic concept, domain, metadata, related notes
  2. `conceptual-modeler-agent` (opus, Distill) — classifies `note_mode` (atom vs thesis) at the start of distillation per ADR-0002 D2, then branches its output skeleton: atom → one-line definition + optional Why/Boundary/Code (≤500-char body budget); thesis → executive summary + theme chapters + optional appendix (per-chapter 200–1500-char soft target). Emits mental model, spinoff candidates (atom-spinoffs and thesis-chapter-overflow spinoffs are reported together), and a mode-aware char-budget self-check.
  3. `diagram-agent` (sonnet, Render) — Image > ASCII > Mermaid > Structural Bullets per CLAUDE.md (modality routing unchanged across modes)
  4. `obsidian-formatter-agent` (sonnet, Integrate) — consumes `note_mode` and branches skeleton assembly accordingly; writes `Mode: atom | thesis` into frontmatter (ADR-0002 D8); omits Before/Next; returns suggested MOC entries without editing MOCs or neighbors
  5. Spinoff candidates — returned in the report only, never written to a file
  6. Cleanup — deletes only intermediate files this run created (`raw/src-*.md`); web clips (`raw/<Page Title>.md` + attachments) and user-dropped `raw/` sources stay

**On success**: Update task to `completed`, store results
**On failure (domain unclear)**: Ask user to specify domain, then retry

### Phase 2.5: Cross-Pollination

**Update task**: Mark "Cross-pollinate related notes" as `in_progress`

After the new note is created, propose backlinks to existing related notes:

1. Run `~/.local/bin/vault-knowledge search "<new note's concept terms>" --limit 10`, then `~/.local/bin/vault-knowledge read "<path>" --heading "<Heading>"` on promising results
2. Delegate to `cross-pollinator-agent`:

```
Prompt: "You are delegated to act as the cross-pollinator-agent agent.

Read the agent instructions at: ~/.claude/agents/cross-pollinator-agent.md

Then cross-pollinate this newly created note:
New note path: <note_path from Phase 2>
Vault root: <vault_root>
Candidates: <top 10 paths from search>
Dry run: true

Return the proposed backlink edits."
```

Present the proposed edits plus the suggested MOC entries from Phase 2 (MOC path + line) to the user. Apply only the ones the user explicitly approves; never create a new MOC automatically.

**On success**: Update task to `completed`, store approved cross-update results
**On failure**: Warn user, continue to Phase 3 — the note is still created

### Phase 3: Validate (Mandatory)

**Update task**: Mark "Validate" as `in_progress`

Phase 3 is **mandatory** — do not skip even if earlier phases had warnings.

1. Run `~/.local/bin/vault-knowledge lint` and report violations touching the new or edited files
2. Run `~/.local/bin/vault-knowledge build` to regenerate the catalog

**On success**: Update task to `completed`
**On failure**: Report the error to the user. Do NOT mark the pipeline as fully successful.

### Step 3: Report

**Update task**: Mark "Report completion" as `in_progress`

After all phases complete, output:

```
✅ Zettelkasten note created
📄 Location: <domain>/<filename>.md
🧬 Mode: <atom | thesis>                        ← from zk-note skill report
🔗 Links: <backlinks added>
📑 Suggested MOC entries: <MOC path + line>
🔄 Cross-updates: <N> existing notes enriched (user-approved only)
🧪 Lint: <result>
📇 Catalog: rebuilt via vault-knowledge build
🪴 Spinoff candidates (not saved): <concept — rationale list>   ← only if any
```

**Update task**: Mark "Report completion" as `completed`

**Final step**: You may now display the TaskList to show the user all completed tasks.

## Error Handling

| Phase | Error                  | Action                            |
| ----- | ---------------------- | --------------------------------- |
| 0     | Transcript fetch fails | **ABORT** entire workflow         |
| 1     | URL unreachable        | Report error, suggest alternative |
| 2     | Domain unclear         | Ask user to specify               |
