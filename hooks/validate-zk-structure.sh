#!/bin/bash
# PreToolUse guard for Zettelkasten notes. A configured vault (docs/knowledge/scope.json above
# the note) decides through scripts/knowledge-hook.py and is never redirected; elsewhere the
# legacy layout check sends a new note to ./output/ when the working directory is no vault.
# A note is told by what is written: frontmatter holding Type: and Categories:, the keys lint
# requires. Any other Markdown (a repo's docs, a skill, a PR body), every edit, every write over
# a file that exists, and every path outside the root stay where they are.
#
# Two input shapes on stdin, told apart by the toolCall key:
#   Claude Code, Codex and Pi's extension (extensions/zkfy.ts):
#     {tool_name: Write|Edit, cwd, tool_input: {file_path, content}}; the root is the payload's
#     cwd (the session's, so a git worktree resolves to itself), else the git work tree holding
#     the file, never the hook's own pwd. With neither, nothing is redirected.
#     Output: nothing to allow, else Claude Code's hookSpecificOutput (a deny, an updatedInput,
#     an additionalContext), which Codex shares and the Pi extension translates.
#   Antigravity (the root hooks.json):
#     {toolCall: {name, args: {TargetFile, CodeContent}}, workspacePaths}; the cwd is the plugin root, so the
#     first workspace stands in for the working directory.
#     Output: {decision: allow|deny, reason?, overwrite?}. Antigravity's PostToolUse returns
#     nothing to the agent, so the catalog reminder of signal-index-update.sh rides on the
#     allow decision here.

input=$(cat)
here=$(cd "$(dirname "$0")" && pwd)

if printf '%s' "$input" | jq -e '.toolCall' >/dev/null 2>&1; then
  cli=agy
  tool=$(printf '%s' "$input" | jq -r '.toolCall.name // empty')
  file_path=$(printf '%s' "$input" | jq -r '.toolCall.args.TargetFile // empty')
  workspace=$(printf '%s' "$input" | jq -r '.workspacePaths[0] // empty')
  edit_tools='^(write_to_file|replace_file_content|multi_replace_file_content)$'
else
  cli=claude
  tool=$(printf '%s' "$input" | jq -r '.tool_name // .tool // empty')
  file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
  workspace=$(printf '%s' "$input" | jq -r '.cwd // empty')
  edit_tools='^(Write|Edit)$'
fi

required_folders=("cs" "web" "ai" "principle" "devops" "math" "000.Index" "row")

writes_a_note() {  # whether the call writes a whole file whose frontmatter is a note's; an edit carries none
  printf '%s' "$input" | jq -e '
    (.toolCall.args.CodeContent // .tool_input.content // "") | tostring
    | split("\n") | map(rtrimstr("\r"))
    | if .[0] == "---" then .[1:] | .[:(index("---") // 0)] else [] end
    | any(startswith("Type:")) and any(startswith("Categories:"))' >/dev/null 2>&1
}

repo_root_of() {  # $1: an absolute path; the git work tree holding it, though the file or its folders may not exist yet
  local dir
  dir=$(dirname "$1")
  while [[ ! -d "$dir" && "$dir" != "/" ]]; do dir=$(dirname "$dir"); done
  git -C "$dir" rev-parse --show-toplevel 2>/dev/null
}

real_path() {  # $1: a path; where it really is, symlinks (macOS /tmp is /private/tmp) and .. resolved, though it may not exist yet
  python3 -B -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

allow() {  # $1: words for the agent, optional
  if [[ "$cli" == agy ]]; then
    jq -n -c --arg reason "${1:-}" '{decision: "allow"} + (if $reason == "" then {} else {reason: $reason} end)'
  elif [[ -n "${1:-}" ]]; then
    jq -n -c --arg text "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $text}}'
  fi
  exit 0
}

deny() {  # $1: the reason
  if [[ "$cli" == agy ]]; then
    jq -n -c --arg reason "$1" '{decision: "deny", reason: $reason}'
  else
    jq -n -c --arg reason "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
  fi
  exit 0
}

redirect() {  # $1: the new path
  local text="zkfy: no vault structure in $workspace (required folders: ${required_folders[*]}); the note goes to $1"
  if [[ "$cli" == agy ]]; then
    jq -n -c --arg path "$1" --arg reason "$text" '{decision: "allow", reason: $reason, overwrite: {TargetFile: $path}}'
  else
    printf '%s' "$input" | jq -c --arg path "$1" --arg text "$text" \
      '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "allow", updatedInput: (.tool_input | .file_path = $path), additionalContext: $text}}'
  fi
  exit 0
}

# Only notes being written or edited
[[ "$tool" =~ $edit_tools ]] || allow
[[ -n "$file_path" && "$file_path" =~ \.md$ ]] || allow

# A configured vault decides for itself: exit 0 with a deny or nothing; exit 3 means unconfigured.
guard=$(python3 -B "$here/../scripts/knowledge-hook.py" guard "$file_path" 2>/dev/null)
status=$?
if [[ $status -eq 0 ]]; then
  reason=$(printf '%s' "$guard" | jq -r '.hookSpecificOutput.permissionDecisionReason // empty' 2>/dev/null)
  [[ -n "$reason" ]] && deny "$reason"
  reminder=""
  if [[ "$cli" == agy ]]; then
    reminder=$(python3 -B "$here/../scripts/knowledge-hook.py" index "$file_path" 2>/dev/null | jq -r '.reminder // empty' 2>/dev/null)
  fi
  allow "$reminder"
elif [[ $status -ne 3 ]]; then
  echo 'zkfy: scoped hook runtime unavailable; structure check skipped.' >&2
  allow
fi

# Legacy vaults: the layout check on the working directory, for a note being written
if [[ -z "$workspace" && "$file_path" == /* ]]; then  # no cwd sent: the repo the file is in
  workspace=$(repo_root_of "$file_path")
fi
[[ -n "$workspace" && -d "$workspace" ]] || allow
# Never move what is already placed: an edit, a write over a file that exists, a path outside the root
[[ "$tool" =~ ^(Write|write_to_file)$ ]] || allow
[[ "$file_path" == /* ]] || file_path="$workspace/$file_path"  # relative to the session, not to this hook's pwd
[[ ! -e "$file_path" ]] || allow
[[ "$(real_path "$file_path")" == "$(real_path "$workspace")"/* ]] || allow
writes_a_note || allow
for folder in "${required_folders[@]}"; do
  if [[ ! -d "$workspace/$folder" ]]; then
    mkdir -p "$workspace/output"
    redirect "$workspace/output/$(basename "$file_path")"
  fi
done
allow
