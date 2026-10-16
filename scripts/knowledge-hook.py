#!/usr/bin/env python3
"""Scoped plugin-hook bridge. Exit 3 lets an unscoped vault retain legacy behavior."""
import json
from pathlib import Path
import sys


def main(kind, filename):
    path = Path(filename).expanduser().absolute()
    # Never probe inside a source directory while locating the ancestor policy.
    source = next((i for i, part in enumerate(path.parts) if part.casefold() == "raw"), None)
    start = Path(*path.parts[:source]) if source is not None else path.parent
    root = next((p for p in (start, *start.parents)
                 if (p / "docs/knowledge/scope.json").is_file()), None)
    if root is None:
        return 3
    relative = path.relative_to(root).as_posix()
    if any(p.casefold() == "raw" for p in Path(relative).parts):
        if kind == "guard":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                  "permissionDecision": "deny", "permissionDecisionReason":
                  "This vault excludes raw/ from knowledge and maintenance workflows."}}))
        return 0
    from knowledge import KnowledgeError, POLICY, Scope, read_file, safe_path
    try:
        scope = Scope(read_file(root, POLICY))
        safe_path(root, relative)
    except (KnowledgeError, OSError) as e:
        if kind == "guard":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                  "permissionDecision": "deny", "permissionDecisionReason": str(e)}}))
        else:
            print(f"zkfy: scoped reminder unavailable: {e}", file=sys.stderr)
        return 0
    if kind == "index" and scope.eligible(relative):
        print(json.dumps({"index_update_needed": True, "note_path": relative,
              "reminder": "After separately approved authoring, run scoped vault-index/build. "
                          "Generated artifacts only; never rebuild or log during a query. "
                          "The commit hook validates the staged snapshot."}))
    # A configured vault is valid regardless of the legacy hardcoded folder layout.
    # Do not create output/ or redirect authored files.
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
