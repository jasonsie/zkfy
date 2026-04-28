#!/usr/bin/env zsh
# Web Clipper — fetch a URL → raw/<slug>.md + raw/attachments/<slug>/
# Usage: clip.sh <url> [--no-attachments] [--out <path>]
# Self-contained: depends only on defuddle (npm) installed locally in this skill dir.
set -euo pipefail

# Project root = invocation CWD (user's vault/project root when run as a plugin).
# Captured BEFORE any cd so output paths land at the project root, not in skill dir.
PROJECT_ROOT="$PWD"

RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'; BLUE='\033[94m'
CYAN='\033[96m'; RESET='\033[0m'

die()  { echo -e "${RED}ERROR${RESET} $*" >&2; exit 1; }
info() { echo -e "${BLUE}[web-clipper]${RESET} $*"; }
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
warn() { echo -e "${YELLOW}WARN${RESET} $*" >&2; }

# ── Arg parsing ────────────────────────────────────────────────────────────
URL=""
NO_ATTACHMENTS=false
OUT_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-attachments) NO_ATTACHMENTS=true; shift ;;
    --out) OUT_PATH="$2"; shift 2 ;;
    http*) URL="$1"; shift ;;
    -h|--help)
      echo "Usage: clip.sh <url> [--no-attachments] [--out <path>]"
      exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -z "$URL" ]] && die "Usage: clip.sh <url> [--no-attachments] [--out <path>]"

# ── Preflight ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFUDDLE_BIN="$SKILL_DIR/node_modules/.bin/defuddle"

command -v node &>/dev/null || die "node not found on PATH"
command -v curl &>/dev/null || die "curl not found on PATH"

if [[ ! -x "$DEFUDDLE_BIN" ]]; then
  die "defuddle not installed. Run:\n  cd $SKILL_DIR && npm install"
fi

# ── Slug + output path ─────────────────────────────────────────────────────
slug=$(echo "$URL" | sed -E 's|https?://||; s|/$||; s|/|-|g; s|[^a-zA-Z0-9._-]||g' | cut -c1-80)
[[ -z "$OUT_PATH" ]] && OUT_PATH="$PROJECT_ROOT/raw/${slug}.md"
# Resolve relative --out against PROJECT_ROOT
[[ "$OUT_PATH" != /* ]] && OUT_PATH="$PROJECT_ROOT/$OUT_PATH"
mkdir -p "$(dirname "$OUT_PATH")"

# ── Clip via defuddle ──────────────────────────────────────────────────────
info "Clipping ${CYAN}${URL}${RESET}"

TMP_JSON=$(mktemp)
trap 'rm -f "$TMP_JSON"' EXIT

"$DEFUDDLE_BIN" parse "$URL" --markdown --json > "$TMP_JSON" \
  || die "defuddle failed for $URL"

# Parse with node — handles raw control chars in JSON that jq rejects.
# Each call strips U+0000-U+001F (except tab/LF/CR) before JSON.parse.
_jfield() {
  node -e "
    const fs = require('fs');
    const raw = fs.readFileSync(process.argv[1], 'utf8');
    const d = JSON.parse(raw.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, ''));
    process.stdout.write((d[process.argv[2]] || '').toString().replace(/\n/g, ' ').replace(/\r/g, ''));
  " "$TMP_JSON" "$1"
}

title=$(    _jfield title)
author=$(   _jfield author)
published=$(  _jfield published)
domain=$(   _jfield domain)
today=$(date +%Y-%m-%d)

content_md=$(node -e "
  const fs = require('fs');
  const raw = fs.readFileSync(process.argv[1], 'utf8');
  const d = JSON.parse(raw.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, ''));
  process.stdout.write(d.contentMarkdown || d.content || '');
" "$TMP_JSON")

# ── Compose Markdown file ──────────────────────────────────────────────────
title_escaped=$(printf '%s' "$title" | sed "s/'/''/g")

{
  echo "---"
  echo "Date: $today"
  echo "Type: literature"
  echo "Link: '$URL'"
  echo "Categories: []"
  echo "Sub-Categories: []"
  echo "Aliases: ['$title_escaped']"
  echo "tags: []"
  echo "Before: ''"
  echo "Next: ''"
  [[ -n "$author"    ]] && echo "Author: '$author'"
  [[ -n "$published" ]] && echo "Published: '$published'"
  [[ -n "$domain"    ]] && echo "Source: '$domain'"
  echo "---"
  echo
  [[ -n "$title" ]] && echo "# $title" && echo
  printf '%s\n' "$content_md"
} > "$OUT_PATH"

ok "Saved → ${CYAN}${OUT_PATH}${RESET}"

# ── Attachments ────────────────────────────────────────────────────────────
if [[ "$NO_ATTACHMENTS" == "true" ]]; then
  info "Skipping attachment download (--no-attachments)"
  exit 0
fi

ATT_DIR="$PROJECT_ROOT/raw/attachments/${slug}"
mkdir -p "$ATT_DIR"

info "Scanning for remote images..."

IMG_LIST=$(
  {
    grep -oE '!\[[^]]*\]\((https?://[^)]+)\)' "$OUT_PATH" | grep -oE 'https?://[^)]+' || true
    grep -oE 'src="(https?://[^"]+)"'         "$OUT_PATH" | grep -oE 'https?://[^"]+' || true
  } | sort -u
) || true

downloaded=0
failed=0

while IFS= read -r img_url; do
  [[ -z "$img_url" ]] && continue

  ext="${img_url##*.}"; ext="${ext%%\?*}"; ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
  [[ ${#ext} -gt 5 || "$ext" =~ [^a-z0-9] ]] && ext="bin"

  hash=$(echo -n "$img_url" | md5 2>/dev/null || echo -n "$img_url" | md5sum | cut -c1-32)
  local_name="${hash}.${ext}"
  local_path="${ATT_DIR}/${local_name}"

  if curl -fsSL --max-time 15 -o "$local_path" "$img_url" 2>/dev/null; then
    rel_path="attachments/${slug}/${local_name}"
    esc_url=$(printf '%s' "$img_url" | sed 's|[#&]|\\&|g')
    sed -i '' "s#${esc_url}#${rel_path}#g" "$OUT_PATH"
    downloaded=$((downloaded + 1))
  else
    warn "Failed to download: $img_url"
    rm -f "$local_path"
    failed=$((failed + 1))
  fi
done <<< "$IMG_LIST"

if [[ -z "$IMG_LIST" ]]; then
  info "No remote images found."
  rmdir "$ATT_DIR" 2>/dev/null || true
else
  ok "Attachments: ${downloaded} downloaded, ${failed} failed → ${CYAN}${ATT_DIR}/${RESET}"
fi

exit 0
