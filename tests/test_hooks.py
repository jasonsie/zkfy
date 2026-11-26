"""The two hook scripts in the shapes each CLI sends: Claude Code's, which Codex and the Pi
extension share, and Antigravity's. Run: python3 -B -m unittest discover -s tests -p 'test_hooks.py' -v"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parents[1]
HOOKS = ROOT / "hooks"
SCOPE = '{"version": 1, "domains": {"cs": "111.cs"}}'
FOLDERS = ("cs", "web", "ai", "principle", "devops", "math", "000.Index", "row")  # the legacy layout
NOTE = "---\nDate: 2026-11-23\nType: literature\nCategories: [CS]\n---\n### Abstract\nx\n"  # a note, by its frontmatter
SKILL = "---\nname: x\ndescription: y\n---\n# X\n"  # frontmatter, but no note's


def run(script, payload, cwd):
    proc = subprocess.run(["bash", str(HOOKS / script)], input=json.dumps(payload),
                          capture_output=True, text=True, cwd=cwd)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def claude(tool, path, content="x"):
    return {"tool_name": tool, "tool_input": {"file_path": str(path), "content": content}}


def agy(tool, path, workspace, content="x"):
    return {"toolCall": {"name": tool, "args": {"TargetFile": str(path), "CodeContent": content}},
            "workspacePaths": [str(workspace)] if workspace else [], "conversationId": "t"}


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.plain = self.tmp / "plain"  # a zkfied folder (.claude/) without the legacy layout
        (self.plain / ".claude").mkdir(parents=True)
        (self.plain / "raw").mkdir()
        self.vault = self.tmp / "vault"  # a configured vault
        (self.vault / "docs/knowledge").mkdir(parents=True)
        (self.vault / "docs/knowledge/scope.json").write_text(SCOPE)
        (self.vault / "111.cs").mkdir()
        (self.vault / "raw").mkdir()
        self.legacy = self.tmp / "legacy"
        for folder in FOLDERS:
            (self.legacy / folder).mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def guard(self, payload, cwd, proc=None, send_cwd=True):
        # Claude Code's payload carries the session's cwd; the process runs there unless `proc` says otherwise
        if send_cwd and "toolCall" not in payload:
            payload = {**payload, "cwd": str(cwd)}
        code, out, _ = run("validate-zk-structure.sh", payload, proc or cwd)
        self.assertEqual(code, 0)
        return json.loads(out) if out else None

    def worktree(self):
        """A git repository and a linked worktree of it, whose .git is a file."""
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        main, linked = self.tmp / "repo", self.tmp / "repo-wt"
        for args in (["init", "-q", str(main)],
                     ["-C", str(main), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x"],
                     ["-C", str(main), "worktree", "add", "-q", str(linked)]):
            subprocess.run(["git", *args], check=True, capture_output=True, env=env)
        return main, linked

    def signal(self, payload, cwd):
        code, out, err = run("signal-index-update.sh", payload, cwd)
        self.assertEqual(code, 0)
        return (json.loads(out) if out else None), err

    # Claude Code's shape (Codex and the Pi extension send the same)

    def test_a_note_outside_a_vault_is_redirected_to_output(self):
        out = self.guard(claude("Write", self.plain / "note.md", NOTE), self.plain)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "allow")
        self.assertEqual(out["updatedInput"], {"file_path": str(self.plain / "output/note.md"), "content": NOTE})
        self.assertIn("output", out["additionalContext"])
        self.assertTrue((self.plain / "output").is_dir())

    def test_an_ordinary_markdown_file_outside_a_vault_is_left_where_it_is(self):
        # a repo's docs, a skill, a file in another folder: Markdown, but no note
        for path, content in ((self.plain / "docs/plans/plan.md", "# Plan\n"), (self.plain / "skills/x/SKILL.md", SKILL),
                              (self.tmp / "elsewhere/pr-body.md", "## Summary\n"), (self.plain / "empty.md", ""),
                              (self.plain / "open.md", "---\nType: literature\nCategories: [CS]\n")):
            with self.subTest(path=path.name):
                self.assertIsNone(self.guard(claude("Write", path, content), self.plain))
        self.assertFalse((self.plain / "output").exists())

    def test_an_edit_is_never_redirected(self):
        # the file is where it is: a redirected Edit would look for it in output/ and fail
        (self.plain / "note.md").write_text(NOTE)
        edit = {"tool_name": "Edit", "tool_input": {"file_path": str(self.plain / "note.md"), "old_string": NOTE, "new_string": NOTE + "y"}}
        self.assertIsNone(self.guard(edit, self.plain))
        # whatever an edit carries, it never moves a note
        edit["tool_input"] = {"file_path": str(self.plain / "other.md"), "content": NOTE}
        self.assertIsNone(self.guard(edit, self.plain))
        self.assertFalse((self.plain / "output").exists())

    def test_a_write_over_an_existing_file_is_never_redirected(self):
        (self.plain / "note.md").write_text("# old\n")
        self.assertIsNone(self.guard(claude("Write", self.plain / "note.md", NOTE), self.plain))
        self.assertFalse((self.plain / "output").exists())

    def test_a_relative_path_is_the_sessions_not_the_hooks(self):
        (self.plain / "old.md").write_text("# old\n")
        self.assertIsNone(self.guard({"tool_name": "Write", "tool_input": {"file_path": "old.md", "content": NOTE}}, self.plain, proc=self.tmp))
        out = self.guard({"tool_name": "Write", "tool_input": {"file_path": "new.md", "content": NOTE}}, self.plain, proc=self.tmp)["hookSpecificOutput"]
        self.assertEqual(out["updatedInput"]["file_path"], str(self.plain / "output/new.md"))
        self.assertFalse((self.tmp / "output").exists())

    def test_a_path_outside_the_root_passes_untouched(self):
        # the repro: a PR body in a session's scratchpad, far from the worktree the session runs in
        main, linked = self.worktree()
        pr_body = self.tmp / "scratch/project/session/scratchpad/pr-body.md"
        self.assertIsNone(self.guard(claude("Write", pr_body, "## Summary\n\nFixes it.\n"), linked, proc=linked))
        self.assertFalse(pr_body.parent.exists())
        for path, content in ((pr_body, NOTE), (self.plain / "../elsewhere/note.md", NOTE), (self.tmp / "repo/note.md", NOTE)):
            with self.subTest(path=str(path)):
                self.assertIsNone(self.guard(claude("Write", path, content), linked, proc=linked))
        for folder in (linked, main, self.tmp):
            self.assertFalse((folder / "output").exists())

    def test_inside_or_outside_is_told_by_real_path(self):
        # macOS reaches /private/tmp as /tmp: the root and the file may name one place two ways
        link = self.tmp / "link"
        link.symlink_to(self.plain)
        out = self.guard(claude("Write", self.plain / "note.md", NOTE), link, proc=self.plain)["hookSpecificOutput"]
        self.assertEqual(out["updatedInput"]["file_path"], str(link / "output/note.md"))
        out = self.guard(claude("Write", link / "docs/note.md", NOTE), self.plain)["hookSpecificOutput"]
        self.assertEqual(out["updatedInput"]["file_path"], str(self.plain / "output/note.md"))
        self.assertIsNone(self.guard(claude("Write", self.plain / "docs/../../elsewhere/note.md", NOTE), self.plain))

    def test_the_root_is_the_payloads_cwd_not_the_hooks_pwd(self):
        # a linked worktree is a .git file, not a folder: the session's cwd still names its root
        main, linked = self.worktree()
        out = self.guard(claude("Write", linked / "note.md", NOTE), linked, proc=main)["hookSpecificOutput"]
        self.assertEqual(out["updatedInput"]["file_path"], str(linked / "output/note.md"))
        self.assertTrue((linked / "output").is_dir())
        self.assertFalse((main / "output").exists())
        self.assertFalse((self.tmp / "output").exists())

    def test_without_a_cwd_the_root_is_the_repo_holding_the_file(self):
        main, linked = self.worktree()
        out = self.guard(claude("Write", linked / "docs/new/note.md", NOTE), linked, proc=self.tmp, send_cwd=False)["hookSpecificOutput"]
        self.assertEqual(out["updatedInput"]["file_path"], str(linked / "output/note.md"))
        self.assertFalse((main / "output").exists())
        self.assertFalse((self.tmp / "output").exists())

    def test_without_a_cwd_or_a_repo_nothing_is_redirected(self):
        # the hook's own pwd is no stand-in: a note in a plain folder stays put
        self.assertIsNone(self.guard(claude("Write", self.plain / "note.md", NOTE), self.plain, proc=self.plain, send_cwd=False))
        self.assertFalse((self.plain / "output").exists())

    def test_a_cwd_that_is_no_folder_redirects_nothing(self):
        self.assertIsNone(self.guard(claude("Write", self.plain / "note.md", NOTE), self.tmp / "gone", proc=self.plain))
        self.assertFalse((self.tmp / "gone").exists())

    def test_a_note_in_a_legacy_vault_passes_silently(self):
        self.assertIsNone(self.guard(claude("Edit", self.legacy / "cs/note.md"), self.legacy))

    def test_other_tools_and_other_files_pass_silently(self):
        self.assertIsNone(self.guard(claude("Read", self.plain / "note.md"), self.plain))
        self.assertIsNone(self.guard(claude("Write", self.plain / "a.txt"), self.plain))
        self.assertFalse((self.plain / "output").exists())

    def test_a_configured_vault_decides_itself(self):
        # never redirected, whatever the working directory looks like
        self.assertIsNone(self.guard(claude("Write", self.vault / "111.cs/note.md"), self.plain))
        out = self.guard(claude("Write", self.vault / "raw/x.md"), self.vault)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("raw/", out["permissionDecisionReason"])

    def test_the_reminder_after_a_note_in_a_zkfied_folder(self):
        out, _ = self.signal(claude("Write", self.plain / "output/note.md"), self.plain)
        text = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("vault-knowledge build", text)
        self.assertIn(str(self.plain / "output/note.md"), text)
        out, _ = self.signal(claude("Write", self.vault / "111.cs/note.md"), self.vault)
        self.assertIn("vault-index/build", out["hookSpecificOutput"]["additionalContext"])

    def test_no_reminder_for_excluded_paths_other_files_or_plain_folders(self):
        for path in (self.plain / "raw/x.md", self.plain / "a.txt", self.legacy / "cs/note.md"):
            with self.subTest(path=path.name):
                self.assertEqual(self.signal(claude("Write", path), self.tmp), (None, ""))

    # Antigravity's shape: run from the plugin root, the workspace stands in for the cwd

    def test_antigravity_redirects_through_overwrite(self):
        out = self.guard(agy("write_to_file", self.plain / "note.md", self.plain, NOTE), ROOT)
        self.assertEqual(out["decision"], "allow")
        self.assertEqual(out["overwrite"], {"TargetFile": str(self.plain / "output/note.md")})
        self.assertIn("output", out["reason"])

    def test_antigravity_leaves_ordinary_markdown_and_edits_where_they_are(self):
        self.assertEqual(self.guard(agy("write_to_file", self.plain / "docs/plan.md", self.plain, "# Plan\n"), ROOT), {"decision": "allow"})
        edit = {"toolCall": {"name": "replace_file_content", "args": {"TargetFile": str(self.plain / "note.md"), "ReplacementContent": NOTE}},
                "workspacePaths": [str(self.plain)], "conversationId": "t"}
        self.assertEqual(self.guard(edit, ROOT), {"decision": "allow"})
        self.assertFalse((self.plain / "output").exists())

    def test_antigravity_never_moves_an_existing_file_or_a_path_outside_the_workspace(self):
        (self.plain / "old.md").write_text("# old\n")
        self.assertEqual(self.guard(agy("write_to_file", self.plain / "old.md", self.plain, NOTE), ROOT), {"decision": "allow"})
        self.assertEqual(self.guard(agy("write_to_file", self.tmp / "elsewhere/pr.md", self.plain, NOTE), ROOT), {"decision": "allow"})
        self.assertFalse((self.plain / "output").exists())

    def test_antigravity_allows_other_tools_legacy_vaults_and_unknown_workspaces(self):
        self.assertEqual(self.guard(agy("run_command", self.plain / "note.md", self.plain), ROOT), {"decision": "allow"})
        self.assertEqual(self.guard(agy("replace_file_content", self.legacy / "cs/n.md", self.legacy), ROOT), {"decision": "allow"})
        self.assertEqual(self.guard(agy("write_to_file", self.plain / "note.md", None), ROOT), {"decision": "allow"})
        self.assertFalse((self.plain / "output").exists())

    def test_antigravity_configured_vault_denies_raw_and_carries_the_reminder(self):
        out = self.guard(agy("write_to_file", self.vault / "raw/x.md", self.vault), ROOT)
        self.assertEqual(out["decision"], "deny")
        self.assertIn("raw/", out["reason"])
        out = self.guard(agy("write_to_file", self.vault / "111.cs/note.md", self.vault), ROOT)
        self.assertEqual(out["decision"], "allow")
        self.assertNotIn("overwrite", out)
        self.assertIn("vault-index/build", out["reason"])  # PostToolUse returns nothing to the agent there

    def test_antigravity_post_tool_use_answers_an_empty_object(self):
        out, err = self.signal({"toolCall": {"name": "write_to_file", "args": {"TargetFile": str(self.plain / "output/note.md")}}}, ROOT)
        self.assertEqual(out, {})
        self.assertIn("vault-knowledge build", err)


if __name__ == "__main__":
    unittest.main()
