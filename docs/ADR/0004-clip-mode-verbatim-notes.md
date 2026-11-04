# ADR-0004 — Clip mode: verbatim source notes

Status: Accepted 2026-11-04; not yet implemented. Amends ADR-0002 D8 (allowed `Mode` values) and, for `clip-to-zk` only, commit `966bf6b` (web clips in `raw/` are durable). Implementation plan: `docs/plans/clip-to-zk.md`.

## Decision

Add a third note mode, `Mode: clip`, for a **clip note**: a literature note whose body is the source exactly as captured (web page, video transcript, file or text), with zkfy frontmatter, a Train-Case filename, a domain folder and an appended `### Links` section. A new skill, `clip-to-zk`, produces it. ADR-0001 named this future command `/source-to-raw`; that name no longer fits, because the note leaves `raw/`.

Why: ADR-0001 removed `--preserve` because verbatim storage cannot coexist with the atom 500-character budget, and said preservation belongs in a separate, single-purpose command. A clip note is that command's output. It is a third body shape, so it is a `Mode`, not a new `Type`: it stays `Type: literature`, a record of a source.

Clip notes deliberately depart from the frontmatter block in CLAUDE.md "Note conventions" (which lists `Before`, `Next`, `Src` and `Mode: atom | thesis`): they follow the vault's minimal set described below.

## What a clip note may and may not contain

- The body is the captured content byte for byte. Only two changes are allowed: image embed targets (`![[…]]`) are rewritten when images are renamed, and `---` plus `### Links` is appended at the end.
- Required core section: `### Links` only. No body budget: vault-lint Checks 9 and 11 skip clip notes, and Check 10 does not flag `### Abstract` or `### Content` headings in them, because real web pages contain those headings.
- The structural validator skips in-page anchor checks (`[x](#anchor)`) for clip notes. Those anchors belong to the source page. Wikilinks to notes stay strictly checked. Image embeds are not checked by `knowledge.py` at all (it treats asset links as outside the vault), so `clip_note.py` checks that every `![[…]]` target exists before `raw/` is deleted.
- Frontmatter follows the vault's minimal set (no `Sub-Categories`, `Before`, `Next`, `Src`), plus `Link:` holding the source URL. `Link` is the one exception to the vault's rule, because once `raw/` is deleted nothing else records where the clip came from. Source metadata (author, published date, description, unknown clip-template keys, tags outside the controlled vocabulary as `Source-Tags`) is carried over, never dropped.

## Raw lifecycle

`clip-to-zk` moves its capture out of `raw/` into the vault and then deletes the `raw/` leftovers it created, but only after the new note passes verification and lint. At every failure point, at least one complete copy exists. `/source-to-zk` is unchanged: its distilled notes need the raw clip beside them, so those clips stay durable.

## Ownership

Each concern has one owner; the others call it and never copy it.

- The **web-clipper plugin** (its own repo, extracted from ai_dotfiles) owns the clip's files: fetching, the attachment folder, image naming and `assets.json`, image-embed rewrites, and moving an adopted clip (`--adopt`). zkfy calls it as the `web-clipper` command, through its `--json` output and exit codes.
- **zkfy** owns what the note means in the vault: Discover, the frontmatter adapter and writer (`scripts/clip_note.py`), the filename and folder, `### Links`, cross-pollination proposals.
- **`scripts/knowledge.py`** owns validation, including `Mode: clip`.

## Considered options

- `Type: clip` with no `Mode`: rejected. A clip is a literature note; a new type would blur what `Type` means.
- `Type: fleeting`: rejected. Fleeting means a draft to process later.
- Keeping all clip-file logic inside zkfy: rejected. It would copy the clipper's attachment lookup, naming, manifest and embed scanning, and the copies would drift.
- Appending the clip as a chapter of an existing topic note (the vault's placement rule for Postgres material): rejected. It edits an existing note automatically and mixes a source with the user's own writing.
- `Date` = the day the note entered the vault: rejected by the user in favour of the clip's `created` date. Consequence: an adopted clip from before 2026-05-28 gets the pre-ADR LOW severity in vault-lint. That is harmless, because clip notes have no body budget to fail.
