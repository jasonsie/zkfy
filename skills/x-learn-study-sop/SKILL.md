---
name: x-learn-study-sop
description: "Reusable 4-phase study SOP for any x-learn project: checkpoint tracking, RAG extraction from any source, team-based parallel implementation with bilingual RADIO docs + FE folder examples, and git commit + doc update per item"
---

# x-learn Study SOP

Extracted from two completed x-learn projects:
- `design-patterns/` — 23 GoF patterns (PDF RAG + structured implementation)
- `oop/` — 17 OOP concepts (same pipeline + checkpoint system + git workflow)

Use this SOP to bootstrap any new x-learn project or to understand what skills and agents to generate.

---

## 1. When to Use

Trigger when:
- Bootstrapping a new x-learn subdirectory project (data structures, algorithms, system design, etc.)
- Implementing items (patterns, concepts, algorithms) within an existing x-learn project
- Creating the scaffolding files (CLAUDE.md, skills, agents, checkpoints, SUMMARY_MAP)

---

## 2. Project Config Template

Each project fills in this table once (in its CLAUDE.md or RAG skill):

| Field | Description | design-patterns | oop |
|-------|-------------|-----------------|-----|
| `DOMAIN` | Topic area | GoF Design Patterns | OOP Fundamentals |
| `REFERENCE_TYPE` | `pdf` / `web` / `md` / `repo` / `none` | `pdf` | `md` |
| `REFERENCE_PATH` | Source location | `reference/Design_Patterns.pdf` | `reference/*.md` |
| `TOPIC_CATALOG` | Item index file | `SUMMARY_MAP.md` | `SUMMARY_MAP.md` |
| `TIER_SCHEME` | Item grouping | `01-foundation/…04-specialized/` | `01-foundations/…03-solid/` |
| `ITEM_FOLDER_ROOT` | Where items live | `patterns/` | `concepts/` |
| `LANGUAGE` | Implementation language | TypeScript | TypeScript |
| `TEST_RUNNER` | Test command | `npx vitest run` | `npx vitest run` |
| `EXAMPLE_RUNNER` | Run example command | `npx tsx` | `npx tsx` |
| `EXTRACTION_FIELDS` | What to extract from source | See §6 | See §6 |

---

## 3. The 4-Phase Pipeline (per item)

Each item (pattern, concept, algorithm) runs through all 4 phases sequentially.

### Phase 0 — Checkpoint: Start

Before any work, record a start checkpoint:

```zsh
TIMESTAMP=$(date +%Y-%m-%d-%H:%M)
SHA=$(git rev-parse --short HEAD)
echo "${TIMESTAMP} | {ITEM_NAME}-start | ${SHA}" >> .claude/checkpoints.log
```

Report to user:
```
CHECKPOINT: {ITEM_NAME}-start
========================
SHA:       {sha}
Time:      {timestamp}
```

---

### Phase 1 — RAG: Knowledge Extraction

**Rule: Always read the actual source. Never rely on model memory.**

#### 1a. Locate the source

Based on `REFERENCE_TYPE`:

| Type | How to read |
|------|------------|
| `pdf` | Use Read tool with `pages` parameter; look up page range in the page-map table in the RAG skill |
| `md` | Use Read tool on the specific reference `.md` file(s) mapped to this item |
| `web` | Use WebFetch or `/firecrawl-scrape` to fetch the canonical documentation URL |
| `repo` | Use Serena MCP (`mcp__serena__*`) + Grep/Read to scan source code |
| `none` | Skip to Phase 2 Step 2 (deep research only) |

For PDFs spanning > 10 pages: split into two Read calls (PDF tool max = 20 pages per call).

#### 1b. Extract N structured fields

Extract the fields defined by `EXTRACTION_FIELDS` for this domain (see §6 for domain-specific templates).

Output: a structured block with all fields clearly labeled. This feeds into Phase 2.

---

### Phase 2 — Implementation

#### Team-Based Parallel Execution

When implementing multiple items (e.g., all items in a tier):
- Create a **team** where each agent tackles one item independently
- Each agent runs its own Phase 0→1→2→3 pipeline
- Parallelism = number of items in the current batch (tier or subset)
- Each agent reports independently when done

#### Step 1: Re-read Source (mandatory)

If running as a subagent, always re-read the source — never rely on context passed from another agent or prior phases.

#### Step 2: Deep Research (CRITICAL — quality bar is high)

**Real-world examples are non-negotiable.** No Animal/Dog/Cat textbook examples.

**Research tools available:**
- `/deep-research` — multi-source deep research with reasoning synthesis
- `/firecrawl` or `/firecrawl-scrape` — scrape real library source code or live docs
- `/exa-search` — neural search for finding specific implementations in the wild
- `/search-first` — research-before-coding: find what already exists before building
- **Serena MCP** (`mcp__serena__*`) — scan reference source code for real patterns, class hierarchies, and usage examples when the reference is a codebase

**Research questions to answer for every item:**
1. Where does this appear in popular open-source projects? (React, Vue, Express, NestJS, TypeORM, Axios, etc.)
2. What real engineering problem does it solve that developers hit weekly?
3. What breaks when this concept/pattern is NOT used? (failure mode analysis)
4. What are the language-specific idioms and gotchas?
5. What are common misconceptions or confusions with related concepts?

**Reasoning process:** Show the chain — why this example was chosen, what alternatives were considered, what makes it a good teaching example. The reasoning is part of the output.

**3-layer example depth (required):**
1. Where it appears in the wild (specific library/framework + version)
2. What problem it solves that developers encounter regularly
3. What goes wrong when it's missing or misapplied

#### Step 3: Craft Bilingual Design Question

Write ONE concrete question that:
- Describes a realistic business scenario a senior engineer would actually face
- Naturally leads to this concept/pattern without naming it
- Is specific enough to have concrete requirements (not "design a system")
- Works in both English and Traditional Chinese

Format:
```
EN: {question in English}
中文: {same question in Traditional Chinese}
```

#### Step 4: Build RADIO README

Create `{ITEM_FOLDER_ROOT}/{tier}/{name}/README.md` with this exact structure:

```markdown
# {Item Name}

## Design Scenario (設計情境)

> **EN**: {Concrete design question from Step 3}
> **中文**: {Same question in Traditional Chinese}

---

## [R] Requirements Exploration

### Core Problem
{What is varying? What should stay stable? What breaks without this concept/pattern?}

### When to Use
- {Condition 1}
- {Condition 2}

### When NOT to Use
- {Anti-condition 1: when the simpler approach is fine}
- {Anti-condition 2}

---

## [A] Architecture

### Classification
- **Category / Type**: {e.g., Behavioral / Structural / Creational / Principle}
- **Scope**: {Class / Object / Method / Interface}
- **Core principle**: {One-liner: what OO/design principle this embodies}

### Structure
{ASCII diagram}

### Participants
| Role | Description |
|------|-------------|
| ... | ... |

### Collaborations
{How participants interact at runtime}

---

## [D] Data Model

### Core Interfaces (TypeScript)
\`\`\`typescript
// Key interfaces/types defining the contract
\`\`\`

### Type Relationships
{implements / extends / composes — describe the relationship graph}

---

## [I] Interface Definition

### Public API
\`\`\`typescript
// What client code looks like
\`\`\`

### Extension Points
{How to add a new concrete implementation}

---

## [O] Optimizations & Deep Dive

### Consequences (Trade-offs)
{From source material or reasoned analysis}

### TypeScript-Specific Considerations
- {Generics usage}
- {Functional variant idioms}

### Real-World Usage in the Wild
- **{Framework/Library}**: {How it uses this — specific version/file if known}
- **{Framework/Library}**: {How it uses this}

### Related Items
| Item | Relationship | Notes |
|------|-------------|-------|
| ... | ... | ... |

### Key Design Insights
1. {Most important insight}
2. {Second insight}
3. {Common mistake to avoid}
```

#### Step 5: Implement Code

**`src/{name}.ts`:**
- OOP variant first (canonical structure with interfaces and classes)
- Functional variant second (closures, HOFs, TypeScript-specific idioms)
- Real domain names from the design question (no ConcreteClassA, Animal/Dog/Cat)
- Inline comments explaining each participant's role
- Runnable `demo()` or `main()` section at the bottom
- Strict TypeScript: no `any`, generics where they add genuine value

**`src/{name}.test.ts`:**
- Tests with `vitest` (`import { describe, it, expect } from 'vitest'`)
- Core behavior tests
- Extensibility test: add a NEW concrete implementation and verify it works
- Edge cases

**`examples/{scenario-name}/` — Full FE Folder Structure (required):**

```
examples/
  {scenario-name}/
    types/
      index.ts              # All interfaces, types, enums — zero implementation
    {role-plural}/          # Named after pattern participants:
      {concrete-1}.ts       #   strategies/ handlers/ states/ decorators/ etc.
      {concrete-2}.ts       # One class per file
      {concrete-3}.ts
      index.ts              # Re-exports all concretes
    services/
      {context-service}.ts  # Context / orchestration / facade layer
      index.ts
    utils/
      index.ts              # Pure helpers — no pattern classes
    index.ts                # Entry point: opens with problem comment, main(), runs it
```

**`index.ts` entry point requirements:**
- Opens with: `// Problem: {what breaks without this pattern/concept}`
- `async function main()` demonstrating: the design scenario, 2-3 concretes in action, runtime swap/extension (if applicable)
- Output that tells a story (not just "works!")
- Ends with `main().catch(console.error)`
- Runnable: `npx tsx {ITEM_FOLDER_ROOT}/{tier}/{name}/examples/{scenario}/index.ts`

---

### Phase 3 — Checkpoint: Done + Git Commit + Doc Update

After all files are created and tests pass:

**1. Verify:**
```zsh
npx vitest run {ITEM_FOLDER_ROOT}/{tier}/{name}/
npx tsx {ITEM_FOLDER_ROOT}/{tier}/{name}/examples/{scenario}/index.ts
```
Fix any failures before proceeding.

**2. Record done checkpoint:**
```zsh
TIMESTAMP=$(date +%Y-%m-%d-%H:%M)
SHA=$(git rev-parse --short HEAD)
echo "${TIMESTAMP} | {ITEM_NAME}-done | ${SHA}" >> .claude/checkpoints.log
```

**3. Git commit (one commit per completed item):**
```zsh
git add {ITEM_FOLDER_ROOT}/{tier}/{name}/
git commit -m "feat({item-name}): add Tier {N} {tier-label} -- {scenario description}, {N} tests"
```

Commit message convention: `feat({item}): add Tier {N} {tier-label} -- {scenario}, {N} tests`
Example: `feat(strategy): add Tier 1 Foundation -- payment gateway (3 providers), 12 tests`

**4. Run `/everything-claude-code:update-docs`** (ECC plugin command) to update related documentation:
- Mark item as "Done ✓" in `{TOPIC_CATALOG}` (SUMMARY_MAP) status column
- Update any cross-references in README or related items tables
- Alternatively, use the `doc-updater` agent from ECC

**5. Report to user:**
```
CHECKPOINT: {ITEM_NAME}-done
========================
SHA:       {sha}
Time:      {timestamp}
State:     complete ({X} files created, {N} tests passed)

Files:
  {list of files created}

Run: npx tsx {ITEM_FOLDER_ROOT}/{tier}/{name}/examples/{scenario}/index.ts
```

---

## 4. Checkpoint & Git Workflow Reference

### Checkpoint Log

**File:** `.claude/checkpoints.log` (append-only, never edit past entries)

**Format:** `{YYYY-MM-DD-HH:MM} | {label} | {git-short-sha}`

**Labels:**
- `project-init` — project first created
- `{item-name}-start` — beginning work on an item
- `{item-name}-done` — item fully complete and tested

**Using the log for session resumption:**
```zsh
cat .claude/checkpoints.log
```
Find unpaired starts (start with no matching done) = work in progress.

### Git Conventions

- **One commit per item** (not batched)
- **Conventional commit format**: `feat({item}): add Tier {N} {tier-label} -- {scenario}, {N} tests`
- **Types used**: `feat` (new item), `fix` (correction), `chore` (scaffold/config), `docs` (doc-only)
- **Commits happen after tests pass** — never commit broken code

---

## 5. Universal Folder Structure

```
{project-root}/
  CLAUDE.md                          # Project instructions for Claude
  SUMMARY_MAP.md                     # Topic catalog with status column
  reference/                         # Source material (PDFs, MDs, etc.)
  {ITEM_FOLDER_ROOT}/
    {tier-01}/
      {item-name}/
        README.md                    # RADIO walkthrough (bilingual)
        src/
          {item-name}.ts             # OOP + functional implementation
          {item-name}.test.ts        # Vitest tests
        examples/
          {scenario-name}/           # FE folder structure (not a flat file)
            types/index.ts
            {role-plural}/           # pattern participants
            services/index.ts
            utils/index.ts
            index.ts                 # Entry point with main()
    {tier-02}/
      ...
  .claude/
    checkpoints.log                  # Append-only progress log
    settings.json                    # Tool permissions for agents
    skills/
      {domain}-rag.md                # RAG skill with source page/file map
      implement-{domain}-item.md     # Implementation skill (5 steps)
    agents/
      {domain}-builder.md            # Orchestrating agent (4 phases)
```

---

## 6. Domain-Specific Extraction Field Templates

### Design Patterns (from GoF PDF)
1. **Structure** — ASCII class diagram + participant descriptions (from "Structure" and "Participants" sections)
2. **Design Question (Bilingual)** — concrete EN + 中文 question from "Motivation" section (must NOT name the pattern)
3. **Consequences** — numbered list verbatim from "Consequences" section
4. **Related Patterns** — list from "Related Patterns" section with relationship types (alternative to / often used with / similar structure, different intent / implements using / complement to)

### Data Structures
1. **Operations & Complexity** — table: operation / average time / worst time / space
2. **Visual Representation** — ASCII diagram of the data structure's memory/node layout
3. **Use Cases & When to Use** — real scenarios where this structure is the right choice
4. **Variants & Related Structures** — alternative forms, language-specific implementations

### Algorithms
1. **Pseudocode & Step-by-Step** — language-agnostic pseudocode + numbered steps
2. **Complexity Analysis** — time (best/avg/worst) + space, with reasoning
3. **Constraints & Preconditions** — when the algorithm is valid, input requirements
4. **Applications & Variations** — real-world uses, named variants (e.g., quicksort → introsort)

### System Design Patterns
1. **Problem Context** — the scalability/reliability/consistency problem this solves
2. **Architecture Diagram** — ASCII diagram of components and their relationships
3. **Trade-offs** — CAP theorem implications, latency vs. consistency, cost analysis
4. **Real-World Deployments** — specific systems that use this pattern (with source)

### API Design Patterns
1. **Problem & Motivation** — what the naive approach breaks at scale
2. **Interface Contract** — request/response shape, status codes, versioning approach
3. **Error Handling Strategy** — error taxonomy, recovery patterns, client guidance
4. **Evolution & Versioning** — how the API changes without breaking existing clients

---

## 7. Bootstrap Instructions

When creating a **new x-learn project**, generate these files:

### Step 1: Scaffold project structure
```zsh
mkdir -p {project-root}/.claude/{skills,agents}
mkdir -p {project-root}/reference
mkdir -p {project-root}/{ITEM_FOLDER_ROOT}
cd {project-root}
git init
```

### Step 2: Create these files (in order)

1. **`package.json`** — with `tsx`, `typescript`, `vitest`, `@types/node` as devDependencies
2. **`tsconfig.json`** — `strict: true`, `target: ES2022`, `module: NodeNext`, `includes: ["{ITEM_FOLDER_ROOT}/**/*.ts"]`
3. **`SUMMARY_MAP.md`** — Topic catalog with classification table, relationship diagram, learning order, and status tracker (all items start as "Not started")
4. **`.claude/settings.json`** — Tool permissions for agents:
   ```json
   {
     "permissions": {
       "allow": [
         "Bash(npx vitest run*)",
         "Bash(npx tsx*)",
         "Bash(git rev-parse*)",
         "Bash(git add*)",
         "Bash(git commit*)",
         "Bash(date*)",
         "Bash(echo*)"
       ]
     }
   }
   ```
5. **`.claude/checkpoints.log`** — Initialize with project-init entry:
   ```
   {TIMESTAMP} | project-init | {SHA}
   ```
6. **`.claude/skills/{domain}-rag.md`** — RAG skill with:
   - Source type and how to read it
   - Page/file map table for all items in the domain
   - Extraction field definitions (from §6)
   - Bilingual style guide examples
7. **`.claude/skills/implement-{domain}-item.md`** — Implementation skill with:
   - The 5-step process (re-read, deep research, design question, RADIO README, code)
   - Domain-specific folder naming conventions (role-plural folder names)
   - Quality bar and requirements
8. **`.claude/agents/{domain}-builder.md`** — Orchestrating agent with:
   - Phase 0: checkpoint start
   - Phase 1: RAG (delegates to RAG skill)
   - Phase 2: implementation (delegates to implementation skill)
   - Phase 3: checkpoint done + git commit + /everything-claude-code:update-docs
9. **`CLAUDE.md`** — Project instructions summary (structure, commands, agent to use, key reference files)
10. **`reference/`** — Add source material (PDFs, MDs, etc.)

### Step 3: Initial git commit
```zsh
git add .
git commit -m "chore: init {DOMAIN} project scaffold"
```

---

## 8. Dependency Resolution

The SOP references skills, MCP servers, and tools that may not all be available in every project context. This section maps each dependency and how to resolve it.

### Dependency Matrix

| Dependency | Type | Scope | How It's Resolved |
|-----------|------|-------|-------------------|
| `/deep-research` | ECC plugin skill | Global | Available everywhere if `everything-claude-code` plugin is installed |
| `/firecrawl` / `/firecrawl-scrape` | ECC plugin skill | Global | Available everywhere via ECC plugin |
| `/exa-search` | ECC plugin skill | Global | Available everywhere via ECC plugin. **Requires Exa MCP server** (see below) |
| `/search-first` | ECC plugin skill | Global | Available everywhere via ECC plugin |
| `/everything-claude-code:update-docs` | ECC plugin command | Global | Available everywhere via ECC plugin |
| `doc-updater` agent | ECC plugin agent | Global | Available everywhere via ECC plugin |
| **Serena MCP** | MCP server | Per-project | Must be in `.mcp.json` (project or parent directory) |
| **Firecrawl MCP** | MCP server | Per-project | Must be in `.mcp.json` with `FIRECRAWL_API_KEY` |
| **Exa MCP** | MCP server | User-level | Must be in `~/.claude.json` with `EXA_API_KEY` |
| **Context7 MCP** | MCP server | User-level | Already in `~/.claude.json` (no key needed) |
| `WebFetch` / `WebSearch` | Built-in tool | Global | Always available |
| `Read` (PDF pages) | Built-in tool | Global | Always available |

### .mcp.json Inheritance (Key Insight)

`.mcp.json` **searches upward through all parent directories** and merges all configs. This means:

```
/Users/jason/Developer/x-learn/programming/
  .mcp.json                    ← Shared by ALL x-learn projects
  design-patterns/
    .mcp.json                  ← Merges with parent (overrides on conflict)
  oop/
    .mcp.json                  ← Merges with parent
  {new-project}/               ← Inherits parent .mcp.json automatically!
```

**This is independent of git** — even if a subdirectory has its own `.git`, it still inherits parent `.mcp.json`.

### Recommended Setup: Parent-Level `.mcp.json`

Create a **shared `.mcp.json` at the `programming/` root** so all x-learn projects inherit common MCP servers:

```json
// /Users/jason/Developer/x-learn/programming/.mcp.json
{
  "mcpServers": {
    "serena": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"]
    },
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": { "FIRECRAWL_API_KEY": "${FIRECRAWL_API_KEY}" }
    }
  }
}
```

Then add **Exa MCP to user-level config** (`~/.claude.json`) since it's useful across all projects:

```json
// Add to ~/.claude.json mcpServers section:
"exa-web-search": {
  "command": "npx",
  "args": ["-y", "exa-mcp-server"],
  "env": { "EXA_API_KEY": "${EXA_API_KEY}" }
}
```

### API Key Management

Move API keys from hardcoded `.mcp.json` values to **environment variables**:

| Key | Set In | How |
|-----|--------|-----|
| `FIRECRAWL_API_KEY` | `~/.zshrc` | `export FIRECRAWL_API_KEY="fc-..."` |
| `EXA_API_KEY` | `~/.zshrc` | `export EXA_API_KEY="..."` |

`.mcp.json` supports `${VAR}` syntax to reference env vars — no hardcoded secrets in config files.

### Plugin Prerequisite

The following ECC plugin must be installed for skill dependencies to resolve:

```
everything-claude-code (v1.9.0+)
```

This provides: `/deep-research`, `/firecrawl`, `/firecrawl-scrape`, `/exa-search`, `/search-first`, `/everything-claude-code:update-docs`, `doc-updater` agent, `code-reviewer` agent, and more.

### Bootstrap Checklist (updated)

When bootstrapping a new x-learn project, verify these dependencies:

- [ ] `everything-claude-code` plugin is installed (`~/.claude/plugins/`)
- [ ] Parent `.mcp.json` exists at `programming/` root (or create per-project)
- [ ] `FIRECRAWL_API_KEY` env var is set
- [ ] `EXA_API_KEY` env var is set (if using `/exa-search`)
- [ ] Exa MCP is in `~/.claude.json` (if using `/exa-search`)
- [ ] Context7 MCP is in `~/.claude.json` (already done)

---

## 9. Lessons Learned from Reference Projects

| Lesson | Source | Applied In |
|--------|--------|-----------|
| Always read source on re-entry — never trust memory | design-patterns/ | Phase 1, Phase 2 Step 1 |
| Checkpoint log enables session resumption | oop/ | Phase 0, Phase 3 |
| SUMMARY_MAP status must be updated on completion | oop/ (wasn't updated) | Phase 3 Step 4 |
| FE folder structure (not flat files) is non-negotiable | design-patterns/ | Step 5 examples/ |
| One commit per item (not batched) | oop/ | Phase 3 Step 3 |
| Real-world examples over textbook examples | both | Phase 2 Step 2 |
| /everything-claude-code:update-docs after every completion | design-patterns/ (missing) | Phase 3 Step 4 |
| Serena MCP for scanning repo-based references | oop/ (MCP config) | Phase 1 source reading |
