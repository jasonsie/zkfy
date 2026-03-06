---
description: "Create a Zettelkasten note from a Notion page via MCP integration"
---

# Notion to Zettelkasten

Transform any Notion page into a well-formed Zettelkasten literature note.

## Input

If `$ARGUMENTS` is provided, use it as the Notion page URL.

Otherwise, use `AskUserQuestion` to prompt for input:

```json
{
  "questions": [
    {
      "question": "Which Notion page do you want to import into your Zettelkasten?",
      "header": "Notion Page",
      "multiSelect": false,
      "options": [
        {
          "label": "Paste URL",
          "description": "Enter the full Notion page URL (e.g., https://www.notion.so/workspace/Page-Title-abc123). Users can select 'Other' to input their URL."
        }
      ]
    }
  ]
}
```

**Note**: The user will be able to select "Other" to paste their Notion URL.

After getting the URL, extract the page ID and fetch the page title using MCP tools, then display it for confirmation before proceeding with extraction.

## Prerequisites

Before executing, verify:

1. **MCP Configuration**: Notion MCP server enabled in `.claude/settings.local.json`
2. **Authentication**: `NOTION_API_KEY` set in `.mcp.json`
3. **Integration Access**: Your Notion integration connected to target page/database

If prerequisites are not met, provide setup instructions and abort.

## Execution

You are an orchestrator running a specialized pipeline for Notion content. Read each agent file before delegating.

### Step 0: Initialize Task List

Create a task list to track pipeline progress:

1. **Validate Notion page access**
   - Subject: "Validate Notion page"
   - Description: "Extract page ID and verify accessibility via MCP"
   - ActiveForm: "Validating Notion page"

2. **Extract Notion content**
   - Subject: "Extract Notion content"
   - Description: "Fetch page metadata and convert all blocks to Markdown"
   - ActiveForm: "Extracting Notion content"

3. **Integrate into Zettelkasten**
   - Subject: "Integrate into Zettelkasten"
   - Description: "Transform staging file into literature note with domain detection, frontmatter, links, and MOC updates"
   - ActiveForm: "Integrating into Zettelkasten"

4. **Report completion**
   - Subject: "Report completion"
   - Description: "Output final location, domain, backlinks, and MOC updates"
   - ActiveForm: "Reporting completion"

**Important**: Update each task's status as you progress.

### Step 1: Validate Notion Page

**Update task**: Mark "Validate Notion page" as `in_progress`

Extract page ID from URL (typically the last segment after the final `-`).

Use MCP tools to verify access:
- `mcp__notion__search` — find the page
- `mcp__notion__retrieve-a-data-source` — verify read access

**On failure (401/404)**: STOP workflow, provide troubleshooting:
- Check token in `.mcp.json`
- Verify integration connection to page/database
- Confirm read access permissions
- Suggest opening page in Notion to test

**Update task**: Mark "Validate Notion page" as `completed`

### Phase 0: Notion Content Extraction

**Update task**: Mark "Extract Notion content" as `in_progress`

**Read prompt**: `~/.claude/prompts/notion-crawler.prompt.toml` (if exists)

#### Extract Metadata

Use `mcp__notion__retrieve-a-data-source` to get:
- Page title
- Page URL (canonical)
- Database name (auto-detected from parent, or "None" if standalone page)
- Properties: tags, status, created/edited dates, custom fields

Store in memory for frontmatter generation.

#### Extract Content Blocks

Use `mcp__notion__retrieve-page-blocks`:
1. Fetch all top-level blocks
2. Recursively fetch children for nested structures
3. Preserve block order exactly

Convert each block type to Markdown:
- **Text blocks**: Preserve inline formatting, convert headings (`#`), quotes (`>`)
- **Lists**: Maintain indentation (2 spaces/level), convert to-dos (`- [ ]`), toggles (`<details>`)
- **Code blocks**: ` ```lang\ncode\n``` `
- **Tables**: Markdown table format with `|` delimiters
- **Media**: `![alt](url)` for images, `[filename](url)` for files
- **Equations**: Preserve LaTeX as `$$latex$$`
- **Callouts**: `> **Type:** content`
- **Unsupported**: `<!-- Unsupported: type -->`

#### Generate Frontmatter

Create staging frontmatter:
```yaml
---
notion_source: <original page URL>
notion_database: <database name from metadata, or "None">
notion_properties:
  tags: [...]
  status: ...
  created: ...
  last_edited: ...
---
```

#### Save Staging File

Assemble:
1. Frontmatter (YAML)
2. Page title as H1: `# [Title]`
3. All converted blocks in order
4. Clean excessive whitespace (max 2 consecutive newlines)

**Save to**: `zz.original-source/src-notion-<title-kebab-case>.md`

**Error Handling**:
- **401 Unauthorized**: STOP. Verify token, restart Claude Code
- **404 Not Found**: STOP. Check URL and integration permissions
- **429 Rate Limit**: Wait 5s, retry once, then abort
- **Empty content**: SKIP Phase 2, notify user

**Update task**: Mark "Extract Notion content" as `completed`, store staging file path

### Phase 1: Content Crawling

**SKIP THIS PHASE** — content extraction completed in Phase 0.

### Phase 2: Zettelkasten Integration

**Update task**: Mark "Integrate into Zettelkasten" as `in_progress`

**Read agent**: `~/.claude/agents/zettelkasten-agent.md`
**Read prompt**: `~/.claude/prompts/obsidian-note.prompt.md`

Use the Task tool to delegate to `general-purpose` subagent:

```
Prompt: "You are delegated to act as the zettelkasten-agent agent.

Read the agent instructions at: ~/.claude/agents/zettelkasten-agent.md
Read the formatting rules at: ~/.claude/prompts/obsidian-note.prompt.md

Then integrate this Notion-sourced Markdown into a Zettelkasten literature note:
Source file: <staging file path from Phase 0>

Special handling for Notion sources:
1. Extract domain from notion_properties.tags and content analysis
2. Use keyword matching: cs → 111.cs/, web → 222.web/, ai → 333.ai/
3. Weight: Notion tags × 3, headings × 2, body × 1
4. Fallback to 111.cs/ if uncertain

Follow standard integration procedure:
1. Auto-detect domain folder → determine subfolder (up to 3 layers)
2. Create filename: Domain-Concept-Name-In-Train-Case.md
3. Transform frontmatter:
   - Remove notion_* fields
   - Add Zettelkasten fields (Date, Type, Categories, Before/Next)
   - Set Link to notion_source
   - Set Src to '<database name> (Notion)' or 'Notion' if database is "None"
4. Structure: Abstract (list/diagram/text) → Content sections → Links
5. Add code examples (Bad vs Good, TypeScript preferred)
6. Scan vault → add ≥2 backlinks with rationales
7. Update MOCs in 000.Index/
8. Delete staging file
9. Report: note path, domain detection results, backlinks, MOC updates

Return:
- Note path
- Domain (with detection justification)
- Backlinks added
- MOC updates
- Staging file deletion status"
```

**On success**: Update task to `completed`, store results
**On failure (domain unclear)**: Ask user to specify, then retry

### Step 3: Report

**Update task**: Mark "Report completion" as `in_progress`

Output:
```
✅ Zettelkasten note created from Notion
📄 Location: <domain>/<filename>.md
🏷️  Domain: <detected domain> (<keyword matches>)
🔗 Links: <backlinks added>
📑 MOC updates: <MOCs modified>
```

**Update task**: Mark "Report completion" as `completed`

**Final step**: Display TaskList to show completed pipeline.

## Error Handling

| Phase | Error                   | Action                                              |
| ----- | ----------------------- | --------------------------------------------------- |
| 0     | Authentication failed   | **STOP** — verify token, restart Claude Code        |
| 0     | Page not found          | **STOP** — check URL and integration permissions    |
| 0     | Rate limit exceeded     | Wait 5s, retry once, then abort                     |
| 0     | Empty content           | **SKIP** Phase 2 — notify user                      |
| 2     | Domain unclear          | Ask user to specify domain                          |

## Future: Batch Processing

After validating single-article workflow, implement:
- Category-based batch import
- Progress tracking for multiple articles
- Duplicate detection (match Notion URL in frontmatter)
- Resume capability for interrupted batches
