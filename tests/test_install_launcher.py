"""Run: python3 -B -m unittest discover -s tests -p 'test_install_launcher.py' -v"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).parents[1] / "scripts"
INSTALLER = SCRIPTS / "install-launcher.py"


class InstallLauncherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="launcher test 空間 ")
        self.home = Path(self.tmp.name)
        self.vault = self.home / "Vault With Space"
        (self.vault / "docs/knowledge").mkdir(parents=True)
        (self.vault / "docs/knowledge/scope.json").write_text('{"version": 1, "domains": {"cs": "111.cs"}}')
        (self.vault / "111.cs").mkdir()
        self.config = self.home / ".config/zkfy/knowledge.json"
        self.bin = self.home / ".local/bin"

    def tearDown(self):
        self.tmp.cleanup()

    def run_installer(self, *args):
        env = {**os.environ, "HOME": str(self.home)}
        env.pop("ZKFY_KNOWLEDGE_CONFIG", None)
        p = subprocess.run([sys.executable, "-B", str(INSTALLER), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8")

    def test_install_writes_binding_and_link_then_is_idempotent(self):
        code, out, err = self.run_installer("--vault", str(self.vault))
        self.assertEqual((code, err), (0, ""), out)
        binding = json.loads(self.config.read_text())
        self.assertEqual(binding, {"python": sys.executable, "tool": str((SCRIPTS / "knowledge.py").resolve()), "vault": str(self.vault.resolve())})
        link = self.bin / "vault-knowledge"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), str((SCRIPTS / "knowledge-launcher.py").resolve()))
        self.assertTrue(os.access(link, os.X_OK))
        self.assertIn("written", out)
        # The launcher now runs the shared CLI against the bound vault.
        env = {**os.environ, "HOME": str(self.home), "ZKFY_KNOWLEDGE_CONFIG": str(self.config)}
        status = subprocess.run([str(link), "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["notes"], 0)
        again = self.run_installer("--vault", str(self.vault))
        self.assertEqual(again[0], 0)
        self.assertIn("unchanged", again[1])
        self.assertNotIn("written", again[1])

    def test_dry_run_writes_nothing_and_uninstall_removes_only_ours(self):
        code, out, _ = self.run_installer("--vault", str(self.vault), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would write", out)
        self.assertFalse(self.config.exists())
        self.assertFalse((self.bin / "vault-knowledge").exists())
        self.run_installer("--vault", str(self.vault))
        code, out, _ = self.run_installer("--uninstall")
        self.assertEqual(code, 0)
        self.assertFalse(self.config.exists())
        self.assertFalse((self.bin / "vault-knowledge").is_symlink())
        self.assertIn("removed", out)
        # A foreign vault-knowledge is left alone and reported.
        self.bin.mkdir(parents=True, exist_ok=True)
        (self.bin / "vault-knowledge").write_text("#!/bin/sh\necho other\n")
        code, out, err = self.run_installer("--vault", str(self.vault))
        self.assertEqual(code, 2)
        self.assertIn("vault-knowledge", err)
        self.assertEqual((self.bin / "vault-knowledge").read_text(), "#!/bin/sh\necho other\n")

    def test_refuses_a_folder_without_scope_policy(self):
        code, _, err = self.run_installer("--vault", str(self.home))
        self.assertEqual(code, 2)
        self.assertIn("scope.json", err)
        self.assertFalse(self.config.exists())


if __name__ == "__main__":
    unittest.main()
