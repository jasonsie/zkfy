#!/usr/bin/env python3
"""Machine-local binding for the shared knowledge CLI; no cwd-derived vault."""
import json
import os
from pathlib import Path
import sys


def main():
    path = Path(os.environ.get("ZKFY_KNOWLEDGE_CONFIG", "~/.config/zkfy/knowledge.json")).expanduser()
    try:
        config = json.loads(path.read_text())
        python, tool, vault = (str(Path(config[k]).expanduser().resolve(strict=True)) for k in ("python", "tool", "vault"))
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"vault-knowledge: unavailable binding: {e}", file=sys.stderr)
        return 2
    os.execv(python, [python, "-B", tool, "--vault", vault, *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())
