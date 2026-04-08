<!-- Generated: 2026-04-08 | Files scanned: 23 | Token estimate: ~1100 -->

# zkfy Plugin Codemap

## Pipeline Architecture

```
INPUT (URL/video/text/file)
  |
  v
[Phase 0] video-agent -----> transcript (conditional: video URLs only)
  |
  v
[Phase 1] markdown-file-agent --> row/src-*.md
  |          \--- may delegate to diagram-agent
  v
[Phase 2] zk-note skill orchestrates:
  |
  +---> zettelkasten-agent (Opus)  --> analysis JSON
  |       atomic concept, domain, metadata, Feynman text, relationships
  |
  +---> obsidian-formatter-agent (Sonnet) --> final .md in vault
  |       filename, frontmatter, nav links, MOC update, file write
  v
[Phase 2.5] cross-pollinator-agent (Sonnet)
  |       propagate backlinks to 5-10 existing related notes
  |       flag contradictions with inline warnings
  v
[Phase 3] wiki-log + vault-index
          append to .claude/log.md, update .claude/index.md
```

### LLM Wiki Pattern — Three Core Operations

```
Ingest:  /source-to-zk  → Phase 0-3 full pipeline
Query:   /query-to-note  → vault-search → synthesize → zk-note → cross-pollinate → log
Lint:    /vault-lint      → 7 semantic checks → [auto-fix] → log
```

## Agents

| Agent | Model | Purpose | Key I/O |
|-------|-------|---------|---------|
| `video-agent` | default | Extract video transcripts | URL --> transcript markdown |
| `markdown-file-agent` | default | Scrape + convert to markdown | URL/text --> `row/src-*.md` |
| `diagram-agent` | default | Mermaid diagrams for Obsidian | concept --> mermaid code block |
| `ascii-diagram-agent` | default | ASCII diagrams for plain-text | concept --> ASCII art |
| `zettelkasten-agent` | Opus | Deep content analysis | source markdown --> analysis (concept, domain, metadata, links) |
| `obsidian-formatter-agent` | Sonnet | Vault formatting + integration | analysis --> final note file + MOC updates |
| `cross-pollinator-agent` | Sonnet | Knowledge graph enrichment | new note + candidates --> backlinks added to existing notes |

## Skills

| Skill | Purpose |
|-------|---------|
| `zk-note/` | Orchestrates zettelkasten-agent + obsidian-formatter-agent pipeline |
| `vault-search/` | Natural language vault search: Tier 0 index lookup + 3-tier Grep across Aliases/metadata/body, returns ranked notes with abstracts |
| `vault-index/` | Auto-maintained vault catalog at `.claude/index.md`, grouped by domain with abstracts and tags |
| `vault-lint/` | 7 semantic health checks: contradictions, staleness, orphans, missing pages, weak links, concept gaps, cross-ref gaps. Checks 5-7 auto-fixable |
| `wiki-log/` | Append-only operation log at `.claude/log.md` tracking ingest, query, and lint operations |
| `firecrawl-cli/` | Firecrawl CLI usage reference (scrape, crawl, map, search, agent) |
| `terminal-colors/` | Standardized ANSI color codes for agent output |
| `x-learn-study-sop/` | 4-phase study SOP: checkpoint, RAG extraction, parallel impl, commit |

## Commands

| Command | Trigger | Pipeline Steps |
|---------|---------|----------------|
| `/source-to-zk` | URL, text, or file path | Detect type --> [Phase 0] --> Phase 1 --> Phase 2 --> Phase 2.5 --> Phase 3 |
| `/query-to-note` | Natural language question | vault-search --> synthesize --> zk-note --> cross-pollinate --> log + index |
| `/vault-lint` | Directory path [--fix] [--checks] | 7 semantic checks --> [auto-fix 5,6,7] --> log results |
| `/notion-to-zk` | Notion page URL | Notion MCP fetch --> Phase 1 --> Phase 2 --> Phase 2.5 --> Phase 3 |
| `/firecrawl` | Firecrawl subcommand | Direct CLI wrapper (scrape, crawl, map, search, agent) |

## External Dependencies

| Dependency | Location | Required |
|------------|----------|----------|
| `crawler.prompt.md` | `~/.claude/prompts/` | Yes |
| `obsidian-note.prompt.md` | `~/.claude/prompts/` | Yes |
| `notion-crawler.prompt.toml` | `~/.claude/prompts/` | /notion-to-zk only |
| Vault domain folders | Target vault | Yes |
| `000.Index/` MOCs | Target vault | Yes |
| `row/` | Target vault | Yes |
| `.claude/log.md` | Target vault | Auto-created by wiki-log |
| `.claude/index.md` | Target vault | Auto-created by vault-index |
| Firecrawl CLI + API key | Global npm | Optional (falls back to WebFetch) |
| Notion MCP server | `.claude/settings.local.json` | /notion-to-zk only |

## Error Handling

| Phase | Strategy |
|-------|----------|
| Phase 0 (Video) | ABORT entire workflow — no fallbacks |
| Phase 1 (Markdown) | Report error, suggest alternatives |
| Phase 2 (Integration) | Ask user for clarification |
| Phase 2.5 (Cross-pollination) | Warn user, note still created |
| Phase 3 (Log/Index) | Warn user, note + cross-pollination still done |

## File Structure

```
zkfy/
  .claude-plugin/plugin.json     # Plugin manifest
  commands/                      # 5 slash commands
  agents/                        # 7 specialized agents
  skills/                        # 8 reusable skill modules
  hooks/hooks.json               # Event-based automation
  reference/hookify/             # Reference impl (inactive)
```
