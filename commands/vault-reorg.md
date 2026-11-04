---
description: "Reorganize the vault in one reviewed pass: survey → dialogs → mapping → weave or moves → apply → stage → confirm commit. Use /vault-reorg [<scope>] [--job survey|consolidate|restructure|curate] from the vault root"
---

# Vault Reorg

Run one reorganization pass over the scoped vault, from the vault root.

## Input

$ARGUMENTS — passed to the `vault-reorg` skill.

Format: `[<scope>] [--job survey|consolidate|restructure|curate]`

- `<scope>`: an eligible directory (`111.cs/language/javascript`) or nothing, for the whole corpus.
- `--job`: answers the first dialog; without it the skill asks.

Examples:
- `/vault-reorg` — survey the vault, then choose the job and scope in dialogs
- `/vault-reorg 111.cs/language/javascript` — survey one directory first
- `/vault-reorg --job survey` — write the survey report only; nothing changes

## Execution

Use the `vault-reorg` skill with the arguments. Its steps: survey, the two dialogs (jobs, scope), the
job (weave, moves or coverage), the plan dialog, apply, the commit dialog, the record. The skill stages
its own files and commits only after the commit dialog's yes.

## Report

End with: the pass folder path, the operations applied (or "survey only"), links rewritten, the ledger
review rows approved, and the commit hash or "staged, not committed".
