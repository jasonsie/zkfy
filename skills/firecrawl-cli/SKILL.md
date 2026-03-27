---
name: firecrawl-cli
description: Firecrawl CLI reference — scrape, crawl, map, search, and AI agent commands for extracting web content as-is
---

# Firecrawl CLI

Firecrawl converts web pages into clean markdown or structured data. Use `npx firecrawl` or `firecrawl` if installed globally.

## Setup

```bash
# Set API key (add to ~/.zshrc for persistence)
export FIRECRAWL_API_KEY="fc-your-api-key"

# Or configure via CLI
firecrawl config
firecrawl config --api-url https://firecrawl.mycompany.com --api-key fc-xxx

# View current config
firecrawl view-config

# Override per-command
firecrawl scrape https://example.com --api-key fc-your-key

# Self-hosted
firecrawl --api-url https://firecrawl.mycompany.com scrape https://example.com
```

---

## Commands

### `scrape` — Single Page

```bash
# Default: outputs markdown
firecrawl scrape https://example.com

# Raw HTML
firecrawl scrape https://example.com --html

# Multiple formats (returns JSON)
firecrawl scrape https://example.com --format markdown,links,images

# Main content only (removes nav, footer, ads)
firecrawl scrape https://example.com --only-main-content

# Wait for JavaScript rendering (ms)
firecrawl scrape https://spa-app.com --wait-for 3000

# Screenshot
firecrawl scrape https://example.com --format markdown --screenshot

# Filter HTML elements
firecrawl scrape https://example.com --include-tags article,main
firecrawl scrape https://example.com --exclude-tags nav,aside,.ad

# Save to file
firecrawl scrape https://example.com -o output.md
firecrawl scrape https://example.com --format json -o data.json --pretty

# Show timing
firecrawl scrape https://example.com --timing
```

---

### `crawl` — Multi-Page

```bash
# Start crawl (returns job ID immediately)
firecrawl crawl https://example.com

# Wait for completion
firecrawl crawl https://example.com --wait

# Show progress while waiting
firecrawl crawl https://example.com --wait --progress

# Check job status by ID
firecrawl crawl <job-id> --status

# Limit pages and depth
firecrawl crawl https://example.com --limit 100 --max-depth 3

# Filter paths
firecrawl crawl https://example.com --include-paths /blog,/posts
firecrawl crawl https://example.com --exclude-paths /admin,/login

# Rate limiting
firecrawl crawl https://example.com --delay 1000 --max-concurrency 2

# Subdomains and external links
firecrawl crawl https://example.com --allow-subdomains
firecrawl crawl https://example.com --allow-external-links
firecrawl crawl https://example.com --crawl-entire-domain

# Sitemap handling
firecrawl crawl https://example.com --sitemap include   # default
firecrawl crawl https://example.com --sitemap skip
firecrawl crawl https://example.com --sitemap only

# Save results
firecrawl crawl https://example.com --wait -o results.json --pretty

# Timeout and poll interval
firecrawl crawl https://example.com --wait --timeout 300 --poll-interval 10
```

---

### `map` — URL Discovery

Discovers URLs without scraping content.

```bash
# List all URLs (one per line)
firecrawl map https://example.com

# Output as JSON
firecrawl map https://example.com --json

# Limit results
firecrawl map https://example.com --limit 500

# Search for specific URLs
firecrawl map https://example.com --search "blog"

# Sitemap only
firecrawl map https://example.com --sitemap only

# Include subdomains
firecrawl map https://example.com --include-subdomains --limit 1000

# Deduplicate query params
firecrawl map https://example.com --ignore-query-parameters

# Save to file
firecrawl map https://example.com -o urls.txt

# Timeout for large sites
firecrawl map https://large-site.com --timeout 120
```

---

### `search` — Web/Image/News Search

```bash
# Basic search
firecrawl search "your query"

# Limit results (default 5, max 100)
firecrawl search "query" --limit 10

# Sources: web, images, news
firecrawl search "query" --sources news
firecrawl search "query" --sources web,images

# Categories: github, research, pdf
firecrawl search "query" --categories github
firecrawl search "query" --categories research,pdf

# Time filter
# qdr:h = past hour, qdr:d = day, qdr:w = week, qdr:m = month, qdr:y = year
firecrawl search "query" --tbs qdr:w

# Location targeting
firecrawl search "query" --location "Berlin,Germany"

# Scrape search results content
firecrawl search "query" --scrape --scrape-formats markdown

# Save results
firecrawl search "query" --pretty -o results.json
```

---

### `download` — Download Entire Site

Maps a site first, then scrapes all pages into `.firecrawl/` as nested directories.

```bash
# Download site to .firecrawl/
firecrawl download https://example.com

# Limit pages
firecrawl download https://example.com --limit 50
```

---

### `agent` — AI-Powered Extraction

Autonomous browsing agent that follows links and extracts structured data.

```bash
# Natural language prompt
firecrawl agent "Find the pricing plans for Firecrawl"

# Wait for completion
firecrawl agent "Extract all product names and prices" --wait

# Target specific URLs
firecrawl agent "Get the main features" --urls https://example.com/features

# Structured output via JSON schema
firecrawl agent "Extract company info" \
  --schema '{"type":"object","properties":{"name":{"type":"string"},"employees":{"type":"number"}}}'

# Schema from file
firecrawl agent "Extract product data" --schema-file ./schema.json --wait

# Check existing job status
firecrawl agent <job-id>
firecrawl agent <job-id> --wait

# Limits
firecrawl agent "Find top competitors and pricing" --wait --timeout 300
firecrawl agent "Get all blog post titles" --urls https://blog.example.com --max-credits 100 --wait
```

---

## Output Flags (all commands)

| Flag | Description |
|------|-------------|
| `-o <file>` | Save output to file |
| `--pretty` | Pretty-print JSON |
| `--json` | Force JSON output |
| `--format <types>` | Comma-separated: `markdown`, `html`, `links`, `images`, `screenshot` |
