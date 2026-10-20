---
description: "Run semantic health checks on the vault — contradictions, staleness, orphans, missing pages, concept gaps. Use /vault-lint <path> [--fix]"
---

# Vault Lint

Run semantic health checks on the Obsidian ZK vault and report findings.

## Input

$ARGUMENTS — passed directly to the `vault-lint` skill.

Format: `<path> [--fix] [--checks 1,2,3] [--vault PATH]`

Examples:
- `/vault-lint 333.ai/` — lint the AI directory
- `/vault-lint . --checks 3,4` — check orphans and missing pages across the whole vault
- `/vault-lint 111.cs/ --fix` — lint CS directory and propose fixes for checks 5, 6, 7 (applied only after your approval)
- `/vault-lint 222.web/ --checks 1,2 --vault /path/to/vault` — contradictions and staleness only

## Execution

### Step 0: Initialize Task List

Create tasks to track progress:

1. **Run vault lint checks**
   - Subject: "Run vault lint checks"
   - Description: "Execute semantic health checks on the target path"
   - ActiveForm: "Running vault lint checks"

2. **Apply approved fixes** (conditional on --fix)
   - Subject: "Apply approved fixes"
   - Description: "Propose fixes for checks 5, 6, 7 and apply only those the user approves"
   - ActiveForm: "Applying approved fixes"

3. **Report**
   - Subject: "Report lint findings"
   - Description: "Display formatted lint report to user"
   - ActiveForm: "Reporting lint findings"

### Step 1: Run Lint

Mark task 1 as `in_progress`.

Use the `vault-lint` skill with the provided arguments.

Mark task 1 as `completed`.

### Step 2: Propose fixes (conditional)

If `--fix` was passed:
- Mark task 2 as `in_progress`
- The skill proposes fixes during its Step 3; edits to authored notes are applied only after explicit user approval
- Mark task 2 as `completed`

If `--fix` was NOT passed:
- Mark task 2 as `deleted`

### Step 3: Report

Mark task 3 as `in_progress`.

Display the formatted report from the skill output (Step 4 of vault-lint skill).

If `--fix` was used, append a summary of the fixes the user approved (no log is written):

```
## Approved Fixes Applied
- Check 5: Added links to {N} notes
- Check 6: Created {N} stub notes
- Check 7: Added {N} cross-references
```

Mark task 3 as `completed`.
