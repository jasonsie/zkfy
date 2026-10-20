---
name: vault-index
description: Deterministically rebuild or check the scoped vault catalog, bounded shards, content-fingerprint manifest, and structural health report. Explicit maintenance only; never run during a read-only query. Supports full or append requests through one shared generator.
---

# Vault Index — Deterministic Maintenance

Input: `[--full | --append <note-path> | --check] [--vault PATH]`.

For the configured canonical vault:

```bash
~/.local/bin/vault-knowledge build
~/.local/bin/vault-knowledge build --check
```

For an explicitly chosen other vault:

```bash
python3 -B <zkfy-root>/scripts/knowledge.py --vault "<explicit vault>" build [--check]
```

Resolve `<zkfy-root>` two levels above this skill, never from a hardcoded cache version. Python 3.10+ and `scripts/requirements-knowledge.txt` are required.

- Both full and append requests currently run the same complete deterministic rebuild. This deliberately handles removed/renamed notes, changed aliases, and deleted links correctly before optimizing incrementally.
- `--check` is read-only: exits 1 on drift, 0 when current, 2 on errors.
- Require `docs/knowledge/scope.json`. Missing/invalid policy stops maintenance; do not guess domains or run an unrestricted scanner.
- The generator alone owns `.claude/index.md`, `.claude/index/`, and `.claude/QUALITY.md`. Never hand-edit or use an LLM to write catalog entries.
- No timestamps or Git dates enter committed outputs. Identical content and policy produce identical bytes, including in shallow clones.
- Health reports describe structural defects, not truth. No source-backlog inventory, semantic auto-fix, authored-note changes, MOC changes, log updates, Git staging, commits, or pushes occur here.
- Rebuilding is explicit maintenance after authorized note changes. A query must use live scoped fallback instead of invoking this skill.

Baseline initialization and Git hook activation are separately reviewed operations; see the target vault's `docs/knowledge/maintenance.md`.
