# Hooks - ZK Structure Validation

## Overview

This hook validates that the current directory follows proper Zettelkasten folder structure before allowing markdown notes to be written. If the structure is invalid, notes are automatically redirected to `/output/`.

## Required Folder Structure

A valid Zettelkasten vault must contain these folders:

```
.
├── cs/                    # Computer Science notes
├── web/                   # Web development notes
├── ai/                    # AI/ML notes
├── principle/             # Principle notes
├── devops/                # DevOps notes
├── math/                  # Math notes
├── 000.Index/             # Maps of Content (MOCs)
└── zz.original-source/    # Source staging area
```

## Hook Behavior

### When Structure is Valid

The hook passes through all Write/Edit operations unchanged:

```bash
# Working in a valid ZK vault
/path/to/vault/ $ claude
> Write to web/Web-React-Hooks.md
# → File created at: web/Web-React-Hooks.md ✅
```

### When Structure is Invalid

The hook redirects markdown files to `./output/` in the current directory:

```bash
# Working in a non-ZK directory
/some/project/ $ claude
> Write to web/Web-React-Hooks.md
# ⚠️  ZK structure not detected in current directory
# 📁 Required folders: cs web ai principle devops math 000.Index zz.original-source
# 🔀 Redirecting output to: /some/project/output/
# → File created at: /some/project/output/Web-React-Hooks.md
```

## Implementation

**Hook Type**: `PreToolUse`

**Matcher**: `(tool == "Write" || tool == "Edit") && tool_input.file_path matches "\\.md$"`

**Script**: `validate-zk-structure.sh`

The validation script:
1. Receives tool use event as JSON on stdin
2. Extracts tool name and file_path
3. Checks if all required folders exist in current directory
4. If valid → passes through unchanged
5. If invalid → modifies file_path to `$PWD/output/<filename>` and creates directory

## Testing

### Automated Test

Run the comprehensive test script:

```bash
cd /Users/jason/Developer/y-pj/ai/plugin/zkfy/hooks
./test-validation.sh
```

This tests both scenarios:
- ✅ Invalid structure → redirects to `./output/`
- ✅ Valid structure → passes through unchanged

### Manual Testing

To test the hook manually:

```bash
# Test 1: In a valid ZK vault
cd /path/to/obsidian/vault
# Create a markdown file - should work normally

# Test 2: In a non-ZK directory
cd /tmp
# Create a markdown file - should redirect to ./output/
```

## Files

- `hooks.json` - Hook configuration
- `validate-zk-structure.sh` - Validation script
- `README.md` - This documentation
