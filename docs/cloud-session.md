# Run zkfy in a Claude Code cloud session

From the phone: see an article, open the Claude app, tap **Code**, pick the vault
repository on `main`, type `note <url>`. A cloud session clips the page with
web-clipper, distills it with zkfy, commits on `main` and pushes. The Mac's
obsidian-git pulls `main`, and iCloud carries the note to the phone's Obsidian.

A cloud session installs no plugins: not the ones on your machine, not the ones a
repository turns on under `enabledPlugins`. So the environment brings zkfy and
web-clipper in itself, and the vault repository carries the hook and the rules
that make `note <url>` mean something. Decisions and status: jasonsie/zkfy#9.

## How it fits together

| Where | What | From |
|---|---|---|
| Cloud environment (claude.ai) | `cloud/setup.sh` clones zkfy, web-clipper and the obsidian-clipper CLI at pinned refs into `/opt/ai-plugins`, builds the CLI, installs Playwright Chromium, yt-dlp, PyYAML; `CLAUDE_CODE_PLUGIN_DIRS` loads the two plugins | this repo |
| Vault repository | `.claude/settings.json` runs `cloud/session-start.sh` at session start (report, binding, PATH); `AGENTS.md` defines `note <url>`; `.githooks/pre-commit` validates the staged catalog | the vault |
| GitHub `main` | the session pushes; the Mac pulls (obsidian-git, every 30 min while Obsidian is open); iCloud syncs the vault folder to the phone | — |

## One-time setup

### 1. The cloud environment

At [claude.ai/code](https://claude.ai/code), open the environment selector under the
message box and add an environment, for example **CS vault**:

- **Network access**: Full. The Trusted list holds package registries and GitHub only;
  article hosts, image CDNs and YouTube fail with `403 host_not_allowed` without it.
- **Environment variables**:

  ```text
  CLAUDE_CODE_PLUGIN_DIRS=/opt/ai-plugins/zkfy:/opt/ai-plugins/web-clipper
  ```

  Add `ZKFY_CLOUD_LINK_SKILLS=1` only if the verification below shows the plugins did
  not load through the variable (see Fallbacks).
- **Setup script**: the text of `cloud/setup.sh` from the release you want (**Choose
  file**, or paste). The refs at its top (`ZKFY_REF`, `WEB_CLIPPER_REF`,
  `CLIPPER_CLI_REF`) are the pins; the script never fails the session and writes
  `/opt/ai-plugins/SETUP-REPORT.txt` instead.

The script runs on the first session and its result is cached as a filesystem snapshot
for about seven days; it runs again when you change the script or the network setting.
Keep it under about five minutes, or the snapshot is not kept.

### 2. The vault repository

Commit to the vault, on `main`:

`.claude/settings.json`, a SessionStart hook and the permission rules the pipeline
needs (`.claude/settings.local.json` is not read in the cloud):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "[ -x /opt/ai-plugins/zkfy/cloud/session-start.sh ] && /opt/ai-plugins/zkfy/cloud/session-start.sh || true"
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(web-clipper:*)", "Bash(vault-knowledge:*)", "Bash(python3:*)", "Bash(yt-dlp:*)",
      "Bash(git add:*)", "Bash(git commit:*)", "Bash(git push origin HEAD:main)",
      "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)",
      "Skill(zkfy:source-to-zk)", "Skill(web-clipper:web-clipper)"
    ]
  }
}
```

On a Mac the hook finds no `/opt/ai-plugins` and does nothing.

`AGENTS.md`, the contract of a cloud session:

```markdown
## Cloud sessions

A Claude Code cloud session on this repository has `/opt/ai-plugins` and runs zkfy's
`cloud/session-start.sh` at start; otherwise nothing in this section applies.

- `note <url>` means: run the `source-to-zk` skill on that URL. A bare URL is not a command.
- Decide alone: pick the most specific domain, apply only the cross-pollination links you
  are confident about, skip the questions the skill would ask on a Mac, and state every
  such choice in the commit message.
- This is the one exception to "no commits or pushes": commit the files the pipeline
  produced (the clip in `raw/` with its assets, the new note, the notes it cross-linked,
  the catalog the commit gate stages) on `main`, with the choices in the message, then
  `git push origin HEAD:main`. Never touch `.obsidian/`; never force-push.
- If the clipper exits 2 (bot wall, paywall, login), or the setup report shows a FAIL
  line, stop and report; commit nothing.
```

`.githooks/pre-commit`: the knowledge gate must accept the 1.7 binding (`python` and
`vault`, no `tool`) by finding `vault-knowledge` on PATH. The CS vault's hook does so
since the cloud-session change; a 1.6-era hook refuses the commit with "invalid tool
binding".

### 3. Verify

Start a cloud session on the vault repository, `main`, in the new environment, and
paste:

```text
Verification for jasonsie/zkfy#9. Commit and push nothing. Report, as a table:
1. The contents of /opt/ai-plugins/SETUP-REPORT.txt.
2. Which zkfy skills (source-to-zk, clip-to-zk, zk-note, query) and whether the
   web-clipper skill are available to you in this session, and whether
   `vault-knowledge --help` and `web-clipper --help` run.
3. `env | grep -E 'CLAUDE_CODE_PLUGIN_DIRS|ZKFY_CLOUD|OBSIDIAN_CLIPPER_CLI'`.
4. `web-clipper https://en.wikipedia.org/wiki/Zettelkasten --vault . --json`: the JSON
   summary and the first 20 lines of the clip.
5. `vault-knowledge status`.
Then remove what the clip wrote (`git checkout -- . && git clean -fd raw/`) and show
that `git status` is clean.
```

| Answer | Meaning |
|---|---|
| Report all `ok` | the environment is complete |
| `FAIL clone` | the GitHub proxy refused the clone of an unattached repository; see Fallbacks |
| Skills missing although the clones are `ok` | `CLAUDE_CODE_PLUGIN_DIRS` did not take effect; set `ZKFY_CLOUD_LINK_SKILLS=1` on the environment |
| `FAIL chromium` or the clip fails | Playwright or its system libraries did not install; read `/opt/ai-plugins/setup.log` |

## Daily use

1. Claude app → **Code** → **New session** → repository `jasonsie/CS_Obsidian_vault`,
   branch `main`, environment **CS vault**.
2. Type `note https://…` and send. Pick **Auto** when the app asks for a permission mode.
3. The session reports the note's path and its choices and pushes to `main`. Nothing
   notifies the phone; open the session to read the result.
4. The Mac pulls within 30 minutes while Obsidian is open; the phone's Obsidian shows the
   note once iCloud has synced the folder.

## Limits

- A page behind a bot challenge, login or paywall stops with the clipper's exit 2. The
  recourse on a Mac (save the page from your browser, rerun with `--html`) has no
  equivalent from the phone.
- The phone sees the note only after the Mac has woken and pulled.
- Plain cloud sessions send no push notification.
- Full network access means a page written to steer the agent could make it send vault
  content elsewhere. The vault is private and the GitHub credential never enters the VM
  (the proxy swaps it), and zkfy allows no fetcher but the clipper; the agents still read
  the clipped text.
- Video URLs use yt-dlp subtitles only, strictly: no transcript, no note.
- The pipeline needs the whole vault: the clone must carry `docs/knowledge/scope.json`,
  the domain folders, `000.Index/` and the tracked catalog (`.claude/index.md`,
  `.claude/index/`, `.claude/lint-baseline.json`).

## Fallbacks

- **Plugins not loaded through the variable**: set `ZKFY_CLOUD_LINK_SKILLS=1` on the
  environment. `session-start.sh` then links every skill and agent of both plugins into
  the vault's `.claude/skills/` and `.claude/agents/`, which a cloud session does read,
  and excludes them from git. Skill text names plugin files relative to the skill folder,
  so the links resolve.
- **Clones refused**: the GitHub proxy serves only repositories attached to the session and
  refuses archives of others "even a public one". If plain clones fail too, the way in
  is a registry on the Trusted list: publish each release as an npm tarball and have
  `setup.sh` install from npm. Not built yet; copying the plugins into the vault is not
  an option (shared tooling lives here).

## Updating

Bump the refs at the top of the environment's setup script (`ZKFY_REF` to the new tag,
`WEB_CLIPPER_REF`, `CLIPPER_CLI_REF`). The snapshot rebuilds on the next new session.
Re-run the verification prompt after a bump.
