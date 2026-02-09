---
name: crawler
description: Convert any source (URL, text, or file) into clean, structured Markdown with zero data loss. Use when you need to extract content from web pages, preserve raw text with structure, or prepare content for later processing. Supports tables, code blocks, SVG, images, and automatic diagram generation.
---

# Crawler

Convert any source into clean, structured Markdown with zero data loss.

## Input

$ARGUMENTS — <URL | raw text | file path>

## Workflow

This workflow follows these steps:

1. Read formatting rules
2. Detect source type
3. Extract content
4. Convert to Markdown
5. Save output

## Execution

### Step 1: Read Formatting Rules

Read the content extraction rules from:
`/Users/jason/Desktop/claude/prompts/crawler.prompt.md`

Follow these rules throughout the extraction process.

### Step 2: Detect Source Type

Classify the input:
- **Web URL**: Starts with http:// or https://
- **File path**: File exists on disk
- **Raw text**: Everything else

### Step 3: Extract Content

**For Web URLs:**
- Fetch page content using WebFetch tool
- Extract main content area (strip nav/footer/ads)
- Preserve metadata (author, date, source URL)

**For File paths:**
- Read file using Read tool
- Detect format (markdown, text, etc.)
- Preserve existing structure

**For Raw text:**
- Accept as-is
- Infer structure from formatting

### Step 4: Convert to Markdown

Apply crawler.prompt.md rules:

- **Headings**: Preserve hierarchy (h1→#, h2→##, etc.)
- **Code blocks**: Triple backticks with language identifiers
- **Tables**: Convert to Markdown pipe tables
- **SVG**: Wrap in fenced code block
- **Images**: Keep URLs with alt text
- **Links**: Convert to inline format `[text](url)`
- **Diagrams**: For complex diagrams, delegate to diagram-generator agent

Ensure zero data loss—include all content from source.

### Step 5: Save Output

Generate filename:
- Extract title from content (first heading or URL)
- Convert to kebab-case
- Prefix with `src-`
- Max 60 characters
- Example: `src-react-server-components.md`

Save to: `zz.original-source/<filename>.md`

Report file location to user.

## Output

File path: `zz.original-source/src-<title>.md`

## Error Handling

**URL unreachable:**
- Report specific error (timeout, 404, etc.)
- Suggest checking URL or trying alternative source

**File not found:**
- Report path that was tried
- Ask user to verify path

**Empty content:**
- Warn user that no content was extracted
- Ask whether to save empty file
