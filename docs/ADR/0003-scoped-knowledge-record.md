# ADR-0003 — Scoped knowledge record and deterministic catalogs

Status: Implemented locally; no release/commit implied.

## Decision

Use one portable Python core in `scripts/knowledge.py` for explicit-vault scoped discovery, read-only search/read, deterministic generation, structural lint, and staged-snapshot validation. PyYAML 6.x is an explicit dependency rather than a second incomplete YAML parser. A per-vault `docs/knowledge/scope.json` controls eligible roots, optional maps/root notes, shard size, schema compatibility, and bilingual synonyms.

Queries never write caches/logs/notes, refresh catalogs, or perform network retrieval. The read-only `query` skill is separate from the write-producing `query-to-note`. Both Pi and Claude can use ordinary shell/file tools, with a machine-local binding supplied by the source-managed adapter in ai-cli-workspace. No Claude-only delegation API is required.

## Navigation and scope

Retain `.claude/index.md` as the canonical generated route map and add bounded shards plus a fingerprint manifest beneath `.claude/index/`. The historical location is not client ownership. MOCs remain optional curated reading guides. At this scale, search scores current eligible source text locally and returns only bounded matches; it does not inject the full catalog into model context. It remains correct with missing/stale indexes.

Apply scope before reading. Excluded roots (especially `raw/`), hidden/system directories, traversal, and symlink paths cannot become evidence or backlog inventory. Link expansion, legacy compatibility, maintenance, and search use the same policy. Tool scope is not an OS sandbox; skill instructions prohibit using other filesystem tools to bypass it.

## Health and formats

Derive structural metrics, not epistemic trust. Legacy, atom, thesis, and structure notes coexist; this does not supersede the ingestion templates in ADR-0001/0002. Ingestion's body-budget/semantic checks are not retroactively imposed on the full vault. Missing Mode on an existing note is a legacy profile, not permission to migrate it.

All committed generated outputs, including QUALITY, use content/config only. No wall clock or Git history. Optional historical diagnostics must be separate; no implicit unshallow/fetch. Identical source snapshots generate identical bytes.

## Git semantics

The interactive reader uses the live eligible working tree. The commit gate uses one allowlisted Git object batch of staged blobs, not working-tree files. It validates the complete link graph so unchanged incoming links can break a rename/delete commit.

Use a reviewed HEAD-derived structural-debt baseline. Normal commits may shrink but cannot expand it. First deploy report-only; after review, ratchet mode blocks only new violations. A successful ratchet transaction stages only generated files and baseline reductions, preserves authored staging/unstaged hunks, and refuses manual generated-file conflicts. Runtime unavailability can warn/fail open; invalid policy and actual errors cannot masquerade as a passing validation. Capture the Git index before validation and check it again before the transaction, not merely before writing, to reject concurrently restaged source. An unborn HEAD has no inherited debt. A generated manifest cannot claim ownership of or delete the separately managed baseline.

## Compatibility and bounded reads

The legacy scanner delegates to `inventory`, retaining its useful metadata/link shape without enumerating non-note or source artifacts. Inventory, audit, catalog generation, and retrieval share scope and parsing. Source plugin hooks use `knowledge-hook.py` to recognize policy-scoped vaults, avoid legacy output redirection, and emit maintenance reminders only for eligible edits. Updating the source does not silently publish or patch installed plugin caches.

`read` returns actual line numbers, selected Date/Type/Mode metadata, a bounded heading list, and continuation/clipping flags. The text budget is 16,000 bytes, 1,600 bytes per line, at most 200 lines. Do not treat hidden metadata or unread continuation as absent. Source dates and structural metrics never establish truth or precedence.

## Non-goals

No vectors, MCP service, note migration, MOC rewriting, source-backlog processing, cloud gardening, automatic commits/pushes, or plugin-cache edits. `vault-index --append` deliberately rebuilds deterministically rather than risking stale aliases/deletions with premature incremental updates.

## Verification

`python3 -B -m unittest discover -s tests -p 'test_knowledge.py' -v` exercises boundary reads, aliases, schemas, links, mutation-free queries, freshness, shard generation, full/shallow clone determinism, partial staging, inherited debt, broken inbound links, baseline expansion refusal, transaction rollback/index races, bounded continuation, compatibility inventory, unborn HEAD, and failure preservation. Live client trigger verification is a separate gate, not inferred from unit tests.
