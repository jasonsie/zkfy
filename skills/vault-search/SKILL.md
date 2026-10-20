---
name: vault-search
description: Find relevant eligible Obsidian notes with read-only, bilingual metadata and full-text retrieval. Works across projects through an explicit vault binding. Returns bounded ranked paths, headings, line excerpts, and freshness rather than reading a monolithic index. Does not write notes or refresh indexes.
---

# Vault Search

Input: `<query> [--limit N] [--vault PATH]`. Default limit: 6 (maximum 20).

For the configured canonical vault, use:

```bash
~/.local/bin/vault-knowledge search "query" --limit 6
```

For an explicitly selected different vault, resolve this skill's directory and call the shared source-relative CLI:

```bash
python3 -B <zkfy-root>/scripts/knowledge.py --vault "<explicit vault>" search "query" --limit 6
```

`<zkfy-root>` is two levels above this SKILL.md. Do not assume the calling cwd is the vault or hardcode a plugin-cache version. Requires Python 3.10+ and `scripts/requirements-knowledge.txt`.

The vault must have `docs/knowledge/scope.json`. If absent, report that scoped retrieval is not configured; never fall back to whole-vault grep, old indexes, or excluded-source reads.

## Procedure

1. Extract task concepts and useful English/Traditional Chinese variants. Search focused terms; split multi-part tasks into a few bounded searches.
2. Report ranked paths, headings, excerpts, and freshness from the JSON output. An excerpt is a candidate, not a complete answer.
3. Use the same CLI's `read <returned-path> --heading <heading>` before making claims; use `--start N --limit 80` for long sections.
4. Deduplicate by full path, not basename. Do not privilege permanent notes as automatically correct.
5. With no evidence, report terms attempted and gaps. Do not automatically research externally or save notes.

The CLI searches current eligible files even if catalogs are stale. Index maintenance, logging, note creation, and source ingestion are separate operations. `raw/` and all policy-excluded targets remain entirely outside search, link expansion, and fallback.

For synthesized, cited answers and proactive use, follow the shared `query` skill.
