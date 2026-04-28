---
name: web-clipper
description: Clip a web page into a clean Markdown file under raw/, with images downloaded locally to raw/attachments/. Self-contained — depends only on the defuddle npm package installed inside this skill folder. Use when given a URL and asked to capture it for the vault without firecrawl or API keys.
---

# Web Clipper

Fetch a URL → `raw/<slug>.md` with all images materialized to `raw/attachments/<slug>/`.

## Input

`$ARGUMENTS — <url> [--no-attachments] [--out <path>]`

- `<url>` (required) — the page to clip
- `--no-attachments` — skip image download; keep remote URLs as-is
- `--out <path>` — override default output path (`raw/<slug>.md`)

## Setup (one-time)

```bash
cd skills/web-clipper && npm install
```

This installs `defuddle` (+ its optional deps `linkedom` and `turndown`) locally
into `skills/web-clipper/node_modules/`. No API key or external service required.

Runtime requirements: `node`, `curl`, `jq`.

## Execution

Run the wrapper script from the **vault root**:

```bash
bash skills/web-clipper/scripts/clip.sh <url>
bash skills/web-clipper/scripts/clip.sh <url> --no-attachments
bash skills/web-clipper/scripts/clip.sh <url> --out raw/my-note.md
```

### Pipeline

```
URL
 │
 ▼
[1] defuddle CLI  (skills/web-clipper/node_modules/.bin/defuddle)
    defuddle <url> --markdown --json
    → JSON: title, author, published, domain, contentMarkdown
 │
 ▼
[2] Compose Markdown file
    • YAML frontmatter  (Date, Type, Link, Categories, tags, Before, Next, …)
    • # <title> heading
    • contentMarkdown body
    → raw/<slug>.md
 │
 ▼
[3] Attachment materialization  (skipped with --no-attachments)
    • grep remote image URLs from output
    • curl → raw/attachments/<slug>/<md5>.<ext>
    • rewrite Markdown links to local relative paths
```

### Frontmatter produced

```yaml
---
Date: <today>
Type: literature
Link: '<url>'
Categories: []
Sub-Categories: []
Aliases: ['<page title>']
tags: []
Before: ''
Next: ''
Author: '<author>'       # omitted if empty
Published: '<date>'      # omitted if empty
Source: '<domain>'       # omitted if empty
---
```

Compatible with `/zk-note` and `/source-to-zk` downstream.

## Output layout

```
raw/
  <slug>.md
  attachments/
    <slug>/
      <md5>.png
      <md5>.jpg
      …
```

## Continue the pipeline

```bash
/zk-note raw/<slug>.md
# or
/source-to-zk raw/<slug>.md
```

## Verification

```bash
# Sanity: defuddle installed
skills/web-clipper/node_modules/.bin/defuddle --help

# Clip with attachments
bash skills/web-clipper/scripts/clip.sh https://react.dev/learn

# Clip without attachments
bash skills/web-clipper/scripts/clip.sh https://react.dev/learn --no-attachments

# Pipe into the ZK pipeline
/source-to-zk raw/react-dev-learn.md
```
