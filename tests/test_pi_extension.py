"""extensions/zkfy.ts, driven as Pi drives it by tests/pi_extension_harness.mjs (node 23+ runs the
TypeScript as is). Run: python3 -B -m unittest discover -s tests -p 'test_pi_extension.py' -v"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parents[1]
EXTENSION = ROOT / "extensions/zkfy.ts"
HARNESS = ROOT / "tests/pi_extension_harness.mjs"
NODE = shutil.which("node")
NOTE = "---\nDate: 2026-11-23\nType: literature\nCategories: [CS]\n---\n### Abstract\nx\n"  # a note, by its frontmatter


@unittest.skipUnless(NODE, "node is not installed")
class PiExtensionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.plain = self.tmp / "plain"
        (self.plain / ".claude").mkdir(parents=True)
        (self.plain / ".claude/index.md").write_text("# catalog\n")  # a built catalog marks a vault
        self.vault = self.tmp / "vault"
        (self.vault / "docs/knowledge").mkdir(parents=True)
        (self.vault / "docs/knowledge/scope.json").write_text('{"version": 1, "domains": {"cs": "111.cs"}}')
        (self.vault / "raw").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def replay(self, cwd, note, content="# note\n"):
        proc = subprocess.run([NODE, str(HARNESS), str(EXTENSION), str(cwd), str(note), content],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_registers_the_notion_server_and_listens_to_both_tool_events(self):
        got = self.replay(self.plain, self.plain / "a.txt")
        self.assertEqual(got["events"], ["tool_call", "tool_result"])
        self.assertEqual([c["mcp"] for c in got["calls"]], ["notion"])
        url = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["notion"]["url"]
        self.assertEqual(got["calls"][0]["config"]["url"], url)

    def test_a_note_outside_a_vault_moves_to_output_and_the_result_carries_both_notes(self):
        got = self.replay(self.plain, self.plain / "note.md", NOTE)
        self.assertEqual(got["path"], str(self.plain / "output/note.md"))
        self.assertIsNone(got["onCall"])
        texts = [c["text"] for c in got["onResult"]["content"] if c["type"] == "text"]
        self.assertEqual(texts[0], "wrote")
        self.assertIn("output", texts[1])
        self.assertIn("vault-knowledge build", texts[1])

    def test_raw_in_a_configured_vault_is_blocked(self):
        got = self.replay(self.vault, self.vault / "raw/x.md")
        self.assertTrue(got["onCall"]["block"])
        self.assertIn("raw/", got["onCall"]["reason"])
        self.assertIsNone(got["onResult"])

    def test_other_files_are_left_alone(self):
        got = self.replay(self.plain, self.plain / "a.txt")
        self.assertEqual(got["path"], str(self.plain / "a.txt"))
        self.assertIsNone(got["onCall"])
        self.assertIsNone(got["onResult"])

    def test_ordinary_markdown_outside_a_vault_stays_where_it_is(self):
        got = self.replay(self.plain, self.plain / "docs/plan.md", "# Plan\n")
        self.assertEqual(got["path"], str(self.plain / "docs/plan.md"))
        self.assertIsNone(got["onCall"])
        self.assertFalse((self.plain / "output").exists())

    def test_a_note_outside_the_cwd_or_over_an_existing_file_stays_where_it_is(self):
        outside = self.tmp / "scratch/pr-body.md"
        got = self.replay(self.plain, outside, NOTE)
        self.assertEqual(got["path"], str(outside))
        self.assertIsNone(got["onCall"])
        (self.plain / "old.md").write_text("# old\n")
        got = self.replay(self.plain, self.plain / "old.md", NOTE)
        self.assertEqual(got["path"], str(self.plain / "old.md"))
        self.assertFalse((self.plain / "output").exists())
        self.assertFalse((self.tmp / "scratch").exists())


if __name__ == "__main__":
    unittest.main()
