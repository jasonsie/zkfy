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

### [feat] /vault-migrate command — opt-in batch migration to Concept-First spec

**Context:** During the same refactor that introduced the Concept-First pipeline (ADR-0001), we agreed on a hybrid migration strategy for pre-existing notes (γ + δ). The lint side (δ — severity downgrade for pre-ADR notes) lands inside this refactor's `vault-lint` extension. The batch migration side (γ — explicit `/vault-migrate` command) is deferred to its own session.

**Why deferred:** Migration tooling is risky surface area. Auto-rewriting hundreds of notes can lose nuance, break links, or destroy hand-curated phrasing. It deserves a session where the only goal is to design the review queue carefully. Bundling it with the spec landing would dilute review attention.

**Acceptance criteria:**

- New command at `commands/vault-migrate.md` taking `<path> [--dry-run] [--auto-accept]`.
- For each pre-ADR note under `<path>` that violates the Concept-First spec, the command treats the existing note as source material and runs it through the full 3-stage pipeline (`zettelkasten-agent` → `conceptual-modeler-agent` → `obsidian-formatter-agent`).
- Output writes to `_migration_review/<original-filename>.md` — **never** overwriting the original until the user explicitly accepts.
- Preserves these fields from the original: `Date`, `Src`, `Link`, `Before`, `Next`. Regenerates: `### Mental Model`, content sections (compressed to ≤ 500 chars), `### Boundary`, `### Why It Matters`.
- `--dry-run` reports what would change without writing anything.
- `--auto-accept` is the only path that allows direct overwrite — and only when explicitly passed. Default behavior is review-queue.
- Refuses to migrate notes whose `Date` is on/after the ADR adoption date if they already conform (idempotency check).

**Explicit non-goals:**

- No lazy migration on edit (e.g., when `cross-pollinator-agent` touches a note, it must NOT trigger migration as a side effect).
- No silent batch — `--auto-accept` requires explicit user intent.
- No semantic merge between original and regenerated content; review queue is full-replacement candidates.

**Touch points to investigate:**

- vault-lint's pre/post-ADR severity gating (lands in the current refactor) — `/vault-migrate` consumes the same severity output to pick migration candidates.
- `_migration_review/` folder location — should it be inside the vault, or sibling? Affects Obsidian indexing.
- How to surface migration diffs to the user (side-by-side preview? git-style diff?).

**Reference:** `docs/ADR/0001-concept-first-pipeline.md` — Future Tooling section.

---

### [design-question] Spinoff backlog source-reference staleness

**Context:** During Stage 2 of the Concept-First refactor, the zk-note skill was wired to (a) write spinoff candidates to `row/_spinoffs.md` and (b) delete the source file from `row/` after the primary note is created. The backlog entries reference the (now-deleted) source path:

```
- [ ] <source_file> → <concept-name> | rationale: <why>
```

After cleanup, `<source_file>` is a dead path. This is currently treated as provenance metadata (not a click-through link), which is fine for now — but `/spinoff-flush` (deferred) needs to decide: does it (i) require the source file to still exist (and therefore should the cleanup be conditional on `spinoff_candidates.is_empty()`?), or (ii) resolve spinoffs from concept-name alone using a fresh re-fetch of the original URL?

**Decision needed during `/spinoff-flush` design**, not now. Flagged here so the design session doesn't miss it.

**Options to evaluate then:**

- Conditional cleanup: keep `row/src-*.md` if spinoff_candidates non-empty; delete when last spinoff is flushed.
- Stable identifier: backlog references concept-name + URL, not `row/` path. URL is in primary note's `Link` frontmatter, so it can be re-fetched.
- Archive instead of delete: move to `row/_archive/<original-name>.md` when spinoffs exist; backlog references the archive path.

**ADR-0002 impact:** `/spinoff-flush` design must also handle thesis-mode chapter-overflow spinoffs (rationale string `"thesis chapter overflow — sub-concept has its own thesis-worthy structure"`). The flush behavior is identical (promote backlog entry into full note) but the resulting note often needs to back-fill the wikilink reference inside the originating thesis chapter — different from atom-spinoffs which have no back-reference to fix.

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

**Context:** Check 12 verifies wikilink targets via `Glob **/<target>.md`. This currently matches files under `row/`, `y.template/`, `x.temp/`, `docs/`, `.obsidian/`, `.claude/`, `000.Index/` — the same exclude list `vault-lint` ignores for domain auto-discovery.

**Why deferred:** A wikilink that resolves only to a staging file in `row/` should still be considered "dangling" from the vault's perspective. Currently Check 12 silently treats it as valid.

**Acceptance criteria:**

- Add the exclude list to Check 12's Glob filter (or to a post-filter step on the Glob results).
- A wikilink target that exists only under `row/` or any other excluded folder is reported as dangling.
- Spinoff backlog entries (`row/_spinoffs.md`) remain the second path for "valid dangling" recognition — that part is unchanged.

**Reference:** `docs/ADR/0002-hybrid-atom-thesis-mode.md` D9, CLAUDE.md "Vault contract" exclude list.
