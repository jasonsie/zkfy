#!/usr/bin/env python3
"""The mechanical steps of the note-update skill: one eligible note, edited in the primary checkout,
carried through a linked worktree and landed on main.

  resolve NOTE                       the note's vault-relative path (exact path only) and its profile

--vault is the primary checkout, never inferred from the current folder. Each subcommand prints one
JSON object on stdout; a stop also prints its reason on stderr.

Exit codes: 0 ok · 1 usage, git or environment · 2 refused, nothing changed ("error" says why).
Python 3.9+: the standard library and zkfy's knowledge.py (scope policy, note profile).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def _load_knowledge():
    path = Path(__file__).with_name("knowledge.py")
    spec = importlib.util.spec_from_file_location("knowledge", path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


K = sys.modules.get("knowledge") or _load_knowledge()

class Refused(Exception):
    """A step's rule said no; nothing was changed. `data` joins the JSON beside the reason."""

    def __init__(self, reason, data=None):
        super().__init__(reason)
        self.reason, self.data = reason, data or {}


class GitError(Exception):
    pass


def git(root, *args, data=None, check=True):
    p = subprocess.run(["git", "-C", str(root), "-c", "core.quotePath=false", "--literal-pathspecs", *args],
                       input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode:
        raise GitError(f"git {args[0]}: " + (p.stderr.decode(errors="replace").strip() or f"exit {p.returncode}"))
    return p


def out(root, *args):
    return git(root, *args).stdout.decode().strip()


# --- the vault and the note -----------------------------------------------------------------------

def primary(value):
    """The primary checkout: a git repo's main working tree holding the scope policy."""
    root = Path(value).expanduser().resolve(strict=True)
    if not (root / K.POLICY).is_file():
        raise K.KnowledgeError(f"{root} has no {K.POLICY}; --vault must be the vault root")
    top = Path(out(root, "rev-parse", "--show-toplevel")).resolve()
    common = Path(out(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if top != root or common != (root / ".git").resolve():
        raise K.KnowledgeError(f"{root} is not the primary checkout; pass the vault's main folder, not a worktree")
    return root


def note_of(root, value):
    """The vault-relative path of the eligible note `value` names: an exact vault-relative path, or an
    absolute path inside the vault. Anything else is refused."""
    raw = os.path.expanduser(value)
    if os.path.isabs(raw):
        p = Path(os.path.abspath(raw))
        try:
            value = (p.parent.resolve() / p.name).relative_to(root).as_posix()
        except ValueError:
            raise Refused(f"{value} is outside the vault") from None
    scope = K.Snapshot(root).scope
    try:
        name = K.relative(value)
        if not scope.eligible(name):
            raise Refused(f"{name} is not an eligible note: the vault's scope policy leaves it out")
        path = K.safe_path(root, name)
    except K.KnowledgeError as e:
        raise Refused(f"{value}: {e}") from None
    if not path.is_file():
        raise Refused(f"no note at {name}; note-update never creates one")
    return name, scope


# --- subcommands -----------------------------------------------------------------------------------

def cmd_resolve(root, args):
    note, scope = note_of(root, args.note)
    if scope.is_map(note):
        profile = "map"
    else:
        meta = K.Note.parse(note, K.read_file(root, note), scope).meta
        profile = str(meta.get("Mode", "legacy"))
    return {"note": note, "profile": profile}


# --- the command line ------------------------------------------------------------------------------

COMMANDS = {"resolve": cmd_resolve}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", required=True, help="the vault's primary checkout; never inferred from cwd")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("resolve",):
        sub.add_parser(name).add_argument("note", help="the note's exact vault-relative path")
    args = parser.parse_args(argv)
    try:
        root = primary(args.vault)
        code, result = 0, COMMANDS[args.command](root, args)
    except Refused as e:
        code, result = 2, {**e.data, "error": e.reason}
    except (K.KnowledgeError, GitError, OSError) as e:
        code, result = 1, {"error": str(e)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if code:
        print(f"note_update {args.command}: {result['error']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
