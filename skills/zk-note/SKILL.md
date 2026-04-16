---
name: zk-note
description: Transform markdown files into fully integrated Zettelkasten literature notes with frontmatter, backlinks, and MOC updates. Use when you need to (1) Create atomic notes from existing markdown, (2) Add proper navigation and categorization, (3) Link notes into your knowledge graph, (4) Apply Feynman-style synthesis (--digest, default) or preserve original content verbatim (--preserve).
---

# ZK-Note

Transform markdown into a fully integrated Zettelkasten literature note.

## Input

$ARGUMENTS — <path-to-markdown-file> [domain] [--preserve | --digest]

Optional domain: cs/web/ai/principle/devops/math

Optional flags:
- **--digest** (default): Full Feynman-style rewriting with synthesized code examples and bad/good patterns
- **--preserve**: Keep original content verbatim; only add structural elements (frontmatter, abstract, links, navigation)

## Execution Order

This skill orchestrates two agents in sequence:

```
Source File
    │
    ▼
┌─────────────────────────┐
│  zettelkasten-agent      │  Opus — deep reasoning
│  (analyze & synthesize)  │
│                          │
│  → atomic concept        │
│  → domain classification │
│  → Feynman explanations  │  (digest mode)
│  → verbatim pass-through │  (preserve mode)
│  → relationship rationale│
└──────────┬──────────────┘
           │ analysis results
           ▼
┌─────────────────────────┐
│  obsidian-formatter-agent│  Sonnet — mechanical
│  (format & integrate)    │
│                          │
│  → Train-Case filename   │
│  → frontmatter + nav     │
│  → assemble note file    │
│  → update neighbors      │
│  → update MOCs           │
└──────────┬──────────────┘
           │
           ▼
      Cleanup & Report
```

### Step 1: Read Source and Parse Flags

Read the markdown file from the provided path. Extract the source URL if present in the file.

Parse flags from `$ARGUMENTS`:
- If `--preserve` is present → `format_mode = preserve`
- If `--digest` is present → `format_mode = digest`
- If neither is present → `format_mode = digest` (default)

### Step 2: Delegate to zettelkasten-agent (Analysis)

Use the Task tool to delegate to `general-purpose` subagent:

```
Prompt: "You are delegated to act as the zettelkasten-agent agent.

Read the agent instructions at: ~/.claude/agents/zettelkasten-agent.md

Then analyze this source content for Zettelkasten integration:
Source file: <path>
Vault root: <vault_root>
Format mode: <digest|preserve>
[Domain: <domain> — if provided by user]

Return a structured analysis:
- domain
- concept (atomic concept name)
- key_insights (bullet points)
- source_url
- abstract (formatted abstract section)
- content_sections (digest: fully written sub-sections with Feynman explanations and code examples; preserve: original content sections verbatim with ### headings applied)
- related_notes (list of [[Note]] — rationale pairs)"
```

If the zettelkasten-agent asks about domain, relay the question to the user.

### Step 3: Delegate to obsidian-formatter-agent (Integration)

Use the Task tool to delegate to `general-purpose` subagent:

```
Prompt: "You are delegated to act as the obsidian-formatter-agent agent.

Read the agent instructions at: ~/.claude/agents/obsidian-formatter-agent.md
Read the formatting rules at: ~/.claude/prompts/obsidian-note.prompt.md

Then format and integrate this literature note:

Domain: <domain from step 2>
Concept: <concept from step 2>
Abstract: <abstract from step 2>
Content sections: <content_sections from step 2>
Related notes: <related_notes from step 2>
Source URL: <source_url from step 2>
Source file: <source_file>
Today's date: <today's date>
Vault root: <vault_root>
Format mode: <digest|preserve>

Return:
- Note path and filename
- Neighbors updated
- MOCs updated"
```

### Step 3.5: Cross-Pollinate (optional)

If called from `/source-to-zk` or `/query-to-note`, delegate to `cross-pollinator-agent` to update existing related notes with backlinks to the new note:

```
Prompt: "You are delegated to act as the cross-pollinator-agent agent.

Read the agent instructions at: ~/.claude/agents/cross-pollinator-agent.md

Then cross-pollinate this newly created note:
New note path: <note path from step 3>
Vault root: <vault_root>
Candidates: <related_notes from step 2>
Dry run: false

Return the list of files updated and changes made."
```

If cross-pollination fails, warn but do not abort — the note is already created.

### Step 4: Cleanup & Report

Delete the source file from `row/`.

Report completion:
```
✅ Zettelkasten note created
📄 Location: <domain>/<filename>.md
🔗 Links: <backlinks added>
📑 MOC updates: <MOCs modified>
🔄 Navigation: Before→<note>→Next
🔄 Cross-updates: <N> existing notes enriched (if cross-pollination ran)
```

## Output

- Note path: `<domain>/<Domain-Concept-In-Train-Case>.md`
- Backlinks: List of related notes linked
- MOC updates: List of MOCs modified
- Navigation: Before/Next files updated

## Error Handling

**Source file not found:**
- Report the path that was tried
- Ask user to verify path

**Domain unclear (from zettelkasten-agent):**
- Present content summary
- Ask user to specify domain from: cs/web/ai/principle/devops/math

**Analysis fails:**
- Report error from zettelkasten-agent
- Abort workflow

**Formatting fails:**
- Report error from obsidian-formatter-agent
- Note: analysis is not lost, user can retry step 3

**No related notes found:**
- Proceed — Links section will be empty
- Warn user that no backlinks were added

**MOC missing:**
- Ask user: "Create new MOC or skip MOC update?"
- Proceed based on user choice
