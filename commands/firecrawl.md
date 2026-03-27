---
description: Run Firecrawl CLI commands — scrape, crawl, map, search, or agent
---

# /firecrawl

Runs a Firecrawl CLI command based on the provided argument.

## Usage

```
/firecrawl <command> [args]
/firecrawl scrape https://example.com
/firecrawl crawl https://example.com --wait --limit 50
/firecrawl map https://example.com
/firecrawl search "your query"
/firecrawl agent "Extract pricing info from this page" --urls https://example.com/pricing
```

## Behavior

Parse $ARGUMENTS to determine the command:

1. **If $ARGUMENTS starts with a URL** → run `firecrawl scrape <url>`
2. **If $ARGUMENTS starts with `scrape`** → run `firecrawl scrape` with remaining args
3. **If $ARGUMENTS starts with `crawl`** → run `firecrawl crawl` with remaining args
4. **If $ARGUMENTS starts with `map`** → run `firecrawl map` with remaining args
5. **If $ARGUMENTS starts with `search`** → run `firecrawl search` with remaining args
6. **If $ARGUMENTS starts with `agent`** → run `firecrawl agent` with remaining args
7. **If $ARGUMENTS is empty** → ask the user which command to run

## Execution

Run the constructed command using Bash. Use `npx firecrawl` if `firecrawl` is not installed globally.

After running:
- Present the output as-is (markdown, JSON, or URL list)
- If the output is JSON, format it clearly
- If the crawl returns a job ID (async), show the ID and suggest `firecrawl crawl <job-id> --status` to check progress

## Error Handling

- If the command fails with an auth error, remind the user to set `FIRECRAWL_API_KEY`
- If the URL is unreachable, show the error from Firecrawl without modification
- Do not retry automatically — show the error and let the user decide

## Reference

For full options, see the `firecrawl-cli` skill.
