---
name: note-update
description: "Land an update to one vault note on main: your instruction (the agent edits after a plan gate) or your own Obsidian edit, carried through a worktree, a diff gate, commit, ship and approve, with your copy never overwritten."
disable-model-invocation: true
argument-hint: "<note: path, filename or alias> [instruction] [--vault <root>]"
---

# Note update

One run lands one **target note**'s update on the vault's base branch. Built so far:

- **case A:** you give an instruction, and the agent edits after a plan gate;
- **case B:** you edited the note in the primary checkout (Obsidian) and give no instruction, and the
  run carries your edit.

Case C (neither) stops at step 3.

`<zkfy-root>` is this plugin's root: two levels above the folder this file was loaded from. Resolve every
`<zkfy-root>/…` path to an absolute path before you run it.

- `NU` = `python3 -B <zkfy-root>/scripts/note_update.py --vault "<V>"`. It prints one JSON object.
  Exit 0 is done, 1 is an error, 2 is a refusal, 3 is resolve's several matches; `error` says why.
- `KNOW` = `python3 -B <zkfy-root>/scripts/knowledge.py`, always with an explicit `--vault`.

The primary checkout `<V>` is read-only for the whole run. Every edit and commit happens in the
worktree `<W>`, named by its path in every command (`git -C "<W>" …`, `cd "<W>" && …`), because
ship deletes it at the end. The session stays where it started.

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

`NU state "<N>"`, adding `--instruction-given` when the user gave an instruction. Keep its `dirty`.

- `case` A → step 4.
- `case` B → step 5.
- `case` C → stop: give an instruction, or edit `<N>` in Obsidian first, then rerun.

### 4. Plan gate (case A)

Run `NU plan "<N>"`. Read `<V>/<N>`, and `<V>/docs/workflows/vault-authoring.md` when the vault has
it. Then work out the change the instruction asks for. Stop before the gate, with the reason, when
the change would:

- touch a clip note (`profile` clip) outside its frontmatter and `### Links`: a clip note's body
  stays verbatim (`<zkfy-root>/docs/ADR/0004-clip-mode-verbatim-notes.md`);
- rename or remove a heading that an `inbound` entry's `heading` targets. Repointing those links is
  not built yet, so keep the heading, or fix the links by hand first;
- rename, move or merge the note (the `vault-reorg` skill), or rebuild it from its source (`zk-note`).

Otherwise show, in one gate:

- **Target:** `<N>` and its profile.
- **Change:** what changes, section by section, naming every section it touches. A conversion names
  the target profile.
- **Budget:** `budget.warnings` now, and what the change does to them. These are warnings only.
- **Fallout:** the `inbound` links, with maps and heading links named.
- **Base**, when `dirty`: the user's uncommitted edit is the base, and it lands as its own commit
  before the agent's.

Stop → end the run. Nothing is written and no worktree exists.

### 5. Worktree

`NU names "<N>"` gives the branch `<B>` and the `subject_stub`. Then run this as a command of its
own, since the worktree guard reads the command line:

```bash
ai-dotfiles worktree new <B> --repo "<V>"
```

`<W>` is the path it prints. When `dirty`, run `NU carry "<N>" "<W>"`. Done when it returns
`identical: true`; keep its `sha256`.

### 6. Edit (case A)

The main session edits `<W>/<N>` with the file-edit tool; the worktree guard refuses a subagent's
writes in the session's worktree. Follow the plan, and these rules:

- Keep the profile, unless the plan converts it. A conversion follows the target profile's skeleton
  in `<zkfy-root>/agents/obsidian-formatter-agent.md` (step 4a atom, 4b thesis).
- Touch only the sections the plan names. Every other section stays byte-identical.
- Keep every frontmatter key in its order, plus the filename, `Src` and `Link`. Strip nothing and
  backfill nothing.
- Section headings are 2–4 words, and the vault's authoring rules apply.

Then `NU edit-check "<N>" "<W>"`. Done when:

- its `problems` is empty, apart from a `profile` change the plan made;
- every section it marks changed, added or removed is one the plan named.

Otherwise fix `<W>/<N>` and rerun it.

### 7. Diff gate

Show, in one gate:

- **Diff:** `git -C "<W>" diff -- "<N>"`. In case A on a dirty note, show the user's edit
  (`git -C "<V>" diff -- "<N>"`) and the agent's (`git diff --no-index "<V>/<N>" "<W>/<N>"`) apart.
- **Sections** (case A): the `edit-check` sections that are not `same`, and its `budget.warnings`.
- **Other files touched:** every line of `git -C "<W>" status --porcelain` that is not `<N>`.
  There should be none.
- **Structural lint:** the entries whose `path` is `<N>` in `KNOW --vault "<W>" lint`, which lists
  the whole vault and exits 1 on any issue. Mark each one missing from
  `KNOW --vault "<W>" lint --snapshot head` as **new**; the ratchet hook refuses a commit with a new
  issue.
- **Commit message**, per the `small-commits` rules. In case A on a dirty note there are two: the
  user's edit first, then the agent's.

  ```text
  <subject_stub><what the edit achieves>

  Why: <the edit's reason, in the user's terms>
  Scope: <N>
  Verified: structural lint, <k> issues on <N>, none new; ratchet hook and catalog check at commit and ship
  ```

Stop → end the run. `<V>` is untouched; `<W>` keeps the edit. Say so, and that
`ai-dotfiles worktree rm <worktree folder name> --force` drops the worktree.

### 8. Land

"approve" at the diff gate runs this whole step with no further questions:

1. Restore stray catalog edits, which make the ratchet hook refuse: `git -C "<W>" restore --` each
   file that `git -C "<W>" diff --name-only -- .claude/index.md .claude/index .claude/QUALITY.md
   .claude/lint-baseline.json` lists.
2. Write each message to a file outside the vault (the scratchpad, or `mktemp`). The ratchet hook
   validates each commit's staged link graph and stages the rebuilt catalogs.
   - **Case A on a dirty note:** `NU stage-carried "<N>" "<W>" --sha256 <carry's sha256>`, then
     `git -C "<W>" commit -F <user's message>`, then `git -C "<W>" add -- "<N>"` and
     `git -C "<W>" commit -F <agent's message>`.
   - **Otherwise:** `git -C "<W>" add -- "<N>"`, then `git -C "<W>" commit -F <file>`.
3. Write the PR body per the `pr` skill to a file outside the vault. The title is the last commit's
   subject. Run `cd "<W>" && ai-dotfiles ship --dry-run --title "<subject>" --body-file <body>`,
   then the same without `--dry-run`. Ship runs the vault's Verify check. `<n>` is the PR number on
   its `pr` line.
4. `cd "<V>" && ai-dotfiles approve <n>`. Its `main` line normally reads `skipped: uncommitted
   changes in <N>`: the land check does that fast-forward.
5. `NU land-check "<N>"`. Exit 0: the primary checkout is at the merge. When `superseded` is true,
   the user's copy was brought to the merged version, which builds on it. Exit 2 with a
   `difference`: the user edited `<N>` again during the run. Show the difference; nothing was
   touched, and the choice is the user's.

### 9. Report

The note and its profile, the case, the PR's link, and the land check's result (`fast_forwarded`,
`restored`, `superseded`).
