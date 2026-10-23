<!-- Generated: 2026-04-11 | Files scanned: 24 | Token estimate: ~1300 -->

# zkfy Plugin Codemap

## Pipeline Architecture

```
INPUT (URL/video/text/file)
  |
  v
[Phase 0] video-agent -----> transcript (conditional: video URLs only)
  |
  v
[Phase 1] markdown-file-agent --> raw/src-*.md
  |          \--- may delegate to diagram-agent
  v
[Phase 2] zk-note skill orchestrates:
  |
  +---> zettelkasten-agent (Opus)  --> analysis JSON
  |       atomic concept, domain (auto-discovered), metadata, Feynman text, relationships
  |
  +---> obsidian-formatter-agent (Sonnet) --> final .md in vault
  |       filename, frontmatter (Before/Next empty), file write, suggested MOC entries (no MOC/neighbor edits)
  v
[Phase 2.5] cross-pollinator-agent (Sonnet)
  |       Dry run: propose backlinks to 5-10 existing related notes (+ suggested MOC entries)
  |       flag contradictions; apply only user-approved edits
  v
[Phase 3] Validate (mandatory)
          vault-knowledge lint, then vault-knowledge build (catalog is generated only by build; .claude/log.md is frozen)
```

### LLM Wiki Pattern — Three Core Operations

```
Ingest:  /source-to-zk  → Phase 0-3 full pipeline
Query:   /query-to-note  → [dedup check] → vault-knowledge search/read → synthesize → zk-note → cross-pollinate (proposals) → lint + build
Lint:    /vault-lint      → semantic checks → [proposed fixes, applied on approval]
```

### Vault Retrieval — Scoped CLI

```
~/.local/bin/vault-knowledge search "<terms>" --limit N
  → ranked paths + headings + excerpts
~/.local/bin/vault-knowledge read "<path>" --heading "<Heading>"
  → actual section text (cite before claiming)
```

Read-only and scoped by the vault's `docs/knowledge/scope.json`; `raw/` is excluded. Commands and skills call the CLI directly (the former `vault-search` skill was folded into `query`).

## Agents

| Agent | Model | Purpose | Key I/O |
|-------|-------|---------|---------|
| `video-agent` | default | Extract video transcripts | URL --> transcript markdown |
| `markdown-file-agent` | default | Capture + convert to markdown | URL --> `raw/<Page Title>.md` via the global `web-clipper` skill; text/transcript --> `raw/src-*.md` |
| `diagram-agent` | default | Mermaid diagrams for Obsidian | concept --> mermaid code block |
| `ascii-diagram-agent` | default | ASCII diagrams for plain-text | concept --> ASCII art |
| `zettelkasten-agent` | Opus | Deep content analysis | source markdown --> analysis (concept, domain, metadata, links) |
| `obsidian-formatter-agent` | Sonnet | Vault formatting + integration | analysis --> final note file + suggested MOC entries |
| `cross-pollinator-agent` | Sonnet | Knowledge graph enrichment | new note + candidates --> proposed backlinks (dry run); applied only after user approval |

## Skills

| Skill | Purpose |
|-------|---------|
| `zk-note/` | Orchestrates zettelkasten-agent + obsidian-formatter-agent pipeline |
| `query/` | Read-only vault queries via `vault-knowledge search` / `read` |
| `vault-index/` | Catalog generation: `.claude/index.md` and related files are produced only by `vault-knowledge build` |
| `vault-lint/` | 7 semantic health checks: contradictions, staleness, orphans, missing pages, weak links, concept gaps, cross-ref gaps. Checks 5-7 fixes proposed, applied on user approval |
| `terminal-colors/` | Standardized ANSI color codes for agent output |
| `x-learn-study-sop/` | 4-phase study SOP: checkpoint, RAG extraction, parallel impl, commit |

## Commands

| Command | Trigger | Pipeline Steps |
|---------|---------|----------------|
| `/source-to-zk` | URL, text, or file path | Detect type --> [Phase 0] --> Phase 1 --> Phase 2 --> Phase 2.5 --> Phase 3 Validate (mandatory) |
| `/query-to-note` | Natural language question | [Step 0.5 dedup] --> vault-knowledge search/read --> synthesize --> zk-note --> cross-pollinate (proposals) --> lint + build |
| `/vault-lint` | Directory path [--fix] [--checks] | semantic checks --> [proposed fixes 5,6,7, applied on approval] |
| `/notion-to-zk` | Notion page URL | Notion MCP fetch --> Phase 1 --> Phase 2 --> Phase 2.5 --> Phase 3 |

## Hooks

| Event | Script | Purpose |
|-------|--------|---------|
| PreToolUse (Write/Edit .md) | `validate-zk-structure.sh` | Redirect notes to `/output` if vault structure invalid |
| PostToolUse (Write .md) | `signal-index-update.sh` | Remind about separate catalog maintenance after note writes (structure-based vault detection) |

## External Dependencies

| Dependency | Location | Required |
|------------|----------|----------|
| `crawler.prompt.md` | `~/.claude/prompts/` | Yes |
| `obsidian-note.prompt.md` | `~/.claude/prompts/` | Yes |
| `notion-crawler.prompt.toml` | `~/.claude/prompts/` | /notion-to-zk only |
| Vault domain folders | Target vault (auto-discovered) | Yes |
| `000.Index/` MOCs | Target vault | Optional but recommended |
| `raw/` | Target vault | Source drop zone (excluded from queries) |
| `.claude/log.md` | Target vault | Frozen history, no longer written |
| `.claude/index.md` | Target vault | Generated only by `vault-knowledge build` |
| `web-clipper` skill | `~/.claude/skills/web-clipper/` (ai_dotfiles) | URL sources; exit 2 means save the page from a browser and rerun with `--html` |
| Notion MCP server | `.claude/settings.local.json` | /notion-to-zk only |

## Error Handling

| Phase | Strategy |
|-------|----------|
| Phase 0 (Video) | ABORT entire workflow — no fallbacks |
| Phase 1 (Markdown) | Report error, suggest alternatives |
| Phase 2 (Integration) | Ask user for clarification |
| Phase 2.5 (Cross-pollination) | Warn user, note still created |
| Phase 3 (Validate) | Mandatory — report lint/build failure; pipeline not marked fully successful |

## Vault-Agnostic Design

All skills default to `.` (cwd). Domain folders are auto-discovered by scanning top-level dirs and stripping numeric prefixes (e.g., `111.cs/` → `cs`). No hardcoded vault paths.

## File Structure

```
zkfy/
  .claude-plugin/plugin.json     # Plugin manifest
  commands/                      # 5 slash commands
  agents/                        # 7 specialized agents
  skills/                        # 7 reusable skill modules
  hooks/
    hooks.json                   # PreToolUse + PostToolUse hooks
    validate-zk-structure.sh     # ZK structure validation
    signal-index-update.sh       # Auto-index signal (vault detection)
  reference/                     # Reference docs (hookify, llm-wiki)
  docs/CODEMAPS/                 # This codemap
```
