"""note_update.py through its command line only, the way the note-update skill runs it, against a
temporary vault (spaces and CJK in its path), a bare origin, a linked worktree and a fake `gh`.
Run: python3 -B -m unittest discover -s tests -p 'test_note_update.py' -v"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).parents[1] / "scripts" / "note_update.py"
NOTE = "555.tools/Tools-Agent-Trust-Pyramid.md"
MAP = "000.Index/CS Map.md"
SCOPE = {"version": 1, "domains": {"cs": "111.cs", "tools": "555.tools"}, "maps": ["000.Index"]}


def page(mode=None, body="Body."):
    mode_line = f"Mode: {mode}\n" if mode else ""
    return f"---\nDate: 2026-11-01\nType: literature\n{mode_line}Categories: [Tools]\nAliases: []\n---\n### Abstract\n{body}\n### Links\n"


FILES = {
    "docs/knowledge/scope.json": json.dumps(SCOPE),
    NOTE: page("thesis", "信任金字塔 trust pyramid."),
    "111.cs/CS-Harness.md": page("atom"),
    "111.cs/CS-Old-Note.md": page(),
    MAP: "---\nType: structure\n---\n[[Tools-Agent-Trust-Pyramid]]\n",
    "111.cs/筆記.md": page("atom"),
    "raw/Source.md": "a source\n",
    "docs/workflows/vault-authoring.md": "rules\n",
    ".obsidian/workspace.json": "{}\n",
    ".claude/index.md": "catalog\n",
}


class NoteUpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="note update 空間 ")
        base = Path(self.tmp.name).resolve()
        self.vault, self.origin, self.bin = base / "CS 筆記 vault", base / "origin.git", base / "bin"
        self.gh_log = base / "gh-calls.log"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(f'#!/bin/sh\necho "$*" >> "{self.gh_log}"\necho "gh: unexpected call" >&2\nexit 97\n')
        gh.chmod(0o755)
        self.env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}"}
        self.git(base, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.git(base, "init", "-q", "-b", "main", str(self.vault))
        for name, text in FILES.items():
            self.put(self.vault, name, text)
        self.git(self.vault, "config", "user.email", "test@example.invalid")
        self.git(self.vault, "config", "user.name", "Note Update Test")
        (self.vault / ".git/info/exclude").write_text(".claude/worktrees/\n")
        self.git(self.vault, "add", ".")
        self.git(self.vault, "commit", "-qm", "fixture")
        self.git(self.vault, "remote", "add", "origin", str(self.origin))
        self.git(self.vault, "push", "-q", "-u", "origin", "main")
        self.git(self.vault, "remote", "set-head", "origin", "main")
        self.tree = self.vault / ".claude/worktrees/docs-update-tools-agent-trust-pyramid"
        self.git(self.vault, "worktree", "add", "-q", "--detach", str(self.tree), "origin/main")

    def tearDown(self):
        self.assertFalse(self.gh_log.exists(), "note_update.py called gh")
        self.tmp.cleanup()

    # --- helpers ---

    def put(self, root, name, text):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def git(self, cwd, *args):
        p = subprocess.run(["git", "-C", str(cwd), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, env=getattr(self, "env", None))
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.strip()

    def run_script(self, *args, vault=None):
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--vault", str(vault or self.vault), *args],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
        lines = p.stdout.splitlines()
        self.assertEqual(len(lines), 1, f"one JSON object expected: {p.stdout!r} {p.stderr!r}")
        return p.returncode, json.loads(lines[0]), p.stderr

    def ok(self, *args):
        code, result, err = self.run_script(*args)
        self.assertEqual(code, 0, err)
        return result

    def refused(self, *args, why=""):
        code, result, err = self.run_script(*args)
        self.assertEqual(code, 2, result)
        self.assertIn(why, result["error"])
        self.assertIn(result["error"], err)
        return result

    def snapshot(self):
        """What the primary checkout holds: HEAD, porcelain status, the note's bytes and inode."""
        stat = (self.vault / NOTE).stat()
        return (self.git(self.vault, "rev-parse", "HEAD"), self.git(self.vault, "status", "--porcelain"),
                (self.vault / NOTE).read_bytes(), stat.st_ino)

    def merge(self, text):
        """What ship and approve do, in short: the worktree's commit lands on origin's main."""
        self.put(self.tree, NOTE, text)
        self.git(self.tree, "commit", "-qam", "docs(tools): update the note")
        self.git(self.tree, "push", "-q", "origin", "HEAD:main")

    # --- resolve ---

    def test_resolve_takes_an_exact_path_and_names_the_profile(self):
        self.assertEqual(self.ok("resolve", NOTE), {"note": NOTE, "profile": "thesis"})
        self.assertEqual(self.ok("resolve", str(self.vault / NOTE))["note"], NOTE)
        self.assertEqual(self.ok("resolve", "111.cs/CS-Harness.md")["profile"], "atom")
        self.assertEqual(self.ok("resolve", "111.cs/CS-Old-Note.md")["profile"], "legacy")
        self.assertEqual(self.ok("resolve", MAP)["profile"], "map")
        self.assertEqual(self.ok("resolve", "111.cs/筆記.md")["note"], "111.cs/筆記.md")

    def test_resolve_refuses_what_is_not_an_eligible_note(self):
        for target in ("raw/Source.md", "docs/workflows/vault-authoring.md", ".obsidian/workspace.json",
                       ".claude/index.md", "../outside.md", str(self.tree / NOTE)):
            with self.subTest(target=target):
                self.refused("resolve", target)
        self.refused("resolve", "Tools-Agent-Trust-Pyramid", why="not an eligible note")
        self.refused("resolve", "555.tools/Tools-Missing.md", why="no note at")

    def test_a_worktree_is_not_a_vault(self):
        code, result, _ = self.run_script("resolve", NOTE, vault=self.tree)
        self.assertEqual(code, 1)
        self.assertIn("not the primary checkout", result["error"])


if __name__ == "__main__":
    unittest.main()
