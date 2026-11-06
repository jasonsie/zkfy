"""The portable-plugin invariants: what Claude Code, Codex, Pi and Antigravity need to load this
plugin as shipped. Run: python3 -B -m unittest discover -s tests -p 'test_portable.py' -v"""
import json
import os
from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).parents[1]
LIMIT = 24000  # Antigravity reads only the first 24000 bytes of a skill or agent file


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path}: no frontmatter"
    return yaml.safe_load(m.group(1)), len(text.encode("utf-8")), text


class PortableTest(unittest.TestCase):
    def test_every_skill_parses_strictly_and_is_named_after_its_folder(self):
        skills = sorted(ROOT.glob("skills/*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 10)
        for f in skills:
            with self.subTest(skill=f.parent.name):
                data, size, _ = frontmatter(f)
                self.assertEqual(data.get("name"), f.parent.name)
                self.assertTrue(data.get("description"))
                self.assertLess(size, LIMIT)

    def test_every_agent_parses_strictly_and_inherits_the_model(self):
        agents = sorted(ROOT.glob("agents/*.md"))
        self.assertEqual(len(agents), 8)
        for f in agents:
            with self.subTest(agent=f.stem):
                data, size, _ = frontmatter(f)
                self.assertEqual(data.get("model", "inherit"), "inherit")
                self.assertLess(size, LIMIT)

    def test_skill_and_agent_text_never_relies_on_claudes_path_variable(self):
        for f in list(ROOT.glob("skills/**/*.md")) + list(ROOT.glob("agents/*.md")):
            self.assertNotIn("CLAUDE_PLUGIN_ROOT", f.read_text(encoding="utf-8"), f)

    def test_no_commands_folder(self):
        self.assertFalse((ROOT / "commands").exists())

    def test_hook_commands_quote_the_path_variable(self):
        hooks = json.loads((ROOT / "hooks/hooks.json").read_text())
        for entries in hooks["hooks"].values():
            for entry in entries:
                for h in entry["hooks"]:
                    self.assertTrue(h["command"].startswith('"${CLAUDE_PLUGIN_ROOT}/'), h["command"])

    def test_manifests_agree(self):
        claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        agy = json.loads((ROOT / ".antigravity-plugin/plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual((agy["name"], agy["version"]), (claude["name"], claude["version"]))
        self.assertTrue(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", agy["name"]))
        entries = [e for e in market["plugins"] if e["name"] == claude["name"]]
        self.assertEqual(len(entries), 1)
        self.assertNotIn("version", entries[0], "one version, in plugin.json")
        self.assertEqual(entries[0]["source"], "./")

    def test_mcp_servers_match_across_formats(self):
        claude = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]
        agy = json.loads((ROOT / "mcp_config.json").read_text())["mcpServers"]
        self.assertEqual(set(claude), set(agy))
        for name, server in claude.items():
            self.assertEqual(server["url"], agy[name].get("serverUrl") or agy[name].get("url"))

    def test_antigravity_hooks_run_the_scripts_claude_runs_by_relative_path(self):
        claude = json.loads((ROOT / "hooks/hooks.json").read_text())["hooks"]
        scripts = {Path(h["command"].strip('"')).name for entries in claude.values() for e in entries for h in e["hooks"]}
        agy_tools = {"write_to_file", "replace_file_content", "multi_replace_file_content", "run_command",
                     "view_file", "list_dir", "find_by_name", "grep_search"}
        seen = set()
        for group, events in json.loads((ROOT / "hooks.json").read_text()).items():
            self.assertTrue(re.fullmatch(r"[a-z0-9-]+", group), group)
            for event, entries in events.items():
                if event == "enabled":
                    continue
                self.assertIn(event, ("PreToolUse", "PostToolUse"))
                for entry in entries:
                    self.assertTrue(set(entry["matcher"].split("|")) <= agy_tools, entry["matcher"])
                    for h in entry["hooks"]:
                        self.assertTrue(h["command"].startswith("./hooks/"), h["command"])
                        self.assertNotIn("PLUGIN_ROOT", h["command"])
                        script = ROOT / h["command"][2:]
                        self.assertTrue(os.access(script, os.X_OK), script)
                        seen.add(script.name)
        self.assertTrue(seen)
        self.assertTrue(seen <= scripts, seen - scripts)  # the same scripts; PostToolUse is Claude's channel only

    def test_pi_extension_runs_the_same_scripts_and_registers_the_same_server(self):
        text = (ROOT / "extensions/zkfy.ts").read_text(encoding="utf-8")
        claude = json.loads((ROOT / "hooks/hooks.json").read_text())["hooks"]
        for script in {Path(h["command"].strip('"')).name for entries in claude.values() for e in entries for h in e["hooks"]}:
            self.assertIn(f'"{script}"', text, script)
        servers = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]
        self.assertEqual(re.search(r'url: "([^"]+)"', text).group(1), servers["notion"]["url"])
        self.assertIn("registerMcpServer(NOTION.name", text)
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", text)

    def test_bin_commands_are_executable_scripts(self):
        files = sorted((ROOT / "bin").iterdir())
        self.assertTrue(files)
        for f in files:
            self.assertTrue(os.access(f, os.X_OK), f)
            self.assertTrue(f.read_text().startswith("#!"), f)

    def test_plugin_paths_named_in_skills_and_agents_exist(self):
        for f in ROOT.glob("skills/*/SKILL.md"):
            for ref in re.findall(r"`<zkfy-root>/([^`\s<>]+)`", f.read_text(encoding="utf-8")):
                if "…" in ref:  # the placeholder in the paths note
                    continue
                self.assertTrue((ROOT / ref).exists(), f"{f.parent.name}: {ref} missing")
        for f in ROOT.glob("agents/*.md"):
            for ref in re.findall(r"`((?:agents|docs|reference)/[^`\s<>]+\.md)`", f.read_text(encoding="utf-8")):
                self.assertFalse(ref.startswith("reference/"), f"{f.stem}: reference/ is gitignored")
                self.assertTrue((ROOT / ref).exists(), f"{f.stem}: {ref} missing")


if __name__ == "__main__":
    unittest.main()
