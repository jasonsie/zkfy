---
name: clip-to-zk
description: File a source verbatim as a Mode clip vault note — URL, raw/ clip, video, file or text — with zkfy frontmatter, a Train-Case name, a domain folder and proposed backlinks.
disable-model-invocation: true
argument-hint: "<url | raw/<clip>.md | file | text | video-url> [domain] [--vault <root>]"
---

# Clip to Zettelkasten

One run files one source as one **clip note**: the source's content kept verbatim, with zkfy frontmatter
(`Mode: clip`), a Train-Case filename, a domain folder and an appended `### Links` section. Decisions and
reasons: `${CLAUDE_PLUGIN_ROOT}/docs/ADR/0004-clip-mode-verbatim-notes.md`; the full rule set:
`${CLAUDE_PLUGIN_ROOT}/docs/plans/clip-to-zk.md`.

The body is never edited by hand. Every file operation runs through one of three commands, via Bash:

- `web-clipper` — the web-clipper plugin (2.2 or later); owns clip files: fetching, images, `--adopt`,
  `--release`, `--unadopt`, `--localize`
- `CLIP` = `python3 -B ${CLAUDE_PLUGIN_ROOT}/scripts/clip_note.py --vault "<V>"`
- `KNOW` = `python3 -B ${CLAUDE_PLUGIN_ROOT}/scripts/knowledge.py --vault "<V>"`

`web-clipper` and `CLIP` take `--json`: read the JSON line and act on the exit code as each step says.
Run every command from the vault root (`cd "<V>" && …`): web-clipper resolves relative paths against the
current folder, and `<C>`, `<D>` below are vault-relative. Paths web-clipper reports back are absolute;
`CLIP` accepts those as they are.

## Steps

### 1. Vault

`<V>` is `--vault <root>` when given, else the `vault` value in `~/.config/zkfy/knowledge.json`. Neither →
stop and say: pass `--vault <root>` or install the `vault-knowledge` binding. Never infer the vault from the
current folder. Done when `<V>/docs/knowledge/scope.json` exists.

### 2. Source kind

| Input | Kind | Capture `<C>` |
|---|---|---|
| video URL (youtube.com, youtu.be, vimeo.com, other video hosts) | `video` | `raw/src-<kebab-title>.md` |
| other `http(s)://` URL | `clip` | `raw/<Page Title>.md`, written by web-clipper |
| `raw/…md` whose frontmatter has `source:` | `clip` | that file (adoption) |
| other existing file path | `text` | `raw/src-<kebab-title>.md` (a copy) |
| anything else | `text` | `raw/src-<kebab-title>.md` |

### 3. Duplicate check

For a URL, run `CLIP find-link "<url>" --json`; for a `raw/` clip, use its `source:`. Text and files skip this.
Exit 3 lists the notes that already record the source:

- a `Mode: clip` match → stop and show it (refresh is not built yet);
- an atom, thesis or legacy match → show it and ask whether to add the verbatim clip beside it.

### 4. Capture

- **URL**: `web-clipper "<url>" --vault "<V>" --out raw --json`.
  - `0` → continue.
  - `5` (some images remote) → run `web-clipper --localize "<note>" --vault "<V>" --json` once; keep every URL still remote for the report.
  - `2` (bot wall, login, paywall) → ask the user to save the page from their browser, then rerun with `--html <file>`.
  - `3` (a clip already exists) → ask whether to adopt that existing clip; yes → continue with it as the capture.
  - `1` or `4` → stop and show the message.
- **Video**: delegate to `${CLAUDE_PLUGIN_ROOT}/agents/video-agent.md` (Task tool, `subagent_type: general-purpose`, prompt: read that file, Mode STRICT, output `raw/src-<kebab-title>.md`). Any failure aborts the whole run.
- **File**: `cp` it to `raw/src-<kebab-title>.md`. The original stays where it is.
- **Text**: write it to `raw/src-<kebab-title>.md` with a quoted heredoc (`cat > … <<'EOF'`).

Done when `<C>` exists. For a clip, also keep the capture's attachment folder: `assets_dir` in the clipper's
JSON summary, or, for an existing `raw/` clip, the folder whose `assets.json` lists the clip's images.

### 5. Discover

Delegate to `${CLAUDE_PLUGIN_ROOT}/agents/zettelkasten-agent.md` (same Task pattern) with:

- the capture path `<C>`;
- the domains from `<V>/docs/knowledge/scope.json` (`domains`: key → folder) and, for each, its existing sub-folders (`find "<V>/<folder>" -type d -not -path '*/.*'`, listed vault-relative);
- related-note candidates from `KNOW search "<title or concept terms>" --limit 10`;
- the domain argument, when the user gave one.

Domain or folder unclear → ask the user; never pick heuristically and never invent a folder.

Build the destination `<D>` = `<domain folder>/<sub-folder>/<Prefix>-<concept>.md`. `<Prefix>` is the domain
prefix the notes already in that folder use (e.g. `CS-`, `Web-`, `AI-`; see
`${CLAUDE_PLUGIN_ROOT}/agents/obsidian-formatter-agent.md` Step 2).

Write the Discover result to a JSON file in the session scratchpad, never inside the vault:

```json
{"categories": [...], "aliases": [...], "tags": [...], "related": ["Note-Name", ...],
 "tag_vocabulary": ["<every facet tag in the tags line of obsidian-formatter-agent.md Step 3>"]}
```

The tag vocabulary is the formatter's facet list, which matches the vault's authoring rules
(`docs/workflows/vault-authoring.md`); `tags` from Discover must come from it too.

Done when `<D>`'s stem is ASCII Train-Case, its folder exists, `categories` has at least one entry and every `related` name is an existing note.

### 6. Preview

Before anything is staged, dry-run the whole note from the capture itself:

```bash
CLIP format --kind <kind> --source "<C>" --dest "<D>" --original "<C>" \
  [--assets "<capture's attachment folder>"] --discover "<discover.json>" --dry-run --json
```

Show the user the destination, the frontmatter keys, the adapter report and the lint result. Continue only on
exit `0` with an empty `lint`; on any other result, stop and report it. Nothing has been written, so nothing
needs undoing.

| Exit | Meaning | Action |
|---|---|---|
| `6` | lint issues in the would-be note | report each issue; stop |
| `3` | duplicate source, or `<D>` exists | stop; show the conflicting note |
| `4` | the adapter refused a frontmatter key | stop; name the key (rename it in the clip template) |
| `2` | body or images do not check out | stop; report the message |
| `1` | path, scope or input problem | stop; show the message |

### 7. Place (clips only)

`web-clipper --adopt "<C>" --to "<D>" --vault "<V>" --dry-run --json`, then the same without `--dry-run`. It
copies the note and the renamed images (`<stem of D>-NN-<name>`) and leaves `<C>` in place. Keep the JSON's
`assets_dir` as `<A>` (null when the clip has no local images). Exit `3` (destination, image folder or an
earlier adoption exists) or `4` (an image does not match its sha256) → stop and report; nothing was written.
A web-clipper older than 2.2 (no `--adopt`) → stop: this run needs web-clipper 2.2.

Video, file and text sources skip this step.

### 8. Format

```bash
CLIP format --kind <kind> --source "<D for clips, C otherwise>" --dest "<D>" --original "<C>" \
  [--assets "<A>"] --discover "<discover.json>" --json
```

After a clean preview, the only expected failure here is exit `2`: the adopted body or renamed images differ
from the capture. Then undo the adoption with `web-clipper --unadopt "<C>" --vault "<V>" --json` (it deletes
only the adopted copy; `<C>` stays) and stop. Exit `6` → keep the note **and** `<C>`, report each issue, skip
step 9. Any other exit → `--unadopt` the same way, then stop and report.

### 9. Cleanup

Only after step 8 exits `0`. A clip → `web-clipper --release "<C>" --vault "<V>" --json`. A video, file or text
capture → `CLIP release "<C>" --json`. Only this run's capture goes; a user's original file is never touched.

### 10. Integrate

1. Delegate to `${CLAUDE_PLUGIN_ROOT}/agents/cross-pollinator-agent.md` with the new note, the vault root, the
   step 5 candidates and `Dry run: true`. Show its proposals; apply only the ones the user approves.
2. Map suggestions: read the vault's maps (`maps` in `scope.json`) and propose a line and a place for the new
   note, as in `obsidian-formatter-agent.md` Step 5. Never edit or create a map.
3. `KNOW lint` (report issues touching the new or edited notes), then `KNOW build`.

Failures here are warnings: the note already exists.

## Report

```
✅ Clip note filed
📄 Location: <D>
🧬 Mode: clip
🖼  Images: <n> saved · <m> left remote: <urls>
🔗 Links: <related>
🔄 Backlinks: <n> proposed · <k> applied (user-approved)
📑 Map suggestions: <map path + line>
🧹 Removed: <C> (and its old image folder)
🧪 Lint: <result>
📇 Catalog: rebuilt
```
