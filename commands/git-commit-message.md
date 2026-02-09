# Automated Git Commit & Push Workflow

A multi-phase workflow to automatically stage, commit with a generated message, and push changes to the remote repository.

---

## Phase 1: Stage Changes

### Objective

Stage all changes in the working directory for commit.

### Requirements

1. **Change Detection**

   -  Include all modified files
   -  Include all new files
   -  Include all deletions
   -  No user confirmation needed

2. **Validation**
   -  Check if there are changes to commit
   -  Report number of files changed

### Execution Steps

**Run git add command:**

```bash
git add .
```

**Verify staging:**

```bash
git status
```

**Success Criteria**: All changes staged successfully. If no changes exist, inform user and stop workflow.

---

## Phase 2: Generate Commit Message & Commit

### Objective

Analyze staged changes and generate a conventional commit message following best practices.

### Agent Reference

-  **Agent**: `.agents/git-commit-agent` (see `git-commit-agent.md`)
-  **Purpose**: Generate high-quality conventional commit messages

### Commit Message Requirements

Following conventional commit format:

1. **Type Prefix**

   -  `feat`: New feature
   -  `fix`: Bug fix
   -  `docs`: Documentation changes
   -  `refactor`: Code refactoring
   -  `chore`: Maintenance tasks
   -  `test`: Test additions/changes
   -  `style`: Formatting changes

2. **Scope** (optional but recommended)

   -  Domain or component affected
   -  Examples: `(system-design)`, `(web-net)`, `(algorithm)`

3. **Description**

   -  Concise, imperative mood
   -  Start with lowercase
   -  No period at the end
   -  Max 50 characters for subject

4. **Body** (optional for complex changes)
   -  Explain what and why
   -  Wrap at 72 characters

### Execution Steps

**Use git-commit-agent:**

```
Invoke git-commit-agent with:
- Analyze: git diff --staged
- Generate: Conventional commit message
- Execute: git commit -m "<generated message>"
- Validate: Commit created successfully
```

**Agent handles:**

1. Analysis of staged changes
2. Pattern detection (new files, modifications, deletions)
3. Scope determination from file paths
4. Message generation following conventions
5. Commit execution

**Success Criteria**: Commit created with properly formatted message.

---

## Phase 3: Push to Remote

### Objective

Push the committed changes to the remote repository.

### Requirements

1. **Push Execution**

   -  Push to default remote (origin)
   -  Push current branch
   -  Handle push rejections

2. **Error Handling**
   -  Detect remote changes
   -  Suggest rebase strategy
   -  Provide clear feedback

### Execution Steps

**Push changes:**

```bash
git push
```

**If push rejected (remote has changes):**

```bash
git pull --rebase
git push
```

**Success Criteria**: Changes successfully pushed to remote repository.

---

## Complete Execution Flow

```
┌─────────────────────────────────────┐
│  User invokes git workflow          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Phase 1: Stage Changes             │
│  Command: git add .                 │
│  Validate: Changes exist            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Phase 2: Commit                    │
│  Agent: git-commit-agent            │
│  Analyze: Staged changes            │
│  Generate: Commit message           │
│  Execute: git commit                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Phase 3: Push                      │
│  Command: git push                  │
│  Handle: Remote conflicts           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Report: Commit hash + push status  │
└─────────────────────────────────────┘
```

---

## Output Format

Provide clear feedback at each phase:

```
Phase 1 - Staging:
✓ Staged all changes (X files changed)

Phase 2 - Commit:
✓ Generated commit message:
  docs(system-design): add load balancing strategies
✓ Created commit: abc123d

Phase 3 - Push:
✓ Pushed to remote: origin/main
```

---

## Error Handling

**No Changes to Commit:**

```
✗ No changes detected
  Working tree is clean
```

**Push Rejected:**

```
✗ Push rejected (remote has new commits)
→ Suggested action:
  git pull --rebase
  git push
```

**Commit Message Generation Failed:**

```
✗ Could not generate commit message
→ Manual input required
```

---

## Special Cases

### Multiple Unrelated Changes

If git-commit-agent detects multiple unrelated changes:

-  Pause workflow
-  Present detected change groups
-  Ask user: "Commit separately or together?"
-  Proceed based on user preference

### Force Push Scenarios

This is a personal learning repository, so force-pushing is acceptable:

```bash
# Amend last commit
git commit --amend
git push --force-with-lease
```

---

## Implementation Notes

1. All phases execute sequentially (Phase 1 → Phase 2 → Phase 3)
2. Each phase has clear success criteria for validation
3. Phase 2 uses git-commit-agent for consistent message quality
4. Automatic staging of all changes (no selective staging)
5. Push happens immediately after successful commit
6. Rebase strategy preferred over merge for remote conflicts

---

## Quick Reference Commands

**Full automatic workflow:**

```bash
git add .
# (git-commit-agent generates message)
git commit -m "<generated>"
git push
```

**Handle rejected push:**

```bash
git pull --rebase
git push
```

**Amend last commit:**

```bash
git commit --amend
git push --force-with-lease
```
