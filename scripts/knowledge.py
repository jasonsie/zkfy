#!/usr/bin/env python3
"""Scoped, read-only retrieval and separate deterministic maintenance for Markdown vaults.

Requires Python >=3.10 and PyYAML >=6. No network, model, or database dependency.
All callers use the same scope; neither search nor read writes caches or logs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote

try:
    import yaml
except ImportError:
    sys.exit("Missing PyYAML. Install scripts/requirements-knowledge.txt with the configured Python.")

VERSION = 1
GENERATOR_VERSION = 2
POLICY = "docs/knowledge/scope.json"
MANIFEST = ".claude/index/manifest.json"
BASELINE = ".claude/lint-baseline.json"
DENIED = {"raw", "row", "template", "y.template", "x.temp", "z.attachments", "docs"}
ASSETS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".canvas", ".mp4", ".base"}
STOP = set("a an the and or of to in for on with my me help how what which is are should works work across multiple based notes please use coding".split())
WIKI = re.compile(r"!?\[\[([^\]\n]+)\]\]")
MDLINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^\s)]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")


class KnowledgeError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode()


def git(root: Path, *args: str, data=None, env=None, check=True) -> bytes:
    p = subprocess.run(["git", "-C", str(root), *args], input=data, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, env=env)
    if check and p.returncode:
        raise KnowledgeError(p.stderr.decode(errors="replace").strip())
    return p.stdout


def relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise KnowledgeError("Expected a nonempty vault-relative POSIX path")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in (".", "..") for x in value.split("/")):
        raise KnowledgeError("Absolute paths and traversal are not allowed")
    return p.as_posix()


def safe_path(root: Path, name: str) -> Path:
    """Reject every symlink component, including links that remain inside the vault."""
    root = root.resolve(strict=True)
    path = root
    for part in PurePosixPath(relative(name)).parts:
        path = path / part
        if path.is_symlink():
            raise KnowledgeError("Symlink paths are not eligible")
    if not path.resolve().is_relative_to(root):
        raise KnowledgeError("Path escapes vault")
    return path


def read_file(root: Path, name: str) -> bytes:
    p = safe_path(root, name)
    fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        return stream.read()


class Scope:
    def __init__(self, data: bytes):
        try:
            self.config = json.loads(data)
            if self.config["version"] != VERSION:
                raise ValueError("unsupported scope version")
            self.domains = self.config["domains"]
            self.maps = self.config.get("maps", [])
            self.files = self.config.get("include_files", [])
            self.size = int(self.config.get("shard_size", 40))
            if not isinstance(self.domains, dict) or not self.domains or not 1 <= self.size <= 100:
                raise ValueError("domains must be nonempty; shard_size must be 1..100")
            if not all(re.fullmatch(r"[a-z][a-z0-9-]*", k) for k in self.domains):
                raise ValueError("domain labels must be lowercase slugs")
            for name in [*self.domains.values(), *self.maps, *self.files]:
                parts = PurePosixPath(relative(name)).parts
                if any(p.startswith(".") or p.casefold() in DENIED for p in parts):
                    raise ValueError("system/source directories cannot be included")
            if len(set(self.roots)) != len(self.roots):
                raise ValueError("duplicate roots")
            for a in self.roots:
                if any(a != b and a.startswith(b + "/") for b in self.roots):
                    raise ValueError("overlapping roots")
        except (ValueError, TypeError, KeyError) as e:
            raise KnowledgeError(f"Invalid scope policy: {e}") from e
        self.hash = digest(encoded(self.config))

    @property
    def roots(self):
        return [*self.domains.values(), *self.maps]

    def eligible(self, name: str) -> bool:
        try:
            name = relative(name)
        except KnowledgeError:
            return False
        parts = PurePosixPath(name).parts
        return (name.endswith(".md") and not any(p.startswith(".") or p.casefold() in DENIED for p in parts)
                and (name in self.files or any(name.startswith(r + "/") for r in self.roots)))

    def domain(self, name: str) -> str:
        for key, root in self.domains.items():
            if name.startswith(root + "/"):
                return key
        return "maps" if self.is_map(name) else "unfiled"

    def is_map(self, name):
        return any(name.startswith(r + "/") for r in self.maps)


class Snapshot:
    def __init__(self, root: Path, view="worktree", bootstrap=False, scope=None):
        self.root = root.expanduser().resolve(strict=True)
        self.view = view
        self.objects = {}
        self.blobs = None
        if scope is not None:
            policy = encoded(scope.config)
        elif view != "worktree":
            policy = self.control(POLICY)
            if policy is None and bootstrap:
                policy = read_file(self.root, POLICY)
            if policy is None:
                raise KnowledgeError(f"No {POLICY} in {view}; stage the policy or explicitly bootstrap baseline")
        else:
            policy = read_file(self.root, POLICY)
        self.scope = Scope(policy)
        if view != "worktree":
            if view == "head" and not git(self.root, "rev-parse", "--verify", "HEAD", check=False).strip():
                return  # An unborn repository has no inherited source/debt.
            paths = [*self.scope.roots, *self.scope.files]
            args = ["ls-files", "--stage", "-z", "--", *paths] if view == "staged" else ["ls-tree", "-r", "-z", "HEAD", "--", *paths]
            for entry in git(self.root, *args).split(b"\0"):
                if not entry:
                    continue
                meta, path = entry.split(b"\t", 1)
                name = os.fsdecode(path)
                fields = meta.decode().split()
                mode, oid = (fields[0], fields[1]) if view == "staged" else (fields[0], fields[2])
                if view == "staged" and fields[2] != "0":
                    raise KnowledgeError("Resolve unmerged entries before validation")
                if mode in ("100644", "100755") and self.scope.eligible(name):
                    self.objects[name] = oid

    def control(self, name: str):
        if self.view == "worktree":
            try:
                return read_file(self.root, name)
            except FileNotFoundError:
                return None
        spec = (":" if self.view == "staged" else "HEAD:") + name
        p = subprocess.run(["git", "-C", str(self.root), "show", spec], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.stdout if p.returncode == 0 else None

    def paths(self):
        if self.view != "worktree":
            return sorted(self.objects)
        found = set()
        for name in self.scope.roots:
            directory = safe_path(self.root, name)
            if not directory.exists():
                continue
            for parent, dirs, files in os.walk(directory, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d.casefold() not in DENIED
                                 and not (Path(parent) / d).is_symlink())
                for f in sorted(files):
                    path = Path(parent) / f
                    rel = path.relative_to(self.root).as_posix()
                    if self.scope.eligible(rel) and not path.is_symlink():
                        found.add(rel)
        for name in self.scope.files:
            p = safe_path(self.root, name)
            if p.is_file():
                found.add(name)
        return sorted(found)

    def read(self, name: str):
        if not self.scope.eligible(name):
            raise KnowledgeError("Path is outside the knowledge corpus")
        if self.view == "worktree":
            return read_file(self.root, name)
        if name not in self.objects:
            raise KnowledgeError("Note does not exist in this snapshot")
        if self.blobs is None:
            # Read only allowlisted objects, in one Git process. Names never enter
            # this line-oriented protocol, so Unicode/newline filenames stay safe.
            oids = sorted(set(self.objects.values()))
            data = git(self.root, "cat-file", "--batch", data=("\n".join(oids) + "\n").encode())
            self.blobs = {}
            position = 0
            for oid in oids:
                newline = data.index(b"\n", position)
                actual, kind, size = data[position:newline].split()
                if actual.decode() != oid or kind != b"blob":
                    raise KnowledgeError("Unexpected staged Git object")
                position = newline + 1
                end = position + int(size)
                if data[end:end + 1] != b"\n":
                    raise KnowledgeError("Incomplete Git object batch")
                self.blobs[oid] = data[position:end]
                position = end + 1
        return self.blobs[self.objects[name]]


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    mapping = {}
    for key, value in node.value:
        k = loader.construct_object(key, deep=deep)
        if not isinstance(k, str) or k in mapping:
            raise ValueError("frontmatter keys must be unique strings")
        mapping[k] = loader.construct_object(value, deep=deep)
    return mapping


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def prose_lines(lines):
    fence = None
    for number, line in lines:
        m = re.match(r"^\s*(`{3,}|~{3,})", line)
        if m:
            marker = m[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield number, re.sub(r"`[^`]*`", "", line)


def outside_ref(target):
    target = unquote(target.split("|", 1)[0].split("#", 1)[0]).strip()
    return (any(p.casefold() in DENIED or p.startswith(".") for p in target.split("/") if p)
            or bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target)))


def visible(text):
    text = WIKI.sub(lambda m: "[out-of-scope reference]" if outside_ref(m[1]) else m[0], text)
    return MDLINK.sub(lambda m: "[out-of-scope reference]" if outside_ref(m[1]) and not m[1].startswith(("https://", "http://")) else m[0], text)


@dataclass
class Note:
    path: str
    sha: str
    meta: dict
    lines: list
    headings: list
    links: list
    errors: list
    domain: str
    line_count: int

    @classmethod
    def parse(cls, name, data, scope):
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise KnowledgeError(f"Invalid UTF-8 in eligible note {name}") from e
        all_lines = text.splitlines()
        start, meta, errors = 0, {}, []
        if all_lines and all_lines[0].strip() == "---":
            end = next((i for i in range(1, len(all_lines)) if all_lines[i].strip() == "---"), None)
            if end is None:
                errors.append(("metadata", "unclosed frontmatter"))
                start = len(all_lines)
            else:
                start = end + 1
                try:
                    meta = yaml.load("\n".join(all_lines[1:end]), Loader=UniqueLoader) or {}
                    if not isinstance(meta, dict):
                        raise ValueError("expected a mapping")
                except (yaml.YAMLError, ValueError, TypeError):
                    errors.append(("metadata", "invalid YAML or duplicate keys"))
                    meta = {}
        else:
            errors.append(("metadata", "missing frontmatter"))
        lines = [(i + 1, line) for i, line in enumerate(all_lines) if i >= start]
        headings, links = [], []
        for n, line in prose_lines(lines):
            h = HEADING.match(line)
            if h:
                headings.append((n, h[1]))
            links.extend(m[1].split("|", 1)[0].strip() for m in WIKI.finditer(line))
            links.extend(unquote(m[1]) for m in MDLINK.finditer(line) if not re.match(r"^[\w+.-]+:", m[1]))
        return cls(name, digest(data), meta, lines, headings, links, errors, scope.domain(name), len(all_lines))

    def summary(self):
        for _, text in prose_lines(self.lines):
            if text.strip() and not HEADING.match(text) and not text.strip().startswith(("---", "|")):
                return visible(text.strip())[:240]
        return ""

    def values(self, field):
        value = self.meta.get(field, [])
        values = value if isinstance(value, list) else [value]
        return [visible(str(v)) for v in values if v and not outside_ref(str(v))]


class Corpus:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.scope = snapshot.scope
        self.notes = {p: Note.parse(p, snapshot.read(p), self.scope) for p in snapshot.paths()}
        self.names = defaultdict(set)
        for p, note in self.notes.items():
            for name in [p, p[:-3], PurePosixPath(p).stem, *note.values("Aliases")]:
                self.names[name.casefold()].add(p)
        self.hashes = {p: n.sha for p, n in self.notes.items()}

    def resolve(self, target, source=None):
        # A table cell escapes the alias pipe as `[[Note\|alias]]`; drop the escape.
        target, _, anchor = unquote(target).rstrip("\\").partition("#")
        if outside_ref(target) or PurePosixPath(target).suffix.lower() in ASSETS:
            return "outside", []
        if not target and source:
            matches = {source}
        else:
            matches = self.names.get(target.casefold(), set())
            if not matches and source and "/" not in target:
                sibling = str(PurePosixPath(source).parent / target)
                matches = self.names.get(sibling.casefold(), set())
        if len(matches) != 1:
            return ("ambiguous" if matches else "unresolved"), sorted(matches)
        p = next(iter(matches))
        if anchor:
            note = self.notes[p]
            def slug(s):
                return re.sub(r"[^\w\u4e00-\u9fff]+", "-", s.casefold()).strip("-")
            if anchor.startswith("^"):
                exists = any(re.search(r"\^" + re.escape(anchor[1:]) + r"\s*$", s) for _, s in note.lines)
            else:
                exists = any(slug(h) == slug(anchor) for _, h in note.headings)
            if not exists:
                return "anchor", [p]
        return "ok", [p]

    def repair_hint(self, path, rule, detail):
        if rule == "heading":
            if detail == "thesis summary":
                hint = "Add a summary section headed 執行摘要, Executive Summary, or Abstract."
            elif detail == "thesis theme":
                hint = "Add a content-specific thematic section beyond the summary, Mental Model, and Links."
            else:
                hint = f"Add a `### {detail}` section, or review whether this note needs a different Mode."
        elif rule == "field":
            examples = {"Date": "YYYY-MM-DD", "Type": "permanent", "Categories": "[]"}
            hint = f"Add `{detail}: {examples.get(detail, 'value')}` to frontmatter; choose the actual date/type/values."
        elif rule == "list-field":
            hint = f"Convert `{detail}` to a YAML list, e.g. `{detail}: [value]`, preserving the intended values."
        elif rule == "filename":
            parts = re.findall(r"[A-Za-z0-9]+", PurePosixPath(path).stem)
            prefix = {"ai": "AI", "cs": "Cs"}.get(self.scope.domain(path), self.scope.domain(path).title())
            if not parts or parts[0].casefold() != prefix.casefold():
                parts.insert(0, prefix)
            if len(parts) < 2:
                parts.append("Concept")
            hint = f"Review rename to `{'-'.join(parts)}.md` (use a meaningful concept name), and update inbound/nav links."
        elif rule == "metadata":
            hint = {"missing frontmatter": "Add a valid YAML frontmatter block between two standalone `---` lines.",
                    "unclosed frontmatter": "Close frontmatter with a standalone `---` line before the body."}.get(
                        detail, "Remove duplicate keys and repair YAML syntax; replace template placeholders with valid values or quote literal text.")
        elif rule == "type":
            hint = "Set Type to literature, permanent, fleeting, or structure according to the note's role."
        elif rule == "mode":
            hint = "Use Mode: atom or Mode: thesis with matching sections, or omit Mode for a legacy note."
        elif rule == "link-ambiguous":
            _, matches = self.resolve(detail, path)
            hint = "Choose the intended path-qualified target from: " + ", ".join(f"`{p}`" for p in matches[:5]) + "."
        elif rule == "link-anchor":
            hint = f"Correct the heading/block anchor in `[[{detail}]]` to one present in the target, or review removing the anchor."
        elif rule == "link-unresolved":
            hint = f"Correct `[[{detail}]]` to an existing eligible target, or review unlinking it; do not scan sources or auto-create a replacement note."
        else:
            hint = f"Review {rule}: {detail}."
        return hint + " Authored changes require approval."

    def issues(self):
        issues = []
        for p, note in self.notes.items():
            errors = list(note.errors)
            meta = note.meta
            if not self.scope.is_map(p) and p not in self.scope.files:
                if not re.fullmatch(r"[A-Za-z]+(?:-[A-Za-z0-9]+)+", PurePosixPath(p).stem):
                    errors.append(("filename", PurePosixPath(p).name))
                for key in ("Date", "Type", "Categories"):
                    if key not in meta:
                        errors.append(("field", key))
                for key in ("Categories", "Sub-Categories", "Aliases", "tags"):
                    if key in meta and not isinstance(meta[key], list):
                        errors.append(("list-field", key))
                if meta.get("Type") not in (None, "literature", "permanent", "fleeting", "structure"):
                    errors.append(("type", str(meta["Type"])))
                mode = meta.get("Mode", "legacy")
                hs = {h.casefold() for _, h in note.headings}
                if meta.get("Type") not in ("fleeting", "structure"):
                    required = {"atom": ["Definition", "Mental Model", "Links"],
                                "thesis": ["Mental Model", "Links"],
                                "legacy": ["Abstract", "Links"]}
                    if mode not in required:
                        errors.append(("mode", str(mode)))
                    else:
                        for heading in required[mode]:
                            if heading.casefold() not in hs:
                                errors.append(("heading", heading))
                        if mode == "thesis":
                            summaries = self.scope.config.get("thesis_summaries", ["執行摘要", "Executive Summary", "Abstract"])
                            if not hs.intersection(h.casefold() for h in summaries):
                                errors.append(("heading", "thesis summary"))
                            if not hs.difference({h.casefold() for h in summaries} | {"mental model", "links", "appendix", "附錄"}):
                                errors.append(("heading", "thesis theme"))
            targets = list(note.links)
            for key in ("Before", "Next"):
                targets += [m[1].split("|", 1)[0] for m in WIKI.finditer(str(meta.get(key, "")))]
            for target in targets:
                status, _ = self.resolve(target, p)
                if status not in ("ok", "outside"):
                    errors.append(("link-" + status, target))
            for rule, detail in sorted(set(errors)):
                issues.append({"path": p, "rule": rule, "detail": detail,
                               "fix": self.repair_hint(p, rule, detail)})
        return sorted(issues, key=issue_key)

    def manifest(self):
        return {"version": VERSION, "generator": GENERATOR_VERSION, "scope": self.scope.hash, "files": self.hashes}

    def freshness(self):
        data = self.snapshot.control(MANIFEST)
        if data is None:
            return "missing; live scoped search"
        try:
            m = json.loads(data)
            return "current" if all(m.get(k) == v for k, v in self.manifest().items()) else "stale; live scoped search"
        except (ValueError, TypeError):
            return "invalid; live scoped search"

    def outputs(self):
        issues = self.issues()
        incoming, outgoing, mapped = defaultdict(set), defaultdict(set), set()
        for p, note in self.notes.items():
            for link in note.links:
                status, matches = self.resolve(link, p)
                if status == "ok" and matches[0] != p:
                    outgoing[p].add(matches[0])
                    incoming[matches[0]].add(p)
                    if self.scope.is_map(p):
                        mapped.add(matches[0])
        grouped = defaultdict(list)
        for p in self.notes:
            grouped[self.notes[p].domain].append(p)
        root = ["# Vault knowledge map", "", "Generated by zkfy; notes, not this catalog, are answer evidence.",
                "Use scoped search/read. Detailed aliases and excerpts live in bounded shards.", "",
                "| Domain | Notes | Shards |", "|---|---:|---|"]
        result = {}
        for domain, paths in sorted(grouped.items()):
            shards = []
            for i in range(0, len(paths), self.scope.size):
                name = f".claude/index/{domain}-{i // self.scope.size + 1:03}.md"
                shards.append(f"[{i // self.scope.size + 1}](index/{PurePosixPath(name).name})")
                lines = [f"# {domain} — catalog shard {i // self.scope.size + 1}", "", "Generated navigation, not verified claims.", ""]
                for p in paths[i:i + self.scope.size]:
                    n = self.notes[p]
                    fields = {k: n.values(k) for k in ("Type", "Mode", "Aliases", "Categories", "Sub-Categories", "tags")}
                    lines.append(f"- `{p}` — {n.summary()} | metadata: {json.dumps(fields, ensure_ascii=False)} | inbound: {len(incoming[p])}")
                result[name] = ("\n".join(lines) + "\n").encode()
            root.append(f"| {domain} | {len(paths)} | {' '.join(shards)} |")
        root += ["", f"Eligible notes: {len(self.notes)}. MOC membership is not required for discovery.",
                 "", "## Keyword Index", "", "Search aliases, headings and body with `knowledge search`; do not load all shards.",
                 "See `docs/knowledge/query.md` for evidence rules."]
        result[".claude/index.md"] = ("\n".join(root) + "\n").encode()
        health = ["# Knowledge structural health", "", "Generated, content-derived diagnostics. These are not factual-trust ratings.",
                  "No timestamps or Git-history signals; identical source bytes yield identical reports.", "",
                  "| Domain | Notes | Violations | No inbound links | No outgoing links | MOC coverage |",
                  "|---|---:|---:|---:|---:|---:|"]
        for domain, paths in sorted(grouped.items()):
            count = sum(i["path"] in paths for i in issues)
            health.append(f"| {domain} | {len(paths)} | {count} | {sum(not incoming[p] for p in paths)} | {sum(not outgoing[p] for p in paths)} | {sum(p in mapped for p in paths)}/{len(paths)} |")
        health += ["", "Body links determine connectivity; Before/Next chains do not inflate it.",
                   "Unresolved means unresolved inside the eligible corpus, not proven absent everywhere.",
                   "Legacy/atom/thesis headings are recognized; semantic checks and body budgets remain a separate review.", "", "## Eligible-note debt", ""]
        for issue in issues:
            health.append(f"- `{issue['path']}` — {issue['rule']}: {issue['detail']}. {issue['fix']}")
        result[".claude/QUALITY.md"] = ("\n".join(health) + "\n").encode()
        manifest = self.manifest()
        manifest["outputs"] = {p: digest(b) for p, b in sorted(result.items())}
        result[MANIFEST] = encoded(manifest)
        return result


def issue_key(issue):
    return (issue["path"], issue["rule"], issue["detail"])


def tokens(text):
    return [s for s in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", text.casefold()) if len(s) > 1 and s not in STOP]


def search(corpus, query, limit):
    terms = set(tokens(query))
    # Treat Chinese word-segmentation spaces as equivalent for phrase expansion,
    # while retaining English word boundaries (e.g. context management).
    matching = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", " ".join(query.casefold().split()))
    for group in corpus.scope.config.get("synonyms", []):
        if any(t.casefold() in matching for t in group):
            terms.update(t.casefold() for t in group)
    terms = sorted(terms - STOP)
    if not terms:
        return []
    rows = []
    for p, n in corpus.notes.items():
        title = PurePosixPath(p).stem.replace("-", " ").casefold()
        aliases = " ".join(n.values("Aliases")).casefold()
        metadata = " ".join(n.values("Categories") + n.values("Sub-Categories") + n.values("tags")).casefold()
        body = "\n".join(visible(s) for _, s in n.lines).casefold()
        headings = " ".join(visible(h) for _, h in n.headings).casefold()
        rows.append((p, n, title, aliases, metadata, body, headings))
    idf = {t: math.log(1 + len(rows) / (1 + sum(any(t in f for f in row[2:]) for row in rows))) for t in terms}
    ranked = []
    for p, n, title, aliases, metadata, body, headings in rows:
        score = sum(idf[t] * (8 * (t in title) + 10 * (t in aliases) + 3 * (t in metadata)
                             + 4 * (t in headings) + min(body.count(t), 4) / 4) for t in terms)
        if score <= 0:
            continue
        hits = [(sum(t in visible(s).casefold() for t in terms), num) for num, s in n.lines]
        line = max(hits, key=lambda x: (x[0], -x[1]))[1] if hits else 1
        heading = next((h for num, h in reversed(n.headings) if num <= line), "(preamble)")
        excerpt = "\n".join(f"{num}: {visible(s)}" for num, s in n.lines if line - 1 <= num <= line + 2)[:1800]
        ranked.append({"path": p, "heading": visible(heading), "line": line, "sha256": n.sha,
                       "score": round(score, 3), "excerpt": excerpt,
                       "metadata_issues": n.errors})
    return sorted(ranked, key=lambda r: (-r["score"], r["path"]))[:limit]


def clip_bytes(text, budget):
    return text.encode("utf-8")[:budget].decode("utf-8", errors="ignore")


def inventory(corpus, target="."):
    """Scoped compatibility inventory; no non-note/source artifact enumeration."""
    if target != ".":
        target = relative(target)
        if outside_ref(target) or not (corpus.scope.eligible(target) or any(
                target == r or target.startswith(r + "/") for r in corpus.scope.roots)):
            raise KnowledgeError("Inventory target is outside the knowledge corpus")
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, str):
            return "[out-of-scope reference]" if outside_ref(value) else visible(value)
        return value
    notes, broken = [], set()
    for p, n in corpus.notes.items():
        if target != "." and p != target and not p.startswith(target + "/"):
            continue
        links = list(n.links)
        for field in ("Before", "Next"):
            links += [m[1].split("|", 1)[0] for m in WIKI.finditer(str(n.meta.get(field, "")))]
        eligible_links = []
        for link in sorted(set(links)):
            status, _ = corpus.resolve(link, p)
            if status == "outside":
                continue
            eligible_links.append(link)
            if status != "ok":
                broken.add(link)
        notes.append({"path": p, "filename": PurePosixPath(p).name,
                      "directory": str(PurePosixPath(p).parent), "frontmatter": clean(n.meta),
                      "outgoing_links": eligible_links, "line_count": n.line_count,
                      "metadata_issues": n.errors})
    return {"scanned_path": target, "notes": notes, "non_md_files": [],
            "stats": {"total_notes": len(notes), "total_lines": sum(n["line_count"] for n in notes),
                      "orphan_notes": sum(not n["outgoing_links"] for n in notes),
                      "broken_links": sorted(broken), "artifacts": []},
            "scope_note": "Eligible notes only; orphan_notes means no outgoing links, not no inbound links."
                          " No source/non-note inventory or wall-clock timestamp."}


def get_note(corpus, path, heading=None, start=None, limit=80):
    name = relative(path)
    if name not in corpus.notes:
        raise KnowledgeError("No eligible note at that exact relative path")
    note = corpus.notes[name]
    if heading:
        matches = [i for i, h in note.headings if h.casefold() == heading.casefold()]
        if len(matches) != 1:
            raise KnowledgeError("Heading must match exactly one section")
        start = matches[0]
        end = next((i for i, _ in note.headings if i > start), note.line_count + 1)
    else:
        start = start if start is not None else (note.lines[0][0] if note.lines else 1)
        end = note.line_count + 1
    if start < 1:
        raise KnowledgeError("Start line must be positive")
    available = [(i, s) for i, s in note.lines if start <= i < end]
    lines, clipped = [], []
    budget = 16000
    for i, s in available[:limit]:
        text = visible(s)
        bounded = clip_bytes(text, min(1600, budget))
        if text and not bounded:
            break
        if bounded != text:
            clipped.append(i)
        lines.append((i, bounded))
        budget -= len(bounded.encode("utf-8"))
        if budget <= 0:
            break
    more = len(lines) < len(available)
    return {"path": name, "sha256": note.sha, "lines": lines,
            "metadata": {key: clip_bytes(visible(str(note.meta[key])), 240)
                         for key in ("Date", "Type", "Mode")
                         if key in note.meta and not outside_ref(str(note.meta[key]))},
            "headings": [(i, clip_bytes(visible(h), 200)) for i, h in note.headings[:64]],
            "headings_truncated": len(note.headings) > 64,
            "metadata_issues": note.errors, "clipped_lines": clipped,
            "next_start": available[len(lines)][0] if more else None,
            "truncated": more or bool(clipped)}


def owned_path(name):
    return name in (".claude/index.md", ".claude/QUALITY.md", MANIFEST, BASELINE) or bool(re.fullmatch(r"\.claude/index/[a-z][a-z0-9-]*-\d{3}\.md", name))


def old_outputs(snapshot):
    data = snapshot.control(MANIFEST)
    if not data:
        return set()
    try:
        return {p for p in json.loads(data).get("outputs", {}) if owned_path(p) and p != BASELINE} | {MANIFEST}
    except (ValueError, TypeError):
        raise KnowledgeError("Invalid existing generated manifest; review before overwriting")


def write_outputs(snapshot, outputs, check=False):
    old = old_outputs(snapshot)
    differences = [p for p, data in outputs.items() if snapshot.control(p) != data]
    differences += sorted(old - outputs.keys())
    if check:
        return differences
    for name in outputs.keys() | old:
        safe_path(snapshot.root, name)
    for name, data in outputs.items():
        if name in differences:
            path = safe_path(snapshot.root, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                tmp.write(data)
            os.replace(tmp.name, path)
    for name in old - outputs.keys():
        safe_path(snapshot.root, name).unlink(missing_ok=True)
    return differences


def baseline_data(corpus):
    return {"version": VERSION, "issues": corpus.issues()}


def renamed_baseline(root, issues):
    fields = git(root, "diff", "--cached", "--name-status", "-z", "-M").split(b"\0")
    rename, i = {}, 0
    while i < len(fields) and fields[i]:
        status = fields[i].decode()
        if status.startswith(("R", "C")):
            if status.startswith("R"):
                rename[os.fsdecode(fields[i + 1])] = os.fsdecode(fields[i + 2])
            i += 3
        else:
            i += 2
    return [{**x, "path": rename.get(x["path"], x["path"])} for x in issues]


def git_index_path(root):
    return Path(os.fsdecode(git(root, "rev-parse", "--path-format=absolute", "--git-path", "index")).strip())


def stage_outputs(root, outputs, removals, expected_index=None):
    """Transactional generated-only worktree/index update. Never stage note paths."""
    names = set(outputs) | set(removals)
    if not all(owned_path(p) for p in names):
        raise KnowledgeError("Refusing to stage non-generated paths")
    staged = Snapshot(root, "staged")
    head = Snapshot(root, "head", scope=staged.scope)
    originals = {}
    for name in names:
        path = safe_path(root, name)
        current = read_file(root, name) if path.exists() else None
        originals[name] = current
        allowed = (staged.control(name), head.control(name), outputs.get(name))
        if current is not None and current not in allowed:
            raise KnowledgeError(f"Generated file has unstaged edits: {name}; rebuild/review explicitly")
        s, h = staged.control(name), head.control(name)
        if s != h and s not in (outputs.get(name), None):
            raise KnowledgeError(f"Generated file has conflicting staged edits: {name}")
    index = git_index_path(root)
    original_index = index.read_bytes()
    if expected_index is not None and original_index != expected_index:
        raise KnowledgeError("Git index changed during validation; retry")
    lock = Path(str(index) + ".lock")
    with tempfile.TemporaryDirectory(prefix="zkfy-index-") as td:
        temp_index = Path(td) / "index"
        temp_index.write_bytes(original_index)
        env = {**os.environ, "GIT_INDEX_FILE": str(temp_index)}
        updates = []
        for name, data in sorted(outputs.items()):
            oid = git(root, "hash-object", "-w", "--stdin", data=data).strip()
            updates.append(b"100644 " + oid + b"\t" + os.fsencode(name) + b"\0")
        for name in sorted(removals):
            updates.append(b"0 " + b"0" * 40 + b"\t" + os.fsencode(name) + b"\0")
        git(root, "update-index", "-z", "--index-info", data=b"".join(updates), env=env)
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as e:
            raise KnowledgeError("Git index is locked; retry after the other Git operation") from e
        changed = []
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(temp_index.read_bytes())
            if index.read_bytes() != original_index:
                raise KnowledgeError("Git index changed during validation; retry")
            for name in sorted(names):
                path = safe_path(root, name)
                current = read_file(root, name) if path.exists() else None
                if current != originals[name]:
                    raise KnowledgeError("Generated file changed during validation; retry")
                path.parent.mkdir(parents=True, exist_ok=True)
                changed.append(name)
                if name in outputs:
                    path.write_bytes(outputs[name])
                else:
                    path.unlink(missing_ok=True)
            os.replace(lock, index)
        except BaseException:
            for name in changed:
                path = safe_path(root, name)
                if originals[name] is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(originals[name])
            raise
        finally:
            lock.unlink(missing_ok=True)


def run_hook(root, mode):
    original_index = git_index_path(root).read_bytes()
    staged = Snapshot(root, "staged")
    corpus = Corpus(staged)
    head = Snapshot(root, "head", scope=staged.scope)
    previous = head.control(BASELINE)
    allowed = json.loads(previous)["issues"] if previous else Corpus(head).issues()
    allowed = renamed_baseline(root, allowed)
    allowed_keys = {issue_key(x) for x in allowed}
    staged_baseline = staged.control(BASELINE)
    if staged_baseline:
        submitted = json.loads(staged_baseline)
        if submitted.get("version") != VERSION or not {issue_key(x) for x in submitted["issues"]} <= allowed_keys:
            raise KnowledgeError("Baseline expansion requires a separately reviewed reset; normal commits cannot expand it")
        allowed_keys &= {issue_key(x) for x in submitted["issues"]}
    issues = corpus.issues()
    new = [x for x in issues if issue_key(x) not in allowed_keys]
    report = {"mode": mode, "issues": len(issues), "new_issues": new, "staged_generated": False}
    if mode == "report-only":
        return report, 0
    if new:
        return report, 1
    outputs = corpus.outputs()
    outputs[BASELINE] = encoded({"version": VERSION, "issues": issues})
    stage_outputs(root, outputs, old_outputs(staged) - outputs.keys(), expected_index=original_index)
    report["staged_generated"] = True
    return report, 0


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vault", required=True, type=Path, help="Explicit canonical vault; never inferred from cwd")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("search", help="Read-only live lexical retrieval")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=6, choices=range(1, 21), metavar="1..20")
    r = sub.add_parser("read", help="Read-only eligible section retrieval")
    r.add_argument("path")
    r.add_argument("--heading")
    r.add_argument("--start", type=int)
    r.add_argument("--limit", type=int, default=80, choices=range(1, 201), metavar="1..200")
    sub.add_parser("status", help="Read-only freshness/coverage")
    inv = sub.add_parser("inventory", help="Read-only scoped maintenance inventory (legacy scanner adapter)")
    inv.add_argument("--target", default=".", help="Eligible relative directory/file, or . for the configured corpus")
    b = sub.add_parser("build", help="Explicit maintenance: generated artifacts only")
    b.add_argument("--check", action="store_true")
    lint_parser = sub.add_parser("lint", help="Read-only structural report")
    lint_parser.add_argument("--snapshot", choices=("worktree", "staged", "head"), default="worktree")
    b = sub.add_parser("baseline", help="Explicit baseline initialization, never called by queries")
    b.add_argument("--snapshot", choices=("head",), default="head")
    b.add_argument("--bootstrap-policy", action="store_true")
    b.add_argument("--write", action="store_true")
    h = sub.add_parser("hook", help="Validate the staged snapshot")
    h.add_argument("--mode", choices=("report-only", "ratchet"), default="report-only")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        root = args.vault.expanduser().resolve(strict=True)
        if args.command == "hook":
            report, code = run_hook(root, args.mode)
        else:
            snap = Snapshot(root, getattr(args, "snapshot", "worktree"), getattr(args, "bootstrap_policy", False))
            corpus = Corpus(snap)
            code = 0
            if args.command == "search":
                report = {"freshness": corpus.freshness(), "results": search(corpus, args.query, args.limit)}
            elif args.command == "read":
                report = get_note(corpus, args.path, args.heading, args.start, args.limit)
            elif args.command == "status":
                report = {"freshness": corpus.freshness(), "notes": len(corpus.notes), "domains": dict(Counter(n.domain for n in corpus.notes.values()))}
            elif args.command == "inventory":
                report = inventory(corpus, args.target)
            elif args.command == "lint":
                report = {"issues": corpus.issues()}
                code = bool(report["issues"])
            elif args.command == "baseline":
                report = baseline_data(corpus)
                if args.write:
                    path = safe_path(root, BASELINE)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("xb") as stream:
                        stream.write(encoded(report))
            elif args.command == "build":
                differences = write_outputs(snap, corpus.outputs(), args.check)
                report = {"differences": differences, "check": args.check, "notes": len(corpus.notes)}
                code = args.check and bool(differences)
        sys.stdout.buffer.write(encoded(report))
        return int(code)
    except (KnowledgeError, OSError, ValueError, KeyError, TypeError) as e:
        print(f"knowledge: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
