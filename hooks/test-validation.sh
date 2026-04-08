#!/bin/bash
# Test script for ZK structure validation hook

GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
CYAN='\033[96m'
RESET='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BLUE}  ZK Structure Validation Hook Test${RESET}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"

# Test 1: Invalid structure (current directory)
echo -e "${YELLOW}Test 1: Invalid ZK Structure${RESET}"
echo -e "${CYAN}Current directory:${RESET} $(pwd)"
echo -e "${CYAN}Folders present:${RESET}"
ls -d */ 2>/dev/null || echo "  (none)"
echo ""

# Create test input
cat > /tmp/test-input-1.json << 'EOF'
{
  "tool": "Write",
  "tool_input": {
    "file_path": "web/Web-Test-Note.md",
    "content": "# Test"
  }
}
EOF

echo -e "${CYAN}Input:${RESET}"
cat /tmp/test-input-1.json | jq '.'
echo ""

echo -e "${CYAN}Hook output:${RESET}"
result=$(cat /tmp/test-input-1.json | ./validate-zk-structure.sh 2>&1)
echo "$result"
echo ""

# Verify redirection
redirected_path=$(echo "$result" | grep -v "^⚠️" | grep -v "^📁" | grep -v "^🔀" | jq -r '.tool_input.file_path' 2>/dev/null)
if [[ "$redirected_path" == *"/output/"* ]]; then
  echo -e "${GREEN}✅ PASS: Path redirected to output directory${RESET}"
else
  echo -e "\033[91m❌ FAIL: Path was not redirected${RESET}"
fi

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"

# Test 2: Valid structure (simulated)
echo -e "${YELLOW}Test 2: Valid ZK Structure (Simulated)${RESET}"

# Create temporary ZK structure
temp_dir=$(mktemp -d)
cd "$temp_dir"
mkdir -p cs web ai principle devops math 000.Index row

echo -e "${CYAN}Test directory:${RESET} $temp_dir"
echo -e "${CYAN}Folders present:${RESET}"
ls -d */
echo ""

# Create test input
cat > /tmp/test-input-2.json << 'EOF'
{
  "tool": "Write",
  "tool_input": {
    "file_path": "web/Web-Test-Note.md",
    "content": "# Test"
  }
}
EOF

echo -e "${CYAN}Input:${RESET}"
cat /tmp/test-input-2.json | jq '.'
echo ""

echo -e "${CYAN}Hook output:${RESET}"
result=$(cat /tmp/test-input-2.json | /Users/jason/Developer/y-pj/ai/plugin/zkfy/hooks/validate-zk-structure.sh 2>&1)
echo "$result"
echo ""

# Verify no redirection
output_path=$(echo "$result" | jq -r '.tool_input.file_path' 2>/dev/null)
if [[ "$output_path" == "web/Web-Test-Note.md" ]]; then
  echo -e "${GREEN}✅ PASS: Path unchanged (valid structure)${RESET}"
else
  echo -e "\033[91m❌ FAIL: Path was modified unexpectedly${RESET}"
fi

# Cleanup
cd - > /dev/null
rm -rf "$temp_dir"

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}Testing complete!${RESET}\n"
