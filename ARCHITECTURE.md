# Architecture Deep Dive

This document provides a comprehensive overview of the knowledge management plugin collection's architecture, design principles, and implementation patterns.

## Table of Contents

1. [Overview](#overview)
2. [Multi-Phase Agent System](#multi-phase-agent-system)
3. [Zettelkasten Pipeline](#zettelkasten-pipeline)
4. [Plugin System](#plugin-system)
5. [Configuration Architecture](#configuration-architecture)
6. [Agent Design Patterns](#agent-design-patterns)
7. [Integration Patterns](#integration-patterns)
8. [Best Practices](#best-practices)

## Overview

This plugin collection is built on Claude Code's extensibility system, utilizing:

- **Agents** - Specialized workers that execute specific tasks
- **Commands** - Orchestrators that coordinate agent workflows
- **Skills** - User-invocable standalone workflows
- **Prompts** - Reusable formatting and content rules
- **MCP Servers** - External tool integrations (context7, github)
- **Hooks** - Event-driven validation and automation (future)

## Multi-Phase Agent System

### Delegated Architecture

The system uses a **delegated agent architecture** where orchestrators read agent definitions before delegation:

```
┌─────────────────────────────────────────────┐
│ Commands (orchestrators)                     │
│  - Read agent definitions                    │
│  - Coordinate multi-phase workflows          │
│  - Handle errors and state transitions       │
└──────────────┬──────────────────────────────┘
               │ delegates to
               ▼
┌─────────────────────────────────────────────┐
│ Agents (specialists)                         │
│  - Read prompt files for rules               │
│  - Execute specific transformations          │
│  - Report completion or errors               │
└──────────────┬──────────────────────────────┘
               │ applies
               ▼
┌─────────────────────────────────────────────┐
│ Prompts (rules)                              │
│  - Content extraction guidelines             │
│  - Formatting specifications                 │
│  - Output structure requirements             │
└─────────────────────────────────────────────┘
```

### Key Principle: Read Before Delegate

**Commands MUST read agent files before using Task tool:**

```markdown
## Procedure

1. **Read Agent Definitions**
   - Read agents/video-transcript-extractor.md
   - Read agents/markdown-file-generator.md
   - Read agents/zettelkasten-integrator.md

2. **Phase 1: Delegate**
   - Use Task tool with agent context
   - Pass input parameters
   - Wait for completion

3. **Phase 2: Continue**
   - Process Phase 1 output
   - Delegate to next agent
```

This ensures:
- ✅ Consistent agent behavior across invocations
- ✅ Agents have full context and instructions
- ✅ Changes to agent definitions take effect immediately
- ✅ No stale agent logic in command orchestrators

## Zettelkasten Pipeline

### Three-Phase Architecture

#### Phase 0: Video Processing (Conditional)

**Trigger**: Input is a video URL
**Agent**: `video-transcript-extractor.md`
**Output**: `zz.original-source/<video-title>.md`
**Mode**: STRICT - failures abort entire workflow

```
Video URL → Transcript extraction → Markdown file
                ↓ failure
          Abort workflow (no fallback)
```

#### Phase 1: Content Extraction

**Input**: Any source (URL, text, file, transcript)
**Agent**: `markdown-file-generator.md`
**Prompt**: `crawler.prompt.md`
**Output**: `zz.original-source/src-<title>.md`
**Policy**: Zero data loss - preserve all content

```
Source → Parse & Extract → Structured Markdown
         (no summarization)
```

#### Phase 2: Zettelkasten Integration

**Input**: Markdown file from Phase 1
**Agent**: `zettelkasten-integrator.md`
**Prompt**: `obsidian-note.prompt.md`
**Output**: `<domain>/<Domain-Concept-Train-Case>.md`
**Functions**:
- Domain detection (cs/, web/, ai/, principle/, devops/, math/)
- Frontmatter generation (Date, Type, Categories, Before/Next)
- Backlink creation and MOC updates
- Source file deletion after success

```
Markdown → Domain detection → Frontmatter
        → Backlinks        → MOC updates
        → Write note       → Delete source
```

### Error Handling Strategy

**Phase 0 (Video)**:
- Failure → Abort entire workflow
- No partial results accepted
- Clear error message with video URL

**Phase 1 & 2**:
- Failure → Report error
- Don't cascade to next phase
- Preserve source file for retry

## Plugin System

### Monorepo Structure

The plugin collection supports **both unified and modular installation**:

```
knowledge-management/           (Root unified plugin)
├── plugin.json                 # Unified manifest
├── .mcp.json                   # MCP servers
├── agents/                     # Component plugin
│   └── plugin.json
├── commands/                   # Component plugin
│   └── plugin.json
├── statusline/                 # Component plugin
│   └── plugin.json
├── skills/                     # Standalone plugins
│   ├── crawler/plugin.json
│   └── zk-note/plugin.json
└── prompts/                    # Shared resources (no manifest)
```

### Plugin Hierarchy

**Level 1: Unified Plugin**
```json
{
  "name": "knowledge-management",
  "commands": "./commands",
  "agents": "./agents",
  "mcpServers": "./.mcp.json"
}
```

**Level 2: Component Plugins**
```json
{
  "name": "knowledge-management-agents",
  "agents": ".",
  "dependencies": {
    "prompts": "../prompts"
  }
}
```

**Level 3: Shared Resources**
- `prompts/` - Imported by agents
- `examples/` - Reference configurations

### Dependency Declaration

Component plugins declare dependencies on shared resources:

```json
{
  "dependencies": {
    "agents": "../agents",
    "prompts": "../prompts"
  }
}
```

This enables:
- ✅ Standalone component usage
- ✅ Clear dependency tracking
- ✅ Modular installation

## Configuration Architecture

### Settings Hierarchy

Claude Code uses layered configuration with the following precedence (highest to lowest):

1. **Managed Settings** (`managed-settings.json`) - Organization policies
2. **Local Settings** (`settings.local.json`) - User/project overrides
3. **Global Settings** (`settings.json`) - Default configuration
4. **Built-in Defaults** - Hardcoded fallbacks

### Permission System

**Permission Pattern Syntax:**
```
Bash(command:*)         # Allow command with any args
Bash(command:arg)       # Allow command with specific arg
mcp__server__tool       # Allow specific MCP tool
ToolName                # Entire tool (Read, Write, etc.)
```

**Example Configuration:**
```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(npm:*)",
      "mcp__context7__*"
    ],
    "ask": ["Bash(git:push)"],
    "deny": []
  }
}
```

### Statusline System

**Input Data Structure** (from Claude Code):
```json
{
  "workspace": { "current_dir": "/path" },
  "model": { "display_name": "Claude Sonnet 4.5" },
  "version": "1.2.3",
  "output_style": { "name": "markdown" },
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 1000,
      "cache_creation_input_tokens": 500,
      "cache_read_input_tokens": 100
    },
    "total_input_tokens": 5000,
    "total_output_tokens": 2000
  },
  "cost": { "total_cost_usd": 0.25 }
}
```

**Output Format** (3 lines):
```
Line 1: 📁 ~/project | 🌿 main | 🤖 Claude Sonnet 4.5 | v1.2.3 | markdown
Line 2: 🧠 85% remaining ████████████████████░░░░ (green/orange/red based on %)
Line 3: 📊 7.0k tokens (↓5.0k ↑2.0k) | 💰 $0.25
```

## Agent Design Patterns

### Standard Agent Structure

Every agent follows this template:

```markdown
# Agent: <Name>

## Role
<One-sentence specialization>

## Input
- Input type 1
- Input type 2

## Output
- Output location and format

## Procedure

1. **Phase 1: <Name>**
   - Read `prompts/<relevant>.prompt.md`
   - Parse input
   - Extract data

2. **Phase 2: <Name>**
   - Transform content
   - Apply rules
   - Validate

3. **Phase 3: <Name>**
   - Write output
   - Update related files
   - Report completion

## Error Handling
- Failure modes
- Recovery strategies
```

### Agent Inventory

**1. markdown-file-generator.md**
- **Input**: Web URL, text, file path, video transcript
- **Output**: `zz.original-source/src-<title>.md`
- **Reads**: `prompts/crawler.prompt.md`
- **Policy**: Zero data loss

**2. video-transcript-extractor.md**
- **Input**: Video URL (YouTube, Vimeo, etc.)
- **Output**: `zz.original-source/<video-title>.md`
- **Mode**: STRICT (failures abort workflow)

**3. zettelkasten-integrator.md**
- **Input**: Markdown file from Phase 1
- **Output**: `<domain>/<Domain-Concept-Train-Case>.md`
- **Reads**: `prompts/obsidian-note.prompt.md`
- **Functions**: Domain detection, frontmatter, backlinks, MOC updates

**4. ascii-diagram-generator.md**
- **Input**: Concept description
- **Output**: ASCII art diagram
- **Usage**: Sub-delegated from other agents

**5. diagram-generator.md**
- **Input**: Concept description
- **Output**: Mermaid/PlantUML diagram
- **Usage**: Sub-delegated for visualizations

### Prompt Files

**crawler.prompt.md**
- Content extraction guidelines
- Zero data loss policy
- Markdown structuring rules
- Code block preservation

**obsidian-note.prompt.md**
- Zettelkasten formatting rules
- Frontmatter specifications
- Backlink creation guidelines
- Train-Case naming conventions

## Integration Patterns

### MCP (Model Context Protocol)

**Configuration Methods:**

1. **Inline in plugin.json:**
```json
{
  "mcpServers": {
    "server-name": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server.js"],
      "env": { "API_KEY": "${API_KEY}" }
    }
  }
}
```

2. **Dedicated .mcp.json:**
```json
{
  "context7": {
    "command": "npx",
    "args": ["-y", "@context7/mcp-server"],
    "env": {}
  }
}
```

**Environment Variables:**
- `${CLAUDE_PLUGIN_ROOT}` - Plugin directory path
- `${API_KEY}` - Injected from shell environment
- `${VAR:-default}` - With fallback value

### Task Management

**Task Tracking Pattern:**
```markdown
1. Create task: TaskCreate(subject, description, activeForm)
2. Mark in progress: TaskUpdate(taskId, status: "in_progress")
3. Complete: TaskUpdate(taskId, status: "completed")
```

This provides:
- ✅ Progress visualization for users
- ✅ Clear workflow structure
- ✅ Error recovery points

## Best Practices

### 1. Configuration

**Security First:**
```json
{
  "permissions": {
    "disableBypassPermissionsMode": "disable",
    "allow": ["Bash(git:add)", "Bash(git:commit)"],
    "ask": ["Bash(git:push)"]
  }
}
```

**Performance:**
- Enable `fastMode: true` for faster output
- Use custom statusline only if needed
- Configure appropriate hook timeouts

### 2. Agent Development

**Always Read Prompts First:**
```markdown
1. Read prompts/crawler.prompt.md
2. Apply rules from prompt
3. Execute transformation
```

**Zero Data Loss:**
- No summarization during extraction
- Preserve all source information
- Transformation happens in later phases

**Strict Video Mode:**
- Video failures abort workflow
- No fallback to partial content
- Clear error messages

### 3. Path Resolution

**Use Plugin Root:**
```json
{
  "command": "bash ${CLAUDE_PLUGIN_ROOT}/statusline/statusline.sh"
}
```

This ensures:
- ✅ Portability across installations
- ✅ Works in any installation directory
- ✅ No hardcoded paths

### 4. Error Handling

**Conditional Abort:**
- Phase 0 (video): Abort on failure
- Phase 1 & 2: Report error, don't cascade

**Clear Error Messages:**
- Include context (URL, file path)
- Suggest recovery steps
- Preserve state for retry

## Research Foundation

This architecture is based on comprehensive research of:
- Claude Code's configuration system
- Plugin and hook integration patterns
- MCP server architecture
- Agent delegation best practices
- 172 debug sessions analyzed
- Official documentation cross-referenced via context7 MCP

The design prioritizes:
- ✅ **Modularity** - Components independently usable
- ✅ **Portability** - Works across installations
- ✅ **Maintainability** - Clear separation of concerns
- ✅ **Extensibility** - Easy to add new components
- ✅ **Documentation** - Comprehensive guides and examples

## Version History

- **1.0.0** - Initial release with unified and modular plugin structure
