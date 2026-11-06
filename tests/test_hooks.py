"""The two hook scripts in the shapes each CLI sends: Claude Code's, which Codex and the Pi
extension share, and Antigravity's. Run: python3 -B -m unittest discover -s tests -p 'test_hooks.py' -v"""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parents[1]
HOOKS = ROOT / "hooks"
SCOPE = '{"version": 1, "domains": {"cs": "111.cs"}}'
FOLDERS = ("cs", "web", "ai", "principle", "devops", "math", "000.Index", "row")  # the legacy layout


def run(script, payload, cwd):
    proc = subprocess.run(["bash", str(HOOKS / script)], input=json.dumps(payload),
                          capture_output=True, text=True, cwd=cwd)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def claude(tool, path):
    return {"tool_name": tool, "tool_input": {"file_path": str(path), "content": "x"}}


def agy(tool, path, workspace):
    return {"toolCall": {"name": tool, "args": {"TargetFile": str(path), "CodeContent": "x"}},
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

    def guard(self, payload, cwd):
        code, out, _ = run("validate-zk-structure.sh", payload, cwd)
        self.assertEqual(code, 0)
        return json.loads(out) if out else None

    def signal(self, payload, cwd):
        code, out, err = run("signal-index-update.sh", payload, cwd)
        self.assertEqual(code, 0)
        return (json.loads(out) if out else None), err

    # Claude Code's shape (Codex and the Pi extension send the same)

    def test_a_note_outside_a_vault_is_redirected_to_output(self):
        out = self.guard(claude("Write", self.plain / "note.md"), self.plain)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "allow")
        self.assertEqual(out["updatedInput"], {"file_path": str(self.plain / "output/note.md"), "content": "x"})
        self.assertIn("output", out["additionalContext"])
        self.assertTrue((self.plain / "output").is_dir())

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
        out = self.guard(agy("write_to_file", self.plain / "note.md", self.plain), ROOT)
        self.assertEqual(out["decision"], "allow")
        self.assertEqual(out["overwrite"], {"TargetFile": str(self.plain / "output/note.md")})
        self.assertIn("output", out["reason"])

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
