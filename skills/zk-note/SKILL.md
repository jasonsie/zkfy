---
name: zk-note
description: Transform markdown files into fully integrated Zettelkasten literature notes with frontmatter, backlinks, and MOC updates. Use when you need to (1) Create atomic notes from existing markdown, (2) Add proper navigation and categorization, (3) Link notes into your knowledge graph, (4) Apply Feynman-style explanations with code examples.
---

# ZK-Note

Transform markdown into fully integrated Zettelkasten literature note.

## Input

$ARGUMENTS — <path-to-markdown-file> [domain]

Optional domain: cs/web/ai/principle/devops/math

## Workflow

This workflow follows these steps:

1. Read formatting rules
2. Read source & determine domain
3. Analyze content & structure note
4. Create frontmatter with navigation
5. Add content elements
6. Create backlinks
7. Update MOCs
8. Cleanup

## Execution

### Step 1: Read Formatting Rules

Read the Zettelkasten rules from:
`/Users/jason/Desktop/claude/prompts/obsidian-note.prompt.md`

Follow these rules throughout the integration process.

### Step 2: Read Source & Determine Domain

Read the markdown file from the provided path.

**Determine domain:**
- If provided in arguments → use it
- Otherwise → analyze content and suggest domain
- If unclear → ask user to specify

Domain folders: `cs/`, `web/`, `ai/`, `principle/`, `devops/`, `math/`

### Step 3: Analyze & Structure

Extract the core concept (one atomic idea per note).

Generate Train-Case filename:
- Pattern: `Domain-Concept-Name-In-Train-Case.md`
- Domain prefix: `cs/`→`CS-`, `web/`→`Web-`, etc.
- Example: `Web-React-Server-Components.md`

Plan note structure:
- **Abstract** (bullets OR diagram + 1-2 sentences)
- **Content sections** (one aspect per section)
- **Links** (backlinks with explanations)

### Step 4: Create Frontmatter

Required YAML frontmatter:
```yaml
---
Date: YYYY-MM-DD
Type: literature
Categories: []
Sub-Categories: []
Aliases: []
Before: '[[Domain-Previous-Note]]'
Next: '[[Domain-Next-Note]]'
Link: '<source-url>'
Src: '[[zz.original-source/src-file]]'
---
```

**Calculate Before/Next:**
- List notes in domain folder
- Sort alphabetically
- Find insertion point
- Set Before to previous note, Next to following note

### Step 5: Add Content Elements

**Abstract section:**
- Brief text (2-3 Feynman sentences) OR
- ASCII diagram + 1-2 sentences

**Content sections:**
- One aspect per section
- Rewrite in your own words (Feynman Technique)
- For programming topics: include code examples

**Code examples pattern:**
```markdown
❌ Bad: <problematic code>
✅ Good: <better code>
```

Use TypeScript when applicable.

**Diagrams:** For visual aids, delegate to diagram-generator agent.

### Step 6: Create Backlinks

Scan vault for related notes using Grep tool.

Add backlinks in Links section:
```markdown
### Links

- Related to [[Note-Name]] because <explanation>
- Contrasts with [[Other-Note]] because <explanation>
- Leads to [[Advanced-Topic]] because <explanation>
```

Patterns: Related to, Contrasts with, Leads to, Part of, Example of

### Step 7: Update Navigation

Update neighbor files' frontmatter:

**If Before note exists:**
- Update its `Next: '[[new-note]]'` field

**If Next note exists:**
- Update its `Before: '[[new-note]]'` field

### Step 8: Update MOCs

Find relevant MOC in `000.Index/`:
- Search for MOC matching note's domain/topic
- If found: Add wiki-link to new note in appropriate section
- If not found: Ask user to create new MOC or skip
- Maintain alphabetical or logical ordering

### Step 9: Cleanup

Delete source file from `zz.original-source/`.

Report completion:
```
✅ Zettelkasten note created
📄 Location: <domain>/<filename>.md
🔗 Links: <backlinks added>
📑 MOC updates: <MOCs modified>
🔄 Navigation: Before→<note>→Next
```

## Output

- Note path: `<domain>/<Domain-Concept-In-Train-Case>.md`
- Backlinks: List of related notes linked
- MOC updates: List of MOCs modified
- Navigation: Before/Next files updated

## Error Handling

**File not found:**
- Report the path that was tried
- Ask user to verify path

**Domain unclear:**
- Present content summary
- Ask user to specify domain from: cs/web/ai/principle/devops/math

**No related notes found:**
- Create note anyway
- Warn user that no backlinks were added
- Suggest manual linking

**MOC missing:**
- Ask user: "Create new MOC or skip MOC update?"
- Proceed based on user choice
