#!/usr/bin/env python3
"""The mechanical steps of the note-update skill: one eligible note, edited in the primary checkout,
carried through a linked worktree and landed on main.

  resolve NOTE                       the note's vault-relative path (exact path only) and its profile
  state NOTE [--instruction-given]   the case: A (an instruction), B (the note has uncommitted edits in
                                     the primary checkout), C (neither); no other file's status counts
  names NOTE                         the branch docs/update-<stem-kebab>, the commit scope, a subject stub
  carry NOTE WORKTREE                copy the primary copy into a linked worktree at the same path and
                                     check the two are byte-identical
  land-check NOTE                    after the merge: fast-forward the primary checkout to origin's base,
                                     only when the primary copy is clean or byte-identical to the merged
                                     blob; otherwise refuse and print the difference

--vault is the primary checkout, never inferred from the current folder. Each subcommand prints one
JSON object on stdout; a stop also prints its reason on stderr (a diverged land-check, the difference
too). The primary copy is only ever read: land-check stages an identical copy so the fast-forward
keeps it, and never stashes, resets or writes it.

Exit codes: 0 ok · 1 usage, git or environment · 2 refused, nothing changed ("error" says why).
Python 3.9+: the standard library and zkfy's knowledge.py (scope policy, note profile).
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile


def _load_knowledge():
    path = Path(__file__).with_name("knowledge.py")
    spec = importlib.util.spec_from_file_location("knowledge", path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


K = sys.modules.get("knowledge") or _load_knowledge()

WORK_NAME = re.compile(r"[a-z][a-z0-9]*/[a-z0-9][a-z0-9-]*")  # ai-dotfiles worktree-guard's <type>/<slug>


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


def blob(root, rev, note):
    """The blob id of `note` at `rev`, or '' when `rev` has no such file."""
    p = git(root, "rev-parse", "--verify", "--quiet", f"{rev}:{note}", check=False)
    return p.stdout.decode().strip() if p.returncode == 0 else ""


def file_blob(root, note):
    """The blob id git would store for the working copy of `note` (clean filters applied)."""
    return out(root, "hash-object", f"--path={note}", "--", str(K.safe_path(root, note)))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


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


def status_of(root, note):
    """The two-letter porcelain status of `note` in the primary checkout, '' when clean."""
    entries = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", note).stdout.split(b"\0")
    return entries[0][:2].decode() if entries and entries[0] else ""


def tracked_change(root, note):
    """Whether the primary copy of `note` has uncommitted edits; refuses what note-update does not carry."""
    status = status_of(root, note)
    if status == "??":
        raise Refused(f"{note} is not tracked; note-update changes notes already on the base branch")
    if "U" in status or status in ("AA", "DD"):
        raise Refused(f"{note} has merge conflicts; resolve them first")
    if "D" in status:
        raise Refused(f"{note} is deleted in the primary checkout")
    if status[:1] in ("A", "R", "C"):
        raise Refused(f"{note} is staged as {'added' if status[0] == 'A' else 'renamed or copied'}; "
                      f"note-update changes one existing note in place")
    if not blob(root, "HEAD", note):
        raise Refused(f"{note} is not on the checked-out branch")
    return status


# --- subcommands -----------------------------------------------------------------------------------

def cmd_resolve(root, args):
    note, scope = note_of(root, args.note)
    if scope.is_map(note):
        profile = "map"
    else:
        meta = K.Note.parse(note, K.read_file(root, note), scope).meta
        profile = str(meta.get("Mode", "legacy"))
    return {"note": note, "profile": profile}


def cmd_state(root, args):
    note, _ = note_of(root, args.note)
    change = tracked_change(root, note)
    case = "A" if args.instruction_given else ("B" if change else "C")
    return {"note": note, "case": case, "dirty": bool(change), "status": change,
            "instruction_given": args.instruction_given}


def cmd_names(root, args):
    note, _ = note_of(root, args.note)
    parts = PurePosixPath(note).parts
    slug = re.sub(r"[^a-z0-9]+", "-", parts[-1][:-3].lower()).strip("-")
    branch = f"docs/update-{slug}"
    if not slug or not WORK_NAME.fullmatch(branch):
        raise Refused(f"{note}: its filename gives no ASCII branch name; name the worktree by hand "
                      f"(ai-dotfiles worktree new docs/update-<slug>)")
    top = parts[0] if len(parts) > 1 else ""
    scope = re.sub(r"[^a-z0-9]+", "-", re.sub(r"^\d+\.", "", top).lower()).strip("-") or "vault"
    return {"note": note, "branch": branch, "scope": scope, "subject_stub": f"docs({scope}): "}


def linked_worktree(root, value):
    """`value` as a linked worktree of the primary checkout `root`."""
    try:
        path = Path(value).expanduser().resolve(strict=True)
        top = Path(out(path, "rev-parse", "--show-toplevel")).resolve()
        common = Path(out(path, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    except (OSError, GitError):
        raise Refused(f"{value} is not a git worktree") from None
    if top != path or path == root or common != (root / ".git").resolve():
        raise Refused(f"{value} is not a linked worktree of {root}")
    return path


def cmd_carry(root, args):
    note, _ = note_of(root, args.note)
    tree = linked_worktree(root, args.worktree)
    primary_head, tree_head = blob(root, "HEAD", note), blob(tree, "HEAD", note)
    if not primary_head:
        raise Refused(f"{note} is not on the primary checkout's branch")
    if primary_head != tree_head:
        raise Refused(f"{note} differs between the primary checkout's HEAD and the worktree's HEAD "
                      f"(it changed on the base branch since your copy's base); carrying would undo that change")
    source = K.safe_path(root, note)
    data = K.read_file(root, note)
    target = K.safe_path(tree, note)
    if target.is_file() and target.read_bytes() == data:
        carried = False
    else:
        if not target.is_file() or file_blob(tree, note) != tree_head:
            raise Refused(f"the worktree's copy of {note} has edits of its own; carry never overwrites them")
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".note-update-", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            shutil.copymode(source, tmp)
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        carried = True
    copy = target.read_bytes()
    result = {"note": note, "worktree": str(tree), "carried": carried, "identical": copy == data,
              "sha256": sha256(data)}
    if copy != data:
        raise Refused(f"the worktree's copy of {note} is not byte-identical to the primary copy", result)
    return result


def base_branch(root):
    """Origin's default branch, as `origin/HEAD` names it (or origin itself says)."""
    p = git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", check=False)
    name = p.stdout.decode().strip()
    if p.returncode == 0 and name.startswith("origin/"):
        return name[len("origin/"):]
    for line in out(root, "ls-remote", "--symref", "origin", "HEAD").splitlines():
        m = re.match(r"ref: refs/heads/(\S+)\tHEAD$", line)
        if m:
            return m[1]
    raise GitError("origin's default branch is unknown; run: git remote set-head origin --auto")


def paths_of(root, *args):
    return {os.fsdecode(x) for x in git(root, *args).stdout.split(b"\0") if x}


def cmd_land_check(root, args):
    note, _ = note_of(root, args.note)
    base = base_branch(root)
    git(root, "fetch", "--quiet", "origin", base)
    ref = git(root, "symbolic-ref", "--quiet", "HEAD", check=False).stdout.decode().strip()
    if ref != f"refs/heads/{base}":
        on = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else "a detached HEAD"
        raise Refused(f"the primary checkout is on {on}, not {base}")
    head, tip = out(root, "rev-parse", "HEAD"), out(root, "rev-parse", f"origin/{base}")
    merged = blob(root, f"origin/{base}", note)
    if not merged:
        raise Refused(f"origin/{base} has no {note}")
    change = tracked_change(root, note)
    copy = file_blob(root, note)
    result = {"note": note, "base": base, "from": head, "to": tip, "dirty": bool(change),
              "identical": copy == merged}
    if change and copy != merged:
        old = git(root, "cat-file", "blob", merged).stdout.decode("utf-8", "replace").splitlines(keepends=True)
        new = K.read_file(root, note).decode("utf-8", "replace").splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(old, new, f"origin/{base}:{note}", f"{note} (primary copy)"))
        raise Refused(f"{note} in the primary checkout differs from what merged; nothing was touched",
                      {**result, "difference": diff})
    if head != tip and git(root, "merge-base", "--is-ancestor", head, tip, check=False).returncode:
        raise Refused(f"{base} has commits origin/{base} lacks; nothing was touched")
    incoming = paths_of(root, "diff", "--name-only", "-z", "--no-renames", head, tip)
    uncommitted = (paths_of(root, "diff", "--name-only", "-z", "--no-renames")
                   | paths_of(root, "diff", "--name-only", "-z", "--no-renames", "--cached")
                   | paths_of(root, "ls-files", "-z", "--others", "--exclude-standard"))
    clash = sorted((incoming & uncommitted) - {note})
    if clash:
        raise Refused(f"uncommitted changes in {', '.join(clash[:3])} would block the fast-forward; "
                      f"nothing was touched", {**result, "clash": clash})
    entry = None
    if change and head != tip:
        # Stage the identical copy: the fast-forward then keeps it, and the file is never written.
        entry = git(root, "ls-files", "--stage", "-z", "--", note).stdout.split(b"\t", 1)[0].decode().split()
        git(root, "add", "--", note)
    if head != tip:
        p = git(root, "merge", "--ff-only", "--quiet", f"origin/{base}", check=False)
        if p.returncode:
            if entry:  # the index entry as the run found it, the user's own staging included
                git(root, "update-index", "--cacheinfo", entry[0], entry[1], note)
            why = (p.stderr or p.stdout).decode(errors="replace").strip().splitlines()
            raise GitError(f"git refused the fast-forward: {why[0] if why else p.returncode}; "
                           f"the primary copy is as it was")
    left = status_of(root, note)
    return {**result, "fast_forwarded": head != tip, "restored": bool(change) and not left, "status": left}


# --- the command line ------------------------------------------------------------------------------

COMMANDS = {"resolve": cmd_resolve, "state": cmd_state, "names": cmd_names, "carry": cmd_carry,
            "land-check": cmd_land_check}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", required=True, help="the vault's primary checkout; never inferred from cwd")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("resolve", "names", "land-check"):
        sub.add_parser(name).add_argument("note", help="the note's exact vault-relative path")
    s = sub.add_parser("state")
    s.add_argument("note")
    s.add_argument("--instruction-given", action="store_true", help="the user gave an instruction (case A)")
    c = sub.add_parser("carry")
    c.add_argument("note")
    c.add_argument("worktree", help="the linked worktree the note is carried into")
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
        if result.get("difference"):
            sys.stderr.write(result["difference"])
    return code


if __name__ == "__main__":
    sys.exit(main())
