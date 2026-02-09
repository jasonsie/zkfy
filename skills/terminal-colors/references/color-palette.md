# Terminal Color Palette Reference

## Color Definitions

```bash
# Colors
RED='\033[91m'      # Errors, critical failures, ABORT conditions
GREEN='\033[92m'    # Success, completion, validation passed
YELLOW='\033[93m'   # Warnings, manual review needed, fallback attempts
BLUE='\033[94m'     # Info, progress steps
CYAN='\033[96m'     # File paths, note titles, metadata
MAGENTA='\033[95m'  # Domain, category, video info, source type detection

# Styles
BOLD='\033[1m'      # Emphasis
DIM='\033[2m'       # Secondary information
RESET='\033[0m'     # Reset formatting
```

## Usage Patterns

### Progress Indicators

```bash
# Step progress with bold blue
echo -e "${BLUE}${BOLD}[1/6] Validating input...${RESET}"
echo -e "${BLUE}${BOLD}[2/6] Processing data...${RESET}"
```

### Success Messages

```bash
# Green checkmark for success
echo -e "${GREEN}✓${RESET} File saved successfully"
echo -e "${GREEN}  ✓${RESET} 8 headings preserved"
echo -e "${GREEN}  ✓${RESET} 12 code blocks converted"
```

### Error Messages

```bash
# Red X for errors
echo -e "${RED}✗ Error:${RESET} Failed to fetch URL"
echo -e "${RED}${BOLD}✗ ABORT:${RESET} Critical validation failed"
```

### Warnings

```bash
# Yellow warning symbol
echo -e "${YELLOW}  ⚠${RESET} Manual review needed"
echo -e "${YELLOW}  ⚠${RESET} Potential link: ${CYAN}[[Note]]${RESET} ${DIM}(review)${RESET}"
```

### File Paths and Metadata

```bash
# Cyan for paths and metadata
echo -e "${CYAN}  → ${DIM}~/.claude/prompts/file.md${RESET}"
echo -e "${CYAN}  Channel:${RESET} ${DIM}Tech Education Pro${RESET}"
echo -e "${CYAN}  Duration:${RESET} ${DIM}24m 35s${RESET}"
```

### Domain/Category Information

```bash
# Magenta for domains and categories
echo -e "${MAGENTA}📁${RESET} Domain: ${BOLD}web/${RESET}"
echo -e "${MAGENTA}📹${RESET} ${BOLD}Understanding React Hooks${RESET}"
echo -e "${MAGENTA}🔍${RESET} Source type: ${BOLD}Web URL${RESET}"
```

### Summary/Details (Dimmed)

```bash
# Dim for secondary details
echo -e "${DIM}  Total: 3 backlinks${RESET}"
echo -e "${DIM}  Size: 45 KB | Lines: 892 | Words: 5,234${RESET}"
echo -e "${DIM}  Backlinks: 3 | MOCs updated: 2 | Source deleted: ✓${RESET}"
```

### Combined Patterns

```bash
# Domain detection
echo -e "${BLUE}${BOLD}[2/9] Analyzing source...${RESET}"
echo -e "${MAGENTA}📁${RESET} Domain: ${BOLD}web/${RESET}"
echo -e "${CYAN}  Concept:${RESET} ${DIM}React Server Components${RESET}"

# Link creation
echo -e "${BLUE}${BOLD}[6/9] Scanning for links...${RESET}"
echo -e "${GREEN}  ✓${RESET} Linked to ${CYAN}[[Web-React-Hooks]]${RESET} ${DIM}(related)${RESET}"
echo -e "${GREEN}  ✓${RESET} Linked to ${CYAN}[[Web-Next-JS-App-Router]]${RESET} ${DIM}(dependency)${RESET}"
echo -e "${YELLOW}  ⚠${RESET} Potential link: ${CYAN}[[CS-Client-Server-Model]]${RESET} ${DIM}(review)${RESET}"

# Final report
echo -e "${GREEN}${BOLD}✓ Integration complete${RESET}"
echo -e "${CYAN}  → web/Web-React-Server-Components.md${RESET}"
echo -e "${DIM}  Backlinks: 3 | MOCs updated: 2 | Source deleted: ✓${RESET}"
```

## Color Usage Guidelines

- **RED**: Use sparingly for actual errors or critical abort conditions
- **GREEN**: Success states, confirmations, completed tasks
- **YELLOW**: Warnings that need attention but aren't failures
- **BLUE**: Informational messages, progress indicators
- **CYAN**: File paths, URLs, note titles, technical identifiers
- **MAGENTA**: High-level categorization (domains, sources, types)
- **BOLD**: Emphasize important information within any color
- **DIM**: De-emphasize supplementary details
- **RESET**: Always reset formatting after colored text

## Common Symbols

- `✓` - Success checkmark
- `✗` - Error/failure X
- `⚠` - Warning triangle
- `→` - Direction/path indicator
- `📁` - Folder/domain
- `📹` - Video content
- `🔍` - Search/detection
