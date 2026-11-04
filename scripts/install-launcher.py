#!/usr/bin/env python3
"""Install the `vault-knowledge` launcher: the machine-local binding for the shared knowledge CLI.

Writes ~/.config/zkfy/knowledge.json (python, tool, vault) and links ~/.local/bin/vault-knowledge
to scripts/knowledge-launcher.py. Idempotent; --dry-run prints what would change; --uninstall
removes the binding and the link when the link is ours. The vault is always given explicitly.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TOOL = HERE / "knowledge.py"
LAUNCHER = HERE / "knowledge-launcher.py"
POLICY = "docs/knowledge/scope.json"


class InstallError(Exception):
    pass


def ours(link: Path) -> bool:
    return link.is_symlink() and Path(os.readlink(link)) == LAUNCHER


def install(vault: str, python: str, config: Path, link: Path, dry_run: bool) -> list[str]:
    root = Path(vault).expanduser().resolve(strict=True)
    if not (root / POLICY).is_file():
        raise InstallError(f"{root} has no {POLICY}; the vault must carry its scope policy")
    binding = {"python": str(Path(python).expanduser()), "tool": str(TOOL), "vault": str(root)}
    lines = []
    current = None
    if config.is_file():
        try:
            current = json.loads(config.read_text())
        except ValueError:
            current = None
    if current == binding:
        lines.append(f"config: unchanged {config}")
    else:
        lines.append(f"config: {'would write' if dry_run else 'written'} {config}")
        if not dry_run:
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n")
    if link.exists() or link.is_symlink():
        if not ours(link):
            raise InstallError(f"{link} exists and is not zkfy's launcher; move it away or pass --bin-dir")
        lines.append(f"link: unchanged {link}")
    else:
        lines.append(f"link: {'would write' if dry_run else 'written'} {link} -> {LAUNCHER}")
        if not dry_run:
            link.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(LAUNCHER, link)
    if not dry_run and not os.access(LAUNCHER, os.X_OK):
        LAUNCHER.chmod(LAUNCHER.stat().st_mode | 0o111)
        lines.append(f"launcher: made executable {LAUNCHER}")
    return lines


def uninstall(config: Path, link: Path, dry_run: bool) -> list[str]:
    lines = []
    if config.is_file():
        lines.append(f"config: {'would remove' if dry_run else 'removed'} {config}")
        if not dry_run:
            config.unlink()
    else:
        lines.append(f"config: absent {config}")
    if ours(link):
        lines.append(f"link: {'would remove' if dry_run else 'removed'} {link}")
        if not dry_run:
            link.unlink()
    elif link.exists() or link.is_symlink():
        lines.append(f"link: left alone, not zkfy's launcher {link}")
    else:
        lines.append(f"link: absent {link}")
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", help=f"Vault root holding {POLICY}; required unless --uninstall")
    parser.add_argument("--python", default=sys.executable, help="Python the launcher runs the CLI with (default: this one)")
    parser.add_argument("--config", default=os.environ.get("ZKFY_KNOWLEDGE_CONFIG", "~/.config/zkfy/knowledge.json"))
    parser.add_argument("--bin-dir", default="~/.local/bin", help="Where the vault-knowledge link goes")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change; write nothing")
    parser.add_argument("--uninstall", action="store_true", help="Remove the binding and the link")
    args = parser.parse_args(argv)
    config = Path(args.config).expanduser()
    link = Path(args.bin_dir).expanduser() / "vault-knowledge"
    try:
        if args.uninstall:
            lines = uninstall(config, link, args.dry_run)
        else:
            if not args.vault:
                parser.error("--vault is required (never inferred from the current directory)")
            lines = install(args.vault, args.python, config, link, args.dry_run)
    except (InstallError, OSError) as e:
        print(f"install-launcher: {e}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
