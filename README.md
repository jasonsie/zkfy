# zkfy

A Claude Code plugin that transforms unstructured content (URLs, videos, raw text) into structured Zettelkasten literature notes for Obsidian vaults.

## What It Does

zkfy automates the process of converting web content, YouTube videos, and raw text into well-structured Zettelkasten literature notes:

- **Extracts content** from URLs, YouTube videos, or plain text
- **Generates clean Markdown** following your formatting rules
- **Integrates into your vault** with proper frontmatter, backlinks, and navigation
- **Updates Maps of Content (MOCs)** automatically
- **Creates bidirectional links** between related notes

## Features

### Multi-Phase Pipeline

```
INPUT → [VIDEO TRANSCRIPTION] → MARKDOWN GENERATION → ZETTELKASTEN INTEGRATION → OUTPUT
```

1. **Phase 0 (Conditional)**: Extract video transcripts from YouTube/Vimeo
2. **Phase 1**: Convert content to clean, formatted Markdown
3. **Phase 2**: Integrate into vault with proper Zettelkasten structure

### Specialized Agents

- **video-agent**: Fetches video transcripts (YouTube, Vimeo)
- **markdown-file-agent**: Extracts and converts content to Markdown via Firecrawl CLI or WebFetch
- **diagram-agent**: Creates Mermaid diagrams for complex concepts
- **zettelkasten-agent** (Opus): Deep content analysis — atomic concept, domain, metadata classification (Categories/Sub-Categories/Aliases/tags), Feynman explanations, relationships
- **obsidian-formatter-agent** (Sonnet): Vault integration — filename, frontmatter, navigation, MOC updates, file writing

### Smart Features

- **Zero data loss**: Preserves all source content during transformation
- **Automatic domain detection**: Places notes in correct folders (cs/, web/, ai/, etc.)
- **Navigation links**: Generates Before/Next frontmatter for sequential reading
- **Diagram generation**: Creates visual aids for complex topics
- **Progress tracking**: Visual feedback for each pipeline phase

## Installation

### Prerequisites

- [Claude Code CLI](https://claude.com/code)
- An Obsidian vault with proper folder structure

### Required Vault Structure

Your Obsidian vault must contain these folders:

```
your-vault/
├── cs/                    # Computer Science notes
├── web/                   # Web development notes
├── ai/                    # AI/ML notes
├── principle/             # Principle notes
├── devops/                # DevOps notes
├── math/                  # Math notes
├── 000.Index/             # Maps of Content (MOCs)
└── zz.original-source/    # Source staging area
```

### Install Plugin

```bash
# Clone the repository
git clone https://github.com/jasonsie/zkfy.git
cd zkfy

# Link to Claude Code plugins directory
ln -s "$PWD" ~/.claude/plugins/zkfy

# Create required prompt files
mkdir -p ~/.claude/prompts
touch ~/.claude/prompts/crawler.prompt.md
touch ~/.claude/prompts/obsidian-note.prompt.md
```

### Configure Prompts

Create these prompt files with your formatting rules:

**`~/.claude/prompts/crawler.prompt.md`** — Markdown formatting rules for content extraction

**`~/.claude/prompts/obsidian-note.prompt.md`** — Zettelkasten literature note structure rules

**`~/.claude/prompts/notion-crawler.prompt.toml`** _(optional)_ — Custom rules for Notion content extraction

## Usage

### Commands

#### `/source-to-zk` — Web, Video, or Text to Zettelkasten

```bash
# Navigate to your Obsidian vault
cd /path/to/your/vault

# Run with any source type
/source-to-zk <url-or-text-or-file>
```

Examples:

```bash
# From a YouTube video
/source-to-zk https://www.youtube.com/watch?v=dQw4w9WgXcQ

# From a web article
/source-to-zk https://example.com/article

# From raw text
/source-to-zk "Your content here..."

# From a file
/source-to-zk /path/to/source.txt
```

#### `/notion-to-zk` — Notion Page to Zettelkasten

Import any Notion page directly into your vault via MCP integration.

```bash
/notion-to-zk https://www.notion.so/workspace/Page-Title-abc123
```

Requires Notion MCP server configured in `.claude/settings.local.json` and a `NOTION_API_KEY`.

#### `/firecrawl` — Web Scraping Utility

Run Firecrawl CLI commands directly from Claude Code.

```bash
/firecrawl scrape https://example.com
/firecrawl crawl https://example.com --wait --limit 50
/firecrawl map https://example.com
/firecrawl search "your query"
/firecrawl agent "Extract pricing info" --urls https://example.com/pricing
```

### Output

The plugin generates:

1. **Source file**: Saved to `zz.original-source/` with original content
2. **Literature note**: Placed in appropriate domain folder (e.g., `web/`, `ai/`)
3. **Updated neighbors**: Before/Next links updated in adjacent notes
4. **MOC updates**: Relevant Maps of Content updated with new entry

### Note Structure

Generated notes follow this format:

```markdown
---
Date: 2026-02-10
Type: literature
Categories: [Web, React]
Sub-Categories: [Hooks, State Management]
Aliases: [React Hooks, useState]
tags: [design-pattern, advanced]
Before: '[[Web-Previous-Note]]'
Next: '[[Web-Next-Note]]'
Link: 'https://source-url.com'
Src: '[[zz.original-source/20260210-source]]'
---

# Note Title

## Abstract

- Key point 1
- Key point 2
- Key point 3

## Section 1: Main Concept

Content with code examples...

## Section 2: Related Concept

More content...

## Links

- [[Related-Note]] - Explanation of relationship
```

## File Naming Convention

All notes use Train-Case naming:

```
Domain-Concept-Name-In-Train-Case.md
```

Examples:
- `Web-React-Server-Components.md`
- `CS-Binary-Search-Tree.md`
- `AI-Transformer-Architecture.md`

## Architecture

### Component Structure

```
zkfy/
├── .claude-plugin/
│   ├── plugin.json              # Plugin manifest
│   └── marketplace.json         # Marketplace listing
├── commands/
│   ├── source-to-zk.md          # Main pipeline: web/video/text → vault
│   ├── notion-to-zk.md          # Notion page → vault (via MCP)
│   └── firecrawl.md             # Firecrawl CLI wrapper
├── agents/
│   ├── video-agent.md            # Video transcript extraction
│   ├── markdown-file-agent.md    # Content extraction + Markdown conversion
│   ├── diagram-agent.md          # Mermaid diagram generation
│   ├── ascii-diagram-agent.md    # ASCII diagram generation
│   ├── zettelkasten-agent.md     # Content analysis (Opus)
│   └── obsidian-formatter-agent.md # Vault integration (Sonnet)
├── skills/
│   ├── zk-note/                 # Two-agent integration pipeline skill
│   ├── firecrawl-cli/           # Firecrawl CLI reference
│   └── terminal-colors/         # Standardized output formatting
└── hooks/
    ├── hooks.json               # Event-based automation
    └── validate-zk-structure.sh # Hook validation script
```

### Agent Delegation

The pipeline uses a two-stage integration design:

1. `markdown-file-agent` uses Firecrawl CLI (preferred) or WebFetch to scrape content; may delegate to `diagram-agent` for complex visuals
2. `zk-note` skill orchestrates the vault integration pipeline:
   - `zettelkasten-agent` (Opus) — analyzes content, extracts atomic concept, writes Feynman explanations
   - `obsidian-formatter-agent` (Sonnet) — generates filename, frontmatter, navigation links, writes to vault, updates MOCs

Each agent has a single, clear purpose and standardized terminal output formatting.

### Error Handling

- **Video extraction failures**: Abort entire workflow (no fallbacks)
- **Markdown generation failures**: Report error, suggest alternatives
- **Integration failures**: Ask user for clarification (e.g., domain selection)

## Development

### Testing

```bash
# Test the full pipeline
cd /path/to/vault
/source-to-zk <test-source>

# Test hook validation
cd hooks/
./test-validation.sh
```

### Modifying Agents

Each agent in `agents/*.md` has:
- **YAML frontmatter**: metadata, tools, model, color
- **System prompt**: role, procedures, error handling
- **Output formatting**: standardized progress indicators

When modifying agents:
1. Read the `terminal-colors` skill for formatting standards
2. Maintain numbered step patterns (`[1/N]`, `[2/N]`)
3. Use consistent color codes
4. Follow zero data loss policy

## Design Principles

1. **Atomic Responsibility**: Each agent has one clear purpose
2. **Zero Data Loss**: Preserve all source content in transformations
3. **Progress Visibility**: Use TaskCreate/TaskUpdate for tracking
4. **Graceful Degradation**: Handle missing optional dependencies
5. **User Confirmation**: Ask for input when approach is unclear

## Requirements

- **Claude Code**: Latest version
- **Obsidian**: With proper vault structure
- **External prompts**: `crawler.prompt.md` and `obsidian-note.prompt.md`
- **Firecrawl CLI** _(optional, recommended)_: `npm install -g firecrawl` + `FIRECRAWL_API_KEY` for better web scraping
- **Notion MCP** _(optional)_: Required for `/notion-to-zk` command

## License

[Your License Here]

## Contributing

Contributions welcome! Please read the architecture documentation in `CLAUDE.md` before submitting PRs.

## Support

For issues or questions, please open an issue on GitHub.
