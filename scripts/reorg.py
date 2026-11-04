#!/usr/bin/env python3
"""Reorganization passes for a scoped vault: survey, units, plan, ledger, apply.

Shares scope, parsing and link resolution with knowledge.py. A pass is one reviewed mapping;
a merge is a weave gated by a unit ledger. Nothing here commits; apply stages its own files.
See docs/ADR/0005-reorganization-as-reviewed-weave.md.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote

if "knowledge" in sys.modules:
    k = sys.modules["knowledge"]
else:  # standalone use: python3 scripts/reorg.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import knowledge as k

LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
RULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


def normalize(text: str) -> str:
    return " ".join(text.split())


def body_start(lines):
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        return len(lines) if end is None else end + 1
    return 0


def units(text: str):
    """Split a note into the content units the ledger tracks: paragraph, list, table, code, links."""
    lines = text.splitlines()
    out, heading, i = [], "", body_start(lines)

    def push(kind, first, chunk):
        body = "\n".join(chunk).strip("\n")
        if body.strip():
            norm = normalize(body)
            out.append({"id": "u-" + k.digest(norm.encode())[:12], "kind": "links" if heading.casefold() == "links" else kind,
                        "heading": heading, "line": first + 1, "text": body})

    def starts_block(line):
        return bool(HEADING_RE.match(line) or FENCE.match(line) or line.strip().startswith("|") or LIST.match(line))

    HEADING_RE = k.HEADING
    while i < len(lines):
        line = lines[i]
        if not line.strip() or RULE.match(line):
            i += 1
            continue
        h = HEADING_RE.match(line)
        if h:
            heading = h[1]
            i += 1
            continue
        fence = FENCE.match(line)
        if fence:
            j = i + 1
            while j < len(lines):
                close = re.match(r"^\s*(`{3,}|~{3,})\s*$", lines[j])
                if close and close[1][0] == fence[1][0] and len(close[1]) >= len(fence[1]):
                    break
                j += 1
            push("code", i, lines[i:j + 1])
            i = j + 1
            continue
        if line.strip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            push("table", i, lines[i:j])
            i = j
            continue
        if LIST.match(line):
            j = i
            while j < len(lines) and (LIST.match(lines[j]) or (lines[j].strip() and lines[j][:1] in " \t")):
                j += 1
            push("list", i, lines[i:j])
            i = j
            continue
        j = i
        while j < len(lines) and lines[j].strip() and not starts_block(lines[j]) and not RULE.match(lines[j]):
            j += 1
        push("paragraph", i, lines[i:j])
        i = j
    return out


def preview(unit):
    return {"note": unit["note"], "unit": unit["id"], "kind": unit["kind"], "heading": unit["heading"],
            "line": unit["line"], "text": unit["text"][:120]}


def ledger_check(texts, draft, ledger):
    """The preservation check: one row per unit of every clustered note; kept rows must be in the draft."""
    draft_norm = normalize(draft)
    draft_links = {m[1].split("|", 1)[0].strip().casefold() for m in k.WIKI.finditer(draft)}
    all_units = {}
    for path, text in texts.items():
        for u in units(text):
            all_units[(path, u["id"])] = {**u, "note": path}
    report: dict = {"missing": [], "unknown": [], "mismatch": [], "dangling": [], "invalid": [], "review": []}
    rows = ledger.get("rows", []) if isinstance(ledger, dict) else []
    statuses = {}
    for row in rows:
        key = (row.get("note"), row.get("unit"))
        if key not in all_units:
            report["unknown"].append(row)
            continue
        if key in statuses:
            report["invalid"].append({**row, "problem": "duplicate row for one unit"})
            continue
        statuses[key] = row.get("status")
    for key, status in statuses.items():
        unit = all_units[key]
        row = next(x for x in rows if (x.get("note"), x.get("unit")) == key)
        if status == "kept":
            if unit["kind"] == "links":
                targets = {m[1].split("|", 1)[0].strip().casefold() for m in k.WIKI.finditer(unit["text"])}
                ok = targets <= draft_links
            else:
                ok = normalize(unit["text"]) in draft_norm
            if not ok:
                report["mismatch"].append(preview(unit))
        elif status == "duplicate":
            of = row.get("of")
            carried = any(s in ("kept", "reworded") and u["id"] == of for (p, _), s in statuses.items() for u in [all_units[(p, _)]])
            entry = {**preview(unit), "status": status, "of": of}
            if not carried:
                report["dangling"].append(entry)
            report["review"].append(entry)
        elif status in ("reworded", "dropped"):
            entry = {**preview(unit), "status": status}
            for field in ("heading", "reason"):
                if field in row:
                    entry[field] = row[field]
            if status == "dropped" and not row.get("reason"):
                report["invalid"].append({**row, "problem": "dropped rows need a reason"})
            report["review"].append(entry)
        else:
            report["invalid"].append({**row, "problem": f"unknown status {status!r}"})
    for key, unit in all_units.items():
        if key not in statuses:
            report["missing"].append(preview(unit))
    report["counts"] = dict(sorted(k.Counter(statuses.values()).items()))
    report["ok"] = not any(report[x] for x in ("missing", "unknown", "mismatch", "dangling", "invalid"))
    return report


THRESHOLDS = {"tiny_folder_max": 2, "max_depth": 3, "oversized_lines": 1200, "category_share": 0.2, "category_min": 4}
GENERIC = set("introduction intro overview basics basic fundamentals guide notes note concepts concept advanced "
              "practice problems questions cheatsheet summary part chapter implementation usage "
              "and or vs the of in to for with on by from how what why is are".split())
WEIGHT = {"alias": 3, "headings": 2, "subset": 2, "stem": 1}
STRUCTURAL = {"abstract", "content", "links", "mental model", "執行摘要", "executive summary", "附錄", "appendix", "definition"}


def thresholds(scope):
    custom = scope.config.get("reorg", {})
    if not isinstance(custom, dict) or not all(isinstance(custom.get(x, 0), (int, float)) for x in THRESHOLDS):
        raise k.KnowledgeError("Invalid scope policy: reorg thresholds must be numbers")
    return {**THRESHOLDS, **{x: custom[x] for x in THRESHOLDS if x in custom}}


def nav_target(value):
    value = str(value or "").strip().strip("'\"").strip()
    return value


def same_token(a, b):
    return a == b or (len(a) >= 6 and len(b) >= 6 and (a.startswith(b[:6]) and b.startswith(a[:6])))


def inbound_counts(corpus):
    incoming = k.defaultdict(set)
    for p, note in corpus.notes.items():
        for link in note.links:
            status, matches = corpus.resolve(link, p)
            if status == "ok" and matches[0] != p:
                incoming[matches[0]].add(p)
    return {p: len(s) for p, s in incoming.items()}


def survey(corpus, target=None, limits=None):
    """Deterministic reorganization signals and candidate clusters. Read-only."""
    limits = {**thresholds(corpus.scope), **(limits or {})}
    if target not in (None, "."):
        target = k.relative(target)
        if not any(target == r or target.startswith(r + "/") or r.startswith(target + "/") for r in corpus.scope.roots):
            raise k.KnowledgeError("Survey target is outside the knowledge corpus")
    notes = {p: n for p, n in corpus.notes.items() if target in (None, ".") or p == target or p.startswith(target + "/")}
    conceptual = {p: n for p, n in notes.items() if n.domain not in ("maps",) and not corpus.scope.is_map(p)}
    per_folder = k.Counter(str(k.PurePosixPath(p).parent) for p in conceptual)
    signals = {
        "tiny_folders": [{"folder": f, "notes": c} for f, c in sorted(per_folder.items())
                         if c <= limits["tiny_folder_max"] and f not in corpus.scope.roots],
        "deep_paths": sorted(p for p in conceptual if len(k.PurePosixPath(p).parts) - 1 > limits["max_depth"]),
        "oversized": [{"path": p, "lines": n.line_count} for p, n in sorted(conceptual.items()) if n.line_count > limits["oversized_lines"]],
        "prefix_mismatch": sorted(p for p, n in conceptual.items() if n.domain != "unfiled"
                                  and not k.PurePosixPath(p).stem.casefold().startswith(n.domain.casefold() + "-")),
        "nav_leftovers": sorted(p for p, n in notes.items() if any(nav_target(n.meta.get(f)) for f in ("Before", "Next"))),
    }
    # Candidate pairs: shared specific name tokens within a domain, or a shared alias/title anywhere.
    by_domain = k.defaultdict(list)
    for p, n in conceptual.items():
        by_domain[n.domain].append(p)
    pairs = k.defaultdict(set)
    for paths in by_domain.values():
        tokens = {}
        for p in paths:
            parts = k.PurePosixPath(p).stem.casefold().split("-")[1:]
            tokens[p] = [t for t in parts if len(t) >= 3 and t not in GENERIC]
        frequency = k.Counter(t for ts in tokens.values() for t in set(ts))
        cutoff = max(limits["category_min"], limits["category_share"] * len(paths))
        specific = {p: [t for t in ts if frequency[t] < cutoff] for p, ts in tokens.items()}
        for i, a in enumerate(sorted(paths)):
            for b in sorted(paths)[i + 1:]:
                shared = {t for t in specific[a] for u in specific[b] if same_token(t, u) and not t.isdigit()}
                subset = all(any(same_token(t, u) for u in specific[b]) for t in specific[a]) or \
                    all(any(same_token(t, u) for u in specific[a]) for t in specific[b])
                if shared and (len(shared) >= 2 or subset):
                    pairs[(a, b)].add(("subset" if subset else "stem", "name stem: " + ", ".join(sorted(shared))))
    names = {p: {normalize(x).casefold() for x in [k.PurePosixPath(p).stem.replace("-", " "), k.PurePosixPath(p).stem, *n.values("Aliases")]}
             for p, n in conceptual.items()}
    ordered = sorted(conceptual)
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            common = names[a] & names[b]
            if common:
                pairs[(a, b)].add(("alias", "shared alias: " + ", ".join(sorted(common))))
    for a, b in list(pairs):
        ha = {h.casefold(): h for _, h in conceptual[a].headings if h.casefold() not in STRUCTURAL}
        hb = {h.casefold() for _, h in conceptual[b].headings}
        shared = sorted(ha[key] for key in ha.keys() & hb)
        if shared:
            pairs[(a, b)].add(("headings", "shared headings: " + ", ".join(shared)))

    def strength(pair):
        return sum(WEIGHT[kind] for kind, _ in pairs[pair])

    # Cliques, never chains: a note joins a cluster only when it pairs with every member.
    clusters = []
    for a, b in sorted(pairs, key=lambda pair: (-strength(pair), pair)):
        for members in clusters:
            if a in members and all(((min(b, m), max(b, m)) in pairs) for m in members if m != b):
                members.add(b)
                break
            if b in members and all(((min(a, m), max(a, m)) in pairs) for m in members if m != a):
                members.add(a)
                break
        else:
            clusters.append({a, b})
    incoming = inbound_counts(corpus)
    result = []
    for members in clusters:
        members = sorted(members)
        reasons, score = set(), 0
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                found = pairs.get((a, b), set())
                reasons.update(text for _, text in found)
                score += sum(WEIGHT[kind] for kind, _ in found)
        result.append({"notes": members, "score": score, "reasons": sorted(reasons),
                       "inbound": {p: incoming.get(p, 0) for p in members},
                       "lines": {p: conceptual[p].line_count for p in members}})
    result.sort(key=lambda c: (-c["score"], -len(c["notes"]), c["notes"]))
    return {"target": target or ".", "thresholds": limits, "notes": len(notes), "signals": signals, "clusters": result}


def read_any(root, name):
    """A mapping, draft or ledger file: absolute, or vault-relative (any folder, symlink-free)."""
    path = Path(name).expanduser()
    return path.read_bytes() if path.is_absolute() else k.read_file(root, name)


def load_mapping(root, name):
    try:
        data = json.loads(read_any(root, name))
    except (OSError, ValueError) as e:
        raise k.KnowledgeError(f"Cannot read mapping {name}: {e}") from e
    if not isinstance(data, dict) or data.get("version") != 1:
        raise k.KnowledgeError("Mapping must be a JSON object with version 1")
    data.setdefault("merges", [])
    data.setdefault("moves", [])
    ok = isinstance(data["merges"], list) and isinstance(data["moves"], list)
    ok = ok and all(isinstance(m, dict) and isinstance(m.get("survivor"), str) and isinstance(m.get("absorbed"), list)
                    and m["absorbed"] and all(isinstance(a, str) for a in m["absorbed"]) for m in data["merges"])
    ok = ok and all(isinstance(mv, dict) and isinstance(mv.get("from"), str) and isinstance(mv.get("to"), str) for mv in data["moves"])
    if not ok:
        raise k.KnowledgeError("Mapping merges need survivor + absorbed[]; moves need from + to")
    if not data["merges"] and not data["moves"]:
        raise k.KnowledgeError("Mapping has no operations")
    return data


def text_of(corpus, path):
    return corpus.snapshot.read(path).decode("utf-8-sig")


def dirty_paths(root, paths):
    """Touched paths with uncommitted edits (modified, staged, or untracked); deleted paths included."""
    if not paths:
        return []
    out = k.git(root, "status", "--porcelain", "-z", "--untracked-files=all", "--", *paths)
    fields = out.split(b"\0")
    dirty, i = set(), 0
    while i < len(fields) and fields[i]:
        entry = fields[i]
        status, name = entry[:2].decode(errors="replace"), os.fsdecode(entry[3:])
        dirty.add(name)
        if status[0] in "RC":
            i += 1
            dirty.add(os.fsdecode(fields[i]))
        i += 1
    return sorted(dirty & set(paths))


def inline_code_spans(line):
    return [(m.start(), m.end()) for m in re.finditer(r"`[^`]*`", line)]



def plan(corpus, mapping):
    """Validate a mapping and compute everything apply would do. Read-only."""
    root, scope, notes = corpus.snapshot.root, corpus.scope, corpus.notes
    errors, warnings, merges, moves = [], [], [], []
    used = k.Counter()
    for m in mapping.get("merges", []):
        survivor, absorbed = m["survivor"], list(m["absorbed"])
        if survivor in absorbed:
            errors.append(f"survivor is also absorbed: {survivor}")
        for p in (survivor, *absorbed):
            used[p] += 1
            if scope.is_map(p):
                errors.append(f"maps cannot be woven: {p}")
        rename = m.get("rename")
        if rename is not None and (not scope.eligible(rename) or rename in notes or (root / rename).exists()):
            errors.append(f"rename target must be a new eligible path: {rename}")
        draft = None
        if not m.get("draft"):
            errors.append(f"merge into {survivor} needs a draft")
        else:
            try:
                draft = read_any(root, m["draft"]).decode("utf-8-sig")
            except (OSError, UnicodeDecodeError, k.KnowledgeError) as e:
                errors.append(f"cannot read draft {m['draft']}: {e}")
        merges.append({**m, "absorbed": absorbed, "rename": rename, "draft_text": draft})
    for mv in mapping.get("moves", []):
        src, dst = mv["from"], mv["to"]
        used[src] += 1
        used[dst] += 1
        if not scope.eligible(dst):
            errors.append(f"move target is not an eligible path: {dst}")
        elif dst in notes or (root / dst).exists():
            errors.append(f"move target exists: {dst}")
        moves.append((src, dst))
    for p, count in sorted(used.items()):
        if count > 1:
            errors.append(f"path used more than once: {p}")
    # Already applied? Every absorbed note gone, every survivor equal to its draft, every move done.
    done = [all(a not in notes for a in m["absorbed"]) and (m["rename"] or m["survivor"]) in notes
            and m["draft_text"] is not None and text_of(corpus, m["rename"] or m["survivor"]) == m["draft_text"] for m in merges]
    done += [src not in notes and dst in notes for src, dst in moves]
    if done and all(done):
        return {"errors": [], "warnings": [], "applied": True, "operations": [], "link_rewrites": [], "aliases_to_add": {},
                "touched": [], "dirty": [], "ledger": None, "draft_issues": {}, "markdown": "Already applied; nothing to do.\n"}
    if any(done):
        errors.append("mapping is partially applied; restore the tree or finish by hand before retrying")
    for m in merges:
        for p in (m["survivor"], *m["absorbed"]):
            if p not in notes:
                errors.append(f"not an eligible note: {p}")
    for src, _ in moves:
        if src not in notes:
            errors.append(f"not an eligible note: {src}")
    if errors:
        return {"errors": sorted(set(errors)), "warnings": warnings, "applied": False, "operations": [], "link_rewrites": [],
                "aliases_to_add": {}, "touched": [], "dirty": [], "ledger": None, "draft_issues": {}, "markdown": ""}
    final = {p: p for p in notes}
    redirect, anchors, draft_headings = {}, {}, {}
    for m in merges:
        if m["rename"]:
            final[m["survivor"]] = m["rename"]
        for a in m["absorbed"]:
            final[a] = None
            redirect[a] = m["survivor"]
            anchors[a] = {str(x).casefold(): str(y) for x, y in (m.get("anchors", {}).get(a) or {}).items()}
        draft_headings[m["survivor"]] = {h.casefold(): h for _, h in k.Note.parse(m["survivor"], m["draft_text"].encode(), scope).headings}
    for src, dst in moves:
        final[src] = dst
    stems = k.defaultdict(list)
    for p, f in final.items():
        if f:
            stems[k.PurePosixPath(f).stem.casefold()].append(f)
    for stem, paths in sorted(stems.items()):
        if len(paths) > 1:
            errors.append(f"duplicate basename after the pass: {stem} ({', '.join(sorted(paths))})")
    # Draft checks and aliases.
    draft_issues, aliases_to_add = {}, {}
    for m in merges:
        survivor = m["survivor"]
        note = k.Note.parse(final[survivor], m["draft_text"].encode(), scope)
        problems = [f"{rule}: {detail}" for rule, detail in note.errors]
        for field in ("Date", "Type", "Categories"):
            if field not in note.meta:
                problems.append(f"field: {field}")
        headings = {h.casefold() for _, h in note.headings}
        if note.meta.get("Type") not in ("fleeting", "structure"):
            if "Mode" in note.meta:
                warnings.append(f"{survivor}: woven notes take the legacy profile; the draft declares Mode: {note.meta['Mode']}")
            for required in ("Abstract", "Links"):
                if required.casefold() not in headings:
                    problems.append(f"heading: {required}")
        if problems:
            draft_issues[survivor] = problems
        have = {normalize(str(x)).casefold() for x in (note.meta.get("Aliases") or [])} | {k.PurePosixPath(final[survivor]).stem.casefold()}
        wanted = []
        for a in m["absorbed"]:
            wanted.append(k.PurePosixPath(a).stem)
            wanted.extend(str(x) for x in (notes[a].meta.get("Aliases") or []) if x)
        missing = sorted({w for w in wanted if normalize(w).casefold() not in have}, key=str.casefold)
        if missing:
            aliases_to_add[survivor] = missing
    for src, dst in moves:
        old, new_stem = k.PurePosixPath(src).stem, k.PurePosixPath(dst).stem
        have = {normalize(str(x)).casefold() for x in (notes[src].meta.get("Aliases") or [])}
        if old.casefold() != new_stem.casefold() and old.casefold() not in have:
            aliases_to_add[src] = [old]
    # Link rewrites across every eligible note that remains.
    rewrites = []
    for p in sorted(notes):
        if p in redirect:
            continue
        lines = text_of(corpus, p).splitlines()
        start = body_start(lines)
        sole = {}
        for n, line in enumerate(lines, 1):
            if n > start and LIST.match(line):
                found = list(k.WIKI.finditer(line))
                if len(found) == 1:
                    status, matches = corpus.resolve(found[0][1].split("|", 1)[0].strip().partition("#")[0], p)
                    if status == "ok":
                        sole[n] = matches[0]
        survivors_listed = {t for t in sole.values() if t in {m["survivor"] for m in merges}}
        fence = None
        for n, line in enumerate(lines, 1):
            if n <= start:
                if not re.match(r"^(Before|Next):", line):
                    continue
            else:
                opened = re.match(r"^\s*(`{3,}|~{3,})", line)
                if opened:
                    marker = opened[1]
                    if fence is None:
                        fence = marker
                    elif marker[0] == fence[0] and len(marker) >= len(fence):
                        fence = None
                    continue
                if fence is not None:
                    continue
            spans = inline_code_spans(line)
            new = line

            def outside_code(m):
                return not any(a <= m.start() < b for a, b in spans)

            for m in list(k.WIKI.finditer(line)):
                if not outside_code(m):
                    continue
                raw = m[1]
                target_part, _, alias = raw.partition("|")
                target, _, anchor = target_part.partition("#")
                target = target.strip()
                if not target:
                    continue
                status, matches = corpus.resolve(target, p)
                if status != "ok":
                    continue
                t = matches[0]
                new_target = None
                if t in redirect:
                    survivor = redirect[t]
                    new_target = k.PurePosixPath(final[survivor]).stem
                    if anchor:
                        if anchor.casefold() in draft_headings[survivor]:
                            anchor = draft_headings[survivor][anchor.casefold()]
                        elif anchor.casefold() in anchors[t]:
                            anchor = anchors[t][anchor.casefold()]
                        else:
                            warnings.append(f"{p}:{n}: anchor #{anchor} of {t} has no heading in the woven note; dropped")
                            anchor = ""
                elif final[t] != t:
                    if "/" in target:
                        new_target = final[t][:-3] if final[t].endswith(".md") else final[t]
                    elif k.PurePosixPath(final[t]).stem != k.PurePosixPath(t).stem:
                        new_target = k.PurePosixPath(final[t]).stem
                if new_target is None:
                    continue
                if n <= start:
                    anchor = ""  # Before/Next fields point at notes, never at sections
                link = new_target + (f"#{anchor}" if anchor else "") + (f"|{alias}" if alias else "")
                new = new.replace(m[0], ("!" if m[0].startswith("!") else "") + f"[[{link}]]", 1)
            if n > start:
                for m in list(k.MDLINK.finditer(line)):
                    if not outside_code(m) or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", m[1]) or m[1].startswith("#"):
                        continue
                    target, _, anchor = k.unquote(m[1]).partition("#")
                    joined = os.path.normpath(os.path.join(str(k.PurePosixPath(p).parent), target)).replace(os.sep, "/")
                    rooted = os.path.normpath(target.lstrip("/")).replace(os.sep, "/")
                    candidates = [c for base in (joined, rooted) for c in ((base,) if base.endswith(".md") else (base + ".md", base))]
                    t = next((c for c in candidates if c in notes), None)
                    if t is None:
                        continue
                    destination = final[redirect.get(t, t)]
                    if destination == t and final[p] == p:
                        continue  # neither end moves: leave the author's link form alone
                    # Vault-root paths resolve both in Obsidian and in the structural lint; `../` forms do not lint.
                    rewritten = destination if target.endswith(".md") else destination[:-3]
                    rewritten = quote(rewritten, safe="/")
                    if rewritten != m[1].partition("#")[0]:
                        new = new.replace(m[0], m[0].replace(m[1], rewritten + (f"#{anchor}" if anchor else ""), 1), 1)
            if new == line:
                continue
            action = "rewrite"
            if n in sole and sole[n] in redirect and redirect[sole[n]] in survivors_listed:
                action, new = "drop", ""
            rewrites.append({"file": p, "line": n, "action": action, "old": line, "new": new})
    touched = set()
    for m in merges:
        touched.update((m["survivor"], *m["absorbed"]))
        if m["rename"]:
            touched.add(m["rename"])
    for src, dst in moves:
        touched.update((src, dst))
    touched.update(x["file"] for x in rewrites)
    touched = sorted(touched)
    ledger = None
    if merges:
        results = []
        for m in merges:
            texts = {p: text_of(corpus, p) for p in (m["survivor"], *m["absorbed"])}
            if not m.get("ledger"):
                results.append({"survivor": m["survivor"], "ok": False, "problem": "no ledger"})
                continue
            try:
                data = json.loads(read_any(root, m["ledger"]))
            except (OSError, ValueError, k.KnowledgeError) as e:
                results.append({"survivor": m["survivor"], "ok": False, "problem": f"cannot read ledger: {e}"})
                continue
            check = ledger_check(texts, m["draft_text"], data)
            results.append({"survivor": m["survivor"], "ok": check["ok"], "counts": check["counts"], "review": len(check["review"]),
                            "problems": {x: len(check[x]) for x in ("missing", "unknown", "mismatch", "dangling", "invalid") if check[x]}})
        ledger = {"ok": all(x["ok"] for x in results), "merges": results}
    operations = [{"op": "weave", "survivor": m["survivor"], "absorbed": m["absorbed"], "rename": m["rename"]} for m in merges]
    operations += [{"op": "move", "from": src, "to": dst} for src, dst in moves]
    report = {"errors": sorted(set(errors)), "warnings": warnings, "applied": False, "operations": operations,
              "link_rewrites": rewrites, "aliases_to_add": aliases_to_add, "touched": touched,
              "dirty": dirty_paths(root, touched), "ledger": ledger, "draft_issues": draft_issues}
    report["markdown"] = render(report)
    return report


def yaml_scalar(value):
    text = str(value)
    if re.search(r"[:#,\[\]{}&*!|>'\"%@`]", text) or text != text.strip() or text in ("", "null", "true", "false"):
        return json.dumps(text, ensure_ascii=False)
    return text


def with_aliases(draft, additions):
    """Return the draft with the aliases added to its frontmatter, keeping the author's list style."""
    if not additions:
        return draft
    lines = draft.splitlines(keepends=True)
    end = body_start(lines)
    if end == 0:
        raise k.KnowledgeError("Draft needs frontmatter to receive aliases")
    for i in range(1, end - 1):
        m = re.match(r"^Aliases:\s*(.*?)\s*$", lines[i])
        if not m:
            continue
        value = m[1]
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            items = ([inner] if inner else []) + [yaml_scalar(a) for a in additions]
            lines[i] = f"Aliases: [{', '.join(items)}]\n"
            return "".join(lines)
        if value == "":
            j = i + 1
            while j < end - 1 and re.match(r"^\s+-\s", lines[j]):
                j += 1
            lines[j:j] = [f"  - {yaml_scalar(a)}\n" for a in additions]
            return "".join(lines)
        lines[i] = f"Aliases: [{yaml_scalar(value)}, {', '.join(yaml_scalar(a) for a in additions)}]\n"
        return "".join(lines)
    lines[end - 1:end - 1] = [f"Aliases: [{', '.join(yaml_scalar(a) for a in additions)}]\n"]
    return "".join(lines)


def edited_text(text, rewrites):
    lines = text.splitlines(keepends=True)
    by_line = {x["line"]: x for x in rewrites}
    out = []
    for n, line in enumerate(lines, 1):
        change = by_line.get(n)
        if change is None:
            out.append(line)
        elif change["action"] == "rewrite":
            ending = line[len(line.rstrip("\r\n")):]
            out.append(change["new"] + ending)
    return "".join(out)


def commit_message(mapping, report):
    scope = mapping.get("scope") or "vault"
    label = k.PurePosixPath(str(scope)).name or "vault"
    weaves = [op for op in report["operations"] if op["op"] == "weave"]
    moves = [op for op in report["operations"] if op["op"] == "move"]
    absorbed = sum(len(op["absorbed"]) for op in weaves)
    parts = []
    if weaves:
        parts.append(f"weave {absorbed + len(weaves)} notes into {len(weaves)}")
    if moves:
        parts.append(f"move {len(moves)} notes")
    body = [f"refactor({label}): " + "; ".join(parts), ""]
    for op in weaves:
        body.append(f"- {', '.join(k.PurePosixPath(a).stem for a in op['absorbed'])} → {k.PurePosixPath(op['rename'] or op['survivor']).stem}")
    for op in moves:
        body.append(f"- {op['from']} → {op['to']}")
    body.append("")
    body.append(f"Inbound links rewritten: {len(report['link_rewrites'])}. Ledger-checked; catalog rebuilt.")
    return "\n".join(body) + "\n"


def apply(corpus, mapping, allow_dirty=False):
    """Perform a planned mapping, rebuild the catalog, stage exactly the touched files. Never commits."""
    report = plan(corpus, mapping)
    if report["applied"]:
        return {**report, "changed": False, "staged": [], "commit_message": ""}
    if report["errors"]:
        raise k.KnowledgeError("Mapping has errors: " + "; ".join(report["errors"]))
    if report["draft_issues"]:
        raise k.KnowledgeError("Draft has structural issues: " + json.dumps(report["draft_issues"], ensure_ascii=False))
    if report["ledger"] is not None and not report["ledger"]["ok"]:
        raise k.KnowledgeError("Preservation check failed: " + json.dumps(report["ledger"]["merges"], ensure_ascii=False))
    if report["dirty"] and not allow_dirty:
        raise k.KnowledgeError("Uncommitted edits in files the mapping touches: " + ", ".join(report["dirty"]))
    root = corpus.snapshot.root
    writes, deletes, moves = {}, [], []
    for m in mapping.get("merges", []):
        draft = read_any(root, m["draft"]).decode("utf-8-sig")
        writes[m["survivor"]] = with_aliases(draft, report["aliases_to_add"].get(m["survivor"], []))
        if m.get("rename"):
            moves.append((m["survivor"], m["rename"]))
        deletes.extend(m["absorbed"])
    by_file = k.defaultdict(list)
    for x in report["link_rewrites"]:
        by_file[x["file"]].append(x)
    for p, changes in by_file.items():
        writes[p] = edited_text(text_of(corpus, p), changes)
    for mv in mapping.get("moves", []):
        moves.append((mv["from"], mv["to"]))
        aliases = report["aliases_to_add"].get(mv["from"])
        if aliases:
            writes[mv["from"]] = with_aliases(writes.get(mv["from"], text_of(corpus, mv["from"])), aliases)
    for p, text in writes.items():
        k.safe_path(root, p).write_bytes(text.encode("utf-8"))
    for p in deletes:
        k.safe_path(root, p).unlink()
    for src, dst in moves:
        target = root / k.relative(dst)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(k.safe_path(root, src), target)
    snapshot = k.Snapshot(root, "worktree")
    rebuilt = k.Corpus(snapshot)
    k.write_outputs(snapshot, rebuilt.outputs())
    generated = [p for p in (".claude/index.md", ".claude/QUALITY.md", ".claude/index") if (root / p).exists()]
    k.git(root, "add", "-A", "--", *report["touched"], *generated)
    staged = sorted(os.fsdecode(x) for x in k.git(root, "diff", "--cached", "--name-only", "--no-renames", "-z").split(b"\0") if x)
    return {**report, "applied": True, "changed": True, "written": sorted(writes), "deleted": sorted(deletes),
            "moved": [{"from": a, "to": b} for a, b in moves], "staged": staged, "notes": len(rebuilt.notes),
            "commit_message": commit_message(mapping, report)}


def run(corpus, args):
    """CLI dispatch for `knowledge.py --vault V reorg <command>`; returns (report, exit code)."""
    root = corpus.snapshot.root
    command = args.reorg_command
    if command == "survey":
        return survey(corpus, args.target), 0
    if command == "units":
        name = k.relative(args.path)
        if name not in corpus.notes:
            raise k.KnowledgeError("No eligible note at that exact relative path")
        return {"path": name, "units": units(text_of(corpus, name))}, 0
    mapping = load_mapping(root, args.mapping)
    if command == "plan":
        report = plan(corpus, mapping)
        blocked = bool(report["errors"] or report["draft_issues"] or report["dirty"]) or (report["ledger"] is not None and not report["ledger"]["ok"])
        return report, int(blocked and not report["applied"])
    if command == "ledger":
        results = []
        for m in mapping.get("merges", []):
            texts = {p: text_of(corpus, p) for p in (m["survivor"], *m["absorbed"]) if p in corpus.notes}
            missing = [p for p in (m["survivor"], *m["absorbed"]) if p not in corpus.notes]
            if missing or not m.get("draft") or not m.get("ledger"):
                results.append({"survivor": m["survivor"], "ok": False, "problem": f"missing notes {missing}" if missing else "merge needs draft and ledger"})
                continue
            try:
                draft = read_any(root, m["draft"]).decode("utf-8-sig")
                data = json.loads(read_any(root, m["ledger"]))
            except (OSError, ValueError, UnicodeDecodeError, k.KnowledgeError) as e:
                results.append({"survivor": m["survivor"], "ok": False, "problem": str(e)})
                continue
            results.append({"survivor": m["survivor"], **ledger_check(texts, draft, data)})
        return {"ok": all(x["ok"] for x in results), "merges": results}, int(not all(x["ok"] for x in results))
    if command == "apply":
        return apply(corpus, mapping, allow_dirty=args.allow_dirty), 0
    raise k.KnowledgeError(f"Unknown reorg command {command!r}")


def render(report):
    out = ["# Reorganization plan", ""]
    if report["errors"]:
        out += ["## Errors", ""] + [f"- {e}" for e in report["errors"]] + [""]
    out += ["## Operations", "", "| Op | From | To |", "|---|---|---|"]
    for op in report["operations"]:
        if op["op"] == "weave":
            out.append(f"| weave | {', '.join(f'`{a}`' for a in op['absorbed'])} | `{op['rename'] or op['survivor']}` |")
        else:
            out.append(f"| move | `{op['from']}` | `{op['to']}` |")
    out += ["", f"## Link rewrites ({len(report['link_rewrites'])})", ""]
    for x in report["link_rewrites"]:
        out.append(f"- `{x['file']}:{x['line']}` {x['action']}: `{x['old'].strip()}`" + (f" → `{x['new'].strip()}`" if x["new"] else ""))
    if report["aliases_to_add"]:
        out += ["", "## Aliases to add", ""] + [f"- `{p}`: {', '.join(a)}" for p, a in report["aliases_to_add"].items()]
    if report["draft_issues"]:
        out += ["", "## Draft issues", ""] + [f"- `{p}`: {'; '.join(v)}" for p, v in report["draft_issues"].items()]
    if report["ledger"] is not None:
        out += ["", "## Ledger", ""] + [f"- `{x['survivor']}`: " + ("ok" if x["ok"] else "NOT ok") + f" {json.dumps({k_: v for k_, v in x.items() if k_ not in ('survivor', 'ok')}, ensure_ascii=False)}" for x in report["ledger"]["merges"]]
    if report["dirty"]:
        out += ["", "## Files with uncommitted edits (apply refuses)", ""] + [f"- `{p}`" for p in report["dirty"]]
    if report["warnings"]:
        out += ["", "## Warnings", ""] + [f"- {w}" for w in report["warnings"]]
    out += ["", f"Touched files: {len(report['touched'])}", ""]
    return "\n".join(out)
