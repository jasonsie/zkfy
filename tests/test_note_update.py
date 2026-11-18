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

    # --- state ---

    def test_state_finds_case_b_from_the_note_alone(self):
        self.put(self.vault, ".obsidian/workspace.json", '{"open": 1}\n')
        self.put(self.vault, "111.cs/CS-Harness.md", page("atom", "Someone else's edit."))
        self.assertEqual(self.ok("state", NOTE)["case"], "C")
        self.put(self.vault, NOTE, page("thesis", "My edit."))
        state = self.ok("state", NOTE)
        self.assertEqual((state["case"], state["dirty"], state["status"]), ("B", True, " M"))
        self.assertEqual(self.ok("state", NOTE, "--instruction-given")["case"], "A")

    def test_state_refuses_an_untracked_note(self):
        self.put(self.vault, "555.tools/Tools-New.md", page())
        self.refused("state", "555.tools/Tools-New.md", why="not tracked")

    # --- names ---

    def test_names_derive_the_branch_scope_and_subject_stub(self):
        self.assertEqual(self.ok("names", NOTE), {"note": NOTE, "branch": "docs/update-tools-agent-trust-pyramid",
                                                  "scope": "tools", "subject_stub": "docs(tools): "})
        names = self.ok("names", MAP)
        self.assertEqual((names["branch"], names["scope"]), ("docs/update-cs-map", "index"))
        self.refused("names", "111.cs/筆記.md", why="no ASCII branch name")

    # --- carry ---

    def test_carry_copies_the_primary_copy_byte_for_byte(self):
        self.put(self.vault, NOTE, page("thesis", "My edit, 我的修改."))
        before = self.snapshot()
        result = self.ok("carry", NOTE, str(self.tree))
        self.assertEqual((result["carried"], result["identical"]), (True, True))
        self.assertEqual((self.tree / NOTE).read_bytes(), (self.vault / NOTE).read_bytes())
        self.assertEqual(self.snapshot(), before)
        again = self.ok("carry", NOTE, str(self.tree))
        self.assertEqual((again["carried"], again["identical"]), (False, True))

    def test_carry_never_overwrites_the_worktrees_own_edits(self):
        self.put(self.vault, NOTE, page("thesis", "My edit."))
        self.put(self.tree, NOTE, page("thesis", "The agent's edit."))
        self.refused("carry", NOTE, str(self.tree), why="edits of its own")
        self.assertIn("The agent's edit.", (self.tree / NOTE).read_text(encoding="utf-8"))

    def test_carry_refuses_when_the_note_changed_on_the_base_since(self):
        self.merge(page("thesis", "Merged elsewhere."))
        other = self.vault / ".claude/worktrees/docs-later"
        self.git(self.vault, "fetch", "-q", "origin")
        self.git(self.vault, "worktree", "add", "-q", "--detach", str(other), "origin/main")
        self.put(self.vault, NOTE, page("thesis", "My edit on the old base."))
        self.refused("carry", NOTE, str(other), why="carrying would undo that change")
        self.assertIn("Merged elsewhere.", (other / NOTE).read_text(encoding="utf-8"))

    def test_carry_needs_a_linked_worktree_of_this_vault(self):
        self.put(self.vault, NOTE, page("thesis", "My edit."))
        for where in (self.vault, Path(self.tmp.name) / "bin"):
            with self.subTest(where=where):
                self.refused("carry", NOTE, str(where), why="worktree")

    # --- land-check ---

    def test_land_check_fast_forwards_when_the_copy_is_what_merged(self):
        mine = page("thesis", "My edit, 我的修改.")
        self.put(self.vault, NOTE, mine)
        self.put(self.vault, ".obsidian/workspace.json", '{"open": 1}\n')
        self.ok("carry", NOTE, str(self.tree))
        self.merge(mine)
        inode = (self.vault / NOTE).stat().st_ino
        result = self.ok("land-check", NOTE)
        self.assertEqual((result["identical"], result["fast_forwarded"], result["restored"]), (True, True, True))
        self.assertEqual(self.git(self.vault, "rev-parse", "HEAD"), self.git(self.vault, "rev-parse", "origin/main"))
        self.assertEqual(self.git(self.vault, "status", "--porcelain"), "M .obsidian/workspace.json")
        self.assertEqual((self.vault / NOTE).read_text(encoding="utf-8"), mine)
        self.assertEqual((self.vault / NOTE).stat().st_ino, inode)  # staged, never rewritten

    def test_land_check_refuses_a_copy_that_diverged_and_touches_nothing(self):
        mine = page("thesis", "My edit.")
        self.put(self.vault, NOTE, mine)
        self.ok("carry", NOTE, str(self.tree))
        self.merge(mine)
        self.put(self.vault, NOTE, page("thesis", "My edit, and a later one."))
        before = self.snapshot()
        result = self.refused("land-check", NOTE, why="differs from what merged")
        self.assertIn("+My edit, and a later one.", result["difference"])
        self.assertIn("-My edit.", result["difference"])
        _, _, err = self.run_script("land-check", NOTE)
        self.assertIn("+My edit, and a later one.", err)
        self.assertEqual(self.snapshot(), before)

    def test_land_check_fast_forwards_a_clean_primary(self):
        self.merge(page("thesis", "The agent's edit."))
        result = self.ok("land-check", NOTE)
        self.assertEqual((result["dirty"], result["fast_forwarded"], result["restored"]), (False, True, False))
        self.assertIn("The agent's edit.", (self.vault / NOTE).read_text(encoding="utf-8"))
        self.assertEqual(self.git(self.vault, "status", "--porcelain"), "")

    def test_land_check_refuses_before_touching_when_another_file_blocks(self):
        mine = page("thesis", "My edit.")
        self.put(self.vault, NOTE, mine)
        self.ok("carry", NOTE, str(self.tree))
        self.put(self.tree, "111.cs/CS-Harness.md", page("atom", "Also changed by the PR."))
        self.merge(mine)
        self.put(self.vault, "111.cs/CS-Harness.md", page("atom", "Uncommitted here."))
        before = self.snapshot()
        result = self.refused("land-check", NOTE, why="would block the fast-forward")
        self.assertEqual(result["clash"], ["111.cs/CS-Harness.md"])
        self.assertEqual(self.snapshot(), before)


    def test_a_refused_fast_forward_puts_back_the_index_it_found(self):
        mine = page("thesis", "My edit.")
        self.put(self.vault, NOTE, page("thesis", "My staged draft."))
        self.git(self.vault, "add", NOTE)
        self.put(self.vault, NOTE, mine)  # status MM: the user's own staging stays theirs
        self.ok("carry", NOTE, str(self.tree))
        self.put(self.tree, "z.attachments/pic", "a file the PR adds\n")
        self.git(self.tree, "add", "z.attachments/pic")
        self.merge(mine)
        self.put(self.vault, "z.attachments/pic/inner.txt", "untracked, in the way\n")
        index = self.git(self.vault, "ls-files", "--stage", "--", NOTE)
        before = self.snapshot()
        code, result, _ = self.run_script("land-check", NOTE)
        self.assertEqual(code, 1, result)
        self.assertIn("git refused the fast-forward", result["error"])
        self.assertEqual(self.git(self.vault, "ls-files", "--stage", "--", NOTE), index)
        self.assertEqual(self.snapshot(), before)

if __name__ == "__main__":
    unittest.main()
