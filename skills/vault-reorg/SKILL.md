---
name: vault-reorg
description: "Reorganize the scoped Obsidian vault in one reviewed pass. Surveys candidate clusters first, then runs the job the user picks in a dialog: Consolidate (weave duplicate notes into one through a unit ledger), Restructure (moves, flattening, renames, map lines) or Curate (canonical-subtopic coverage; gaps become an ingest backlog). Use when the user asks to reorganize, consolidate, dedupe, merge or flatten vault notes, or runs /vault-reorg. Applies through `knowledge.py reorg`, stages its own files, and asks before committing."
---

# Vault reorg

A **pass** is one scope, one reviewed **mapping**, one commit. The principle (ADR-0005): one concept,
one note. Merge on duplication only; related but distinct notes get a link, not a merge; chapter
series stay. A merge is a **weave**: one approved outline, every unique passage under it once, repeated
passages in their best version. The **unit ledger** proves nothing unique was lost before any file is
deleted. Vocabulary: `GLOSSARY.md` in the plugin root.

Every file a pass writes has its format in [references/formats.md](references/formats.md).

## Preconditions

1. The working directory holds `docs/knowledge/scope.json`. Otherwise stop: run `/vault-reorg` from
   the vault root.
2. The CLI, with the vault path quoted (it may hold spaces):
   `CLI="python3 -B ${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/zkfy}/scripts/knowledge.py --vault \"$PWD\""`
3. The pass folder is `docs/plans/reorg/<YYYY-MM-DD>-<slug>/` inside the vault. `docs/` is outside the
   knowledge scope, so nothing written there becomes a note. Create it once the scope is known.
4. Arguments: `/vault-reorg [<scope>] [--job survey|consolidate|restructure|curate]`. A given scope or
   job answers the matching dialog; the survey still runs and its evidence is still shown.

## Procedure

### 1. Survey, before the first question

Run `$CLI reorg survey` (`--target <scope>` when a scope was given). The result has `signals`
(`tiny_folders`, `deep_paths`, `oversized`, `prefix_mismatch`, `nav_leftovers`) and `clusters`
(`notes`, `reasons`, `inbound`, `lines`). For each of the top five clusters, read every member's
opening section with `$CLI read <path> --heading Abstract` (or `--limit 40` when the heading differs)
and give a verdict: **duplicate** (one concept written twice), **related** (distinct concepts; propose a
link instead), **unrelated** (a name coincidence). Done when each of those clusters has a verdict and one
line of evidence.

### 2. Dialog 1: jobs

AskUserQuestion, `multiSelect: true`, header "Jobs". The question text carries the survey evidence:
the counts and the duplicate clusters by name. Options, the recommended one first and marked
"(Recommended)":

- **Consolidate**: weave the duplicate clusters. Recommended when a cluster has the duplicate verdict.
- **Restructure**: move, flatten, rename, fix map lines. Recommended when `deep_paths` or
  `tiny_folders` is non-empty and no duplicate cluster exists.
- **Curate**: compare a directory with its canonical curriculum; gaps go to an ingest backlog.
- **Survey only**: write the report and stop.

### 3. Dialog 2: scope

One scope per pass. Offer the duplicate clusters (Consolidate) or the flagged directories
(Restructure, Curate) as options; "Other" takes a path. Create the pass folder. Done when the scope is
one cluster or one directory.

### 4. The job

- Survey only: write `report.md` (signals, clusters, verdicts) in the pass folder and stop.
- Consolidate: the Weave steps below. Restructure: the Restructure steps. Curate: the Curate steps.

Each job ends with `mapping.json` ready in the pass folder, or with a record and no mapping.

### 5. Plan and approve

`$CLI reorg plan docs/plans/reorg/<pass>/mapping.json --markdown`. Show the report whole: operations,
every link rewrite, aliases to add, ledger result, dirty files, warnings. Exit code 1 means something
blocks apply: an anchor with no heading (add it to `anchors` in the mapping), a dirty file (the user
saves or reverts it), a ledger row. Then AskUserQuestion "Apply this mapping?" with Apply
(Recommended) / Adjust (say what) / Stop. Done when the user chose Apply and the plan exits 0.

### 6. Apply, stage, confirm the commit

Write `record.md` first (step 7), then `$CLI reorg apply docs/plans/reorg/<pass>/mapping.json`. Apply
writes the woven survivor, rewrites the links, repoints `Before`/`Next`, adds aliases, deletes the
absorbed files, performs the moves, rebuilds the catalog and stages exactly the touched files. Then
`git add docs/plans/reorg/<pass>` so the record, mapping, ledger and draft land in the same commit.
Show the staged list and the `commit_message` from the result. AskUserQuestion "Commit now?" with
Commit (Recommended) / Leave staged. On Commit: write the suggested message plus the session's
attribution trailer to a file and `git commit -F` it. Done when the commit exists or the user chose to
leave it staged, and `$CLI build --check` reports current.

### 7. Record

`record.md` in the pass folder (template in formats.md): goal and scope; the verdicts; the mapping as
one table; the ledger review rows (reworded, duplicate, dropped) as approved; links rewritten; for
Curate the coverage table and the ingest backlog; the commit hash or "staged, not committed". Write it
as decisions are made, so a stopped pass can resume from it.

## Weave (Consolidate)

For each duplicate cluster in the scope:

1. Read every member in full (`$CLI read <path> --start N --limit 200` pages through a long note).
2. Survivor: the member with the most inbound links (`inbound` in the survey). Keep its filename. Add
   `"rename"` to the merge only when that name would mislead a reader about the concept.
3. Outline dialog: propose the `####` sections of `### Content`, one concept per section, the union of
   the members' structure with repeated topics once. AskUserQuestion with the outline in the question
   text: Approve (Recommended) / Edit (Other). Done when approved.
4. `$CLI reorg units <path>` for each member. Keep the output; ledger rows reference these ids.
5. Write `draft.md`, legacy profile: frontmatter `Date` (today), `Type: literature`, `Categories`
   (the survivor's), `Aliases` (the survivor's plus every absorbed stem and alias), `Src` and `Link`
   when the members had them; then `### Abstract` (one or two sentences for the whole concept),
   `### Content` with the approved sections, `### Links` (the union, one line per target, no
   self-links). Place every unique unit under the outline; where two units say the same thing keep the
   better one once; copy verbatim (`kept`) wherever possible; reword only to join passages or to fix
   an error, and say so in the ledger.
6. Write `ledger.json`: one row per unit per member, `kept` | `reworded` (with `heading`) |
   `duplicate` (with `of`, the kept unit's id) | `dropped` (with `reason`). A dropped row needs a reason
   a reader would accept: a separator, a wrapper line, a sentence repeated inside the same note.
7. `$CLI reorg ledger docs/plans/reorg/<pass>/mapping.json` until `"ok": true`. `missing` is a unit
   without a row; `mismatch` is a kept unit whose text changed (mark it reworded or restore the text);
   `dangling` is a duplicate pointing at nothing kept.
8. Ledger dialog: show the review rows (reworded, duplicate, dropped) with their text.
   AskUserQuestion: Approve (Recommended) / Adjust. Done when approved.
9. Write `mapping.json` with the merge (`survivor`, `absorbed`, `draft`, `ledger`, optional `anchors`,
   optional `rename`). Continue at Plan.

## Restructure

1. From the survey, list the moves: flatten folders deeper than three levels; dissolve folders holding
   one or two notes into their parent; move a misfiled note to the folder its concept belongs to; fix a
   filename prefix that contradicts its folder by moving to a new basename. Wikilinks follow basenames,
   so a plain move keeps them; `plan` rewrites path-qualified wikilinks and Markdown links whose end
   moved, and a basename change rewrites every `[[OldName]]` link and keeps the old name as an alias.
2. Write `mapping.json` with `moves` (`from`, `to`). Two notes can never share a basename; `plan`
   refuses. Continue at Plan; the plan dialog shows every operation, so no separate move dialog.

## Curate

1. Research the canonical subtopics of the scope's topic: official documentation, university
   syllabi, standard books. This is the only step in the plugin that reads the web, and only to build
   the subtopic list.
2. Coverage table: subtopic → covered (which notes) / gap / overlap / off-topic. Overlaps become
   Consolidate clusters (Weave steps); off-topic notes become Restructure moves.
3. Gaps go into `record.md` under "Ingest backlog": subtopic, why it matters, one or two candidate
   sources. Nothing is created in a note folder, no map line, no stub; the user ingests later with
   `/source-to-zk`.
4. When the table yields merges or moves, build `mapping.json` and continue at Plan. Otherwise write
   the record and stop.

## Rules

- `raw/` is never listed, read, moved or edited. Catalog files under `.claude/` are rebuilt by apply,
  never edited by hand.
- The pass commits only after the user's yes in the commit dialog. Apply refuses a mapping that
  touches a file with uncommitted edits; show the file and let the user save or revert it.
  `--allow-dirty` only when the user says so.
- Woven notes keep the legacy profile. `/zk-note` and the modeler never run inside a pass.
- One scope per pass; the mapping is approved as a whole; changes to the woven text are named in the
  ledger dialog.
- Subagents used for drafting each get their own scratch directory and never run another's script.
