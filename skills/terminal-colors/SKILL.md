---
name: terminal-colors
description: Standardized bash terminal color formatting for agent output. Use when creating or updating agent prompts that need colored terminal output for progress indicators, success/error messages, file paths, or structured logging. Provides consistent color palette and usage patterns across all agents.
---

# Terminal Colors

Standardized color palette and formatting patterns for terminal output in bash-based agents.

## Quick Reference

```bash
# Colors
RED='\033[91m'      # Errors, ABORT conditions
GREEN='\033[92m'    # Success, completion
YELLOW='\033[93m'   # Warnings, manual review
BLUE='\033[94m'     # Info, progress steps
CYAN='\033[96m'     # File paths, metadata
MAGENTA='\033[95m'  # Categories, domains

# Styles
BOLD='\033[1m'      # Emphasis
DIM='\033[2m'       # Secondary info
RESET='\033[0m'     # Reset formatting
```

## Common Patterns

### Progress Steps
```bash
echo -e "${BLUE}${BOLD}[1/6] Validating input...${RESET}"
echo -e "${BLUE}${BOLD}[2/6] Processing data...${RESET}"
```

### Success/Error
```bash
echo -e "${GREEN}✓${RESET} Operation completed"
echo -e "${RED}✗ Error:${RESET} Operation failed"
```

### File Paths
```bash
echo -e "${CYAN}  → ${DIM}/path/to/file.md${RESET}"
```

### Warnings
```bash
echo -e "${YELLOW}  ⚠${RESET} Manual review needed"
```

## Detailed Reference

For complete color palette, all usage patterns, and guidelines, see [references/color-palette.md](references/color-palette.md).

## Integration

Include the color palette section in agent prompts that require terminal output formatting. Reference this skill to maintain consistency across all agents.
