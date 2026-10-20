# zkfy TODO

Cross-session backlog for features deferred from active refactors.

## Deferred Features

### [feat] video-frame-capture → source_image

**Context:** During the `zettelkasten-agent` / `zk-note` refactor (introducing `conceptual-modeler-agent` with Mental Model section), we agreed that when the source is a video (YouTube, local file, etc.), the `mental_model.source_image` field should be populated by capturing a representative frame from the video — not left null as the current MVP assumes.

**Why deferred:** The current refactor scope (3-stage pipeline + 500-char limit + spinoff backlog + diagram modality routing) is already large. Frame capture touches `video-agent` and possibly introduces a new dependency (ffmpeg or equivalent), so it gets its own session.

**Acceptance criteria:**

- When `zk-note` runs on a video source, `video-agent` (or a new `video-frame-agent`) extracts 1–3 candidate frames at semantically meaningful timestamps (chapter markers, slide changes, peaks of speech density — pick a heuristic).
- The captured frame is saved under the vault's `attachments/` (or equivalent) folder and the relative path is written into `conceptual-modeler-agent`'s `mental_model.source_image` field.
- `diagram-agent` modality routing must respect: if `source_image` is non-null, skip Mermaid/ASCII generation entirely and embed the image directly under `### Mental Model`.
- Fail-soft: if frame capture fails, fall back to the existing diagram modality chain (Image > ASCII > Mermaid > Structural Bullets per CLAUDE.md).

**Touch points to investigate:**

- `agents/video-agent.md` — current capability surface; does it already extract frames?
- `agents/diagram-agent.md` — needs an `image-embed` branch
- vault attachment path convention — currently undocumented in CLAUDE.md
- Dependencies — ffmpeg, yt-dlp frame extraction flags

**Not in scope for this TODO:** OCR of slide content, multi-frame collage, automatic timestamp selection via vision model. Pick one heuristic, ship, iterate.

---

### [feat] `vault-knowledge merge-plan` — reviewed consolidation (replaces `/vault-migrate`)

**Context:** The CS vault's simplification plan (`docs/plans/vault-simplification.md` in the vault, approved 2026-10-20) replaces batch re-runs of old notes through the agent pipeline with small, reviewed merges. The spinoff backlog was retired in the same change, so its staleness question is moot.

**Acceptance criteria:**

- `vault-knowledge merge-plan --into <survivor> <absorbed>...` prints a dry-run mapping: survivor (exact filename kept), absorbed notes, every inbound link to rewrite (body, MOCs, Before/Next), and anchors that would break.
- `--apply` performs only the printed mapping. Section merging stays a human/model edit; the tool rewrites links and removes absorbed files.
- Ratchet hook validates the staged result; no generated artifact is hand-edited.

**Not in scope:** semantic merging, automatic candidate detection.

---

### [polish] vault-lint Checks 8/9/11/12 — note-scanner `frontmatter.Mode` exposure

**Context:** Stage C of the ADR-0002 refactor added Checks 8 (mode-aware required-core), 9 (atom-only body budget), 11 (thesis per-chapter budget), 12 (dangling thesis back-link). All four read `note.frontmatter.Mode`. Check 9's method documents an inline assumption that `note-scanner`'s JSON exposes `frontmatter.Mode` cleanly.

**Why deferred:** Untested against real `note-scanner` output during the refactor. If `note-scanner` strips unknown frontmatter keys or normalizes case, the lint reads will fail silently.

**Acceptance criteria:**

- Run `/vault-lint` on a sample vault containing at least one `Mode: atom` and one `Mode: thesis` note; verify Checks 8/9/11/12 read the field correctly.
- If `note-scanner` does not expose `Mode`, either (a) patch `note-scanner` to include it, or (b) add a frontmatter re-parse helper inside `vault-lint` and invoke it from Checks 8/9/11/12 before reading `Mode`.

**Reference:** `docs/ADR/0002-hybrid-atom-thesis-mode.md` D9.

---

### [polish] Check 11 back-link sentence regex — whitespace tolerance

**Context:** Check 11 detects D7 overflow back-link by matching `完整討論見 [[…]]` (Chinese) or `For extended treatment, see [[…]]` (English) on the last non-empty line of an over-budget chapter. The current regex assumes a single ASCII space between `完整討論見` and `[[`.

**Why deferred:** If `conceptual-modeler-agent` emits a full-width space (`　`) or no space at all, the regex misses and the chapter is incorrectly flagged.

**Acceptance criteria:**

- Run Check 11 against real modeler output. Confirm the regex catches the actual whitespace style.
- If mismatch: broaden the regex to accept `\s*` or `[\s　]*` between the Chinese phrase and the wikilink.

---

### [polish] Check 12 wikilink existence — path filter for vault Glob

**Context:** Check 12 verifies wikilink targets via `Glob **/<target>.md`. This currently matches files under `raw/`, `y.template/`, `x.temp/`, `docs/`, `.obsidian/`, `.claude/`, `000.Index/` — the same exclude list `vault-lint` ignores for domain auto-discovery.

**Why deferred:** A wikilink that resolves only to a staging file in `raw/` should still be considered "dangling" from the vault's perspective. Currently Check 12 silently treats it as valid.

**Acceptance criteria:**

- Add the exclude list to Check 12's Glob filter (or to a post-filter step on the Glob results).
- A wikilink target that exists only under `raw/` or any other excluded folder is reported as dangling.

**Reference:** `docs/ADR/0002-hybrid-atom-thesis-mode.md` D9, CLAUDE.md "Vault contract" exclude list.
