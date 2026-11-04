# ADR-0005 — Reorganization as a reviewed weave

Status: accepted (2026-11-04)

Refines ADR-0003's "no note migration" non-goal: the weave below is authored, reviewed text, not migration.

## Decision

`/vault-reorg` reorganizes a vault in passes. A pass is one run of the skill over one scope, ending in one reviewed change set. The rule is one concept, one note: notes merge only when they explain the same concept (a cluster). Related but distinct notes get links to each other, and chapter series stay as they are. A merge is a weave: one outline the user approves, every unique unit of every clustered note placed under it once, repeated units kept in their best version only. A unit ledger gates the weave. Without it, a merge can silently lose content that exists nowhere else.

## Rules

- **Preservation check.** Each unit (paragraph, list, table, code block) of every clustered note gets one ledger row: kept, reworded, duplicate of, or dropped. A deterministic check confirms every unit has a row and every kept row matches the woven text. The user reviews the reworded, duplicate and dropped rows before any absorbed note is deleted.
- **Legacy profile.** A woven note uses `### Abstract`, `### Content` (the outline as `####` sections) and `### Links`, with no `Mode` field. This matches the existing vault. Thesis means a claim with supporting themes, and a weave is the complete treatment of one concept.
- **No pipeline inside a pass.** The session model writes the weave. The zk-note pipeline never rewrites a note during a pass, because its budgets drop content. Recasting a note as atom or thesis stays a separate, explicit `/zk-note` request.
- **Survivor name.** The survivor is the clustered note with the most inbound links and keeps its filename, unless the name misleads. Then the mapping gives a new name and every inbound link is rewritten. Absorbed note names become aliases.
- **Apply stages, the user commits.** `apply` writes the mapping, rebuilds the catalog, and stages exactly the files it touched. It refuses to start when a file it must touch has uncommitted edits. The skill ends with one dialog and commits only on yes. The user's unrelated changes stay unstaged.
- **No standing signal.** The survey runs only inside the skill. `build` and `.claude/QUALITY.md` carry no reorganization candidates.
- **Scope.** `raw/` is never listed, moved or edited. The vault is the current folder, marked by `docs/knowledge/scope.json`.

## Considered options

- **Append mode.** Rejected: it keeps the duplication inside one file.
- **Pipeline re-synthesis.** Rejected: the atom budget and thesis chapter targets drop content.
- **Stub notes for coverage gaps.** Rejected: stubs go stale and raise the note count. Gaps become an ingest backlog in the pass record instead.
- **Reorganization candidates in `QUALITY.md`.** Rejected: a standing signal nags, and the user sets the cadence.
- **Auto-commit.** Rejected: the vault's pre-commit hook validates the staged snapshot as a whole, and pending user work must not be committed.

## Consequences

- A merge takes more review than a line check would, because the user reads every reworded, duplicate and dropped row. That cost is the point.
- Woven notes stay in the legacy profile until the user asks for a recast.
