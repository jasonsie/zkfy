#!/usr/bin/env python3
"""The mechanical steps of the note-update skill: one eligible note, edited in the primary checkout,
carried through a linked worktree and landed on main.

  resolve NOTE                       the eligible note NOTE names (an exact path, else a basename, else an
                                     alias) and its profile; several matches list the candidates
  state NOTE [--instruction-given]   the case: A (an instruction), B (the note has uncommitted edits in
                                     the primary checkout), C (neither); no other file's status counts
  names NOTE                         the branch docs/update-<stem-kebab>, the commit scope, a subject stub
  plan NOTE                          what the plan gate shows: the profile, size-budget warnings, the
                                     inbound links (line, text, the heading each targets) and the links
                                     the primary copy's uncommitted edit already breaks
  carry NOTE WORKTREE                copy the primary copy into a linked worktree at the same path and
                                     check the two are byte-identical
  edit-check NOTE WORKTREE [--sha256 S]
                                     the worktree's copy against the edit's base (the carried copy, sha256
                                     S, or the worktree's HEAD): each section same, changed, added or
                                     removed; frontmatter keys; Src and Link; a clip body; the budget
                                     after. Facts only: `problems` lists rule breaks
  stage-carried NOTE WORKTREE --sha256 S
                                     stage the primary copy, as carried (sha256 S), as the worktree's
                                     index entry, so the hand edit commits before the agent's edit
  land-check NOTE                    after the merge: fast-forward the primary checkout to origin's base,
                                     only when the primary copy is clean, byte-identical to the merged
                                     blob, or byte-identical to the note at a commit the merge brought
                                     (then it is updated to the merged blob); otherwise refuse and print
                                     the difference

--vault is the primary checkout, never inferred from the current folder. Each subcommand prints one
JSON object on stdout; a stop also prints its reason on stderr (a diverged land-check, the difference
too). The primary copy is read, never stashed or reset: land-check stages the merged blob so the
fast-forward keeps the file, and writes the file once, only to bring a superseded copy to the merged
blob, after checking it is still what merged.

Exit codes: 0 ok · 1 usage, git or environment · 2 refused, nothing changed ("error" says why) ·
3 resolve found several notes ("candidates"; pick one by its path).
Python 3.9+: the standard library and zkfy's knowledge.py (scope policy, eligible notes, search).
"""
from __future__ import annotations

import argparse
from collections import Counter
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
from urllib.parse import unquote


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

    def __init__(self, reason, data=None, code=2):
        super().__init__(reason)
        self.reason, self.data, self.code = reason, data or {}, code


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


def write_atomic(path, data, mode_from=None):
    """Replace the file at `path` with `data` in one rename, keeping its permissions."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".note-update-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        shutil.copymode(mode_from or path, tmp)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


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


def vault_relative(root, value):
    """`value` as a vault-relative POSIX path: given relative, or absolute inside the vault."""
    raw = os.path.expanduser(value)
    if os.path.isabs(raw):
        p = Path(os.path.abspath(raw))
        try:
            return (p.parent.resolve() / p.name).relative_to(root).as_posix()
        except ValueError:
            raise Refused(f"{value} is outside the vault") from None
    try:
        return K.relative(value)
    except K.KnowledgeError as e:
        raise Refused(f"{value}: {e}") from None


def refusal(scope, name):
    """Why note-update never edits the vault-relative path `name`; None for an eligible note path."""
    parts = PurePosixPath(name).parts
    top = parts[0].casefold() if parts else ""
    if parts[:2] == (".claude", "worktrees"):
        rest = "/".join(parts[3:])
        return (f"{name} is a copy under the agents' worktree folder, not the vault's note"
                + (f"; name the vault's own, {rest}" if rest else ""))
    if K.owned_path(name):
        return f"{name} is a generated catalog; vault-knowledge build writes it"
    if top == ".obsidian":
        return f"{name} is Obsidian's settings, not a note"
    if top == "raw":
        return f"{name} is under raw/, which holds sources, not notes"
    if top == "docs":
        return f"{name} is under docs/, the vault's own documentation"
    if not scope.eligible(name):
        return f"{name} is outside the vault's scope policy"
    return None


def note_path(root, scope, value):
    """The eligible note path `value` spells, `.md` optional, or a refusal with its reason."""
    name = vault_relative(root, value)
    why = refusal(scope, name)
    if why and not name.endswith(".md") and not refusal(scope, name + ".md"):
        name, why = name + ".md", None
    if why:
        raise Refused(why)
    try:
        K.safe_path(root, name)
    except K.KnowledgeError as e:
        raise Refused(f"{name}: {e}") from None
    return name


def note_of(root, value):
    """The eligible note at the exact path `value` (vault-relative, or absolute inside the vault)."""
    scope = K.Snapshot(root).scope
    name = note_path(root, scope, value)
    if not K.safe_path(root, name).is_file():
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


def index_entry(root, note):
    """[mode, blob id, stage] of `note` in the index of the checkout at `root`, [] when untracked."""
    return git(root, "ls-files", "--stage", "-z", "--", note).stdout.split(b"\t", 1)[0].decode().split()


def profile_of(scope, note):
    return "map" if scope.is_map(note.path) else str(note.meta.get("Mode", "legacy"))


PREAMBLE = "(preamble)"  # the title of the text before a note's first heading


def sections(note):
    """The body split at headings of level 1-3, fence-aware: [(title, [(number, line)])], heading line
    first; the PREAMBLE section is left out when blank."""
    raw = dict(note.lines)
    titles = {n: h for n, h in note.headings if re.match(r"#{1,3}\s", raw.get(n, ""))}
    found, title, lines = [], PREAMBLE, []
    for number, line in note.lines:
        if number in titles:
            found.append((title, lines))
            title, lines = titles[number], []
        lines.append((number, line))
    found.append((title, lines))
    return [(t, ls) for t, ls in found if t != PREAMBLE or any(x.strip() for _, x in ls)]


CJK = re.compile(r"[\u4e00-\u9fff]")
# vault-lint Check 11's reserved headings; the scope's thesis summaries join them (knowledge.py's default).
RESERVED = {"definition", "mental model", "why it matters", "boundary", "code", "links", "執行摘要", "附錄", "appendix"}
SUMMARIES = ["執行摘要", "Executive Summary", "Abstract"]


def budget_count(lines):
    """vault-lint Check 9's count: CJK ideographs plus whitespace tokens holding an ASCII letter, over
    the lines outside fenced code (inline code, which K.prose_lines drops, is left out too)."""
    text = "\n".join(line for _, line in K.prose_lines(lines))
    return len(CJK.findall(text)) + sum(bool(re.search(r"[A-Za-z]", w)) for w in text.split())


def budget(note, scope):
    """The body budget of the note's profile (CLAUDE.md, ADR-0002 D5): warnings only, never a stop. A
    note with no Mode counts as atom, as vault-lint's Check 9 does."""
    parts = [(title, lines[1:] if title != PREAMBLE else lines) for title, lines in sections(note)]
    profile = profile_of(scope, note)
    if profile in ("atom", "legacy"):
        count = sum(budget_count(lines) for title, lines in parts
                    if title.casefold() not in ("mental model", "links"))
        return {"rule": "atom", "count": count, "limit": 500,
                "warnings": [f"atom body: {count} over the 500 ceiling"] if count > 500 else []}
    if profile == "thesis":
        skip = RESERVED | {s.casefold() for s in scope.config.get("thesis_summaries", SUMMARIES)} | {PREAMBLE}
        themes = [{"heading": title, "count": budget_count(lines)} for title, lines in parts
                  if title.casefold() not in skip]
        return {"rule": "thesis", "themes": themes, "range": [200, 1500],
                "warnings": [f"theme {t['heading']!r}: {t['count']}, outside 200-1500" for t in themes
                             if not 200 <= t["count"] <= 1500]}
    return {"rule": None, "warnings": []}


# --- subcommands -----------------------------------------------------------------------------------

def name_key(text):
    """A name as the user may type it: case, spaces, underscores and hyphens do not count."""
    return re.sub(r"[\s_-]+", "-", text.strip().casefold())


def cmd_resolve(root, args):
    corpus = K.Corpus(K.Snapshot(root))  # the eligible notes, read once; nothing outside scope is seen
    value = args.note.strip()

    def match(path, how):
        return {"note": path, "profile": profile_of(corpus.scope, corpus.notes[path]), "matched_by": how}

    def no_match():
        hits = K.search(corpus, value, 5)
        return Refused(f"no eligible note matches {value!r}; note-update never creates one",
                       {"suggestions": [{k: v for k, v in match(h["path"], "search").items() if k != "matched_by"}
                                        for h in hits]})

    if re.search(r"[/\\]", value) or value.startswith((".", "~")):
        name = note_path(root, corpus.scope, value)
        if name in corpus.notes:
            return match(name, "path")
        raise no_match()
    stem = value[:-3] if value.casefold().endswith(".md") else value
    if stem + ".md" in corpus.notes:  # a note at the vault's root (the policy's include_files)
        return match(stem + ".md", "path")
    key = name_key(stem)
    for how, names in (("basename", lambda p, n: [PurePosixPath(p).stem]),
                       ("alias", lambda p, n: n.values("Aliases"))):
        hits = sorted(p for p, n in corpus.notes.items() if any(name_key(x) == key for x in names(p, n)))
        if len(hits) == 1:
            return match(hits[0], how)
        if hits:
            raise Refused(f"{len(hits)} notes match {value!r} by {how}; pick one by its path",
                          {"candidates": [match(p, how) for p in hits]}, code=3)
    raise no_match()


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


def inbound_sites(corpus, note):
    """Each link in another eligible note that resolves to `note`: (from, (line, target, text), status)."""
    for path, other in sorted(corpus.notes.items()):
        if path == note:
            continue
        for site in other.sites:
            status, hits = corpus.resolve(site[1], path)
            if hits == [note] and status in ("ok", "anchor"):
                yield path, site, status


def anchor_breaks(corpus, note):
    """{(from, link)} of the corpus's own link-anchor issues that point into `note`: what the ratchet sees."""
    return {(i["path"], i["detail"]) for i in corpus.issues()
            if i["rule"] == "link-anchor" and corpus.resolve(i["detail"], i["path"])[1] == [note]}


def cmd_plan(root, args):
    note, _ = note_of(root, args.note)
    corpus = K.Corpus(K.Snapshot(root))  # the link graph the ratchet hook validates
    inbound = [{"from": path, "line": line, "text": dict(corpus.notes[path].lines)[line].strip(),
                "map": corpus.scope.is_map(path), "heading": unquote(link).partition("#")[2] or None,
                "broken": status == "anchor"} for path, (line, link, _), status in inbound_sites(corpus, note)]
    edited = sorted(anchor_breaks(corpus, note) - anchor_breaks(K.Corpus(K.Snapshot(root, "head")), note))
    target = corpus.notes[note]
    return {"note": note, "profile": profile_of(corpus.scope, target), "budget": budget(target, corpus.scope),
            "inbound": inbound, "broken_by_edit": [{"from": path, "link": link} for path, link in edited]}


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
        write_atomic(target, data, mode_from=source)
        carried = True
    copy = target.read_bytes()
    result = {"note": note, "worktree": str(tree), "carried": carried, "identical": copy == data,
              "sha256": sha256(data)}
    if copy != data:
        raise Refused(f"the worktree's copy of {note} is not byte-identical to the primary copy", result)
    return result


def frontmatter_block(data):
    lines = data.decode("utf-8-sig").splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            return "".join(lines[:end + 1])
    return ""


def section_texts(note, data):
    """{(title, occurrence): the section's exact text}, in order."""
    raw = data.decode("utf-8-sig").splitlines(keepends=True)
    seen, texts = Counter(), {}
    for title, lines in sections(note):
        seen[title] += 1
        texts[(title, seen[title])] = "".join(raw[n - 1] for n, _ in lines)
    return texts


def carried_copy(root, note, sha):
    """The primary copy, still as carried (sha256 `sha`), or a refusal."""
    data = K.read_file(root, note)
    if sha256(data) != sha:
        raise Refused(f"{note} in the primary checkout changed since the carry, so the edit no longer builds on "
                      f"it; nothing was staged. Drop the worktree and rerun", {"sha256": sha256(data)})
    return data


def edit_base(root, tree, note, sha):
    """The edit's base: the carried copy (checked by its sha256), or the note at the worktree's HEAD."""
    return carried_copy(root, note, sha) if sha else git(tree, "show", f"HEAD:{note}").stdout


def cmd_edit_check(root, args):
    note, scope = note_of(root, args.note)
    tree = linked_worktree(root, args.worktree)
    # The edit's base: the carried copy, or the note as the worktree's HEAD has it; never the primary copy
    # as it is now, which may hold typing done after the run began.
    old_data = edit_base(root, tree, note, args.sha256)
    new_data = K.read_file(tree, note)
    old, new = K.Note.parse(note, old_data, scope), K.Note.parse(note, new_data, scope)
    before, after = list(old.meta), list(new.meta)
    keys = {"added": [k for k in after if k not in before], "removed": [k for k in before if k not in after],
            "reordered": [k for k in before if k in after] != [k for k in after if k in before]}
    provenance = [k for k in ("Src", "Link") if old.meta.get(k) != new.meta.get(k)]
    old_texts, new_texts = section_texts(old, old_data), section_texts(new, new_data)
    found = []
    for key, text in old_texts.items():
        status = "removed" if key not in new_texts else "same" if new_texts[key] == text else "changed"
        found.append({"heading": key[0], "status": status})
    found += [{"heading": key[0], "status": "added"} for key in new_texts if key not in old_texts]
    profile = {"before": profile_of(scope, old), "after": profile_of(scope, new)}
    # Mode is the profile: a conversion's new or changed Mode is reported once, as the profile change.
    problems = [f"frontmatter keys {how}: {', '.join(k for k in keys[how] if k != 'Mode')}"
                for how in ("added", "removed") if [k for k in keys[how] if k != "Mode"]]
    problems += ["frontmatter keys reordered"] if keys["reordered"] else []
    problems += [f"{k} changed; provenance stays as it is" for k in provenance]
    if profile["before"] != profile["after"]:
        problems.append(f"profile changed from {profile['before']} to {profile['after']}")
    if profile["before"] == "clip" and any(s["status"] != "same" and s["heading"].casefold() != "links"
                                           for s in found):
        problems.append("a clip note's body changed; it stays verbatim (ADR-0004)")
    return {"note": note, "worktree": str(tree),
            "frontmatter": "same" if frontmatter_block(old_data) == frontmatter_block(new_data) else "changed",
            "keys": keys, "provenance_changed": provenance, "sections": found, "profile": profile,
            "budget": budget(new, scope), "problems": problems}


def cmd_stage_carried(root, args):
    note, _ = note_of(root, args.note)
    tree = linked_worktree(root, args.worktree)
    carried_copy(root, note, args.sha256)
    oid = out(root, "hash-object", "-w", f"--path={note}", "--", str(K.safe_path(root, note)))
    entry = index_entry(tree, note)
    git(tree, "update-index", "--cacheinfo", entry[0] if entry else "100644", oid, note)
    return {"note": note, "worktree": str(tree), "staged": oid, "sha256": args.sha256}


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
    # A copy that matches the note at a commit the merge brought landed too, under later commits (the
    # hand edit's own commit in a case-A run on a dirty note): it is brought to the merged blob.
    landed = {blob(root, c, note) for c in out(root, "log", "--format=%H", f"{head}..{tip}", "--", note).split()}
    superseded = bool(change) and copy != merged and copy in landed
    result = {"note": note, "base": base, "from": head, "to": tip, "dirty": bool(change),
              "identical": copy == merged, "superseded": superseded}
    if change and copy != merged and not superseded:
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
        # Stage the merged blob: the fast-forward then keeps the file as it is instead of refusing.
        entry = index_entry(root, note)
        mode = out(root, "ls-tree", tip, "--", note).split()[0]
        git(root, "update-index", "--cacheinfo", mode, merged, note)
    if head != tip:
        p = git(root, "merge", "--ff-only", "--quiet", f"origin/{base}", check=False)
        if p.returncode:
            if entry:  # the index entry as the run found it, the user's own staging included
                git(root, "update-index", "--cacheinfo", entry[0], entry[1], note)
            why = (p.stderr or p.stdout).decode(errors="replace").strip().splitlines()
            raise GitError(f"git refused the fast-forward: {why[0] if why else p.returncode}; "
                           f"the primary copy is as it was")
    if superseded:
        path = K.safe_path(root, note)
        if file_blob(root, note) != copy:
            raise Refused(f"{note} changed during the land check; {base} is at the merge and your copy is "
                          f"left as it is", {**result, "fast_forwarded": head != tip})
        write_atomic(path, git(root, "cat-file", "--filters", f"{tip}:{note}").stdout)
    left = status_of(root, note)
    return {**result, "fast_forwarded": head != tip, "restored": bool(change) and not left, "status": left}


# --- the command line ------------------------------------------------------------------------------

COMMANDS = {"resolve": cmd_resolve, "state": cmd_state, "names": cmd_names, "plan": cmd_plan,
            "carry": cmd_carry, "edit-check": cmd_edit_check, "stage-carried": cmd_stage_carried,
            "land-check": cmd_land_check}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", required=True, help="the vault's primary checkout; never inferred from cwd")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("resolve").add_argument("note", help="a path, a filename without its folder, or an alias")
    for name in ("names", "plan", "land-check"):
        sub.add_parser(name).add_argument("note", help="the note's exact vault-relative path, as resolve gives it")
    s = sub.add_parser("state")
    s.add_argument("note")
    s.add_argument("--instruction-given", action="store_true", help="the user gave an instruction (case A)")
    c = sub.add_parser("carry")
    c.add_argument("note")
    c.add_argument("worktree", help="the linked worktree the note is carried into")
    check = sub.add_parser("edit-check")
    check.add_argument("note")
    check.add_argument("worktree", help="the linked worktree holding the edited copy")
    check.add_argument("--sha256", help="carry's sha256, when the edit builds on a carried copy")
    stage = sub.add_parser("stage-carried")
    stage.add_argument("note")
    stage.add_argument("worktree")
    stage.add_argument("--sha256", required=True, help="the sha256 carry reported")
    args = parser.parse_args(argv)
    try:
        root = primary(args.vault)
        code, result = 0, COMMANDS[args.command](root, args)
    except Refused as e:
        code, result = e.code, {**e.data, "error": e.reason}
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
