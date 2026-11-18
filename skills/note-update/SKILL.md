---
name: note-update
description: "Land an update to one vault note on main: your instruction (the agent edits after a plan gate), fixes you pick from its structural defects, or your own Obsidian edit, carried through a worktree, with broken heading links repointed and one approved map line, then a diff gate, commit, ship and approve, with your copy never overwritten."
disable-model-invocation: true
argument-hint: "<note: path, filename or alias> [instruction] [--vault <root>]"
---

# Note update

One run lands one **target note**'s update on the vault's base branch, in one of three cases:

- **case A:** you give an instruction, and the agent edits after a plan gate;
- **case B:** you edited the note in the primary checkout (Obsidian) and give no instruction, and the
  run carries your edit;
- **case C:** neither: the run lists the note's structural defects, you pick fixes (or type your own),
  and it goes on as case A.

In every case, inbound links to a heading the update renamed or removed are
repointed in the same PR, and one map line changes only when the user approves it. No other note gains
a link.

`<zkfy-root>` is this plugin's root: two levels above the folder this file was loaded from. Resolve every
`<zkfy-root>/…` path to an absolute path before you run it.

- `NU` = `python3 -B <zkfy-root>/scripts/note_update.py --vault "<V>"`. It prints one JSON object.
  Exit 0 is done, 1 is an error, 2 is a refusal, 3 is resolve's several matches; `error` says why.
- `KNOW` = `python3 -B <zkfy-root>/scripts/knowledge.py`, always with an explicit `--vault`.

Every edit and commit happens in the worktree `<W>`, named by its path in every command
(`git -C "<W>" …`, `cd "<W>" && …`), because ship deletes it at the end. The session stays where it
started. The run never edits the primary checkout `<V>`: only the land check writes there, at the
end, and only as step 9 says.

**Gate.** In a CLI with a question dialog (AskUserQuestion), ask with Approve (Recommended) and
Stop. Without one, print the gate and wait: only the reply "approve" passes.

**Stop.** An `NU` exit of 1 or 2, and any refusal from a hook or `ai-dotfiles`, ends the run.
Report the step's name, the last error line and one proposed fix. Let the hooks and checks run as
they are: no `--no-verify`, no `--no-checks`, no stash or reset.

## Steps

### 1. Vault

`<V>` is `--vault <root>` when given, else the `vault` value in `~/.config/zkfy/knowledge.json`.
Neither → stop: pass `--vault <root>` or install the `vault-knowledge` binding. Never infer it from
the current folder. Done when `<V>/docs/knowledge/scope.json` exists.

### 2. Resolve

`NU resolve "<note>"`, with the user's words for the note. That can be a path (vault-relative, or
absolute inside `<V>`), a filename without its folder, or an alias. `<N>` is the `note` it returns.
Report its `profile` and `matched_by`.

- **Exit 3, several notes match:** ask which one. In a dialog, the `candidates` are the options,
  each with its path and profile; a dialog holds four, so name any others in the question. Without a
  dialog, print a numbered list and wait for a number. `<N>` is the one picked. An answer naming none
  of them stops the run.
- **Exit 2:** stop with the `error`. When it carries `suggestions`, list their paths so the user can
  rerun with one. Nothing is created.

### 3. State

`NU state "<N>"`, adding `--instruction-given` when the user gave an instruction. Keep its `case` and
`dirty`. A run that stopped earlier is found from git and GitHub, never from stored state; its `run`
gives `<B>` (`branch`), `<W>` (`worktree`) and `<n>` (`pr.number`). Go on at `next_step`:

| `next_step` | Go to |
|---|---|
| `fixes` | step 3a; with `<W>` already there, step 5 skips `worktree new` |
| `plan-gate` | step 4; with `<W>` already there, step 5 skips `worktree new` |
| `worktree` | step 5 |
| `carry` | step 5's carry, with `<W>` from `run` |
| `diff-gate` | step 7 |
| `commit` | step 9's commit item: something is staged or committed, so the diff gate was approved |
| `ship` | step 9's ship item |
| `approve` | step 9's approve item |
| `land-check` | step 9's land check |
| `done` | step 10: the run already landed |
| `owned` | stop with `reason`: another live session owns the worktree; never take it over |
| `stop` | stop with `reason`; when it says the note has no defects to fix, ask for an instruction (step 3a) |

A gate the run already passed is not asked again. The plan gate is the exception: the approved plan is
not recorded, so a run resumed before its edit shows the gate again.

### 3a. Pick fixes (case C)

`defects` lists the note's own structural defects, each with its `rule`, `detail` and `fix`. Ask which to
make: in a dialog, `multiSelect`, one option per `pickable` defect (its `fix` in plain words), naming
any beyond four in the question; the dialog's own free-text answer is the user's instruction instead.
Without a dialog, print a numbered list and wait for numbers, the user's own words, or "stop". A defect
that is not `pickable` is named with its `why` (a rename is the `vault-reorg` skill's), never offered.
A picked `field` fix is the user's repair: it adds that key, and step 6 passes it to `edit-check`.

With no defects, say so and ask what should change instead.

The picked fixes, or the user's words, are the instruction from here on: go on as case A at step 4,
whose plan gate shows them. An answer that picks nothing and gives no instruction stops the run.

### 4. Plan gate (case A)

Run `NU plan "<N>"`. Read `<V>/<N>`, and `<V>/docs/workflows/vault-authoring.md` when the vault has
it. Then work out the change the instruction asks for. Stop before the gate, with the reason, when
the change would:

- touch a clip note (`profile` clip) outside its frontmatter and `### Links`: a clip note's body
  stays verbatim (`<zkfy-root>/docs/ADR/0004-clip-mode-verbatim-notes.md`);
- build on a dirty note whose `broken_by_edit` is not empty: the user's own edit already breaks those
  links, and its commit comes first. Land it without an instruction (case B repoints them), then rerun;
- rename, move or merge the note (the `vault-reorg` skill), or rebuild it from its source (`zk-note`).

Otherwise show, in one gate:

- **Target:** `<N>` and its profile.
- **Change:** what changes, section by section, naming every section it touches. A conversion names
  the target profile.
- **Budget:** `budget.warnings` now, and what the change does to them. These are warnings only.
- **Fallout:** the `inbound` links, with maps and heading links named. Links to a heading the change
  renames or removes are repointed in step 7.
- **Map line**, when the change alters the note's title, aliases or summary and an `inbound` entry is
  a map: the new text for that entry's `line` (its `text` now), one line for one map.
- **Base**, when `dirty`: the user's uncommitted edit is the base, and it lands as its own commit
  before the agent's.

Options: Approve (Recommended), plus Approve without the map line when one is proposed, and Stop. In
plain text: "approve", "approve without map line", or anything else to stop. Stop → end the run.
Nothing is written and no worktree exists.

### 5. Worktree

`NU names "<N>"` gives the branch `<B>` and the `subject_stub`. Then run this as a command of its
own, since the worktree guard reads the command line:

```bash
ai-dotfiles worktree new <B> --repo "<V>"
```

`<W>` is the path it prints, on a detached HEAD that stays detached: `ship` pushes it as `<B>`.
`names` dates the branch when origin already has it. When `dirty`, run
`NU carry "<N>" "<W>"`. Done when it returns
`identical: true`; keep its `sha256`.

### 6. Edit (case A; case B goes on at step 7)

The main session edits `<W>/<N>` with the file-edit tool; the worktree guard refuses a subagent's
writes in the session's worktree. Follow the plan, and these rules:

- Keep the profile, unless the plan converts it. A conversion follows the target profile's skeleton
  in `<zkfy-root>/agents/obsidian-formatter-agent.md` (step 4a atom, 4b thesis).
- Touch only the sections the plan names. Every other section stays byte-identical.
- Keep every frontmatter key in its order, plus the filename, `Src` and `Link`. Strip nothing and
  backfill nothing; a planned conversion sets `Mode`, and a picked case-C `field` fix adds its key, and
  nothing else.
- Section headings are 2–4 words, and the vault's authoring rules apply.

Then `NU edit-check "<N>" "<W>"`, adding `--sha256 <carry's sha256>` when step 5 carried, and
`--adds <key>` for each frontmatter key a picked case-C fix adds. Done when:

- its `problems` is empty, apart from a `profile` change the plan made;
- every section it marks changed, added or removed is one the plan named.

Otherwise fix `<W>/<N>` and rerun it.

### 7. Links and map line

`NU links "<N>" "<W>"`. Its `broken` entries come from the ratchet's own issues; a `new` one is a link
the update broke, and the commit would be refused with it.

- **Heading:** decide each `new` heading's fate: renamed → its new heading; removed → the nearest
  heading that stays, or `""` for the note itself. `repoint` also fixes the note's own links; one it
  lists as `left` (the note's own link to a removed heading) gets another heading by an edit of `<N>`. Then `NU repoint "<N>" "<W>" --rename "<OLD>"
  "<NEW>"` (repeat `--rename` per heading) and rerun `NU links`. Done when no `new` entry is left.
- **Block or frontmatter:** stop; those are not repointed here.

Case A, when the plan gate approved a map line: `NU map-line "<N>" "<W>" --map "<map>" --line <line>
--text "<new text>"`. Case B has no plan gate, so its map line is proposed at the diff gate and applied
in step 9.

### 8. Diff gate

Show, in one gate:

- **Diff:** `git -C "<W>" diff -- "<N>"`. In case A on a dirty note, show the user's edit
  (`git -C "<V>" diff -- "<N>"`) and the agent's (`git diff --no-index "<V>/<N>" "<W>/<N>"`) apart.
- **Sections** (case A): the `edit-check` sections that are not `same`, and its `budget.warnings`.
- **Links:** `repoint`'s count and files, and the map line's old and new text.
- **Map line** (case B), when the user's edit changed the note's title, aliases or summary: run
  `NU plan "<N>"`; for an `inbound` entry that is a map, propose the new text for its `line` (its
  `text` now). Nothing is applied before "approve".
- **Other files touched:** every line of `git -C "<W>" status --porcelain` that is not `<N>`. They
  must be exactly `repoint`'s `files` other than `<N>`, plus the approved map.
- **Commits:** `NU commits "<N>" "<W>"`, adding `--sha256 <carry's sha256>` in case A on a dirty note. When `split` is true, the change lands
  as two commits: first the heading renames with the repointed links, as
  `docs(links): repoint <n> links to <note stem>'s renamed headings`, then the rest.
- **Structural lint:** the entries whose `path` is `<N>` in `KNOW --vault "<W>" lint`, which lists
  the whole vault and exits 1 on any issue. Mark each one missing from
  `KNOW --vault "<W>" lint --snapshot head` as **new**; the ratchet hook refuses a commit with a new
  issue.
- **Commit message**, per the `small-commits` rules. In case A on a dirty note there are two: the
  user's edit first, then the agent's. A split adds the links commit's message.

  ```text
  <subject_stub><what the edit achieves>

  Why: <the edit's reason, in the user's terms>
  Scope: <N>
  Verified: structural lint, <k> issues on <N>, none new; ratchet hook and catalog check at commit and ship
  ```

  The trailers, with any co-author line the CLI adds, form the message's last paragraph: the
  small-commits hook reads only that one.

In case B with a proposed map line, the options are those of the plan gate. Stop → end the run.
`<V>` is untouched; `<W>` keeps the edit. Say so, and that
`ai-dotfiles worktree rm <worktree folder name> --force` drops the worktree.

### 9. Land

"approve" at the diff gate runs this whole step with no further questions. `<links>` are `repoint`'s
`files` and `<map>` the approved map, when there are any.

1. Restore stray catalog edits, which make the ratchet hook refuse: `git -C "<W>" restore --` each
   file that `git -C "<W>" diff --name-only -- .claude/index.md .claude/index .claude/QUALITY.md
   .claude/lint-baseline.json` lists. In case B approved with its map line, run `NU map-line` now,
   then `NU commits` again: its `split` decides the commits below.
2. Write each message to a file outside the vault (the scratchpad, or `mktemp`). The ratchet hook
   validates each commit's staged link graph and stages the rebuilt catalogs.
   - **Case A on a dirty note, first:** `NU stage-carried "<N>" "<W>" --sha256 <carry's sha256>`, then
     `git -C "<W>" commit -F <user's message>`.
   - **A split:** `NU stage-renames "<N>" "<W>"` with the same `--rename` pairs as `repoint`, then
     `git -C "<W>" commit -F <links message>`, then `git -C "<W>" add -- "<N>" <map>` and
     `git -C "<W>" commit -F <note message>`.
   - **No split:** `git -C "<W>" add -- "<N>" <links> <map>`, then `git -C "<W>" commit -F <note message>`.
   - **Resumed here:** `git -C "<W>" log --oneline origin/<base>..HEAD` and `git -C "<W>" diff --cached
     --stat` show which of these commits are done and what is staged; commit what is staged with its
     own message, then go on with the commits not done.

   A commit the small-commits hook still refuses as over 300 lines (the note's own change alone) stops
   the run; its one-time retry is the user's call.
3. Write the PR body per the `pr` skill to a file outside the vault. The title is the note
   commit's subject; in case A on a dirty note, the agent's. Run `cd "<W>" && ai-dotfiles ship --dry-run --title "<subject>" --body-file <body>`,
   then the same without `--dry-run`. Ship runs the vault's Verify check. `<n>` is the PR number on
   its `pr` line.
4. `cd "<V>" && ai-dotfiles approve <n>`. Its `main` line normally reads `skipped: uncommitted
   changes in <N>`: the land check does that fast-forward.
5. `NU land-check "<N>"`. Exit 0: the primary checkout is at the merge. When `superseded` is true,
   the user's copy was brought to the merged version, which builds on it. Exit 2 with a
   `difference`: the user edited `<N>` again during the run. Show the difference; nothing was
   touched, and the choice is the user's.

### 10. Report

The note and its profile, the case, the links repointed and the map line, the PR's link, and the land
check's result (`fast_forwarded`, `restored`, `superseded`).
