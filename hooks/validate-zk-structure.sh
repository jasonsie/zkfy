#!/bin/bash
# Validates Zettelkasten folder structure and redirects output if needed

# Read the tool use event from stdin
input=$(cat)

# Extract tool name and file_path from JSON
tool=$(echo "$input" | jq -r '.tool')
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Only validate for Write/Edit tools with markdown files
if [[ "$tool" != "Write" && "$tool" != "Edit" ]]; then
  echo "$input"
  exit 0
fi

# Skip if no file_path or not a markdown file
if [[ -z "$file_path" ]] || [[ ! "$file_path" =~ \.md$ ]]; then
  echo "$input"
  exit 0
fi

# Define required ZK folders
required_folders=("cs" "web" "ai" "principle" "devops" "math" "000.Index" "zz.original-source")

# Get current working directory
cwd=$(pwd)

# Check if all required folders exist
all_exist=true
for folder in "${required_folders[@]}"; do
  if [[ ! -d "$cwd/$folder" ]]; then
    all_exist=false
    break
  fi
done

# If structure is valid, pass through unchanged
if [[ "$all_exist" == "true" ]]; then
  echo "$input"
  exit 0
fi

# Structure invalid - redirect to ./output directory
echo "⚠️  ZK structure not detected in current directory" >&2
echo "📁 Required folders: ${required_folders[*]}" >&2
echo "🔀 Redirecting output to: $cwd/output/" >&2

# Ensure output directory exists in current working directory
mkdir -p "$cwd/output"

# Extract just the filename from the path
filename=$(basename "$file_path")

# Create new file path in ./output
new_path="$cwd/output/$filename"

# Replace file_path in the JSON input
modified_input=$(echo "$input" | jq --arg newpath "$new_path" '.tool_input.file_path = $newpath')

echo "$modified_input"
exit 0
