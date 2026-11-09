#!/usr/bin/env bash
# zkfy in a Claude Code cloud session: the environment's setup script.
#
# Paste this file as the setup script of a cloud environment (docs/cloud-session.md). It runs
# once, as root, on the Anthropic-hosted VM (Ubuntu 24.04, x86_64, Node 20/21/22, Python 3)
# before Claude Code starts, and the result is cached as a filesystem snapshot for about a
# week, so later sessions skip it. It must finish within about five minutes.
#
# It installs, under /opt/ai-plugins: zkfy and web-clipper at pinned release tags, the
# obsidian-clipper CLI built from a pinned upstream commit, Python Playwright with Chromium,
# yt-dlp and PyYAML. Claude Code loads the two plugins through the environment variable
# CLAUDE_CODE_PLUGIN_DIRS=/opt/ai-plugins/zkfy:/opt/ai-plugins/web-clipper; the vault's
# SessionStart hook runs cloud/session-start.sh, which binds the vault and shows the report.
#
# It never fails the session. Every step writes a line to /opt/ai-plugins/SETUP-REPORT.txt
# ("ok" or "FAIL"), and session-start.sh shows that report to the session, so a session on a
# broken environment says what is missing instead of running half a pipeline.
set -u

ZKFY_REF="${ZKFY_REF:-zkfy--v1.8.1}"
WEB_CLIPPER_REF="${WEB_CLIPPER_REF:-web-clipper--v2.2.1}"
CLIPPER_CLI_REF="${CLIPPER_CLI_REF:-6d56d61}" # obsidianmd/obsidian-clipper, at or after 5315b30
ROOT=/opt/ai-plugins
REPORT="$ROOT/SETUP-REPORT.txt"
LOG="$ROOT/setup.log"

mkdir -p "$ROOT"
: >"$REPORT"
: >"$LOG"
report() { printf '%-4s %-16s %s\n' "$1" "$2" "$3" | tee -a "$REPORT"; }

# clone <owner/repo> <ref> <dest>: a tag or branch by name, a commit by SHA.
clone() {
    local repo=$1 ref=$2 dest=$3
    rm -rf "$dest"
    if git clone --quiet --depth 1 --branch "$ref" "https://github.com/$repo" "$dest" >>"$LOG" 2>&1; then
        report ok "clone" "$repo@$ref"
    elif git clone --quiet --filter=blob:none "https://github.com/$repo" "$dest" >>"$LOG" 2>&1 &&
        git -C "$dest" checkout --quiet "$ref" >>"$LOG" 2>&1; then
        report ok "clone" "$repo@$ref"
    else
        report FAIL "clone" "$repo@$ref: $(tail -n 1 "$LOG")"
        return 1
    fi
}

# Node 21 or later for the clipper CLI; the VM puts 22 on PATH, 20/21/22 under /opt.
major=$(node --version 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/')
if [ -z "$major" ] || [ "$major" -lt 21 ]; then
    for d in /opt/node22/bin /opt/node21/bin; do
        [ -x "$d/node" ] && export PATH="$d:$PATH" && break
    done
fi
report "$([ "$(node --version 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/')" -ge 21 ] 2>/dev/null && echo ok || echo FAIL)" "node" "$(node --version 2>&1)"

clone jasonsie/zkfy "$ZKFY_REF" "$ROOT/zkfy" || true
clone jasonsie/web-clipper "$WEB_CLIPPER_REF" "$ROOT/web-clipper" || true
if clone obsidianmd/obsidian-clipper "$CLIPPER_CLI_REF" "$ROOT/obsidian-clipper"; then
    if (cd "$ROOT/obsidian-clipper" && npm ci --no-audit --no-fund --loglevel=error >>"$LOG" 2>&1 &&
        npm run build:cli >>"$LOG" 2>&1) && [ -s "$ROOT/obsidian-clipper/dist/cli.cjs" ]; then
        report ok "clipper-cli" "$ROOT/obsidian-clipper/dist/cli.cjs"
    else
        report FAIL "clipper-cli" "build: $(tail -n 1 "$LOG")"
    fi
fi

# Python packages into the interpreter the session uses (`python3`); Ubuntu 24.04 marks its
# system Python externally managed, so retry with the flag that allows it.
if python3 -m pip install --quiet playwright pyyaml yt-dlp >>"$LOG" 2>&1 ||
    python3 -m pip install --quiet --break-system-packages playwright pyyaml yt-dlp >>"$LOG" 2>&1; then
    report ok "pip" "playwright pyyaml yt-dlp"
else
    report FAIL "pip" "$(tail -n 1 "$LOG")"
fi
if python3 -m playwright install --with-deps chromium >>"$LOG" 2>&1; then
    report ok "chromium" "playwright"
else
    report FAIL "chromium" "$(tail -n 1 "$LOG")"
fi

# What every shell and the session-start hook export.
cat >"$ROOT/env.sh" <<EOF
export OBSIDIAN_CLIPPER_CLI=$ROOT/obsidian-clipper/dist/cli.cjs
export PATH=$ROOT/zkfy/bin:$ROOT/web-clipper/bin:\$PATH
EOF
cp "$ROOT/env.sh" /etc/profile.d/ai-plugins.sh 2>/dev/null || true
mkdir -p "$HOME/.config/web-clipper"
printf '{ "cli": "%s" }\n' "$ROOT/obsidian-clipper/dist/cli.cjs" >"$HOME/.config/web-clipper/config.json"
report ok "env" "$ROOT/env.sh, ~/.config/web-clipper/config.json"

printf '\nzkfy cloud setup, report at %s:\n' "$REPORT"
cat "$REPORT"
exit 0
