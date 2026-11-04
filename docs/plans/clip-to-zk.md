# clip-to-zk — decision record and implementation plan

Status: design settled 2026-11-04 (interview Q1–Q20); implementation not started.
Subject: a zkfy skill that files a source verbatim as a vault note, with zkfy frontmatter, a Train-Case filename, a domain folder and links.
Decision of record: `docs/ADR/0004-clip-mode-verbatim-notes.md`. This file holds the details and the steps.

## Goal

`/zkfy:clip-to-zk <source> [domain] [--vault <root>]` turns a web page, an existing `raw/` clip, a video, a local file or pasted text into a **clip note** (`Mode: clip`). The original content is kept; only the frontmatter, filename and folder change, and `### Links` is appended. The note joins the vault like any other: Discover, backlink proposals, lint, catalog build. Its `raw/` copy is removed once the note checks out.

## Flow

```
/zkfy:clip-to-zk <url | raw/clip.md | file | text | video>
  1. dedupe     stop if a note in scope already has this Link (normalized URL):
                URL input → the argument; raw/ clip → its source:; file and text → skipped
  2. capture    web-clipper plugin: clip (URL → raw/<Title>.md + raw/assets/<slug>/)
                video-agent / copy for video, file, text → raw/src-*.md
  3. Discover   zettelkasten-agent: domain + sub-folder, concept, Categories, tags, Aliases, related
  4. place      web-clipper plugin: --adopt (note to its destination, images renamed, ![[…]] rewritten)
  5. format     clip_note.py: frontmatter adapter + writer, append ---/### Links
  6. verify     body equal to the capture apart from embed targets; knowledge.py issues() empty
  7. cleanup    delete this run's raw/ leftovers, only after 6 passes
  8. integrate  cross-pollinator (Dry run: true), Map suggestions in the report, lint + build
```

Owners: the web-clipper plugin owns steps 1 and 4 (the clip's files). zkfy owns the rest. `knowledge.py` owns validation.

## Decisions

| # | Decision |
|---|---|
| Q1 | Body verbatim. Only the frontmatter, filename and folder change. No cleanup of site chrome, no summary. |
| Q2 | The note is moved, not copied and left behind. Only this run's files are touched. Clipper exit 3 (clip exists) → ask before adopting that file. |
| Q3 | Images renamed `<NoteStem>-NN-<name>.<ext>` in `<attachments>/<NoteStem>/`, NN = order in the body. Only `![[…]]` targets change; alt text stays. Collision → abort. `assets.json` moves with them, `file` fields updated. |
| Q4 | Integration: Discover; `---` + `### Links` appended at the end; cross-pollinator dry run, only approved edits applied; Map suggestions in the report only; lint + build; `Before`/`Next` not written. |
| Q5 | `Type: literature`, `Mode: clip`. Required section: `### Links`. No body budget. |
| Q6 | Skill `skills/clip-to-zk/SKILL.md` for judgment steps; script `scripts/clip_note.py` for exact steps, with `--dry-run` and unit tests. |
| Q7–8 | Inputs: URL (plus `--html`), existing `raw/` clip, video, local file, text. Every source lands in `raw/` first, then goes through the same adopt path. Video uses video-agent in STRICT mode (failure aborts everything). A file outside the vault is copied, never moved; only `raw/` files are moved or deleted. No markdown-file-agent reformatting. |
| Q9 | Transaction: plan (dry run) → stage → verify → lint → delete `raw/`. Verify fails → staged files removed. Lint fails → new note and `raw/` both kept, reported. Cross-pollinator or build failure after cleanup → warning only. |
| Q10 | Adapter: one pure function, `adapt(kind, source_meta, discover) → (frontmatter, report)`, mapping declared as one table per source kind. Discover owns classification; the source owns provenance. |
| Q10a | `Date` = the clip's `created` (today for text and video). |
| Q10b | Unknown clip-template keys carried over unchanged; a key whose name collides with a zk key aborts. |
| Q10c | Clip `tags`: drop `row`; tags in the controlled vocabulary merge into `tags`; the rest go to `Source-Tags`. |
| Q11 | One owner per concern (see ADR-0004). Clip files: web-clipper plugin, extracted in a separate session. |
| Q12 | The vault's minimal frontmatter plus `Link` (see the mapping below). No `Sub-Categories`, `Before`, `Next`, `Src`. |
| Q13 | Always a new file, in the sub-folder Discover picks from existing folders in scope; unclear → ask. The topic note gets a link proposal, never an automatic edit. |
| Q14 | Filename `Domain-English-Concept.md` from Discover's concept (ASCII Train-Case); the original title becomes `Aliases[0]`. |
| Q15 | `Mode: clip` skips the in-page anchor check; wikilinks to notes stay strict. Image embeds are checked by `clip_note.py` (step 4), because `knowledge.py` never checks asset links (correction found while writing this plan; the decision stands). |
| Q16 | A note in scope with the same normalized `Link` → stop and show it, before clipping. Existing distilled note → ask whether to add the clip beside it. Refresh → `TODO.md`. |
| Q17 | One source per run. Batch → `TODO.md`. |
| Q18 | Vault from the installed `vault-knowledge` binding; `--vault <root>` overrides; never inferred from the current folder. Always passed explicitly to web-clipper. |
| Q19 | Agents reached through the existing hand-off pattern; the broken `~/.claude/agents/` path is fixed for all skills first (step 0). |
| Q20 | Clipper exit 5 (images left remote) → retry `--localize` once, then continue and list the remote URLs in the report. |

### Frontmatter mapping (clip source, default `row.json` template)

| Clip key | Clip note key | Transform |
|---|---|---|
| `source` | `Link` | as is |
| `title` | `Aliases[0]` | as is; Discover's aliases follow, deduplicated |
| `author` | `Author` | `"[[A]], [[B]]"` → list `["[[A]]", "[[B]]"]` |
| `published` | `Published` | date; empty → omitted |
| `description` | `Description` | as is; empty → omitted |
| `created` | `Date` | as is |
| `tags` | `tags` / `Source-Tags` | per Q10c |
| any other key | same key | carried over (Q10b) |
| — | `Type: literature`, `Mode: clip` | fixed |
| — | `Categories`, `Aliases` (rest), `tags` | from Discover |

Key order on write: `Date, Type, Mode, Categories, Aliases, tags, Link, Author, Published, Description, Source-Tags`, then carried-over keys in source order. Video and text sources get their own tables: video → `Link` = video URL, title → `Aliases[0]`; text and file → no `Link`.

URL normalization for the duplicate check (Q16): lowercase scheme and host, drop the `#fragment`, drop `utm_*` query parameters, drop a trailing `/`.

## Steps

Each step lists what it changes and what proves it. Steps 0–5 can start now; step 7 waits on the web-clipper plugin.

0. **Fix the agent hand-off path (all skills).** `~/.claude/agents/` does not exist; the agent files live only in the plugin cache. Choose between a link from `~/.claude/agents/` into the plugin and switching the prompts to `${CLAUDE_PLUGIN_ROOT}/agents/<name>.md`. Touches the CLAUDE.md "Agent delegation pattern" rule, `skills/zk-note/SKILL.md`, `commands/source-to-zk.md`, `AGENTS.md`. Proof: `/source-to-zk` reaches zettelkasten-agent on this machine.
1. **Validator: `scripts/knowledge.py`** (lands before any clip note is committed, because the vault's commit check fails on any new issue).
   - `required["clip"] = ["Links"]` (around line 432) and the `mode` hint text (line 401).
   - Skip `link-anchor` for `Mode: clip` (lines 360–370).
   - `ASSETS` (line 34) gains `.avif .bmp .ico .tif .tiff .heic`, matching web-clipper's `IMAGE_EXTS`. 145 of 300 asset files in the vault are `.avif`. Membership in `ASSETS` means "not checked" (`resolve()` returns `outside`, line 349), not "resolves"; today an `.avif` embed is wrongly reported as an unresolved note link.
   - Extract the filename pattern (line 419) as `FILENAME_RE` for `clip_note.py` to import.
   - Tests in `tests/test_knowledge.py` (the `note()` helper gains a clip case): clip note with only `### Links` passes; a clip note's anchors are not flagged; an `.avif` embed resolves; atom/thesis behaviour unchanged.
2. **vault-lint: `skills/vault-lint/SKILL.md`.** Check 8 gains the clip branch (required core `### Links`; its "must be atom or thesis" text updated). Check 9 skips clip (today it runs on every non-thesis note). Check 10 skips clip notes. Checks 11 and 12 already skip. Update `docs/CODEMAPS/plugin.md` (still says "7 checks") and the README check list.
3. **Adapter, test-first.** `adapt()` with the clip, video and text tables; tests cover every row of the mapping, the collision abort, the `Source-Tags` split, author string → list, empty values omitted, key order.
4. **`scripts/clip_note.py`, test-first.** CLI: `--vault`, `--note <adopted note>`, `--source-meta <json>`, `--discover <json>`, `--dry-run`, `--json`. It replaces the clip frontmatter with `adapt()`'s output, appends `---` + `### Links`, checks the body against the capture (equal apart from embed targets, same embed count), checks that every `![[…]]` target exists in the attachment folder with the sha256 recorded in `assets.json` (from `--adopt`'s JSON summary), runs `knowledge.Corpus(...).issues()` filtered to the new path, and reports. It also owns the duplicate-`Link` check and the URL normalization. Every path goes through `knowledge.py`'s `safe_path` (no symlinks, no traversal). Reading the `raw/` capture to compare bodies is an ingest step, not a scoped read, so it does not use the scope helpers, which refuse `raw/` by design (ADR-0003). Tests in `tests/test_clip_note.py` in the style of `test_knowledge.py`: a temporary scoped vault with `.obsidian/app.json`, a synthetic adopted note and assets, no network, no web-clipper call.
5. **Agents.**
   - `agents/zettelkasten-agent.md`: also return a sub-folder chosen from the folders in scope (the skill passes the scope's domains and their existing sub-folders), and a concept name usable as an English Train-Case filename.
   - `agents/cross-pollinator-agent.md` (Step 1, lines 74–78): a `Mode: clip` branch that reads the concept from the frontmatter (`Aliases`, `Description`) and the opening paragraphs, since a clip has no `### Definition`.
6. **Skill `skills/clip-to-zk/SKILL.md`.** Input detection, the flow above, every stop (exit 2 → ask for `--html`, exit 3 → ask, duplicate `Link` → stop, domain or folder unclear → ask, verify or lint failure → keep both copies), the cleanup rule, and the report: note path, Mode, images saved and left remote, backlinks proposed and applied, Map suggestions, lint result, catalog rebuilt. Map-suggestion wording comes from `agents/obsidian-formatter-agent.md` Step 5.
7. **End-to-end (blocked on the web-clipper plugin).** Needs the `web-clipper` command on PATH with `--adopt`, `--localize` on adopted notes, and the two-phase adopt below. Run on a scratch vault, then on one real clip from the vault's `raw/`.
8. **Docs.** `CLAUDE.md` (Note modes table gains a `clip` row; the "Every note declares `Mode: atom | thesis`" line and the "Note conventions" frontmatter block, which lists `Before`, `Next`, `Src` and `Mode: atom | thesis`, both gain the clip exception; the raw-lifecycle exception; the pipeline section names clip-to-zk); `AGENTS.md` (lines 52–63 modes; lines 69–83 schema brought to the minimal set); `README.md`; `docs/CODEMAPS/plugin.md`; the durability lines in `agents/markdown-file-agent.md:199`, `skills/zk-note/SKILL.md:313` and `commands/source-to-zk.md:155` gain "except clip-to-zk, which adopts its clip"; `TODO.md` gains refresh (Q16) and batch (Q17); `GLOSSARY.md` gains **Clip note** and **Adopt** once that file lands on main; plugin version bump.
9. **Vault-side proposals (the user's to apply).** `docs/workflows/vault-authoring.md`: a placement exception for clip notes and the `Link` exception; `docs/knowledge/maintenance.md` and `docs/knowledge/query.md`: `clip` in the profile lists. Draft the wording; do not edit the vault.

## Open interface point with the web-clipper plugin

Q9 says `raw/` is deleted only after zkfy has verified and linted the new note, but step 4 (`--adopt`) is a web-clipper command, and as first sketched it moves the files. To keep one copy intact at every failure point, `--adopt` should run in two phases:

- `web-clipper --adopt <raw-note> --to <dest> --stem <NoteStem>` writes the note and the renamed images at the destination and leaves the `raw/` note and old asset folder in place;
- `web-clipper --release <raw-note>` (name to be decided) deletes the `raw/` note and its old asset folder, only for a clip whose adoption it recorded.

zkfy runs `--release` in step 7 of the flow. This requirement goes to the web-clipper session.

A third command undoes an adoption (removes the adopted note and renamed images, leaves the `raw/` clip): zkfy needs it when `clip_note.py format` exits 2 after `--adopt`, so the staged copy goes away as Q9 requires. Until it exists, the skill stops and reports both paths, deleting nothing.

## Proposed vault wording (step 9; the user applies it)

The vault owns these files; zkfy never edits them. Paths are relative to the vault root.

- `docs/workflows/vault-authoring.md`, Placement, after the PostgreSQL paragraph:
  > Clip notes (`Mode: clip`, written by `/zkfy:clip-to-zk`) are always their own file in the matching bucket: a verbatim source is not a chapter. The topic note may link to it.
- Same file, the metadata paragraph, after "Do not add `Sub-Categories`, `Link`, `Before`, or `Next` to new notes;…":
  > Clip notes are the one exception for `Link`: it holds the source URL, because their `raw/` capture is removed once the note is filed.
- Same file, Note profiles list, after the thesis line:
  > - **Clip (`Mode: clip`):** the source verbatim with `### Links` appended; no body budget; in-page anchors are not checked (zkfy ADR-0004).
- `docs/knowledge/maintenance.md`, Structural profiles sentence ("Legacy notes require…; thesis notes use…"), append:
  > clip notes require only Links.
- `docs/knowledge/query.md`, Formats sentence ("Existing legacy, atom, thesis, structure, and fleeting notes remain readable."): add `clip` to the list.

## Environment notes (2026-11-04)

- The `vault-knowledge` launcher and its binding (`~/.local/bin/vault-knowledge`, `~/.config/zkfy/knowledge.json`) are missing on this machine. Until they exist, the skill runs `python3 <plugin>/scripts/knowledge.py --vault <root>` with the `--vault` override (Q18).
- The vault's attachment folder is `raw/assets` (`.obsidian/app.json`), so renamed images stay under `raw/assets/<NoteStem>/`; cleanup deletes the `raw/` note and the old `raw/assets/<slug>/` folder, not the renamed images.
- Most current `raw/` clips are neon.com Postgres tutorials; they are the first adoption candidates and the test cases for `.avif` and anchor links.
