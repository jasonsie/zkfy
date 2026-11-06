# vault-lint: the 12 check methods

The method behind each check in `../SKILL.md`, whose table gives severity and fixability. Read the
checks you are about to run; the skill's Step 2 collects their findings.

#### Check 1: Contradictions (HIGH)

For each note, read the `### Abstract` and key claims in `### Content`. Compare against notes referenced in its `### Links` section and notes sharing the same `Sub-Categories`.

Flag conflicting statements about the same concept — e.g., one note claims "SSR improves SEO" while a linked note claims "SSR has no SEO benefit".

**Method:**
1. For each note, extract key claims (statements of fact, definitions, comparisons)
2. For notes that share `Sub-Categories` or appear in each other's `### Links`, compare claims
3. Use semantic understanding to detect contradictions (not just textual differences)
4. Report the specific conflicting statements

**Not auto-fixable** — requires human judgment to resolve which claim is correct.

---

#### Check 2: Stale Content (MEDIUM)

Notes with `Date` older than 6 months AND newer notes exist with overlapping `Sub-Categories`.

**Method:**
1. Parse `Date` from each note's frontmatter
2. Calculate age from current date
3. For notes older than 6 months, check if other notes with overlapping `Sub-Categories` have a newer `Date`
4. Flag the older note for review — it may contain outdated information

**Not auto-fixable** — staleness requires human review to determine if content is still accurate.

---

#### Check 3: Orphan Pages (MEDIUM)

Notes with 0 incoming links — no other note in the vault references them.

**Method:**
1. For each note's filename (without `.md` extension), grep the entire vault for `[[Filename-Without-Extension]]`
2. Exclude self-references (the note itself)
3. If zero other notes reference it, it's an orphan

```bash
# For each note, check incoming links:
Grep pattern: \[\[{Note-Name}\]\]
Path: {vault_root}
Glob: **/*.md
```

**Not auto-fixable** — orphans may need to be linked, merged, or deleted depending on content.

---

#### Check 4: Missing Pages (HIGH)

WikiLink targets that don't exist as files in the vault.

**Method:**
1. Collect all `[[WikiLinks]]` from note bodies across scanned notes
2. **Exclude** links found in frontmatter `Before`, `Next`, and `Src` fields — these are navigational
3. For each target, check if `{target}.md` exists anywhere in the vault
4. List non-existent targets with the notes that reference them

```bash
# For each collected target:
Glob pattern: **/{target}.md
Path: {vault_root}
```

**Not auto-fixable** — missing pages may be typos, planned notes, or intentional references to external concepts.

---

#### Check 5: Weak Links (LOW)

Notes with fewer than 2 outgoing links in their `### Links` section (not counting Before/Next/Src frontmatter links).

**Method:**
1. Read the `### Links` section of each note
2. Count outgoing `[[links]]` that have rationale text nearby (e.g., "Related to [[X]] because...")
3. Flag notes with < 2 such links

**Auto-fixable with `--fix`:**
- Run `vault-knowledge search "<terms>" --limit N` (then `vault-knowledge read "<path>" --heading "<Heading>"`) to find related notes based on the note's `Sub-Categories` and `### Abstract`
- Suggest links with rationale text and append to `### Links` section

---

#### Check 6: Concept Gaps (MEDIUM)

Concepts referenced frequently across notes but with no dedicated note file.

**Method:**
1. Aggregate all `[[WikiLink]]` targets across scanned notes
2. Count occurrences of each target
3. Filter targets that appear >= 3 times but have no corresponding `.md` file in the vault
4. These represent concepts important enough to be frequently referenced but lacking a dedicated note

**Auto-fixable with `--fix`:**
- Create stub notes with Train-Case naming in the appropriate domain folder
- Minimal frontmatter with `Type: literature`, current `Date`, inferred `Categories` and `Sub-Categories`
- `### Abstract` section containing: "Stub -- needs dedicated note. Referenced by N notes."
- `### Content` section left empty
- `### Links` section with backlinks to the top 3 referencing notes

---

#### Check 7: Cross-Reference Gaps (LOW)

Notes sharing the same `Sub-Category` that don't link to each other.

**Method:**
1. Group notes by `Sub-Categories` values
2. Within each group, check if notes reference each other via `[[WikiLinks]]`
3. Flag pairs that share a `Sub-Category` but have no cross-reference

**Auto-fixable with `--fix`:**
- Add cross-references to the `### Links` section of both notes
- Include rationale: "Related to [[Note]] — shares Sub-Category: {sub-category}"

---

#### Check 8: Missing required-core section, mode-aware (HIGH post-ADR / LOW pre-ADR)

Per ADR-0001 D5 (atom) and ADR-0002 D4 (thesis), every note must contain a mode-specific set of **required-core** sections. The check branches on `note.frontmatter.Mode`:

**`Mode: atom`** — required-core sections (unchanged from ADR-0001 D5):
- `### Definition`
- `### Mental Model`
- `### Links`

**`Mode: thesis`** — required-core sections (per ADR-0002 D4):
- `### 執行摘要`
- `### Mental Model`
- **at least one** `### <Theme>` chapter — any `###`-level heading that is NOT one of the reserved names below
- `### Links`

**Reserved heading names** (used to recognize non-theme sections in thesis mode): `Definition`, `Mental Model`, `Why It Matters`, `Boundary`, `Code`, `Links`, `執行摘要`, `附錄`. Any `### <heading>` not in this set is presumed to be a thesis chapter.

**`Mode: clip`** — required-core section (per ADR-0004):
- `### Links`

A clip note is a verbatim source with `### Links` appended. It has no `### Definition`, `### Mental Model` or theme chapter, so none of those are required or flagged.

**`Mode:` missing or invalid** — emit a finding with `detail` = `"Mode frontmatter field missing or invalid (must be atom, thesis or clip)"`. Apply the severity-gating helper (pre-adoption → LOW; post-adoption → HIGH). For the remainder of Check 8, fall back to the atom required-core set so the rest of the validation still runs.

**Do NOT** flag missing `### Why It Matters`, `### Boundary`, or `### Code` in atom mode — these are agent-discretion optional sections per ADR-0001 D5. **Do NOT** flag missing `### 附錄` in thesis mode — it is optional per ADR-0002 D4. **Do NOT** flag presence of `### Boundary` / `### Code` in thesis mode — they are removed by D4 but lint tolerates them as legacy content rather than blocking.

**Method:**
1. For each note, read `note.frontmatter.Mode`.
2. If missing or not one of `atom` / `thesis` / `clip`, emit the missing-Mode finding (above) and continue with the atom required-core set.
3. Parse the markdown headings from the body.
4. Determine the required-core set based on mode.
5. For atom mode: check exact-match presence of each required-core heading (`### Definition`, `### Mental Model`, `### Links`).
6. For clip mode: check exact-match presence of `### Links` only.
7. For thesis mode: check exact-match presence of `### 執行摘要`, `### Mental Model`, `### Links`; additionally, scan all `###` headings and confirm at least one is NOT in the reserved-names set. If none qualify, emit a finding with `detail` = `"Thesis note has no ### <Theme> chapter"`.
8. For each missing required-core heading, emit a finding with `detail` = `"Missing required-core section: <section-name>"`.
9. Apply the severity-gating helper: intrinsic severity is HIGH; pre-ADR notes downgrade to LOW.

**Not auto-fixable** — the modeler must regenerate these sections; lint can only detect.

---

#### Check 9: Body over 500-char budget, atom only (HIGH post-ADR / LOW pre-ADR)

Per ADR-0001 D4, ADR-0002 D5, and the CLAUDE.md "Body budget per mode" section, **atom-mode** notes have a hard ceiling of 500 characters on the body. **Thesis-mode** notes are exempt from this flat check (their per-chapter budget is enforced separately by Check 11). **Clip-mode** notes are exempt too: the body is the source verbatim and has no budget (ADR-0004).

The budget covers `### Definition`, `### Why It Matters`, `### Boundary`, and any prose surrounding diagrams or code.

**Applies to:** notes with `Mode: atom`. **Skips:** notes with `Mode: thesis` or `Mode: clip`. If `Mode` is missing, default to running Check 9 (treat as atom for backwards-compat with pre-Hybrid notes); Check 8 will flag the missing `Mode` separately.

**Count rule** — Chinese characters + English words.

**Excluded** from the count:
- Frontmatter (the YAML block between the leading `---` fences)
- Fenced code blocks (everything between ` ``` ` markers)
- The `### Mental Model` section (from that heading until the next `###` heading or end of file) — diagrams are excluded
- The `### Links` section (same approach)

**Method:**
1. Read `note.frontmatter.Mode`. If `thesis` or `clip`, skip this check entirely (no finding). Otherwise (atom or missing), proceed.
2. Strip frontmatter (top `---` block). If `note-scanner` already strips frontmatter and exposes a body slice, count on the body slice — this is the assumption Check 9 relies on; if scanner output changes, this check must be revisited.
3. Strip fenced code blocks (everything between matching ` ``` ` lines, inclusive of the fence lines themselves).
4. Skip the `### Mental Model` section entirely (from that heading to the next `###` heading or end of file).
5. Skip the `### Links` section entirely (same approach).
6. For the remaining prose, count:
   - **Chinese characters:** code points in the `一-鿿` (CJK Unified Ideographs) range.
   - **English words:** whitespace-separated tokens that contain at least one ASCII letter (excludes punctuation-only tokens such as `--` or `...`).
   - Sum them as `total_chars`.
7. If `total_chars > 500`, emit finding with `detail` = `"Body over 500-char budget: <total>/500"`.
8. Apply the severity-gating helper: intrinsic severity is HIGH; pre-ADR notes downgrade to LOW.

**Not auto-fixable** — compression is a content decision; the modeler should regenerate.

---

#### Check 10: Legacy `--preserve` artifacts (MEDIUM)

The `--preserve` mode is removed per ADR-0001 D5. Pre-existing notes may still carry artifacts from that era; flag them for a separately approved hand edit; there is no batch migration command (ADR-0005).

**Applies to:** every note except `Mode: clip`. A clip note is a web page captured verbatim, and real pages contain `### Abstract` and `### Content` headings (ADR-0004). Skip the whole check for a clip note: no finding, no fix.

**What constitutes a legacy artifact (any one match is sufficient to flag):**
- A `### Abstract` heading (the old skeleton's first section — superseded by `### Definition`)
- A `### Content` heading (the old preserve-mode raw-content block)
- A frontmatter field named `format_mode` or `preserve`
- A note body containing the exact phrase `<!-- preserved verbatim -->` or similar preserve-era marker comments

**Method:**
1. Parse frontmatter; check for `format_mode` or `preserve` keys.
2. Scan body for the headings `### Abstract` or `### Content` (case-sensitive, exact match including `### `).
3. Scan body for known preserve-era marker comments (e.g., `<!-- preserved verbatim -->`).
4. If any match, emit a finding with `detail` listing which artifact(s) were found (e.g., `"Legacy artifacts: ### Abstract heading, format_mode frontmatter key"`).

**Severity:** MEDIUM. **No gating applied** — this is a cleanup signal regardless of `Date`.

**Auto-fixable with `--fix`** (conservative):
- Delete `format_mode` and `preserve` frontmatter keys.
- Rename `### Abstract` → `### Definition` **only if** the note has no existing `### Definition` heading; otherwise leave both in place and report.
- For `### Content`: do **not** rename or rewrite — leave as-is and emit a warning. The 500-char budget makes a safe automatic migration impossible; the user edits the note by hand after approving the change; no batch migration exists (ADR-0005).
- Preserve-era comment markers: do **not** strip automatically; report and leave for a separately approved edit.

**Conservatism rule:** when in doubt, do not auto-fix. Report the artifact and let the user decide on a hand edit later. Silent content rewrite is explicitly rejected (D10, ADR-0001 alternative A6).

---

#### Check 11: Thesis chapter budget (MEDIUM post-adoption / LOW pre-adoption)

Per ADR-0002 D5, each `### <Theme>` chapter in a thesis-mode note has a **soft target of 200–1500 chars**. Chapters that fall below 200 are too thin; chapters that exceed 1500 should be compressed OR the modeler should trigger the D7 back-link mechanism (inline essence + `完整討論見 [[Deep-Note]]` + spinoff candidate in the report).

The character calculation uses the same exclusion rules as ADR-0001 D4 / CLAUDE.md "Calculation rule" (Chinese characters + English words; exclude frontmatter, fenced code blocks, embedded diagrams, and the `### Links` section).

**Applies to:** notes with `Mode: thesis`. **Skips:** notes with `Mode: atom`, `Mode: clip` or missing `Mode`.

**Reserved heading names** (same set as Check 8): `Definition`, `Mental Model`, `Why It Matters`, `Boundary`, `Code`, `Links`, `執行摘要`, `附錄`. Any `### <heading>` not in this set is a theme chapter.

**Method:**
1. Read `note.frontmatter.Mode`. If not `thesis`, skip this check entirely.
2. Parse the body into `###`-level sections. Identify each `### <heading>` whose heading text is NOT in the reserved-names set — these are theme chapters.
3. For each theme chapter, extract the chapter body (from the heading line to the next `###` heading or end of file). Apply the exclusion rules: strip fenced code blocks; chapter content does not include the `### Mental Model` or `### Links` sections (those are siblings, not children, of theme chapters).
4. Count chars in the chapter body using the shared calculation rule (Chinese characters in the `一-鿿` range + English-word tokens containing at least one ASCII letter). Call this `char_count`.
5. **If `char_count < 200`** — emit finding with `detail` = `"Thesis chapter '<heading>' below soft target: <N>/200 chars"`. Apply the severity-gating helper: intrinsic MEDIUM; pre-adoption LOW.
6. **If `char_count > 1500`** — check whether the chapter ends with a D7 overflow back-link sentence. Inspect the last non-empty line of the chapter body for either pattern (case-insensitive):
   - `完整討論見 [[<some-note>]]` (Chinese variant)
   - `For extended treatment, see [[<some-note>]]` (English variant)
   - **If a back-link sentence is present** → tolerated; do NOT emit a finding. The modeler's D7 mechanism was already triggered; per ADR-0002 D5, chapters "may still naturally sit above 1500 if D7 was already triggered".
   - **If a back-link sentence is absent** → emit finding with `detail` = `"Thesis chapter '<heading>' over soft target: <N>/1500 chars (consider compressing or triggering D7 back-link)"`. Apply the severity-gating helper: intrinsic MEDIUM; pre-adoption LOW.
7. Chapters with `200 <= char_count <= 1500` produce no finding.

**Not auto-fixable** — compression and back-link triggering are content decisions; the modeler must regenerate.

---

#### Check 12: Dangling thesis back-link (LOW)

Per ADR-0002 D7 and D9, thesis chapters frequently emit `[[Wikilink]]` back-links to deep-dive notes that may not yet exist in the vault (the target may be a spinoff candidate the user has not yet promoted). Check 12 catches typos and stale wiki-links.

For each `[[<target>]]` wikilink appearing inside a `### <Theme>` chapter (NOT in `### Links`, NOT in `### 執行摘要`, NOT in `### Mental Model`), verify the target exists as a file in the vault.

**Applies to:** notes with `Mode: thesis`. **Skips:** notes with `Mode: atom`, `Mode: clip` or missing `Mode`.

**Method:**
1. Read `note.frontmatter.Mode`. If not `thesis`, skip this check entirely.
2. Identify theme chapters per the same method as Check 11 (reserved-names exclusion).
3. For each theme chapter body, extract all `[[<target>]]` wikilinks. Strip any display-text alias suffix (e.g., `[[Target|Display]]` → `Target`).
4. For each unique target, verify presence in the vault: does `<target>.md` exist anywhere under the vault root (any subdirectory)? Use `Glob` with pattern `**/<target>.md`.
5. If the target is absent, emit finding with `detail` = `"Dangling thesis back-link in chapter '<heading>': [[<target>]] — not found in vault"`.
6. Severity is **LOW** always (intrinsic), then passed through the severity-gating helper — though the gate is effectively a no-op since LOW is already the floor. Dangling back-links pointing to not-yet-promoted spinoffs are expected; this check exists mainly to catch typos and stale targets.

**Not auto-fixable** — the user must decide whether to create the missing note or fix the wikilink target.

---
