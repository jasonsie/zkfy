"""The cloud scripts: executable bash that parses, pinned to this release.
Run: python3 -B -m unittest discover -s tests -p 'test_cloud.py' -v"""
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).parents[1]


class CloudTest(unittest.TestCase):
    def test_scripts_are_executable_bash(self):
        for name in ("setup.sh", "session-start.sh"):
            f = ROOT / "cloud" / name
            self.assertTrue(os.access(f, os.X_OK), f)
            self.assertTrue(f.read_text().startswith("#!/usr/bin/env bash"), f)
            subprocess.run(["bash", "-n", str(f)], check=True)

    def test_setup_pins_this_release(self):
        version = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"]
        text = (ROOT / "cloud/setup.sh").read_text()
        self.assertIn(f'ZKFY_REF="${{ZKFY_REF:-zkfy--v{version}}}"', text)
        self.assertRegex(text, r'WEB_CLIPPER_REF="\$\{WEB_CLIPPER_REF:-web-clipper--v\d+\.\d+\.\d+\}"')
        self.assertRegex(text, r'CLIPPER_CLI_REF="\$\{CLIPPER_CLI_REF:-[0-9a-f]{7,40}\}"')

    def test_session_start_is_a_no_op_without_the_plugins(self):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
        r = subprocess.run(["bash", str(ROOT / "cloud/session-start.sh")], env=env, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", "")) if not Path("/opt/ai-plugins").is_dir() else None


if __name__ == "__main__":
    unittest.main()
