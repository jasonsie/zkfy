"""Run: python3 -B -m unittest discover -s tests -p 'test_vault_knowledge.py' -v"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

LAUNCHER = Path(__file__).parents[1] / "bin" / "vault-knowledge"


class VaultKnowledgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="vault knowledge 空間 ")
        home = Path(self.tmp.name)
        self.vault = home / "Vault With Space"
        (self.vault / "docs/knowledge").mkdir(parents=True)
        (self.vault / "docs/knowledge/scope.json").write_text('{"version": 1, "domains": {"cs": "111.cs"}}')
        (self.vault / "111.cs").mkdir()
        self.config = home / ".config/zkfy/knowledge.json"
        bin_dir = home / ".local/bin"
        bin_dir.mkdir(parents=True)
        self.link = bin_dir / "vault-knowledge"  # the link ai-dotfiles makes from the pinned checkout
        os.symlink(LAUNCHER, self.link)
        self.env = {**os.environ, "HOME": str(home), "ZKFY_KNOWLEDGE_CONFIG": str(self.config)}

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *args):
        p = subprocess.run([str(self.link), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
        return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8")

    def test_bind_writes_the_binding_once(self):
        code, out, err = self.run_cmd("bind", "--vault", str(self.vault))
        self.assertEqual((code, err), (0, ""), out)
        binding = json.loads(self.config.read_text())
        self.assertEqual(set(binding), {"python", "vault"})
        self.assertEqual(binding["vault"], str(self.vault.resolve()))
        self.assertTrue(Path(binding["python"]).exists(), binding["python"])
        self.assertIn("written", out)
        code, out, _ = self.run_cmd("bind", "--vault", str(self.vault))
        self.assertEqual(code, 0)
        self.assertIn("unchanged", out)
        self.assertNotIn("written", out)

    def test_runs_the_tool_through_the_link(self):
        self.run_cmd("bind", "--vault", str(self.vault))
        code, out, err = self.run_cmd("status")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["notes"], 0)

    def test_dry_run_writes_nothing_and_unbind_removes_the_binding(self):
        code, out, _ = self.run_cmd("bind", "--vault", str(self.vault), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would write", out)
        self.assertFalse(self.config.exists())
        self.run_cmd("bind", "--vault", str(self.vault))
        code, out, _ = self.run_cmd("unbind")
        self.assertEqual(code, 0)
        self.assertIn("removed", out)
        self.assertFalse(self.config.exists())

    def test_refuses_a_vault_without_scope_policy(self):
        code, _, err = self.run_cmd("bind", "--vault", self.tmp.name)
        self.assertEqual(code, 2)
        self.assertIn("scope.json", err)
        self.assertFalse(self.config.exists())

    def test_without_a_binding_says_how_to_bind(self):
        code, _, err = self.run_cmd("status")
        self.assertEqual(code, 2)
        self.assertIn("vault-knowledge bind --vault", err)

    def test_an_older_binding_with_a_tool_key_still_runs(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({"python": "python3", "tool": "/nowhere/knowledge.py", "vault": str(self.vault)}))
        code, out, err = self.run_cmd("status")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["notes"], 0)


if __name__ == "__main__":
    unittest.main()
