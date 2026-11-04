# Vault reorganization skill — decision record

Status: decisions confirmed by the user 2026-11-04 ("confirm !"); implemented the same day, uncommitted in the main checkout. See "Implementation".
Subject: a zkfy skill that reorganizes the CS vault on request, from the ad-hoc passes of October 2026.

## Goal

Turn the October 2026 consolidation work into a skill a future session can run on request.
A reorganization pass is one run of the skill over one scope, ending in one reviewed change set.
The vocabulary is in `GLOSSARY.md` at the repo root.

## Evidence (2026-11-04)

- The CS vault (`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/CS`) holds 194 eligible notes
  after the October passes: 459 → 188 notes, about 14 passes, lint 125 → 0. Record: the vault's
  `docs/plans/vault-simplification.md` and `docs/plans/ai-raw-reorganization.md`.
- The apply tooling of those passes (`*-map.json` plus `merge_finalize.py check|apply`) lived in a session
  scratchpad and is gone. `TODO.md` here carries the replacement idea, `vault-knowledge merge-plan`.
- The gen-1 `/reorganize` command (web research → canonical subtopics → coverage table → stubs →
  restructure → agent rewrite) was deleted from the vault on 2026-10-20 (vault commit `5224769`).
- Standing rules the user set on 2026-10-20: combine notes eagerly; reduce the note count; the survivor
  keeps its exact filename; show the mapping before applying; never drop content that exists nowhere
  else; append mode by default.
- The plan's steady state says "run a quarterly `inventory` to spot the next cluster". Nothing
  automates the spotting.
- Leftover structural signals: `111.cs` holds 113 notes (58%); folder depth reaches 5
  (`111.cs/database/postgres/sql/…`); 39 notes still carry `Before`/`Next`; 26 filenames carry a prefix
  that differs from their folder (`Database-*` under `111.cs`, `Study-Plan-*` under `888.study-plan`);
  189 notes are legacy profile (no `Mode`), 9 are thesis, 0 are atom.
- Links that break on a move: 6 relative Markdown links, 1 path-style wikilink. `Src` points into
  `raw/` in 11 notes.
- The `vault-knowledge` launcher is not installed on this machine (`~/.config/zkfy/knowledge.json` and
  `~/.local/bin/vault-knowledge` are missing). ai_dotfiles dropped its installer in `dc9bfab`, whose
  message says zkfy must install it. The vault's docs reference the launcher everywhere.
- One incident from October: a subagent re-ran another subagent's non-idempotent script in a shared
  scratch directory and tripled chapters in 3 notes. The apply step must be idempotent and checkable.
- The vault's working tree is dirty right now (Postgres chapter work and a modified generated catalog).
  The vault's authoring rules forbid stashing or committing the user's pending work.

## Decisions

- **D1 — Jobs: all four.** The skill covers Survey (detection report), Consolidate (merge pass through a
  mapping), Restructure (moves, flattening, renames and map edits, no content merges) and Curate
  (research the canonical subtopics of a topic, compare coverage, handle gaps, rewrite). Reason: the
  user's answer to Q1 was "All of them." The job names are working names until confirmed.
- **D2 — The skill opens with an interview.** On invocation the skill first gathers facts (a survey of
  the vault), then asks grilling-style questions, one per message with a recommended answer first, to
  narrow the session's focus: which job or jobs, which scope, which options. Reason: the user's
  instruction; the grilling rule that facts are the tool's job, so the survey runs before the first question.
- **D3 — The interview uses AskUserQuestion dialogs.** Each decision level is one dialog (jobs with
  multi-select, then scope, then per-job options), the recommended option first and marked
  "(Recommended)"; "Other" carries free text. Reason: the user chose dialogs over an embedded
  grilling protocol or a dependency on the personal `grilling` skill (Q2, option 3). Consequence: the
  interview runs only in Claude Code; Pi uses the CLI subcommands directly, without the interview.
- **D4 — Superseded 2026-11-04 by P2 and P6: no pipeline rewrites in a pass.** (Original text kept for history.) Rewrites were opt-in per survivor, thesis only, approved twice. A mapping may mark a survivor
  `rewrite: thesis`. The user approves the mapping, including that intent, before anything runs. After
  the merge is applied and the preservation check passes, zk-note drafts the rewrite; the user sees old
  and new side by side and approves again before the file is replaced. Never atom (its 500-char ceiling
  drops content), never by default. Reason: Q3 option 1, with the user's addition that approval comes
  first. The October "no batch re-runs" decision and ADR-0003's "no Mode retrofit" stay the defaults.
- **D5 — Coverage gaps become an ingest backlog, never files.** In a Curate pass, each canonical subtopic
  with no note is written into the pass record in the vault's `docs/plans/`: subtopic, why it matters,
  one or two candidate sources. Nothing is created in an eligible root; no map line; no stub. The user
  later ingests chosen sources with `/source-to-zk`. Reason: Q4 option 1; the standing rule to reduce
  the note count; the spinoff queue and the AI map's "Not yet written" list both went stale and were
  retired. Stated alongside and not objected to: web research is allowed only inside a Curate pass and
  only to build the canonical subtopic list, never to write note content.
- **D6 — No standing signal; the survey runs only inside the skill.** `build` and `.claude/QUALITY.md`
  stay as they are. Candidates (deterministic signals plus model ranking) are computed when
  `/vault-reorg` starts and shown in its first dialog. The user decides when "after a while" is.
  Reason: Q5 option 2; the user wants to organize on their own cadence, not be prompted.
- **D7 — Apply stages its own files and asks before committing.** After the mapping is applied and
  `build` has regenerated the catalog, the skill stages exactly the files the mapping touched plus the
  catalog, shows the list, and ends with one dialog: commit now with the prepared message, or leave it
  staged. The user's unrelated changes stay unstaged. Work stays on the current branch. Before applying,
  the skill refuses to start if a file the mapping must touch has uncommitted edits, and names it.
  Reason: Q6 option 1; the vault's pre-commit hook validates the staged snapshot as a whole, so one
  mapping must land in one commit; the vault rules forbid stashing or committing pending work.
- **D8 — Link rewriting rules, including `Before`/`Next`.** A link to an absorbed note becomes
  `[[Survivor#Chapter]]`; a map line is redirected the same way, or dropped when the survivor is already
  listed; the absorbed note's title and aliases join the survivor's `Aliases`; self-links are dropped;
  a `Before`/`Next` field that points at an absorbed note is repointed to the survivor, so reading
  chains stay unbroken. The survivor's own fields are untouched; the absorbed note's are not carried.
  Reason: Q7 option 1 for the fields; the other rules were applied consistently in October and were
  stated without objection.
- **D9 — `raw/` is out of scope.** The skill never lists, moves or edits anything under `raw/`. The
  vault contract's exclusion stays one rule with no exceptions; filing the inbox remains a separate
  manual request. Reason: Q8, the user: "not in the scope".
- **D10 — The vault is the current folder, marked by `docs/knowledge/scope.json`.** The skill refuses
  to run unless that file is in the working directory, then calls the plugin's own
  `scripts/knowledge.py --vault "$PWD"` through the plugin root. No launcher is needed. Restoring the
  `vault-knowledge` launcher install (for `/query` from other projects) becomes a separate `TODO.md`
  item owned by zkfy. Reason: Q9 option 1; `/vault-lint` already detects the vault this way; the
  launcher is missing on this machine and ai_dotfiles no longer installs it.

## Open questions (in order)

Reopened 2026-11-04 by the user: the October standing rules (combine eagerly, reduce the count,
survivor keeps its filename, append mode by default) are "not actually right". Their statement of the
principle: we reorganize because some notes are duplicated, each with slightly different content; the
work is to collect the repeated cluster, extract the content, and patch all of them together.

- **P1 — Merge on duplication only (decided 2026-11-04).** Two or more notes explaining the same
  concept are a cluster; related but distinct notes stay separate and get a link to each other; chapter
  series stay as they are. The October rules "combine eagerly" and "reduce the note count" are retired;
  the principle is one concept, one note. Reason: the user's statement of why we reorganize.
- **P2 — A merge is a weave (decided 2026-11-04).** The skill proposes one outline for the concept and
  the user approves it. Every section of every clustered note is placed under that outline; where notes
  say the same thing the better version is kept once; where they differ both pieces are kept. The
  session model writes it, not the budgeted zk-note pipeline. Append mode is retired as the default.
  Reason: the user's description "extract the content and patch all of them together"; append mode
  keeps the duplication inside one file; pipeline budgets drop content.
- **P3 — The preservation gate is a unit ledger (decided 2026-11-04).** Before writing, each clustered
  note is split into content units (paragraph, list, table, code block). The draft ships with one ledger
  row per unit: `kept` (verbatim, at which heading), `reworded` (where, original shown), `duplicate of`
  (the unit it repeats) or `dropped` (reason). A deterministic check confirms every unit has a row and
  every `kept` row matches the draft text. The user reviews the reworded, duplicate and dropped rows and
  approves before the absorbed files are deleted. Reason: a weave moves and rewords passages, so
  October's line check would flag every merge; self-review alone repeats the October incident class.
- **P4 — The woven note keeps the best-linked filename unless it misleads (decided 2026-11-04).** By
  default the mapping writes the weave into the clustered note with the most inbound links and turns the
  other names into aliases. The mapping may give a new concept name when the kept name would mislead;
  then every inbound link is rewritten. Reason: fewest link rewrites and unbroken git history by default,
  with an escape hatch for names that no longer fit.
- **P5 — A woven note takes the legacy profile (decided 2026-11-04).** `### Abstract`, then
  `### Content` holding the approved outline as `####` sections, then `### Links`; no `Mode` field.
  Reason: matches 189 of 194 notes; no chapter budgets or diagram requirement to fight; thesis means a
  claim with supporting themes, while a weave is the complete treatment of one concept.
- **P6 — The weave is the only rewrite a pass does (decided 2026-11-04).** D4 is dropped. Recasting a
  note into atom or thesis form stays a separate, explicit `/zk-note` request and is never part of
  `/vault-reorg`. Reason: running a woven note through the budgeted pipeline would drop content; one
  engine per note.
- Follow-through: D4 superseded by P6; glossary updated for weave, unit, survivor, absorbed note and
  preservation check.

## Assumptions to confirm at the end

- Home: the zkfy plugin, as `skills/vault-reorg/SKILL.md` plus `commands/vault-reorg.md`. The
  deterministic parts (survey signals, mapping validation, apply, preservation check, link rewriting)
  live beside `scripts/knowledge.py` and share its scope and parsing.
- One scope per pass. The mapping is approved as a whole, with content changes called out separately.
- The preservation check is a hard gate: an absorbed note is deleted only when every content line is
  found in its survivor, except lines the mapping lists as intentional removals.
- Artifacts per pass: a machine-readable mapping file, a rendered dry-run report for review, and a
  Markdown pass record in the vault's `docs/plans/`.
- The known ratchet-hook bug (renamed baseline paths, see the vault plan) is fixed in `run_hook` as
  part of this work.
- The interview (D3) is Claude Code-only, and the weave is written by the session model. The CLI
  subcommands (survey signals, mapping check, apply, ledger check, link rewriting) use only Python and
  plain file tools, so Pi can run them without the interview.

## Implementation (2026-11-04)

Built test-first (`tests/test_reorg.py`, 10 tests; whole suite 35 green). Seams under test: `units`,
`ledger_check`, `survey`, `plan`, `apply` end to end on a git fixture, the rename-move case, and the
CLI exit codes.

- `scripts/reorg.py`: the deterministic core, sharing scope, parsing and link resolution with
  `knowledge.py`. `knowledge.py --vault V reorg survey | units | plan | ledger | apply`.
- `survey`: signals (tiny folders, deep paths, oversized notes, prefix ≠ folder, leftover Before/Next)
  and candidate clusters. Clusters are cliques, never chains: a note joins only when it pairs with every
  member. Pairs come from shared specific name tokens (domain-frequent and generic tokens excluded),
  shared aliases or titles, and shared non-structural headings; each cluster carries a strength score.
  Thresholds live under a `reorg` key in `scope.json`. Real-vault run: 194 notes, 59 clusters, the top
  ones plausible (performance-optimization family, design-pattern family, Function / Functional
  Programming / Compose-Abstraction sharing the HOF aliases).
- `plan`: validates the mapping (eligible paths, no path used twice, no duplicate basename after the
  pass, maps never woven, draft readable and legacy-profile clean), computes every link rewrite (body
  wikilinks with anchors and aliases, embeds, `Before`/`Next`, map lines deduped when the survivor is
  already listed, path-qualified wikilinks and Markdown links whose end moves, plain `[[OldName]]` links
  on a basename change), aliases to add, dirty files, and the ledger result; renders Markdown.
- `apply`: refuses on errors, draft issues, a failing ledger or dirty touched files; writes, deletes,
  moves, rebuilds the catalog with the existing `write_outputs`, stages exactly the touched files plus the
  catalog, and returns a commit message. Idempotent: a second run reports `changed: false`.
- Markdown links are rewritten to vault-root paths because the core's resolver treats `../` links as
  outside references; an untouched link keeps the author's form.
- `skills/vault-reorg/SKILL.md` (procedure, dialogs, weave, restructure, curate, rules),
  `skills/vault-reorg/references/formats.md` (mapping, ledger, units, draft, record, CLI results),
  `commands/vault-reorg.md`.
- Delegated: the ratchet-hook renamed-baseline fix with its test (subagent `hook-fix`), and ADR-0005,
  `TODO.md`, `README.md`, `CLAUDE.md` updates (subagent `docs-writer`); both reviewed before landing.

### Proposed vault doc edits (for the user to apply in the vault; not applied here)

- `docs/knowledge/maintenance.md`, after the commands block: "Reorganization passes (`/vault-reorg`,
  zkfy) write `docs/plans/reorg/<date>-<slug>/` and stage their own files; apply never commits."
- `docs/workflows/vault-authoring.md`, section "Renames, moves, and consolidation": replace the
  paragraph with a pointer: "Use `/vault-reorg` from the vault root. A merge is a weave gated by a unit
  ledger; survivors keep the best-linked filename; `raw/` stays out of scope. Record per pass under
  `docs/plans/reorg/`."
- `AGENTS.md` "Separate maintenance" list: one bullet, "`/vault-reorg`: reviewed reorganization
  passes; see zkfy ADR-0005."
