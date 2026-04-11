# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is **zkfy**, a Claude Code plugin that transforms unstructured content (URLs, videos, raw text) into structured Zettelkasten literature notes for Obsidian vaults. The plugin follows a multi-phase pipeline architecture with specialized agents for each transformation step.

## Architecture

### Multi-Phase Pipeline

The core workflow follows this execution model:

```
INPUT → [VIDEO TRANSCRIPTION] → MARKDOWN GENERATION → ANALYSIS → FORMATTING → CROSS-POLLINATION → INDEX + LOG → OUTPUT
```

1. **Input Detection**: Classify source as VIDEO_URL, WEB_URL, or TEXT
2. **Phase 0 (Conditional)**: Extract video transcripts using `video-agent` agent
3. **Phase 1**: Convert content to clean Markdown using `markdown-file-agent` agent
4. **Phase 2**: Integrate into vault using `zk-note` skill, which orchestrates:
   - `zettelkasten-agent` (Opus) — concept analysis, synthesis, relationship reasoning
   - `obsidian-formatter-agent` (Sonnet) — filename, frontmatter, navigation, MOCs, file writing
5. **Phase 2.5**: Cross-pollinate using `cross-pollinator-agent` — update 5-10 existing related notes with backlinks
6. **Phase 3**: Record the operation — append to `.claude/log.md` via `wiki-log` skill, update `.claude/index.md` via `vault-index` skill

### Agent Hierarchy

Agents are specialized, single-purpose workers that can delegate to other agents:

- **video-agent**: Fetches video transcripts (YouTube, Vimeo)
- **markdown-file-agent**: Extracts and converts content to Markdown
  - May delegate to `diagram-agent` for complex visualizations
- **diagram-agent**: Creates Mermaid diagrams for Obsidian rendering
- **ascii-diagram-agent**: Creates ASCII diagrams for plain-text contexts
- **zettelkasten-agent**: Deep content analysis through Zettelkasten principles
  - Identifies atomic concept, domain classification, key insights
  - Classifies metadata: Categories, Sub-Categories, Aliases, and tags (Step 2.5)
  - Writes Feynman-style explanations and code examples
  - Discovers semantic relationships with existing vault notes
- **obsidian-formatter-agent**: Vault formatting and integration
  - Generates Train-Case filenames, frontmatter, note body structure
  - Discovers and updates Before/Next neighbors
  - Updates MOCs, writes the final note file
- **cross-pollinator-agent**: Knowledge graph enrichment
  - After a new note is created, propagates backlinks to existing related notes
  - Detects contradictions and adds inline warnings
  - Append-only — never rewrites existing content, max 10 notes per run

### Component Structure

```
.claude-plugin/
  plugin.json              # Plugin manifest
commands/
  source-to-zk.md         # Main orchestration command (ingest pipeline)
  query-to-note.md        # Promote query answers into permanent ZK notes
  vault-lint.md            # Semantic health checks (contradictions, orphans, gaps)
agents/
  *.md                    # Specialized worker agents with YAML frontmatter
skills/
  */SKILL.md              # Reusable skill modules
  vault-search/           # Tiered retrieval: Keyword Index → enriched entry scan → grep fallback
  wiki-log/               # Append-only operation log (.claude/log.md)
  vault-index/            # Enriched vault catalog with Keyword Index (.claude/index.md)
  vault-lint/             # 7 semantic health checks with auto-fix
hooks/
  hooks.json              # PreToolUse (ZK validation) + PostToolUse (index update signal)
  signal-index-update.sh  # Structure-based vault detection for auto-index hook
reference/
  hookify/                # Reference implementation (not active)
```

## External Dependencies

### Required Files Outside Repository

The plugin depends on these external files in the user's environment:

- `~/.claude/prompts/crawler.prompt.md` - Markdown formatting rules for content extraction
- `~/.claude/prompts/obsidian-note.prompt.md` - Zettelkasten literature note structure rules

### Expected Vault Structure

The target Obsidian vault must have:

- **Domain folders**: Any top-level directories (auto-discovered — no fixed naming required). Numeric prefixes are stripped (e.g., `111.cs/` → `cs` domain). Exclude list: `y.template/`, `row/`, `x.temp/`, `docs/`, `.obsidian/`, `.claude/`, `000.Index/`.
- **Index folder**: `000.Index/` containing Maps of Content (MOCs) — optional but recommended
- **Source staging**: `row/` for temporary files
- **`.claude/log.md`**: Operation log (auto-created by wiki-log skill)
- **`.claude/index.md`**: Auto-maintained vault catalog with enriched metadata + Keyword Index (auto-created by vault-index skill)

All skills default to `.` (current working directory) as vault root — run commands from inside your vault.

### LLM Wiki Pattern Operations

The plugin implements the three core operations from the LLM Wiki Pattern:

- **Ingest** (`/source-to-zk`): Process source → create note → cross-pollinate related notes → log + index
- **Query** (`/query-to-note`): Check for existing synthesis → search vault → synthesize answer → file as permanent note → cross-pollinate → log
- **Lint** (`/vault-lint`): Scan for contradictions, stale content, orphans, missing pages, concept gaps → auto-fix option → log

## Key Conventions

### Filename Pattern

All generated notes follow Train-Case naming:
```
Domain-Concept-Name-In-Train-Case.md
```

Examples:
- `Web-React-Server-Components.md`
- `CS-Binary-Search-Tree.md`
- `AI-Transformer-Architecture.md`

### Frontmatter Structure

```yaml
---
Date: YYYY-MM-DD
Type: literature
Categories: []
Sub-Categories: []
Aliases: []
tags: []
Before: '[[Previous-Note]]'
Next: '[[Next-Note]]'
Link: '<source-url>'
Src: '[[row/src-file]]'
---
```

The `tags` field enables cross-domain discovery using a controlled vocabulary:
`interview-prep`, `career`, `learning-strategy`, `performance`, `security`,
`testing`, `debugging`, `design-pattern`, `architecture`, `api-design`,
`concurrency`, `state-management`, `type-system`, `beginner`, `advanced`,
`reference`, `cheatsheet`, `stub`

The `Before`/`Next` fields create bidirectional navigation by:
1. Listing all notes in the domain folder
2. Sorting alphabetically
3. Finding insertion point for new note
4. Updating neighbor files' frontmatter

### Note Structure

1. **Frontmatter** - Metadata and navigation
2. **Abstract** - Choose one format:
   - List format (preferred): Key points as bullets
   - Diagram + text: Mermaid diagram + 1-2 sentences
   - Brief text: 2-3 Feynman-style sentences
3. **Content sections** - One aspect per section (### level)
   - Code examples required for programming concepts
   - Bad vs Good pattern with TypeScript preferred
4. **Links section** - Backlinks with explanations

### Terminal Colors

All agents use standardized color formatting (defined in `terminal-colors` skill):

```bash
RED='\033[91m'      # Errors
GREEN='\033[92m'    # Success
YELLOW='\033[93m'   # Warnings
BLUE='\033[94m'     # Info/progress
CYAN='\033[96m'     # File paths
MAGENTA='\033[95m'  # Domain/category
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'
```

## Development Workflow

### Testing the Pipeline

To test the full pipeline:
```bash
# Ingest: source → ZK note → cross-pollinate → log + index
/source-to-zk <url-or-text-or-file>

# Query: search vault → synthesize → file as permanent note
/query-to-note "How does X compare to Y?"

# Lint: semantic health check
/vault-lint 333.ai/
/vault-lint . --fix           # auto-fix weak links, concept gaps, cross-ref gaps

# Verify logging
grep "^## \[" .claude/log.md | tail -5
```

### Modifying Agents

Each agent is defined in `agents/*.md` with:
- **Frontmatter** (YAML): metadata, capabilities, tools, model, color
- **System prompt**: Role, procedures, error handling
- **Terminal output patterns**: Standardized progress indicators

When modifying agent files:
1. Read the `terminal-colors` skill first for output formatting
2. Maintain the numbered step pattern (`[1/N]`, `[2/N]`, etc.)
3. Use consistent color codes for similar message types
4. Follow the zero data loss policy for content extraction

### Agent Delegation Pattern

Agents delegate using the Task tool with `general-purpose` subagent:

```markdown
Prompt: "You are delegated to act as the <agent-name> agent.

Read the agent instructions at: ~/.claude/agents/<agent-name>.md
Read the formatting rules at: ~/.claude/prompts/<prompt-file>.md

Then <specific task instructions>

Return: <expected output format>"
```

### Error Handling Strategy

- **Phase 0 (Video)**: ABORT entire workflow on failure - no fallbacks
- **Phase 1 (Markdown)**: Report error, suggest alternatives
- **Phase 2 (Integration)**: Ask user for clarification (e.g., domain selection)

## Plugin Design Principles

1. **Atomic Responsibility**: Each agent has one clear purpose
2. **Zero Data Loss**: Preserve all source content in transformations
3. **Progress Visibility**: Use TaskCreate/TaskUpdate for pipeline tracking
4. **Graceful Degradation**: Agents handle missing optional dependencies
5. **User Confirmation**: Ask for input when domain/approach is unclear
6. **Strict Mode for Critical Paths**: Video transcription must succeed or abort

## Important Notes

- The `reference/hookify/` directory contains a reference plugin implementation but is not active in this plugin
- Diagram generation defaults to Mermaid for Obsidian compatibility, falls back to ASCII for plain-text contexts
- All agent file paths use `~/.claude/agents/` at runtime (symlinked or aliased to actual location)
- The plugin assumes prompt files exist - agents will abort if required prompts are missing
