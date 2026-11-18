---
name: note-update
description: "Land an update to one vault note on main: your own Obsidian edit, carried through a worktree, a diff gate, commit, ship and approve, with your copy never overwritten."
disable-model-invocation: true
argument-hint: "<note: path, filename or alias> [instruction] [--vault <root>]"
---

# Note update

One run lands one **target note**'s update on the vault's base branch. Built so far: **case B**. You
edited the note in the primary checkout (Obsidian) and give no instruction, and the run carries
your edit. Cases A (an instruction) and C (neither) stop at step 3.

`<zkfy-root>` is this plugin's root: two levels above the folder this file was loaded from. Resolve every
`<zkfy-root>/…` path to an absolute path before you run it.

- `NU` = `python3 -B <zkfy-root>/scripts/note_update.py --vault "<V>"`. It prints one JSON object.
  Exit 0 is done, 1 is an error, 2 is a refusal; the `error` field says why.
- `KNOW` = `python3 -B <zkfy-root>/scripts/knowledge.py`, always with an explicit `--vault`.

The primary checkout `<V>` is read-only for the whole run. Every edit and commit happens in the
worktree `<W>`, named by its path in every command (`git -C "<W>" …`, `cd "<W>" && …`), because
ship deletes it at the end. The session stays where it started.

**Gate.** In a CLI with a question dialog (AskUserQuestion), ask with Approve (Recommended) and
Stop. Without one, print the gate and wait: only the reply "approve" passes.

**Stop.** An `NU` exit other than 0, and any refusal from a hook or `ai-dotfiles`, ends the run. Report
the step's name, the last error line and one proposed fix. Let the hooks and checks run as they
are: no `--no-verify`, no `--no-checks`, no stash or reset.

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

`NU state "<N>"`, adding `--instruction-given` when the user gave an instruction.

- `case` B → continue.
- A or C → stop: note-update carries a hand edit only so far. Edit `<N>` in Obsidian, then rerun
  with no instruction.

### 4. Worktree

`NU names "<N>"` gives the branch `<B>` and the `subject_stub`. Then run this as a command of its
own, since the worktree guard reads the command line:

```bash
ai-dotfiles worktree new <B> --repo "<V>"
```

`<W>` is the path it prints. Then `NU carry "<N>" "<W>"`. Done when it returns `identical: true`.

### 5. Diff gate

Show, in one gate:

- **Diff:** `git -C "<W>" diff -- "<N>"`.
- **Other files touched:** every line of `git -C "<W>" status --porcelain` that is not `<N>`.
  There should be none.
- **Structural lint:** the entries whose `path` is `<N>` in `KNOW --vault "<W>" lint`, which lists
  the whole vault and exits 1 on any issue. Mark each one missing from
  `KNOW --vault "<W>" lint --snapshot head` as **new**; the ratchet hook refuses a commit with a new
  issue.
- **Commit message:** per the `small-commits` rules:

  ```text
  <subject_stub><what the edit achieves>

  Why: <the edit's reason, in the user's terms>
  Scope: <N>
  Verified: structural lint, <k> issues on <N>, none new; ratchet hook and catalog check at commit and ship
  ```

Stop → end the run. `<W>` keeps the carried copy and `<V>` is untouched; say so, and that
`ai-dotfiles worktree rm <worktree folder name> --force` drops the worktree.

### 6. Land

"approve" at the diff gate runs this whole step with no further questions:

1. Restore stray catalog edits, which make the ratchet hook refuse: `git -C "<W>" restore --` each
   file that `git -C "<W>" diff --name-only -- .claude/index.md .claude/index .claude/QUALITY.md
   .claude/lint-baseline.json` lists.
2. Write the message to a file outside the vault (the scratchpad, or `mktemp`), then
   `git -C "<W>" add -- "<N>"` and `git -C "<W>" commit -F <file>`. The ratchet hook validates the
   staged link graph and stages the rebuilt catalogs.
3. Write the PR body per the `pr` skill to a file outside the vault. The title is the commit's
   subject. Run `cd "<W>" && ai-dotfiles ship --dry-run --title "<subject>" --body-file <body>`,
   then the same without `--dry-run`. Ship runs the vault's Verify check. `<n>` is the PR number on
   its `pr` line.
4. `cd "<V>" && ai-dotfiles approve <n>`. Its `main` line normally reads `skipped: uncommitted
   changes in <N>`: the land check does that fast-forward.
5. `NU land-check "<N>"`. Exit 0: the primary checkout is at the merge and your copy is unchanged.
   Exit 2 with a `difference`: you edited `<N>` again during the run. Show the difference; nothing
   was touched, and the choice is the user's.

### 7. Report

The note and its profile, the PR's link, and the land check's result (`fast_forwarded`,
`restored`).
