# zkfy

The vocabulary of the zkfy plugin: ingesting sources into Zettelkasten notes and maintaining the
Obsidian vault those notes live in.

## Language

### Vault

**Vault**:
An Obsidian folder of Markdown notes with a `docs/knowledge/scope.json` policy at its root.
_Avoid_: knowledge base, wiki, repo

**Eligible note**:
A note inside one of the roots that the vault's scope policy lists; the only notes the tools read, index, lint or reorganize.
_Avoid_: tracked note, indexed note

**Map**:
A curated note in the vault's maps folder that lists other notes in a reading order; optional navigation, never a coverage gate.
_Avoid_: MOC, index, hub

**Catalog**:
The generated routing files under `.claude/` that `build` writes from the eligible notes; rebuilt, never hand-edited.
_Avoid_: index (when the generated files are meant), cache

### Reorganization

**Pass**:
One run of the reorganization skill over one scope, ending in one reviewed change set.
_Avoid_: migration, sweep, batch

**Cluster**:
A set of eligible notes judged to cover one concept or topic area, and so a candidate for a mapping.
_Avoid_: group, duplicate set

**Mapping**:
The reviewed table of operations a pass applies: survivors, absorbed notes, moves, renames and the link rewrites they imply.
_Avoid_: plan (when the table is meant), merge list

**Survivor**:
The clustered note whose file receives the weave; by default the one with the most inbound links, renamed only when its name would mislead.
_Avoid_: target, canonical note, primary

**Absorbed note**:
A clustered note other than the survivor; its units are woven into the survivor, its name becomes an alias, its file is deleted and every inbound link is redirected.
_Avoid_: merged note, source note, duplicate

**Weave**:
The merge style: one approved outline for the concept, every unique passage of every clustered note placed under it once, repeated passages kept in their best version only.
_Avoid_: append mode, concatenation, re-synthesis, rewrite

**Unit**:
The smallest piece of a note the preservation check tracks: one paragraph, list, table or code block.
_Avoid_: line, chunk, section

**Preservation check**:
The gate before an absorbed note is deleted: every unit of it has a ledger row (kept, reworded, duplicate of, dropped), every kept row matches the woven text, and the user has approved the rows that are not kept.
_Avoid_: diff check, line check, content audit

### Clipping

**Clip note**:
A literature note whose body is a source exactly as captured, marked `Mode: clip`, with zkfy frontmatter and an appended `### Links` section.
_Avoid_: raw note, preserved note, web clip (for the vault note)

**Capture**:
The file in `raw/` that a clip-to-zk run starts from: a web clip, a video transcript, or a copy of a file or text.
_Avoid_: source file, raw copy

**Adopt**:
To turn a capture into a clip note at its vault destination: the note moves, its images are renamed after it, and the capture is released only after the note checks out.
_Avoid_: import, move, promote
