#!/usr/bin/env bash
# zkfy in a Claude Code cloud session: the vault's SessionStart hook.
#
# The vault repository's .claude/settings.json runs this script when a session starts or
# resumes (docs/cloud-session.md). On a machine without /opt/ai-plugins, such as the owner's
# Mac, it does nothing. In the cloud VM that cloud/setup.sh provisioned, it:
#   1. shows the setup report, so the session knows whether every step succeeded;
#   2. binds the knowledge CLI to this vault ($CLAUDE_PROJECT_DIR), writing
#      ~/.config/zkfy/knowledge.json the way `vault-knowledge bind` does on a Mac;
#   3. puts `vault-knowledge` and `web-clipper` on PATH through /usr/local/bin, in case the
#      plugins' bin/ folders were not added by the plugin loader;
#   4. with ZKFY_CLOUD_LINK_SKILLS=1 (the fallback when CLAUDE_CODE_PLUGIN_DIRS did not load
#      the plugins), links the plugins' skills and agents into the vault's .claude/ folder,
#      excluded from git, where a cloud session does read them.
# Its standard output becomes context for the session.
set -u

ROOT=/opt/ai-plugins
[ -d "$ROOT" ] || exit 0
VAULT="${CLAUDE_PROJECT_DIR:-$PWD}"

printf 'zkfy cloud session. Setup report (%s):\n' "$ROOT/SETUP-REPORT.txt"
if [ -s "$ROOT/SETUP-REPORT.txt" ]; then cat "$ROOT/SETUP-REPORT.txt"; else echo "FAIL setup           no report: cloud/setup.sh did not run"; fi
if grep -q '^FAIL' "$ROOT/SETUP-REPORT.txt" 2>/dev/null; then
    echo "A step failed: tell the user before running source-to-zk; see $ROOT/setup.log."
fi

# shellcheck disable=SC1091
[ -f "$ROOT/env.sh" ] && . "$ROOT/env.sh"
for cmd in zkfy/bin/vault-knowledge web-clipper/bin/web-clipper; do
    [ -x "$ROOT/$cmd" ] && ln -sfn "$ROOT/$cmd" "/usr/local/bin/$(basename "$cmd")"
done

if [ -f "$VAULT/docs/knowledge/scope.json" ] && [ -x "$ROOT/zkfy/bin/vault-knowledge" ]; then
    "$ROOT/zkfy/bin/vault-knowledge" bind --vault "$VAULT" 2>&1 | sed 's/^/vault-knowledge: /'
else
    echo "vault-knowledge: not bound ($VAULT has no docs/knowledge/scope.json, or zkfy is missing)."
fi

if [ "${ZKFY_CLOUD_LINK_SKILLS:-0}" = 1 ]; then
    exclude="$VAULT/.git/info/exclude"
    mkdir -p "$VAULT/.claude/skills" "$VAULT/.claude/agents"
    for skill in "$ROOT"/zkfy/skills/* "$ROOT"/web-clipper/skills/*; do
        [ -f "$skill/SKILL.md" ] || continue
        ln -sfn "$skill" "$VAULT/.claude/skills/$(basename "$skill")"
        echo ".claude/skills/$(basename "$skill")" >>"$exclude"
    done
    for agent in "$ROOT"/zkfy/agents/*.md; do
        [ -f "$agent" ] || continue
        ln -sfn "$agent" "$VAULT/.claude/agents/$(basename "$agent")"
        echo ".claude/agents/$(basename "$agent")" >>"$exclude"
    done
    sort -u -o "$exclude" "$exclude"
    echo "Skills and agents linked into .claude/ (ZKFY_CLOUD_LINK_SKILLS=1); never commit them."
fi

echo "Plugins: zkfy $(git -C "$ROOT/zkfy" describe --tags --always 2>/dev/null), web-clipper $(git -C "$ROOT/web-clipper" describe --tags --always 2>/dev/null). \`note <url>\` runs source-to-zk; the contract is in AGENTS.md, Cloud sessions."
exit 0
