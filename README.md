# zkfy

A plugin for Claude Code, Codex, Pi and Antigravity that transforms unstructured content (URLs, videos, raw text) into structured Zettelkasten literature notes for an Obsidian vault, and keeps that vault healthy. One repo, one release tag per version, installed by each CLI's own plugin manager.

## What It Does

zkfy automates the process of converting web content, YouTube videos, and raw text into well-structured Zettelkasten literature notes:

- **Extracts content** from URLs, YouTube videos, or plain text
- **Generates clean Markdown** following your formatting rules
- **Integrates into your vault** with proper frontmatter and backlinks
- **Proposes Maps of Content (MOC) entries** for you to approve
- **Proposes bidirectional links** between related notes (applied only after your approval)

## Features

### Multi-Phase Pipeline

```
INPUT → [VIDEO TRANSCRIPTION] → MARKDOWN GENERATION → ANALYSIS → FORMATTING → CROSS-POLLINATION (PROPOSALS) → VALIDATE → OUTPUT
```

1. **Phase 0 (Conditional)**: Extract video transcripts from YouTube/Vimeo
2. **Phase 1**: Convert content to clean, formatted Markdown
3. **Phase 2**: Integrate into vault via `zk-note` skill — 4-agent Hybrid Atom/Thesis pipeline (zettelkasten-agent → conceptual-modeler-agent → diagram-agent → obsidian-formatter-agent); spinoff candidates are reported, never saved
4. **Phase 2.5**: Cross-pollinate — propose backlinks for 5-10 existing related notes (dry run); apply only the ones you approve
5. **Phase 3**: Validate — run `vault-knowledge lint`, then `vault-knowledge build` to regenerate the catalog

### Five Core Operations (LLM Wiki Pattern)

Each is a skill, invoked by its bare name: `/zkfy:source-to-zk` in Claude Code, `/skill:source-to-zk` in Pi, `/source-to-zk` in Antigravity; Codex lists them under `/skills`.

| Operation | Skill | Description |
|-----------|-------|-------------|
| **Ingest** | `source-to-zk` | Source → note → cross-pollinate (proposals) → lint + build |
| **Clip** | `clip-to-zk` | File a source verbatim as a `Mode: clip` note, images renamed, backlinks proposed |
| **Query** | `query-to-note` | Search vault → synthesize → file as permanent note → cross-pollinate (proposals) → lint + build |
| **Lint** | `vault-lint` | Detect contradictions, orphans, stale content, concept gaps → proposed fixes applied only on approval |
| **Reorganize** | `vault-reorg` | Survey → interview → mapping → weave + ledger → apply → stage → confirm commit |

### Specialized Agents

- **video-agent**: Fetches video transcripts (YouTube, Vimeo)
- **markdown-file-agent**: Captures URLs with the `web-clipper` plugin (full page, images localized) and converts text or transcripts to Markdown
- **diagram-agent**: Creates Mermaid diagrams for complex concepts
- **zettelkasten-agent**: Discover layer — atomic concept identification, domain selection, metadata classification (Categories/Sub-Categories/Aliases/tags), related-notes discovery
- **conceptual-modeler-agent**: Distill layer — classifies `note_mode` (atom vs thesis per ADR-0002), produces mode-appropriate artifact (atom: one-line definition + optional Why/Boundary/Code; thesis: executive summary + theme chapters + optional appendix), emits mental model + spinoff candidates, self-validates mode-aware char budget
- **obsidian-formatter-agent**: Integrate layer — mode-branched skeleton assembly, writes `Mode: atom | thesis` frontmatter, filename, empty `Before`/`Next`, suggested MOC entries, file writing
- **cross-pollinator-agent**: Knowledge graph enrichment — proposes backlinks to existing related notes (dry run), flags contradictions

### Smart Features

- **Zero data loss**: Preserves all source content during transformation
- **Automatic domain detection**: Places notes in correct folders (cs/, web/, ai/, etc.)
- **Navigation fields**: New notes carry empty `Before`/`Next`; neighbors are never rewired automatically
- **Diagram generation**: Creates visual aids for complex topics
- **Cross-pollination**: New notes propose backlinks to existing related notes; you approve what is applied
- **Vault catalog**: `.claude/index.md` and related catalog files are generated only by `vault-knowledge build`; `.claude/log.md` is frozen history and is no longer written
- **Semantic linting**: 12 health checks (contradictions, staleness, orphans, missing pages, weak links, concept gaps, cross-ref gaps, Concept-First conformance, Hybrid Mode conformance)
- **Reorganization**: `/vault-reorg` merges notes that explain the same concept by weaving them into one note, checked by a unit ledger so no content is lost; it stages its own files and commits only on your yes
- **Progress tracking**: Visual feedback for each pipeline phase

## Installation

### Prerequisites

- One of Claude Code, Codex, Pi or Antigravity
- An Obsidian vault with its scope policy, `docs/knowledge/scope.json`, at the root
- The `web-clipper` plugin ([jasonsie/web-clipper](https://github.com/jasonsie/web-clipper)), 2.2 or later, for URL sources

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
├── raw/                   # Source drop zone (excluded from queries)
└── .claude/               # Generated catalog
    ├── log.md             # Frozen history (no longer written)
    └── index.md           # Vault catalog (generated by vault-knowledge build)
```

### Install the plugin

The recommended way is [ai-dotfiles](https://github.com/jasonsie/ai-dotfiles): list `zkfy` and
`web-clipper` in its `config/plugins.json` at exact versions and run `ai-dotfiles install`. It
installs each release tag (`zkfy--v<version>`) through every CLI's own plugin manager and links
the `vault-knowledge` and `web-clipper` commands into `~/.local/bin`.

By hand, per CLI, at a release tag:

```bash
# Claude Code: web-clipper's marketplace first (zkfy depends on it), then zkfy
claude plugin marketplace add jasonsie/web-clipper
/plugin install zkfy --marketplace jasonsie/zkfy

# Codex
codex plugin marketplace add jasonsie/zkfy --ref zkfy--v1.7.0
codex plugin add zkfy@zkfy-marketplace

# Pi
pi install git:github.com/jasonsie/zkfy@zkfy--v1.7.0

# Antigravity
agy plugin install https://github.com/jasonsie/zkfy/tree/zkfy--v1.7.0
```

Without ai-dotfiles, put the plugin's `bin/vault-knowledge` on your PATH yourself; Claude Code
does that on its own.

### Bind the vault

```bash
# Writes ~/.config/zkfy/knowledge.json (python, vault); idempotent; --dry-run; `unbind` removes it
vault-knowledge bind --vault /path/to/your/vault

# The prompt files the agents read
mkdir -p ~/.claude/prompts
touch ~/.claude/prompts/crawler.prompt.md ~/.claude/prompts/obsidian-note.prompt.md
```

### Configure Prompts

Create these prompt files with your formatting rules:

**`~/.claude/prompts/crawler.prompt.md`** — Markdown formatting rules for content extraction

**`~/.claude/prompts/obsidian-note.prompt.md`** — Zettelkasten literature note structure rules

**`~/.claude/prompts/notion-crawler.prompt.toml`** _(optional)_ — Custom rules for Notion content extraction

## Usage

### Skills

The examples use Claude Code's form, `/zkfy:<skill>`; the other CLIs take the bare skill name.

#### `source-to-zk` — Web, Video, or Text to Zettelkasten

```bash
# Navigate to your Obsidian vault
cd /path/to/your/vault

# Run with any source type
/zkfy:source-to-zk <url-or-text-or-file>
```

Examples:

```bash
# From a YouTube video
/zkfy:source-to-zk https://www.youtube.com/watch?v=dQw4w9WgXcQ

# From a web article
/zkfy:source-to-zk https://example.com/article

# From raw text
/zkfy:source-to-zk "Your content here..."

# From a file
/zkfy:source-to-zk /path/to/source.txt
```

#### `query-to-note` — Promote Query Answers to Permanent Notes

Search the vault, synthesize an answer, and file it as a permanent Zettelkasten note.

```bash
/zkfy:query-to-note "How does RAG compare to the LLM Wiki pattern?"
/zkfy:query-to-note "What are the trade-offs between SSR and CSR?"
/zkfy:query-to-note "Summarize all backtracking algorithm patterns in the vault"
```

Pipeline: `vault-knowledge search`/`read` → synthesize → zk-note → cross-pollinate (proposals) → lint + build

#### `vault-lint` — Semantic Health Checks

Run 12 semantic health checks on the vault to detect contradictions, stale content, orphans, and Concept-First / Hybrid Mode spec violations.

```bash
/zkfy:vault-lint 333.ai/                   # Lint the AI directory
/zkfy:vault-lint . --checks 3,4            # Check orphans and missing pages only
/zkfy:vault-lint 111.cs/ --fix             # Lint CS directory and propose fixes for checks 5,6,7,10 (applied only after approval)
/zkfy:vault-lint 222.web/ --checks 8,9,10  # Concept-First spec violations only
/zkfy:vault-lint . --checks 8,9,11,12      # Hybrid Mode conformance only
```

The 12 checks: (1) Contradictions, (2) Stale content, (3) Orphan pages, (4) Missing pages, (5) Weak links [fixable], (6) Concept gaps [fixable], (7) Cross-ref gaps [fixable], (8) Missing required-core section, (9) Body over 500-char budget, (10) Legacy `--preserve` artifacts [fixable], (11) Thesis chapter budget, (12) Dangling thesis back-link

Checks 8–12 enforce the Concept-First and Hybrid Mode specs (see `docs/ADR/0001-concept-first-pipeline.md` and `docs/ADR/0002-hybrid-atom-thesis-mode.md`); Checks 8, 9 and 10 also know `Mode: clip` (`docs/ADR/0004-clip-mode-verbatim-notes.md`). Notes with `Date` before 2026-05-28 receive LOW severity for these checks; newer notes get the intrinsic severity.

**Note modes** (ADR-0002, ADR-0004). Every note declares `Mode: atom | thesis | clip` in frontmatter. The modeler picks atom or thesis per source: atom notes hold a single concept (≤ 500-char body); thesis notes carry a macro claim with supporting theme chapters (per-chapter 200–1500-char soft target). Clip notes (`Mode: clip`, from `/zkfy:clip-to-zk`) hold a source verbatim, with no body budget; Checks 9, 10 and 11 skip them. Completion reports show 🧬 Mode after the note location.

#### `clip-to-zk` — File a Source Verbatim

Keep a source exactly as captured instead of distilling it.

```bash
/zkfy:clip-to-zk <url | raw/clip.md | file | text | video> [domain] [--vault <root>]
```

It writes a `Mode: clip` note: the body is the source verbatim, with zkfy frontmatter, a Train-Case filename in a domain sub-folder, and a `### Links` section appended. Images are renamed to match the note. Backlinks to related notes are proposed, never applied without approval. The `raw/` copy is removed only after the new note passes verification and lint. It needs the `web-clipper` plugin command. One source per run. Design: `docs/ADR/0004-clip-mode-verbatim-notes.md`.

#### `vault-reorg` — Reorganize the vault

Reorganize a vault in passes. A pass is one run over one scope, ending in one reviewed change set. Run it from the vault root (the folder that holds `docs/knowledge/scope.json`).

```bash
/zkfy:vault-reorg                           # Survey first, then the opening dialogs
/zkfy:vault-reorg 111.cs/language/javascript  # Start with this folder as the scope
/zkfy:vault-reorg --job survey              # Detection report only, nothing changes
```

The skill surveys the vault, then asks in dialogs. The first dialog picks the jobs: Survey (a detection report), Consolidate (merge notes that cover one concept), Restructure (moves, flattening and renames, no merges) and Curate (compare a topic's coverage with its canonical subtopics). The next picks the scope, and the last asks per-job options.

A merge is a weave, not an append. You approve one outline for the concept. Every unique unit (paragraph, list, table, code block) of every clustered note is placed under it once, and repeated units keep their best version. A unit ledger records what happened to each unit (kept, reworded, duplicate of, dropped), and a deterministic check must pass before any absorbed note is deleted. You review every row that is not kept.

`apply` stages only the files it touched, rebuilds the catalog, and asks before committing. It refuses to start when a file it must change has uncommitted edits. `raw/` is never touched. Coverage gaps found by Curate become an ingest backlog in the pass record under the vault's `docs/plans/`; no stub notes are created. See `docs/ADR/0005-reorganization-as-reviewed-weave.md`.

#### `notion-to-zk` — Notion Page to Zettelkasten

Import any Notion page directly into your vault via MCP integration.

```bash
/zkfy:notion-to-zk https://www.notion.so/workspace/Page-Title-abc123
```

Uses the plugin's `notion` MCP server (`.mcp.json` for Claude Code and Codex, `mcp_config.json` for Antigravity); connect it once when asked. Pi loads no plugin MCP server until 1.8.0, so this skill is not available there.

### Web clipping

URL sources are captured by the `web-clipper` plugin
([jasonsie/web-clipper](https://github.com/jasonsie/web-clipper)), a zkfy dependency,
exactly as Obsidian Web Clipper would: full body, the clip frontmatter, and every image,
inline SVG and canvas graph saved under the vault's attachment folder as `![[…]]` links.
`source-to-zk <url>` uses it in Phase 1, and it can be run on its own:

```
/web-clipper:web-clipper https://example.com/article
/web-clipper:web-clipper --localize raw/some-clip.md      # download remote images of an existing clip
```

Pages behind a bot challenge, login or paywall cannot be fetched headlessly: the clipper
stops with exit 2, and the recourse is to save the rendered page from your own browser and
rerun with `--html <file>`. There is no scraping-service fallback.

### Output

The plugin generates:

1. **Source file**: Saved to `raw/` with original content
2. **Literature note**: Placed in appropriate domain folder (e.g., `web/`, `ai/`) with empty `Before`/`Next`
3. **Suggested MOC entries**: MOC path + line, applied only after your approval
4. **Proposed cross-pollination**: 5-10 existing related notes with proposed backlinks, applied only after your approval
5. **Spinoff candidates**: Listed in the report only (not saved)
6. **Lint result**: `vault-knowledge lint` violations touching the new or edited files
7. **Catalog**: Rebuilt via `vault-knowledge build`

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
Before: ''
Next: ''
Link: 'https://source-url.com'
Src: '[[raw/20260210-source]]'
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

## Support by CLI

The plugin follows ai-dotfiles' `portable-plugin` rules; a feature a CLI cannot load as shipped is a gap, named here until a release fills it.

| | Claude Code | Codex | Pi | Antigravity |
|---|---|---|---|---|
| Skills (11) | yes, as `/zkfy:<skill>` | yes | yes, as `/skill:<skill>` | yes, as `/<skill>` |
| `vault-knowledge` on PATH | the plugin's `bin/`, and ai-dotfiles' link | ai-dotfiles' link | ai-dotfiles' link | ai-dotfiles' link |
| Hooks (vault guard, catalog reminder) | yes | yes, after trusting them once in `/hooks` | gap: a Pi extension comes in 1.8.0 | gap: a root `hooks.json` comes in 1.8.0 |
| MCP server `notion` | yes (`.mcp.json`) | yes (`.mcp.json`) | gap: the 1.8.0 extension registers it | yes (`mcp_config.json`) |
| Agents (8) | yes | no plugin agents in Codex; skills read the agent file in the session | no subagents; skills read the agent file in the session | yes |

`agy plugin validate --strict` reports three warnings by design: `.mcp.json`, `hooks/hooks.json` and `AGENTS.md` are the files Claude Code, Codex and the maintainers read, not Antigravity's.

## Architecture

### Component Structure

```
zkfy/
├── .claude-plugin/
│   ├── plugin.json              # Plugin manifest: the one version, the web-clipper dependency
│   └── marketplace.json         # Marketplace listing (no version of its own)
├── .antigravity-plugin/
│   └── plugin.json              # Antigravity's native manifest: loads the plugin as is
├── .mcp.json                    # Notion MCP server for Claude Code and Codex
├── mcp_config.json              # The same server for Antigravity
├── bin/
│   └── vault-knowledge          # The knowledge CLI on PATH: bind, unbind, then knowledge.py's commands
├── agents/
│   ├── video-agent.md            # Video transcript extraction
│   ├── markdown-file-agent.md    # Content extraction + Markdown conversion
│   ├── diagram-agent.md          # Diagram rendering (Image > ASCII > Mermaid > Structural Bullets)
│   ├── ascii-diagram-agent.md    # ASCII diagram generation
│   ├── zettelkasten-agent.md     # Discover layer
│   ├── conceptual-modeler-agent.md # Distill layer (detail in docs/agents/)
│   ├── obsidian-formatter-agent.md # Integrate layer
│   └── cross-pollinator-agent.md # Knowledge graph enrichment
├── skills/
│   ├── source-to-zk/            # Ingest: web/video/text → vault
│   ├── clip-to-zk/              # Verbatim clip notes (Mode: clip), with scripts/clip_note.py
│   ├── query-to-note/           # Query: search → synthesize → file as note
│   ├── notion-to-zk/            # Notion page → vault (via MCP)
│   ├── zk-note/                 # The 4-agent integration pipeline
│   ├── query/                   # Read-only vault queries via vault-knowledge search/read
│   ├── vault-index/             # Catalog generation via vault-knowledge build
│   ├── vault-lint/              # 12 semantic health checks (methods in references/checks.md)
│   ├── vault-reorg/             # Reorganization passes: interview, weave, unit ledger, apply
│   ├── x-learn-study-sop/       # 4-phase study SOP
│   └── terminal-colors/         # Standardized output formatting
├── scripts/
│   ├── knowledge.py             # Scoped vault CLI: search, read, build, lint, reorg
│   ├── reorg.py                 # Reorganization subcommands: survey, units, plan, ledger, apply
│   └── clip_note.py             # clip-to-zk's file operations
├── hooks/
│   ├── hooks.json               # PreToolUse / PostToolUse hooks (Claude Code, Codex)
│   ├── validate-zk-structure.sh # Vault structure guard
│   └── signal-index-update.sh   # Catalog maintenance reminder
└── tests/                       # unittest: knowledge, reorg, clip_note, the launcher, the portable invariants
```

### Agent Delegation

The pipeline uses a multi-stage design:

1. `markdown-file-agent` captures URLs with the `web-clipper` plugin (text and transcripts are converted directly); may delegate to `diagram-agent` for complex visuals
2. `zk-note` skill orchestrates the vault integration pipeline:
   - `zettelkasten-agent` — analyzes content, extracts atomic concept, writes Feynman explanations
   - `obsidian-formatter-agent` — generates filename, frontmatter, writes to vault, returns suggested MOC entries
3. `cross-pollinator-agent` (`Dry run: true`) — proposes backlinks for 5-10 existing related notes, flags contradictions; you approve what is applied
4. Validate — `vault-knowledge lint`, then `vault-knowledge build` to regenerate the catalog

Each agent has a single, clear purpose and standardized terminal output formatting.

### Error Handling

- **Video extraction failures**: Abort entire workflow (no fallbacks)
- **Markdown generation failures**: Report error, suggest alternatives
- **Integration failures**: Ask user for clarification (e.g., domain selection)
- **Cross-pollination failures**: Warn user, note is still created
- **Lint/build failures**: Warn user, note and approved cross-pollination are still done

## Development

### Testing

```bash
# Unit tests: knowledge, reorg, clip_note, the launcher, the portable-plugin invariants
python3 -B -m unittest discover -s tests -p 'test_*.py'

# The portable-plugin check (ai-dotfiles' skill): no error in either validator
claude plugin validate .
agy plugin validate --strict .      # three warnings by design, see Support by CLI

# In a vault, end to end
/zkfy:source-to-zk <test-source>
/zkfy:query-to-note "How does X compare to Y?"
/zkfy:vault-lint 333.ai/

# Test hook validation
cd hooks/
./test-validation.sh
```

### Modifying Agents

Each agent in `agents/*.md` has:
- **YAML frontmatter**: name, description, tools, `model: inherit`, color (strict YAML: quote any value holding punctuation)
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

- **Claude Code, Codex, Pi or Antigravity**: a current version (see Support by CLI)
- **Python 3.10+** with PyYAML, for `vault-knowledge`
- **Obsidian**: With proper vault structure
- **External prompts**: `crawler.prompt.md` and `obsidian-note.prompt.md`
- **web-clipper plugin** _(dependency, [jasonsie/web-clipper](https://github.com/jasonsie/web-clipper))_: Node 21+, the built `obsidian-clipper` CLI and Python Playwright, for URL sources
- **Notion MCP** _(optional)_: the plugin's own server, for `notion-to-zk` (not in Pi)

## License

[Your License Here]

## Contributing

Contributions welcome! Please read the architecture documentation in `CLAUDE.md` before submitting PRs.

## Issues

For issues or questions, please open an issue on GitHub.
