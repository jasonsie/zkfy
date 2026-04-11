---
description: "Complete pipeline from any source (URL, text, file) to an integrated Zettelkasten literature note"
---

# Source to Zettelkasten

Create a well-formed Zettelkasten literature note from an external source.

## Input

$ARGUMENTS — a URL (web page or video), raw text, or file path to transform into a Zettelkasten note.

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
   - Description: "Use zettelkasten-agent agent to create literature note with frontmatter, links, and MOC updates"
   - ActiveForm: "Integrating into Zettelkasten"

5. **Cross-pollinate related notes**
   - Subject: "Cross-pollinate related notes"
   - Description: "Use cross-pollinator-agent to add backlinks to existing related notes"
   - ActiveForm: "Cross-pollinating related notes"

6. **Update index and log**
   - Subject: "Update index and log"
   - Description: "Append to .claude/log.md and update .claude/index.md"
   - ActiveForm: "Updating index and log"

7. **Report completion**
   - Subject: "Report completion"
   - Description: "Output final location, backlinks, MOC updates, cross-updates, and log entry"
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

Output location: row/<video-title>.md

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
- Output to: row/src-<title-kebab>.md
- For complex diagrams, you may sub-delegate to ~/.claude/agents/diagram-agent.md

Return the path to the created Markdown file."
```

**On success**: Update task to `completed`, store source file path
**On failure**: Report error, suggest alternatives to user

### Phase 2: Zettelkasten Integration

**Update task**: Mark "Integrate into Zettelkasten" as `in_progress`

Use the `zk-note` skill to orchestrate the integration:
- Pass the source file path from Phase 1
- The skill handles the two-agent pipeline internally:
  1. `zettelkasten-agent` — analyzes content (concept, domain, insights, relationships)
  2. `obsidian-formatter-agent` — formats, writes, and integrates the note into the vault
  3. Cleanup — deletes source file

**On success**: Update task to `completed`, store results
**On failure (domain unclear)**: Ask user to specify domain, then retry

### Phase 2.5: Cross-Pollination

**Update task**: Mark "Cross-pollinate related notes" as `in_progress`

After the new note is created, propagate backlinks to existing related notes:

1. Use `vault-search` skill with the new note's concept as query, `--limit 10`
2. Delegate to `cross-pollinator-agent`:

```
Prompt: "You are delegated to act as the cross-pollinator-agent agent.

Read the agent instructions at: ~/.claude/agents/cross-pollinator-agent.md

Then cross-pollinate this newly created note:
New note path: <note_path from Phase 2>
Vault root: <vault_root>
Candidates: <top 10 paths from vault-search>
Dry run: false

Return the list of files updated and changes made."
```

**On success**: Update task to `completed`, store cross-update results
**On failure**: Warn user, continue to Phase 3 — the note is still created

### Phase 3: Index and Log (Mandatory)

**Update task**: Mark "Update index and log" as `in_progress`

Phase 3 is **mandatory** — do not skip even if earlier phases had warnings.

1. Use `wiki-log` skill:
   `ingest title="<note-concept>" source="<original-source-url>" output="<note-path>" mocs="<MOCs-updated>" links="<backlinks-created>" cross-updates="<files-updated-in-phase-2.5>"`

2. Use `vault-index` skill:
   `--append <note-path>`
   - If vault-index fails, **retry once** before reporting failure
   - After success, verify the note appears in the last 20 lines of `.claude/index.md`

**On success**: Update task to `completed`
**On failure after retry**: Report to user that the index is stale and they should run `/vault-index --full` to resync. Do NOT mark the pipeline as fully successful.

### Step 3: Report

**Update task**: Mark "Report completion" as `in_progress`

After all phases complete, output:

```
✅ Zettelkasten note created
📄 Location: <domain>/<filename>.md
🔗 Links: <backlinks added>
📑 MOC updates: <MOCs modified>
🔄 Cross-updates: <N> existing notes enriched
📝 Logged to: .claude/log.md
📇 Indexed in: .claude/index.md
```

**Update task**: Mark "Report completion" as `completed`

**Final step**: You may now display the TaskList to show the user all completed tasks.

## Error Handling

| Phase | Error                  | Action                            |
| ----- | ---------------------- | --------------------------------- |
| 0     | Transcript fetch fails | **ABORT** entire workflow         |
| 1     | URL unreachable        | Report error, suggest alternative |
| 2     | Domain unclear         | Ask user to specify               |
