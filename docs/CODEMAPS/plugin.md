<!-- Generated: 2026-04-07 | Files scanned: 17 | Token estimate: ~750 -->

# zkfy Plugin Codemap

## Pipeline Architecture

```
INPUT (URL/video/text/file)
  |
  v
[Phase 0] video-agent -----> transcript (conditional: video URLs only)
  |
  v
[Phase 1] markdown-file-agent --> zz.original-source/src-*.md
  |          \--- may delegate to diagram-agent
  v
[Phase 2] zk-note skill orchestrates:
  |
  +---> zettelkasten-agent (Opus)  --> analysis JSON
  |       atomic concept, domain, metadata, Feynman text, relationships
  |
  +---> obsidian-formatter-agent (Sonnet) --> final .md in vault
          filename, frontmatter, nav links, MOC update, file write
```

## Agents

| Agent | Model | Purpose | Key I/O |
|-------|-------|---------|---------|
| `video-agent` | default | Extract video transcripts | URL --> transcript markdown |
| `markdown-file-agent` | default | Scrape + convert to markdown | URL/text --> `zz.original-source/src-*.md` |
| `diagram-agent` | default | Mermaid diagrams for Obsidian | concept --> mermaid code block |
| `ascii-diagram-agent` | default | ASCII diagrams for plain-text | concept --> ASCII art |
| `zettelkasten-agent` | Opus | Deep content analysis | source markdown --> analysis (concept, domain, metadata, links) |
| `obsidian-formatter-agent` | Sonnet | Vault formatting + integration | analysis --> final note file + MOC updates |

## Skills

| Skill | Purpose |
|-------|---------|
| `zk-note/` | Orchestrates zettelkasten-agent + obsidian-formatter-agent pipeline |
| `vault-search/` | Natural language vault search: 3-tier Grep across Aliases/metadata/body, returns ranked notes with abstracts |
| `firecrawl-cli/` | Firecrawl CLI usage reference (scrape, crawl, map, search, agent) |
| `terminal-colors/` | Standardized ANSI color codes for agent output |
| `x-learn-study-sop/` | 4-phase study SOP: checkpoint, RAG extraction, parallel impl, commit |

## Commands

| Command | Trigger | Pipeline Steps |
|---------|---------|----------------|
| `/source-to-zk` | URL, text, or file path | Detect input type --> [Phase 0] --> Phase 1 --> Phase 2 |
| `/notion-to-zk` | Notion page URL | Notion MCP fetch --> Phase 1 --> Phase 2 |
| `/firecrawl` | Firecrawl subcommand | Direct CLI wrapper (scrape, crawl, map, search, agent) |

## External Dependencies

| Dependency | Location | Required |
|------------|----------|----------|
| `crawler.prompt.md` | `~/.claude/prompts/` | Yes |
| `obsidian-note.prompt.md` | `~/.claude/prompts/` | Yes |
| `notion-crawler.prompt.toml` | `~/.claude/prompts/` | /notion-to-zk only |
| Vault domain folders | Target vault | Yes |
| `000.Index/` MOCs | Target vault | Yes |
| `zz.original-source/` | Target vault | Yes |
| Firecrawl CLI + API key | Global npm | Optional (falls back to WebFetch) |
| Notion MCP server | `.claude/settings.local.json` | /notion-to-zk only |

## Error Handling

| Phase | Strategy |
|-------|----------|
| Phase 0 (Video) | ABORT entire workflow — no fallbacks |
| Phase 1 (Markdown) | Report error, suggest alternatives |
| Phase 2 (Integration) | Ask user for clarification |

## File Structure

```
zkfy/
  .claude-plugin/plugin.json     # Plugin manifest
  commands/                      # 3 slash commands
  agents/                        # 6 specialized agents
  skills/                        # 5 reusable skill modules
  hooks/hooks.json               # Event-based automation
  reference/hookify/             # Reference impl (inactive)
```
