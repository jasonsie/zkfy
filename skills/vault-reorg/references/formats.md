# Formats of a pass

All paths are vault-relative unless absolute. The pass folder is `docs/plans/reorg/<YYYY-MM-DD>-<slug>/`.

## mapping.json

```json
{
  "version": 1,
  "scope": "111.cs/language/javascript",
  "merges": [
    {
      "survivor": "111.cs/language/javascript/Cs-Javascript-This-Binding.md",
      "absorbed": ["111.cs/language/javascript/Cs-Javascript-This.md"],
      "draft": "docs/plans/reorg/2026-11-04-this/draft.md",
      "ledger": "docs/plans/reorg/2026-11-04-this/ledger.json",
      "anchors": {"111.cs/language/javascript/Cs-Javascript-This.md": {"Quick Decision Flowchart": "Deciding the Receiver"}},
      "rename": null
    }
  ],
  "moves": [
    {"from": "111.cs/database/postgres/sql/Database-Postgres-Querying.md", "to": "111.cs/database/Database-Postgres-Querying.md"}
  ]
}
```

- `survivor` keeps its filename unless `rename` names a new eligible path.
- `anchors` maps, per absorbed note, an old section heading to the heading in the woven note. A link
  `[[Absorbed#Old]]` becomes `[[Survivor#New]]`. Headings that exist unchanged in the draft need no entry;
  an anchor with no match is dropped with a warning in the plan.
- `moves` never target an existing path or create two notes with one basename.
- A mapping with no `merges` and no `moves` is rejected.

## ledger.json

```json
{
  "version": 1,
  "rows": [
    {"note": "111.cs/language/javascript/Cs-Javascript-This.md", "unit": "u-3f9c1a2b7d4e", "status": "kept"},
    {"note": "111.cs/language/javascript/Cs-Javascript-This.md", "unit": "u-8a1d4c0e9b22", "status": "reworded", "heading": "Abstract"},
    {"note": "111.cs/language/javascript/Cs-Javascript-This-Binding.md", "unit": "u-0b7e2f5a6c11", "status": "duplicate", "of": "u-3f9c1a2b7d4e"},
    {"note": "111.cs/language/javascript/Cs-Javascript-This-Binding.md", "unit": "u-5d2c9e1f0a33", "status": "dropped", "reason": "Content wrapper line, no content"}
  ]
}
```

One row per unit of every clustered note, the survivor included (its old text is replaced by the
draft). Unit ids come from `reorg units <path>`:

```json
{"path": "…/Cs-Javascript-This.md", "units": [
  {"id": "u-3f9c1a2b7d4e", "kind": "paragraph", "heading": "Five Binding Rules", "line": 13, "text": "The value of `this` depends on how a function is called."}
]}
```

Kinds: `paragraph`, `list`, `table`, `code`, `links` (anything under `### Links`). A `kept` row of kind
`links` passes when every wikilink target of the unit appears in the draft; other kinds must appear
verbatim (whitespace folded).

## draft.md

```markdown
---
Date: 2026-11-04
Type: literature
Categories: [CS, JavaScript]
Aliases: [this binding, this keyword, Cs-Javascript-This]
Src: '[[raw/cs/this-binding]]'
---
### Abstract
One or two sentences for the whole concept.
### Content
#### First approved section
…
#### Second approved section
…
### Links
- [[Cs-Javascript-Scope]] - why this link matters
```

Legacy profile: no `Mode`. Lint requires `Date`, `Type`, `Categories`, `### Abstract`, `### Links`.
Apply adds any absorbed stem or alias missing from `Aliases`.

## record.md

```markdown
# Pass <date> <slug>

Scope: <cluster or directory>. Jobs: <Consolidate | Restructure | Curate | Survey>.

## Verdicts
| Cluster | Verdict | Evidence |
|---|---|---|

## Mapping
| Op | From | To |
|---|---|---|

## Ledger review (approved)
| Note | Unit | Status | Where / of / reason |
|---|---|---|---|

## Links rewritten
<count>, from the plan report.

## Coverage (Curate)
| Subtopic | Status | Notes |
|---|---|---|

## Ingest backlog (Curate)
- <subtopic>: <why it matters>. Sources: <one or two>.

## Result
Commit <hash>, or "staged, not committed". Lint: 0 new issues. Catalog: current.
```

## CLI results and exit codes

`reorg survey [--target DIR]` → `{"signals": {...}, "clusters": [{"notes", "reasons", "inbound", "lines"}], "thresholds"}`; exit 0.
Thresholds (`tiny_folder_max` 2, `max_depth` 3, `oversized_lines` 1200) can be overridden under a
`reorg` key in `docs/knowledge/scope.json`.

`reorg plan MAPPING [--markdown]` → `errors`, `warnings`, `applied`, `operations`, `link_rewrites`
(`file`, `line`, `action` rewrite|drop, `old`, `new`), `aliases_to_add`, `touched`, `dirty`, `ledger`
(`ok`, per merge counts), `draft_issues`, `markdown`. Exit 1 when errors, draft issues, a failing
ledger or dirty files block apply; exit 0 when ready or already applied.

`reorg ledger MAPPING` → `ok` and, per merge, `missing`, `unknown`, `mismatch`, `dangling`, `invalid`,
`review`, `counts`. Exit 1 when not ok.

`reorg apply MAPPING [--allow-dirty]` → the plan fields plus `changed`, `written`, `deleted`, `moved`,
`staged`, `notes`, `commit_message`. Exit 2 with the reason on stderr when refused; a second run on an
applied mapping returns `changed: false`.
