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
