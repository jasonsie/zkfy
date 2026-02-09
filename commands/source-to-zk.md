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
   - Description: "Use video-transcript-extractor agent to fetch transcript from video URL"
   - ActiveForm: "Extracting video transcript"

3. **Generate structured Markdown**
   - Subject: "Generate structured Markdown"
   - Description: "Use markdown-file-generator agent to convert source to clean Markdown"
   - ActiveForm: "Generating structured Markdown"

4. **Integrate into Zettelkasten**
   - Subject: "Integrate into Zettelkasten"
   - Description: "Use zettelkasten-integrator agent to create literature note with frontmatter, links, and MOC updates"
   - ActiveForm: "Integrating into Zettelkasten"

5. **Report completion**
   - Subject: "Report completion"
   - Description: "Output final location, backlinks, and MOC updates"
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

**Read agent**: `~/.claude/agents/video-transcript-extractor.md`

Use the Task tool to delegate to `general-purpose` subagent with:

```
Prompt: "You are delegated to act as the video-transcript-extractor agent.

Read the agent instructions at: ~/.claude/agents/video-transcript-extractor.md

Then extract the transcript from this video URL: <video_url>

Mode: STRICT — abort on any failure. No fallbacks. No partial results.

Output location: zz.original-source/<video-title>.md

Return the path to the created transcript file."
```

**On success**: Update task to `completed`, store transcript file path
**On failure**: STOP entire workflow — update all remaining tasks to `deleted`, report error to user

**If transcript extraction fails → STOP the entire workflow. No fallback.**

### Phase 1: Content Crawling & Extraction

**Update task**: Mark "Generate structured Markdown" as `in_progress`

**Read agent**: `~/.claude/agents/markdown-file-generator.md`
**Read prompt**: `~/.claude/prompts/crawler.prompt.md`

Use the Task tool to delegate to `general-purpose` subagent with:

```
Prompt: "You are delegated to act as the markdown-file-generator agent.

Read the agent instructions at: ~/.claude/agents/markdown-file-generator.md
Read the formatting rules at: ~/.claude/prompts/crawler.prompt.md

Then convert this source to structured Markdown:
<source> = <URL | text | transcript file path>

Requirements:
- Zero data loss policy
- Preserve tables/code/SVGs
- Output to: zz.original-source/src-<title-kebab>.md
- For complex diagrams, you may sub-delegate to ~/.claude/agents/diagram-generator.md

Return the path to the created Markdown file."
```

**On success**: Update task to `completed`, store source file path
**On failure**: Report error, suggest alternatives to user

### Phase 2: Zettelkasten Integration

**Update task**: Mark "Integrate into Zettelkasten" as `in_progress`

**Read agent**: `~/.claude/agents/zettelkasten-integrator.md`
**Read prompt**: `~/.claude/prompts/obsidian-note.prompt.md`

Use the Task tool to delegate to `general-purpose` subagent with:

```
Prompt: "You are delegated to act as the zettelkasten-integrator agent.

Read the agent instructions at: ~/.claude/agents/zettelkasten-integrator.md
Read the formatting rules at: ~/.claude/prompts/obsidian-note.prompt.md

Then integrate this source Markdown into a Zettelkasten literature note:
Source file: <path from Phase 1>

Follow this procedure:
1. Analyze content → determine domain folder (cs/web/ai/principle/devops/math)
2. Create filename: Domain-Concept-Name-In-Train-Case.md
3. Apply literature note frontmatter (Date, Type, Categories, Before/Next, Link, Src)
4. Structure: Abstract → Content sub-sections → Links
5. Add code examples with Bad vs Good pattern (TypeScript preferred)
6. For visual aids: you may sub-delegate to ~/.claude/agents/diagram-generator.md
7. Scan vault for related notes → add backlinks
8. Update MOCs in 000.Index/
9. Delete source file from zz.original-source/
10. Report final location + MOC updates

Return:
- Note path
- Domain
- Backlinks added
- MOC updates
- Source file deletion status"
```

**On success**: Update task to `completed`, store results
**On failure (domain unclear)**: Ask user to specify domain, then retry

### Step 3: Report

**Update task**: Mark "Report completion" as `in_progress`

After Phase 2 completes, output:

```
✅ Zettelkasten note created
📄 Location: <domain>/<filename>.md
🔗 Links: <backlinks added>
📑 MOC updates: <MOCs modified>
```

**Update task**: Mark "Report completion" as `completed`

**Final step**: You may now display the TaskList to show the user all completed tasks.

## Error Handling

| Phase | Error                  | Action                            |
| ----- | ---------------------- | --------------------------------- |
| 0     | Transcript fetch fails | **ABORT** entire workflow         |
| 1     | URL unreachable        | Report error, suggest alternative |
| 2     | Domain unclear         | Ask user to specify               |
