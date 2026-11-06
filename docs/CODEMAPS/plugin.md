<!-- Generated: 2026-04-11, updated 2026-11-06 for the portable release | Token estimate: ~1400 -->

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
  +---> zettelkasten-agent         --> analysis JSON
  |       atomic concept, domain (auto-discovered), metadata, Feynman text, relationships
  |
  +---> obsidian-formatter-agent   --> final .md in vault
  |       filename, frontmatter (Before/Next empty), file write, suggested MOC entries (no MOC/neighbor edits)
  v
[Phase 2.5] cross-pollinator-agent
  |       Dry run: propose backlinks to 5-10 existing related notes (+ suggested MOC entries)
  |       flag contradictions; apply only user-approved edits
  v
[Phase 3] Validate (mandatory)
          vault-knowledge lint, then vault-knowledge build (catalog is generated only by build; .claude/log.md is frozen)
```

### LLM Wiki Pattern — Three Core Operations

```
Ingest:  source-to-zk   → Phase 0-3 full pipeline
Query:   query-to-note  → [dedup check] → vault-knowledge search/read → synthesize → zk-note → cross-pollinate (proposals) → lint + build
Lint:    vault-lint     → semantic checks → [proposed fixes, applied on approval]
```

### Vault Retrieval — Scoped CLI

```
vault-knowledge search "<terms>" --limit N
  → ranked paths + headings + excerpts
vault-knowledge read "<path>" --heading "<Heading>"
  → actual section text (cite before claiming)
```

Read-only and scoped by the vault's `docs/knowledge/scope.json`; `raw/` is excluded. Commands and skills call the CLI directly (the former `vault-search` skill was folded into `query`).

## Agents

All eight declare `model: inherit`; skills delegate by having a general subagent read the agent file (or do the work in the session where the CLI has no subagents).

| Agent | Purpose | Key I/O |
|-------|---------|---------|
| `video-agent` | Extract video transcripts | URL --> transcript markdown |
| `markdown-file-agent` | Capture + convert to markdown | URL --> `raw/<Page Title>.md` via the `web-clipper` plugin; text/transcript --> `raw/src-*.md` |
| `diagram-agent` | Diagrams: Image > ASCII > Mermaid > Structural Bullets | modality hint --> diagram block |
| `ascii-diagram-agent` | ASCII diagrams for plain-text | concept --> ASCII art |
| `zettelkasten-agent` | Discover layer | source markdown --> analysis (concept, domain, metadata, links) |
| `conceptual-modeler-agent` | Distill layer (detail in `docs/agents/conceptual-modeler-detail.md`) | analysis --> mode-aware conceptual artifact |
| `obsidian-formatter-agent` | Vault formatting + integration | artifact --> final note file + suggested MOC entries |
| `cross-pollinator-agent` | Knowledge graph enrichment | new note + candidates --> proposed backlinks (dry run); applied only after user approval |

## Skills

| Skill | Purpose |
|-------|---------|
| `zk-note/` | Orchestrates zettelkasten-agent + obsidian-formatter-agent pipeline |
| `query/` | Read-only vault queries via `vault-knowledge search` / `read` |
| `vault-index/` | Catalog generation: `.claude/index.md` and related files are produced only by `vault-knowledge build` |
| `vault-lint/` | 12 semantic health checks: contradictions, staleness, orphans, missing pages, weak links, concept gaps, cross-ref gaps (1-7), plus Concept-First / Hybrid Mode / clip-aware conformance (8-12); methods in `references/checks.md`. Fixes for 5-7 and 10 proposed, applied on user approval |
| `vault-reorg/` | Reorganization passes: survey, dialogs, mapping, weave with a unit ledger, apply |
| `clip-to-zk/` | Files a source verbatim as a `Mode: clip` note (`scripts/clip_note.py` does the exact steps); not part of the 3-stage pipeline |
| `terminal-colors/` | Standardized ANSI color codes for agent output |
| `x-learn-study-sop/` | 4-phase study SOP: checkpoint, RAG extraction, parallel impl, commit |

## Entry-point skills (user-invoked; `/zkfy:<name>` in Claude Code)

| Skill | Trigger | Pipeline Steps |
|-------|---------|----------------|
| `source-to-zk` | URL, text, or file path | Detect type --> [Phase 0] --> Phase 1 --> Phase 2 --> Phase 2.5 --> Phase 3 Validate (mandatory) |
| `query-to-note` | Natural language question | [Step 0.5 dedup] --> vault-knowledge search/read --> synthesize --> zk-note --> cross-pollinate (proposals) --> lint + build |
| `vault-lint` | Directory path [--fix] [--checks] | semantic checks --> [proposed fixes 5,6,7,10, applied on approval] |
| `vault-reorg` | [scope] [--job] | survey --> dialogs --> mapping --> weave or moves --> apply --> stage --> confirm commit |
| `notion-to-zk` | Notion page URL | Notion MCP fetch --> Phase 1 --> Phase 2 --> Phase 2.5 --> Phase 3 (not in Pi: no plugin MCP server) |
| `clip-to-zk` | URL, `raw/` clip, file, text, or video | dedupe --> capture --> Discover --> adopt --> `clip_note.py` --> verify --> delete raw copy --> cross-pollinate (proposals) --> lint + build. See `docs/ADR/0004-clip-mode-verbatim-notes.md` |

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
| `web-clipper` plugin | Dependency (`web-clipper@web-clipper-marketplace`, `^2.2`); provides the `web-clipper` command | URL sources; exit 2 means save the page from a browser and rerun with `--html`. `clip-to-zk` uses `--adopt`, `--release` and `--unadopt` (2.2) |
| Notion MCP server | `.mcp.json` (Claude Code, Codex), `mcp_config.json` (Antigravity) | notion-to-zk only |

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
  .claude-plugin/plugin.json     # Plugin manifest (the one version)
  .antigravity-plugin/plugin.json # Antigravity's native manifest
  .mcp.json, mcp_config.json     # Notion MCP server: Claude Code and Codex; Antigravity
  bin/vault-knowledge            # The knowledge CLI on PATH (bind, unbind, knowledge.py commands)
  agents/                        # 8 agents, model: inherit
  skills/                        # 11 skills; the five entry points among them
  hooks/
    hooks.json                   # PreToolUse + PostToolUse hooks (Claude Code, Codex)
    validate-zk-structure.sh     # ZK structure validation
    signal-index-update.sh       # Auto-index signal (vault detection)
  docs/agents/                   # Long-form detail an agent points at
  docs/CODEMAPS/                 # This codemap
  tests/                         # unittest, incl. test_portable.py
```
