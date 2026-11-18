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


def page(mode=None, body="Body.", aliases="[]"):
    mode_line = f"Mode: {mode}\n" if mode else ""
    return (f"---\nDate: 2026-11-01\nType: literature\n{mode_line}Categories: [Tools]\nAliases: {aliases}\n---\n"
            f"### Abstract\n{body}\n### Links\n")


LONG_ATOM = ("---\nDate: 2026-11-01\nType: literature\nMode: atom\nCategories: [CS]\nAliases: []\n---\n"
             "### Definition\n" + "word " * 505 + "\n```python\n" + "code " * 50 + "\n```\n"
             "### Mental Model\n" + "diagram " * 100 + "\n### Links\n- [[CS-Harness]]\n")
THEMES = ("---\nDate: 2026-11-01\nType: literature\nMode: thesis\nCategories: [Tools]\nAliases: []\n"
          "Src: 'https://example.com/talk'\n---\n### 執行摘要\nSummary.\n### Mental Model\nModel.\n"
          "### Short Theme\n" + "word " * 150 + "\n### Right Theme\n" + "字" * 300 + "\n### Links\n")


FILES = {
    "docs/knowledge/scope.json": json.dumps(SCOPE),
    NOTE: page("thesis", "信任金字塔 trust pyramid.", aliases="[Agent Trust Pyramid, 代理信任金字塔]"),
    "111.cs/CS-Harness.md": page("atom", aliases="[Harness]"),
    "555.tools/Tools-Harness-Setup.md": page(aliases="[harness]"),
    "111.cs/CS-Old-Note.md": page(),
    "111.cs/Shared-Name.md": page(),
    "555.tools/Shared-Name.md": page(),
    "555.tools/Tools-Clip-Page.md": page("clip", "Verbatim."),
    MAP: "---\nType: structure\n---\n[[Tools-Agent-Trust-Pyramid]]\n",
    "111.cs/筆記.md": page("atom"),
    "111.cs/CS-Long-Atom.md": LONG_ATOM,
    "555.tools/Tools-Thesis-Themes.md": THEMES,
    "111.cs/CS-Links-In.md": page(body="See [[Tools-Agent-Trust-Pyramid#Abstract]] and [[Tools-Agent-Trust-Pyramid]]."),
    "raw/Source.md": "a source\n",
    "docs/workflows/vault-authoring.md": "rules\n",
    "template/Template-Note.md": page(),
    "notes/Loose-Note.md": page(),
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

    def resolved(self, value):
        result = self.ok("resolve", value)
        return result["note"], result["profile"], result["matched_by"]

    def test_resolve_takes_an_exact_path_and_names_the_profile(self):
        self.assertEqual(self.resolved(NOTE), (NOTE, "thesis", "path"))
        self.assertEqual(self.resolved(str(self.vault / NOTE)), (NOTE, "thesis", "path"))
        self.assertEqual(self.resolved("555.tools/Tools-Agent-Trust-Pyramid"), (NOTE, "thesis", "path"))
        self.assertEqual(self.resolved("111.cs/CS-Harness.md")[1], "atom")
        self.assertEqual(self.resolved("111.cs/CS-Old-Note.md")[1], "legacy")
        self.assertEqual(self.resolved("555.tools/Tools-Clip-Page.md")[1], "clip")
        self.assertEqual(self.resolved(MAP)[1], "map")
        self.assertEqual(self.resolved("111.cs/筆記.md")[0], "111.cs/筆記.md")

    def test_resolve_takes_a_basename_then_an_alias(self):
        self.assertEqual(self.resolved("Tools-Agent-Trust-Pyramid"), (NOTE, "thesis", "basename"))
        self.assertEqual(self.resolved("tools agent trust pyramid.md"), (NOTE, "thesis", "basename"))
        self.assertEqual(self.resolved("CS Map"), (MAP, "map", "basename"))
        self.assertEqual(self.resolved("agent trust pyramid"), (NOTE, "thesis", "alias"))
        self.assertEqual(self.resolved("代理信任金字塔"), (NOTE, "thesis", "alias"))
        self.assertEqual(self.resolved("筆記"), ("111.cs/筆記.md", "atom", "basename"))

    def test_resolve_lists_the_candidates_when_several_match(self):
        for value, how, paths in (("Shared-Name", "basename", ["111.cs/Shared-Name.md", "555.tools/Shared-Name.md"]),
                                  ("Harness", "alias", ["111.cs/CS-Harness.md", "555.tools/Tools-Harness-Setup.md"])):
            with self.subTest(value=value):
                code, result, err = self.run_script("resolve", value)
                self.assertEqual(code, 3, result)
                self.assertNotIn("note", result)
                self.assertEqual([c["note"] for c in result["candidates"]], paths)
                self.assertEqual({c["matched_by"] for c in result["candidates"]}, {how})
                self.assertIn("pick one", err)

    def test_resolve_stops_on_no_match_with_suggestions(self):
        result = self.refused("resolve", "trust pyramid", why="no eligible note matches")
        self.assertNotIn("note", result)
        self.assertIn(NOTE, [s["note"] for s in result["suggestions"]])
        self.refused("resolve", "555.tools/Tools-Missing.md", why="no eligible note matches")

    def test_resolve_refuses_each_target_it_must_never_touch(self):
        for target, why in (("raw/Source.md", "raw/"), ("docs/workflows/vault-authoring.md", "docs/"),
                            (".obsidian/workspace.json", "Obsidian"), (".claude/index.md", "generated catalog"),
                            ("template/Template-Note.md", "scope policy"), ("notes/Loose-Note.md", "scope policy"),
                            (str(self.tree / NOTE), "agents' worktree folder"), ("../outside.md", "traversal"),
                            ("/elsewhere/Note.md", "outside the vault")):
            with self.subTest(target=target):
                result = self.refused("resolve", target, why=why)
                self.assertNotIn("note", result)

    def test_resolve_never_returns_a_note_that_lives_only_in_a_worktree(self):
        self.put(self.tree, "555.tools/Tools-Only-In-Worktree.md", page(aliases="[Worktree Only]"))
        for value in ("Tools-Only-In-Worktree", "Worktree Only", "555.tools/Tools-Only-In-Worktree.md"):
            with self.subTest(value=value):
                self.refused("resolve", value, why="no eligible note matches")

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

    def test_state_gives_case_a_for_an_instruction_clean_or_dirty(self):
        clean = self.ok("state", NOTE, "--instruction-given")
        self.assertEqual((clean["case"], clean["dirty"]), ("A", False))
        self.put(self.vault, NOTE, page("thesis", "My edit first."))
        dirty = self.ok("state", NOTE, "--instruction-given")
        self.assertEqual((dirty["case"], dirty["dirty"]), ("A", True))
        carried = self.ok("carry", NOTE, str(self.tree))  # the hand edit becomes the agent's base
        self.assertTrue(carried["identical"])
        self.assertIn("My edit first.", (self.tree / NOTE).read_text(encoding="utf-8"))

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

    # --- plan ---

    def test_plan_counts_an_atom_body_without_code_or_mental_model(self):
        budget = self.ok("plan", "111.cs/CS-Long-Atom.md")["budget"]
        self.assertEqual((budget["rule"], budget["count"], budget["limit"]), ("atom", 505, 500))
        self.assertEqual(len(budget["warnings"]), 1)

    def test_plan_counts_each_thesis_theme(self):
        budget = self.ok("plan", "555.tools/Tools-Thesis-Themes.md")["budget"]
        self.assertEqual(budget["themes"], [{"heading": "Short Theme", "count": 150},
                                            {"heading": "Right Theme", "count": 300}])
        self.assertEqual(len(budget["warnings"]), 1)
        self.assertIn("Short Theme", budget["warnings"][0])
        self.assertEqual(self.ok("plan", MAP)["budget"], {"rule": None, "warnings": []})

    def test_plan_counts_a_note_with_no_mode_as_atom_like_vault_lint(self):
        budget = self.ok("plan", "111.cs/CS-Old-Note.md")["budget"]
        self.assertEqual((budget["rule"], budget["count"], budget["warnings"]), ("atom", 1, []))

    def test_plan_lists_the_inbound_links_and_the_headings_they_target(self):
        plan = self.ok("plan", NOTE)
        self.assertEqual((plan["note"], plan["profile"]), (NOTE, "thesis"))
        self.assertEqual(plan["inbound"], [
            {"from": MAP, "map": True, "heading": None, "broken": False},
            {"from": "111.cs/CS-Links-In.md", "map": False, "heading": None, "broken": False},
            {"from": "111.cs/CS-Links-In.md", "map": False, "heading": "Abstract", "broken": False}])

    # --- edit-check ---

    def edited(self, note, old, new):
        self.put(self.tree, note, (self.tree / note).read_text(encoding="utf-8").replace(old, new, 1))
        return self.ok("edit-check", note, str(self.tree))

    def test_edit_check_names_the_one_changed_section(self):
        check = self.edited("555.tools/Tools-Thesis-Themes.md", "Model.", "A better model.")
        self.assertEqual(check["frontmatter"], "same")
        self.assertEqual([(s["heading"], s["status"]) for s in check["sections"]],
                         [("執行摘要", "same"), ("Mental Model", "changed"), ("Short Theme", "same"),
                          ("Right Theme", "same"), ("Links", "same")])
        self.assertEqual(check["problems"], [])
        self.assertEqual(check["profile"], {"before": "thesis", "after": "thesis"})

    def test_edit_check_flags_frontmatter_keys_and_provenance(self):
        check = self.edited("555.tools/Tools-Thesis-Themes.md", "Src: 'https://example.com/talk'\n",
                            "Src: 'https://example.com/other'\nSub-Categories: [x]\n")
        self.assertEqual(check["frontmatter"], "changed")
        self.assertEqual(check["keys"]["added"], ["Sub-Categories"])
        self.assertEqual(check["provenance_changed"], ["Src"])
        self.assertEqual(len(check["problems"]), 2)

    def test_edit_check_lets_a_conversion_set_mode_and_names_the_profile_change(self):
        check = self.edited("111.cs/CS-Old-Note.md", "Categories: [Tools]\n", "Mode: atom\nCategories: [Tools]\n")
        self.assertEqual(check["keys"]["added"], ["Mode"])
        self.assertEqual(check["problems"], ["profile changed from legacy to atom"])

    def test_edit_check_reads_against_the_worktrees_base_not_later_typing(self):
        self.put(self.vault, NOTE, page("thesis", "Typed in Obsidian during the run."))  # clean when the run began
        check = self.edited(NOTE, "### Links\n", "### Links\n- [[CS-Harness]]\n")
        self.assertEqual([s["heading"] for s in check["sections"] if s["status"] != "same"], ["Links"])

    def test_edit_check_with_a_carry_reads_against_the_carried_copy(self):
        self.put(self.vault, NOTE, page("thesis", "My edit."))
        sha = self.ok("carry", NOTE, str(self.tree))["sha256"]
        self.put(self.tree, NOTE, page("thesis", "My edit.").replace("### Links\n", "### Links\n- [[CS-Harness]]\n"))
        check = self.ok("edit-check", NOTE, str(self.tree), "--sha256", sha)
        self.assertEqual([s["heading"] for s in check["sections"] if s["status"] != "same"], ["Links"])
        self.put(self.vault, NOTE, page("thesis", "My edit, typed on."))
        self.refused("edit-check", NOTE, str(self.tree), "--sha256", sha, why="changed since the carry")

    def test_edit_check_flags_a_clip_body_change_but_not_its_links(self):
        clip = "555.tools/Tools-Clip-Page.md"
        self.assertEqual(self.edited(clip, "### Links\n", "### Links\n- [[CS-Harness]]\n")["problems"], [])
        check = self.edited(clip, "Verbatim.", "Summarised.")
        self.assertEqual(len(check["problems"]), 1)
        self.assertIn("ADR-0004", check["problems"][0])

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

    # --- case A on a dirty note: the hand edit lands as its own commit, the agent's on top ---

    def land_two_commits(self, mine, agent):
        self.put(self.vault, NOTE, mine)
        sha = self.ok("carry", NOTE, str(self.tree))["sha256"]
        self.put(self.tree, NOTE, agent)
        staged = self.ok("stage-carried", NOTE, str(self.tree), "--sha256", sha)
        self.assertEqual(self.git(self.tree, "show", f":{NOTE}"), mine.rstrip("\n"))
        self.assertEqual(self.git(self.tree, "rev-parse", f":{NOTE}"), staged["staged"])
        self.assertEqual((self.tree / NOTE).read_text(encoding="utf-8"), agent)
        self.git(self.tree, "commit", "-qm", "docs(tools): the hand edit")
        self.git(self.tree, "commit", "-qam", "docs(tools): the agent's edit")
        self.git(self.tree, "push", "-q", "origin", "HEAD:main")

    def test_land_check_updates_a_copy_that_merged_under_a_later_commit(self):
        mine, agent = page("thesis", "My typo fix."), page("thesis", "My typo fix. Then the split.")
        self.land_two_commits(mine, agent)
        result = self.ok("land-check", NOTE)
        self.assertEqual((result["superseded"], result["fast_forwarded"], result["restored"]), (True, True, True))
        self.assertEqual((self.vault / NOTE).read_text(encoding="utf-8"), agent)
        self.assertEqual(self.git(self.vault, "status", "--porcelain"), "")
        self.assertEqual(self.git(self.vault, "rev-parse", "HEAD"), self.git(self.vault, "rev-parse", "origin/main"))

    def test_land_check_still_refuses_a_copy_edited_again_after_the_carry(self):
        self.land_two_commits(page("thesis", "My typo fix."), page("thesis", "My typo fix. Then the split."))
        self.put(self.vault, NOTE, page("thesis", "My typo fix, and more typing."))
        before = self.snapshot()
        self.refused("land-check", NOTE, why="differs from what merged")
        self.assertEqual(self.snapshot(), before)

    def test_stage_carried_refuses_a_copy_changed_since_the_carry(self):
        self.put(self.vault, NOTE, page("thesis", "My edit."))
        sha = self.ok("carry", NOTE, str(self.tree))["sha256"]
        self.put(self.vault, NOTE, page("thesis", "My edit, typed on."))
        self.refused("stage-carried", NOTE, str(self.tree), "--sha256", sha, why="changed since the carry")
        self.assertEqual(self.git(self.tree, "diff", "--cached", "--name-only"), "")


if __name__ == "__main__":
    unittest.main()
