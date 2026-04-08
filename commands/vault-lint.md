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
- `/vault-lint 111.cs/ --fix` — lint CS directory and auto-fix checks 5, 6, 7
- `/vault-lint 222.web/ --checks 1,2 --vault /path/to/vault` — contradictions and staleness only

## Execution

### Step 0: Initialize Task List

Create tasks to track progress:

1. **Run vault lint checks**
   - Subject: "Run vault lint checks"
   - Description: "Execute semantic health checks on the target path"
   - ActiveForm: "Running vault lint checks"

2. **Apply auto-fixes** (conditional on --fix)
   - Subject: "Apply auto-fixes"
   - Description: "Auto-remediate fixable issues (checks 5, 6, 7)"
   - ActiveForm: "Applying auto-fixes"

3. **Log lint results**
   - Subject: "Log lint results"
   - Description: "Record lint results via wiki-log"
   - ActiveForm: "Logging lint results"

4. **Report**
   - Subject: "Report lint findings"
   - Description: "Display formatted lint report to user"
   - ActiveForm: "Reporting lint findings"

### Step 1: Run Lint

Mark task 1 as `in_progress`.

Use the `vault-lint` skill with the provided arguments.

Mark task 1 as `completed`.

### Step 2: Auto-fix (conditional)

If `--fix` was passed:
- Mark task 2 as `in_progress`
- The skill handles fixes internally during its Step 3
- Mark task 2 as `completed`

If `--fix` was NOT passed:
- Mark task 2 as `deleted`

### Step 3: Log

Mark task 3 as `in_progress`.

Use `wiki-log` skill to record the results:

```
lint path="<path>" scanned=<N> contradictions=<N> orphans=<N> missing-pages=<N> stale=<N> weak-links=<N> concept-gaps=<N> cross-ref-gaps=<N>
```

Mark task 3 as `completed`.

### Step 4: Report

Mark task 4 as `in_progress`.

Display the formatted report from the skill output (Step 4 of vault-lint skill).

If `--fix` was used, append an auto-fix summary:

```
## Auto-fixes Applied
- Check 5: Added links to {N} notes
- Check 6: Created {N} stub notes
- Check 7: Added {N} cross-references
```

Mark task 4 as `completed`.
