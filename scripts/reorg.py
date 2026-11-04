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
