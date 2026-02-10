# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a **configuration repository** containing reusable AI workflow components (skills, agents, commands, hooks) that can be plugged into other repositories. It serves as a centralized library of automation patterns, primarily designed for Zettelkasten knowledge management workflows but extensible to other use cases.

**Key Principle**: Components in this repo are **referenced from other repos**, not executed here. This repo is the source of truth for workflow definitions.

## Component Types

### Skills (`/skills/`)

Reusable prompts invoked via `/<skill-name>` in target repositories.

**Current Skills**:
- `crawler` - Convert any source (URL, text, file) to structured Markdown
- `zk-note` - Transform markdown into integrated Zettelkasten literature notes
- `terminal-colors` - Standardized bash color formatting for agent output

**Structure**: Each skill is a directory with `SKILL.md` (required) + optional `references/` subdirectory.

### Agents (`/agents/`)

Specialized processors that skills or commands delegate to. Agents are markdown files containing detailed step-by-step instructions.

**Current Agents**:
- `video-transcript-extractor.md` - Extract video transcripts using yt-dlp
- `zettelkasten-integrator.md` - Full Zettelkasten integration workflow
- `ascii-diagram-generator.md` - Create plain-text diagrams with Unicode box-drawing
- `diagram-generator.md` - Mermaid diagram generation
- `markdown-file-generator.md` - Structure raw content into proper Markdown

**Key Difference from Skills**: Agents are not directly invocable by users. They are referenced/loaded by skills or other agents.

### Commands (`/commands/`)

Multi-phase workflow definitions that orchestrate skills and agents.

**Current Commands**:
- `git-commit-message.md` - Automated stage, commit with conventional message, and push
- `source-to-zk.md` - Complete pipeline from source to integrated note

### Built-in Components (`.agents/`)

System-provided skills like `skill-creator` that are part of Claude Code itself.

### Hooks (`/hooks/`, `/.claude/hooks/`)

Lifecycle interceptors that modify Claude Code behavior at key execution points.

**Current Hooks**:
- Template-only hooks showing patterns for PreToolUse, PostToolUse, SessionStart, and Stop

**Structure**:
- `hooks/hooks.json` - Template definitions (reference material)
- `.claude/hooks/hooks.json` - Active hooks for this repository
- `rules/hooks.md` - Hook patterns and documentation

**Key Principle**: This repo provides **hook templates** as reference patterns, not production hooks. Target repositories should customize hooks based on their specific needs.

## Integration Pattern

### How Components Are Used

1. **Skills** are installed in target repo's `.claude/skills/` or referenced via path
2. **Agents** are stored externally (e.g., `~/.claude/agents/`) and loaded by path reference
3. **Commands** are workflow documentation referenced when building new automations
4. **Prompts** (external) stored in `~/.claude/prompts/` define formatting rules
5. **Hooks** are customized per target repo in `.claude/hooks/hooks.json` based on templates

### Example: Using in Target Repository

Target repository (e.g., Obsidian vault) references this repo's components:

```
Obsidian Vault/
├── .claude/
│   └── skills/           # Symlink or copy from this repo
│       ├── crawler/
│       ├── zk-note/
│       └── terminal-colors/
└── web/                  # Domain folders for notes
    └── Web-*.md
```

Agent usage in skill:
```markdown
<!-- Inside a skill -->
Delegate to agent:
Read and follow: ~/.claude/agents/video-transcript-extractor.md
```

## Adding New Components

### Creating a New Skill

1. Create directory: `skills/<skill-name>/`
2. Create `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: skill-name
   description: Brief description (shown in skill discovery)
   ---
   ```
3. Document workflow with clear sections: Input, Workflow, Execution, Output, Error Handling
4. Add references if needed: `references/<file>.md`
5. Use terminal color standards (reference `terminal-colors` skill)

### Creating a New Agent

1. Create file: `agents/<agent-name>.md`
2. Add YAML frontmatter with required fields:
   ```yaml
   ---
   description: "Brief description of what the agent does"
   whenToUse: "When this agent should be invoked"
   capabilities:
     - Capability 1
     - Capability 2
   tools:
     - Read
     - Write
   model: sonnet          # sonnet | opus | haiku
   color: blue            # blue | green | cyan | magenta | yellow | red
   mode: best-effort      # strict | best-effort
   externalDependencies:  # optional
     - "~/.claude/prompts/my-prompt.md"
   ---
   ```
3. Include body sections: Role, Terminal Colors, Input, Output, Procedure, Error Handling
4. Use numbered steps with progress indicators: `[N/M] Step...`
5. Define ABORT conditions for strict failure mode if applicable
6. Error Handling must be a table with Issue, Action, and Terminal Output columns
7. Document all dependencies (tools, external files) in frontmatter

### Creating a New Command

1. Create file: `commands/<command-name>.md`
2. Break down into phases (Phase 1, Phase 2, etc.)
3. Specify which agents/skills each phase uses
4. Include complete execution flow diagram
5. Document error handling for each phase

### Creating Hooks

1. Reference `hooks/hooks.json` for template structure
2. Hooks require: `matcher`, `command`, and `description`
3. Use standard input/output pattern: read JSON from stdin, output to stdout
4. Send user messages to stderr with `[Hook]` prefix
5. Exit with non-zero status to block tool execution
6. Common patterns documented in `rules/hooks.md`

**Hook Types**:
- **PreToolUse**: Validate or modify before tool execution
- **PostToolUse**: Process results after tool execution
- **SessionStart**: Initialize on session start
- **PreCompact**: Save state before context compression
- **Stop**: Cleanup on session end

**Matcher Examples**:
- `tool == "Bash"` - Match all bash commands
- `tool == "Bash" && tool_input.command matches "git push"` - Match specific command pattern
- `tool == "Edit" && tool_input.file_path matches "\\.tsx?$"` - Match file extension
- `*` - Match all events

## Configuration Requirements

### External Paths Referenced by Components

Components in this repo reference external configuration files. When using in a target repository, ensure these exist:

**Prompts** (`~/.claude/prompts/`):
- `crawler.prompt.md` - Content extraction and formatting rules
- `obsidian-note.prompt.md` - Zettelkasten note structure and style guide

**Agents** (`~/.claude/agents/`):
- Install agent files from this repo's `/agents/` directory
- Or reference directly if this repo is in a known location

**Tools**:
- `yt-dlp` - Required by video-transcript-extractor agent
- Python 3 - Bash permission configured in target repo's `.claude/settings.local.json`

## Design Patterns

### Zettelkasten Workflow Pattern

Components implement a three-phase pipeline for knowledge capture:

**Phase 0 (Optional)**: Source extraction
- Video → transcript via `video-transcript-extractor`
- Output: Raw content file

**Phase 1**: Content structuring
- URL/File/Text → structured Markdown via `crawler` or `markdown-file-generator`
- Output: `zz.original-source/src-*.md` in target repo

**Phase 2**: Knowledge integration
- Source file → integrated note via `zettelkasten-integrator`
- Output: Properly linked note in domain folder
- Side effects: Updates neighbor links, MOCs, backlinks

### Target Repository Structure (Expected)

Components assume target repos have:

```
target-repo/
├── zz.original-source/    # Temporary storage for Phase 1 output
├── 000.Index/             # Maps of Content (MOCs)
├── cs/                    # Domain folders
├── web/
├── ai/
├── principle/
├── devops/
└── math/
```

### Note Naming Convention

**Pattern**: `<Domain-Prefix>-<Concept-In-Train-Case>.md`

Domain prefixes:
- `cs/` → `CS-`
- `web/` → `Web-`
- `ai/` → `AI-`
- `principle/` → `Principle-`
- `devops/` → `DevOps-`
- `math/` → `Math-`

**Example**: `web/Web-React-Server-Components.md`

### Frontmatter Schema

```yaml
---
Date: YYYY-MM-DD
Type: literature
Categories: []
Sub-Categories: []
Aliases: []
Before: '[[Previous-Note]]'
Next: '[[Next-Note]]'
Link: '<source-url>'
Src: '[[zz.original-source/src-file]]'
---
```

Navigation (`Before`/`Next`) is bidirectional and maintained alphabetically within each domain.

### Terminal Output Standard

**Convention**: All agents must use standardized bash color codes defined in `terminal-colors` skill.

**Color Palette**:
```bash
RED='\033[91m'      # Errors, ABORT conditions
GREEN='\033[92m'    # Success, completion
YELLOW='\033[93m'   # Warnings, manual review needed
BLUE='\033[94m'     # Info, progress steps
CYAN='\033[96m'     # File paths, metadata
MAGENTA='\033[95m'  # Categories, domains
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'
```

**Required Patterns**:
- Progress: `echo -e "${BLUE}${BOLD}[N/M] Step description...${RESET}"`
- Success: `echo -e "${GREEN}✓${RESET} Action completed"`
- Error: `echo -e "${RED}✗ Error:${RESET} Description"`
- File path: `echo -e "${CYAN}  → ${DIM}/path/to/file${RESET}"`

**Reference**: See `skills/terminal-colors/SKILL.md` for complete patterns.

### Agent Execution Modes

**Strict Mode** (video-transcript-extractor):
- Any step failure → immediate ABORT
- No fallbacks, no partial results
- Clear error reporting with context

**Best-effort Mode** (other agents):
- Attempt recovery or alternatives
- Warn user of degraded output
- Complete with available data

## Common Conventions

### Code Examples Pattern

For programming-related content, use this standard format:

```typescript
❌ Bad:
// Problematic approach
const bad = () => { /* anti-pattern */ }

✅ Good:
// Better approach
const good = () => { /* best practice */ }
```

- Use TypeScript when applicable
- Include actual runnable code, not pseudocode
- Explain why bad approach is problematic
- Show concrete improvement in good approach

### Conventional Commits

Git workflow components use conventional commit format:

**Pattern**: `<type>(<scope>): <description>`

**Types**: `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `style`

**Example**: `feat(zk-note): add MOC auto-update`

### Diagram Guidelines

**ASCII Diagrams** (via `ascii-diagram-generator`):
- Use Unicode box-drawing: `─│┌┐└┘├┤┬┴┼`
- Target max 70 characters width
- Align all edges precisely (monospace math)
- Wrap in fenced code blocks
- Use arrows: `▶→` (solid), `╌╌▶` (dashed)

**Mermaid Diagrams** (via `diagram-generator`):
- Use for complex flows that benefit from auto-layout
- Provide as alternative to ASCII when needed

### File Naming

**Skills**: lowercase-kebab (e.g., `terminal-colors`)
**Agents**: lowercase-kebab (e.g., `video-transcript-extractor.md`)
**Commands**: lowercase-kebab (e.g., `git-commit-message.md`)
**Target notes**: Train-Case with domain prefix (e.g., `Web-React-Hooks.md`)

## Repository Structure

```
.
├── .agents/           # Built-in Claude Code agents
│   └── skills/
│       └── skill-creator/
├── .claude/           # Local configuration (not deployed)
│   ├── hooks/
│   │   └── hooks.json # Active hooks for this repo
│   ├── settings.local.json
│   └── projects/*/memory/
├── agents/            # Custom agent definitions (deployable)
│   ├── video-transcript-extractor.md
│   ├── zettelkasten-integrator.md
│   ├── ascii-diagram-generator.md
│   ├── diagram-generator.md
│   ├── markdown-file-generator.md
│   └── agent-creator/
│       └── commands/
│           └── create-agent.md
├── commands/          # Workflow documentation (reference material)
│   ├── git-commit-message.md
│   └── source-to-zk.md
├── hooks/             # Hook templates (reference material)
│   └── hooks.json     # Template hook definitions
├── rules/             # Development patterns and conventions
│   ├── hooks.md       # Hook system documentation
│   └── patterns.md    # General patterns
└── skills/            # User-invocable skills (deployable)
    ├── crawler/
    │   └── SKILL.md
    ├── terminal-colors/
    │   ├── SKILL.md
    │   └── references/
    │       └── color-palette.md
    └── zk-note/
        └── SKILL.md
```

**Deployable vs Local**:
- `skills/` and `agents/` → copied/symlinked to target repos
- `commands/` and `hooks/` → reference templates only
- `rules/` → development documentation
- `.claude/` → local config, repo-specific

## Modifying Components

### Updating a Skill

1. Locate skill directory: `skills/<skill-name>/`
2. Edit `SKILL.md`
3. Test in a target repository before committing
4. Update description if behavior changes significantly
5. Document any new external dependencies or path requirements

### Updating an Agent

1. Locate agent file: `agents/<agent-name>.md`
2. Update YAML frontmatter fields if capabilities, tools, or mode change
3. Maintain body section structure (Role, Terminal Colors, Input, Output, Procedure, Error Handling)
4. Update Terminal Colors section if changing output format
5. Test with skills that reference this agent
6. Update version or changelog if agent has breaking changes

### Updating Hook Templates

1. Locate template: `hooks/hooks.json`
2. Maintain JSON schema structure
3. Ensure examples follow input/output pattern (stdin/stdout)
4. Update `rules/hooks.md` if adding new patterns
5. Test in `.claude/hooks/hooks.json` before committing template changes

**Note**: Hook templates in `hooks/` are reference material. Active hooks live in `.claude/hooks/` for this repo.

### Testing Changes

1. Symlink modified component to a test target repo
2. Invoke skill or trigger workflow that uses the component
3. Verify output matches expected format
4. Check that external path references resolve correctly
5. Test error handling (invalid input, missing dependencies)

## Usage in Target Repositories

### Installing Skills

**Option 1: Symlink** (recommended for development):
```bash
ln -s /path/to/my-ai-usage/skills/crawler ~/.claude/skills/crawler
```

**Option 2: Copy** (for production):
```bash
cp -r /path/to/my-ai-usage/skills/crawler target-repo/.claude/skills/
```

### Installing Agents

Copy to global location:
```bash
cp agents/*.md ~/.claude/agents/
```

Or reference directly if this repo is in a stable location.

### Configuring Hooks

Hooks are customized per target repository based on templates:

**Option 1: Start from template**:
```bash
mkdir -p target-repo/.claude/hooks
cp hooks/hooks.json target-repo/.claude/hooks/hooks.json
# Edit to customize for target repo's needs
```

**Option 2: Reference documentation**:
- Read `hooks/hooks.json` for template patterns
- Read `rules/hooks.md` for hook system documentation
- Create custom hooks in target repo's `.claude/hooks/hooks.json`

**Common Hook Patterns**:
- Validate commands before execution (PreToolUse)
- Auto-format files after edits (PostToolUse)
- Block unsafe operations (PreToolUse with exit 1)
- Save/restore session state (SessionStart/Stop)

### Required External Files

Before using skills in a target repo, ensure external prompts exist:

```bash
# Create prompt directory
mkdir -p ~/.claude/prompts

# Add required prompts
# - crawler.prompt.md (content extraction rules)
# - obsidian-note.prompt.md (Zettelkasten formatting)
```

Prompt files define target-specific formatting and should be customized per use case.

## Extending the System

### Adding a New Workflow

1. **Identify the pattern**: Is it a skill (user-invoked), agent (delegated task), or command (multi-step workflow)?
2. **Create component file** in appropriate directory
3. **Follow conventions**: Use terminal colors, standardized sections, clear error handling
4. **Reference existing components**: Reuse agents where possible
5. **Document dependencies**: External tools, prompts, target repo structure
6. **Test thoroughly**: Verify in target repo before committing

### Adapting for Different Target Repos

Components assume Zettelkasten structure by default. To adapt:

**For different folder structures**:
- Modify domain folder paths in `zk-note` skill
- Update frontmatter schema as needed
- Change navigation logic (Before/Next) if different ordering desired

**For different note formats**:
- Replace `obsidian-note.prompt.md` reference with custom prompt
- Modify content sections in `zettelkasten-integrator`
- Adjust code example patterns if not using TypeScript

**For different workflows**:
- Create new skills that reference existing agents
- Combine agents in different sequences
- Add workflow-specific validation steps
