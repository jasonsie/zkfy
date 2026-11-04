#!/usr/bin/env python3
"""Turn a captured source into a verbatim clip note (Mode: clip), per docs/ADR/0004-clip-mode-verbatim-notes.md.

The deterministic half of the clip-to-zk skill. The web-clipper plugin owns the clip's files (fetching,
image renames, embed rewrites); this script owns what the note means in the vault:

  find-link URL     stop early when a note in scope already records this source (exit 3)
  format            replace the capture's frontmatter with zkfy's, append ### Links, verify, lint, write
  release PATH...   delete text/file/video captures under raw/ once the clip note checks out

Exit codes: 0 ok · 1 usage, path or environment · 2 verification failed, nothing written ·
3 duplicate source or destination exists · 4 adapter refused the metadata · 6 note written, lint issues.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _load_knowledge():
    path = Path(__file__).with_name("knowledge.py")
    spec = importlib.util.spec_from_file_location("knowledge", path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


K = sys.modules.get("knowledge") or _load_knowledge()

EMBED = re.compile(r"!\[\[([^\]|\n]+)(\|[^\]\n]*)?\]\]")
# Every key a zk note can carry. A carried-over source key may not reuse one of these names (Q10b).
ZK_KEYS = ["Date", "Type", "Mode", "Categories", "Aliases", "tags", "Link", "Author", "Published", "Description",
           "Source-Tags", "Sub-Categories", "Before", "Next", "Src"]
ORDER = ["Date", "Type", "Mode", "Categories", "Aliases", "tags", "Link", "Author", "Published", "Description",
         "Source-Tags"]
# Source key -> clip-note role, one table per source kind. "alias" means Aliases[0].
TABLES = {
    "clip": {"source": "Link", "title": "alias", "author": "Author", "published": "Published",
             "description": "Description", "created": "Date", "tags": "tags"},
    "video": {"url": "Link", "source": "Link", "link": "Link", "title": "alias", "channel": "Author",
              "description": "Description", "tags": "tags"},
    "text": {"title": "alias", "tags": "tags"},
}
CLIP_INBOX_TAG = "row"  # the web-clipper template's marker tag; never carried into the vault


class AdaptError(Exception):
    pass


class VerifyError(Exception):
    pass


class Refused(Exception):
    pass


def _list(value):
    if value in (None, ""):
        return []
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def _dedupe(values):
    seen, out = set(), []
    for v in values:
        v = str(v).strip()
        if v and v.casefold() not in seen:
            seen.add(v.casefold())
            out.append(v)
    return out


def _authors(value):
    if isinstance(value, list):
        return _dedupe(value)
    links = re.findall(r"\[\[[^\]]+\]\]", str(value or ""))
    return links or _dedupe(_list(value))


def adapt(kind, source_meta, discover, today=None):
    """Map a source's own metadata plus Discover's classification to clip-note frontmatter.

    Pure: no file access. Discover owns classification (Categories, tags, extra Aliases);
    the source owns provenance (Link, Author, Published, Description). Returns (frontmatter, report).
    """
    if kind not in TABLES:
        raise AdaptError(f"unknown source kind {kind!r}")
    categories = discover.get("categories")
    if not isinstance(categories, list) or not categories:
        raise AdaptError("Discover returned no Categories")
    table, zk = TABLES[kind], {z.casefold() for z in ZK_KEYS}
    mapped, carried, report = {}, {}, []
    for key, value in (source_meta or {}).items():
        role = table.get(key)
        if role:
            mapped.setdefault(role, value)
        elif str(key).casefold() in zk:
            raise AdaptError(f"source key {key!r} collides with the zk key of the same name; rename it in the template")
        else:
            carried[key] = value
            report.append(f"carried over: {key}")

    out = {"Date": mapped.get("Date") or today or datetime.date.today(), "Type": "literature", "Mode": "clip",
           "Categories": list(categories),
           "Aliases": _dedupe([*_list(mapped.get("alias")), *_list(discover.get("aliases"))])}
    vocabulary = {t.casefold() for t in _list(discover.get("tag_vocabulary"))}
    source_tags = [t for t in _list(mapped.get("tags")) if t.casefold() != CLIP_INBOX_TAG]
    if CLIP_INBOX_TAG in [t.casefold() for t in _list(mapped.get("tags"))]:
        report.append(f"dropped tag: {CLIP_INBOX_TAG}")
    out["tags"] = _dedupe([*_list(discover.get("tags")), *(t for t in source_tags if t.casefold() in vocabulary)])
    if mapped.get("Link"):
        out["Link"] = str(mapped["Link"])
    if mapped.get("Author"):
        out["Author"] = _authors(mapped["Author"])
    for role, key in (("Published", "published"), ("Description", "description")):
        if mapped.get(role) not in (None, ""):
            out[role] = mapped[role]
        elif role in mapped:
            report.append(f"{key}: empty, omitted")
    extra = _dedupe(t for t in source_tags if t.casefold() not in vocabulary)
    if extra:
        out["Source-Tags"] = extra
    ordered = {key: out[key] for key in ORDER if key in out}
    ordered.update(carried)
    return ordered, report


def normalize_url(url):
    """The form two Links are compared in: no fragment, no utm_* parameters, no trailing slash."""
    parts = urlsplit(str(url).strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                       if not k.lower().startswith("utm_")])
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def split_frontmatter(text):
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                meta = K.yaml.load("\n".join(lines[1:i]), Loader=K.UniqueLoader) or {}
                if not isinstance(meta, dict):
                    raise VerifyError("frontmatter is not a mapping")
                return meta, "\n".join(lines[i + 1:])
        raise VerifyError("unclosed frontmatter")
    return {}, text


def masked(body):
    """The body with every prose image-embed target blanked, plus those targets (fences left alone)."""
    lines = body.split("\n")
    prose = {n for n, _ in K.prose_lines(enumerate(lines))}
    targets = []
    for n in sorted(prose):
        targets += [m[1].strip() for m in EMBED.finditer(lines[n])]
        lines[n] = EMBED.sub(lambda m: "![[\0" + (m[2] or "") + "]]", lines[n])
    return "\n".join(lines), targets


def verify(original_body, body, root, assets, kind):
    expected, _ = masked(original_body)
    actual, targets = masked(body)
    if expected != actual:
        raise VerifyError("body differs from the capture beyond image-embed targets")
    images = [t for t in targets if PurePosixPath(t.split("#", 1)[0]).suffix.lower() in K.ASSETS]
    if not images:
        return len(targets)
    if assets is None:
        if kind == "clip":
            raise VerifyError("clip has image embeds but no --assets folder to check them against")
        return len(targets)
    if not K.safe_path(root, assets).is_dir():
        raise VerifyError(f"{assets} is not a folder")
    try:
        manifest = json.loads(K.read_file(root, f"{assets}/assets.json"))
        sums = {PurePosixPath(e["file"]).name: e["sha256"] for e in manifest["assets"]}
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise VerifyError(f"cannot read {assets}/assets.json: {e}") from e
    for target in images:
        name = PurePosixPath(target).name
        if name not in sums:
            raise VerifyError(f"image {name} is not in {assets}/assets.json")
        try:
            data = K.read_file(root, f"{assets}/{name}")
        except (OSError, K.KnowledgeError) as e:
            raise VerifyError(f"image {name} missing from {assets}: {e}") from e
        if hashlib.sha256(data).hexdigest() != sums[name]:
            raise VerifyError(f"image {name} does not match its sha256 in assets.json")
    return len(targets)


def compose(meta, body, related):
    fm = K.yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=10 ** 6)
    tail = "" if body.endswith("\n") else "\n"
    links = "".join(f"- [[{str(r).strip().removeprefix('[[').removesuffix(']]')}]]\n" for r in related if str(r).strip())
    return f"---\n{fm}---\n{body}{tail}\n---\n### Links\n{links}"


def corpus_with(root, dest=None, data=None):
    """The scoped corpus as it would be with `data` written at `dest` (nothing touches disk)."""
    snap = K.Snapshot(root)
    if dest is not None:
        paths, read = snap.paths(), snap.read
        snap.paths = lambda: sorted({*paths, dest})
        snap.read = lambda name: data if name == dest else read(name)
    return K.Corpus(snap)


def link_matches(corpus, url, skip=()):
    want = normalize_url(url)
    return [{"path": p, "mode": n.meta.get("Mode", "legacy")} for p, n in sorted(corpus.notes.items())
            if p not in skip and n.meta.get("Link") and normalize_url(n.meta["Link"]) == want]


def check_dest(root, scope, dest, source):
    dest = K.relative(dest)
    if not dest.endswith(".md") or not K.FILENAME_RE.fullmatch(PurePosixPath(dest).stem):
        raise K.KnowledgeError(f"{dest}: filename must be ASCII Train-Case, e.g. Database-Postgres-Index-Internals.md")
    if not scope.eligible(dest):
        raise K.KnowledgeError(f"{dest} is outside the vault's scoped roots")
    path = K.safe_path(root, dest)
    if not path.parent.is_dir():
        raise K.KnowledgeError(f"{PurePosixPath(dest).parent} does not exist; clip-to-zk never creates folders")
    if path.exists() and dest != source:
        raise Refused(f"{dest} already exists")
    return dest, path


def write_atomic(path, data):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".clip-note-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def cmd_find_link(root, args):
    matches = link_matches(corpus_with(root), args.url)
    return (3 if matches else 0), {"url": normalize_url(args.url), "matches": matches}


def cmd_format(root, args):
    scope = K.Snapshot(root).scope
    source = K.relative(args.source)
    original = K.relative(args.original or source)
    dest, path = check_dest(root, scope, args.dest, source)
    try:
        source_text = K.read_file(root, source).decode("utf-8-sig")
        original_text = K.read_file(root, original).decode("utf-8-sig")
        discover = json.loads(Path(args.discover).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as e:
        raise K.KnowledgeError(f"cannot read input: {e}") from e
    original_meta, original_body = split_frontmatter(original_text)
    _, body = split_frontmatter(source_text)
    meta, report = adapt(args.kind, original_meta, discover)
    embeds = verify(original_body, body, root, args.assets and K.relative(args.assets), args.kind)
    data = compose(meta, body, _list(discover.get("related"))).encode()
    corpus = corpus_with(root, dest, data)
    if meta.get("Link"):
        dupes = link_matches(corpus, meta["Link"], skip={dest, source})
        if dupes:
            raise Refused(f"{dupes[0]['path']} already records {meta['Link']}")
    lint = [i for i in corpus.issues() if i["path"] == dest]
    if not args.dry_run:
        write_atomic(path, data)
    result = {"note": dest, "written": not args.dry_run, "embeds": embeds, "keys": list(meta),
              "report": report, "lint": lint}
    return (6 if lint else 0), result


def cmd_release(root, args):
    targets = []
    for name in args.paths:
        name = K.relative(name)
        if PurePosixPath(name).parts[0] != "raw" or not name.endswith(".md"):
            raise K.KnowledgeError(f"{name}: release deletes only .md captures under raw/")
        path = K.safe_path(root, name)
        if not path.is_file():
            raise K.KnowledgeError(f"{name} is not a file")
        targets.append((name, path))
    for _, path in targets:
        path.unlink()
    return 0, {"released": [name for name, _ in targets]}


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print a JSON summary on stdout")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", required=True, type=Path, help="explicit vault root; never inferred from cwd")
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("find-link", parents=[common], help="list notes in scope whose Link is this URL")
    f.add_argument("url")
    f = sub.add_parser("format", parents=[common], help="write the clip note")
    f.add_argument("--kind", choices=sorted(TABLES), required=True)
    f.add_argument("--source", required=True, help="vault-relative file whose body becomes the note body")
    f.add_argument("--dest", required=True, help="vault-relative destination (may equal --source when adopted in place)")
    f.add_argument("--original", help="the raw capture to verify the body against (default: --source)")
    f.add_argument("--assets", help="vault-relative image folder holding assets.json")
    f.add_argument("--discover", required=True, help="JSON file: categories, aliases, tags, tag_vocabulary, related")
    f.add_argument("--dry-run", action="store_true")
    f = sub.add_parser("release", parents=[common], help="delete .md captures under raw/")
    f.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    commands = {"find-link": cmd_find_link, "format": cmd_format, "release": cmd_release}
    result: dict
    try:
        root = args.vault.expanduser().resolve(strict=True)
        code, result = commands[args.command](root, args)
    except (K.KnowledgeError, OSError) as e:
        code, result = 1, {"error": str(e)}
    except VerifyError as e:
        code, result = 2, {"error": str(e)}
    except Refused as e:
        code, result = 3, {"error": str(e)}
    except AdaptError as e:
        code, result = 4, {"error": str(e)}
    if args.command == "format":
        result.setdefault("written", False)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, default=str))
    print(f"clip_note {args.command}: exit {code}" + (f" — {result['error']}" if "error" in result else ""),
          file=sys.stderr)
    for issue in result.get("lint", []):
        print(f"  lint {issue['rule']}: {issue['detail']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
