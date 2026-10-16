"""Run: python3 -B -m unittest discover -s tests -p 'test_knowledge.py' -v"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("knowledge", Path(__file__).parents[1] / "scripts/knowledge.py")
k = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = k
SPEC.loader.exec_module(k)


def note(body="Supported guidance.", mode=None, aliases="[Harness, 代理框架]", extra=""):
    mode_line = f"Mode: {mode}\n" if mode else ""
    headings = {None: "### Abstract\nSummary.\n### Content", "atom": "### Definition\nSummary.\n### Mental Model", "thesis": "### 執行摘要\nSummary.\n### Mental Model\nModel.\n### Theme"}
    return f"---\nDate: 2026-01-01\nType: permanent\n{mode_line}Categories: [AI]\nAliases: {aliases}\nBefore: ''\nNext: ''\n{extra}---\n{headings[mode]}\n{body}\n### Links\n"


class VaultTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="knowledge test 空間 ")
        self.root = Path(self.tmp.name)
        self.config = {"version": 1, "domains": {"ai": "333.ai", "web": "222.web"}, "maps": ["000.Index"],
                       "shard_size": 2, "synonyms": [["context", "上下文"], ["memory", "記憶"]]}
        self.put(k.POLICY, json.dumps(self.config))
        self.put("333.ai/AI-Harness.md", note("Memory and context architecture."))
        self.put("222.web/Web-Memory.md", note("Browser memory leaks.", aliases="[browser]"))
        self.put("000.Index/AI-Map.md", "---\nType: structure\n---\n[[AI-Harness]]\n")
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Knowledge Test")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def git(self, *args):
        return k.git(self.root, *args)

    def corpus(self, view="worktree"):
        return k.Corpus(k.Snapshot(self.root, view))

    def tree(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts}

    def test_scope_excludes_before_read_and_rejects_escapes(self):
        self.put("raw/Secret.md", "sentinel-not-readable")
        self.put("template/Template.md", "sentinel-template")
        (self.root / "333.ai/AI-Escape.md").symlink_to(self.root / "raw/Secret.md")
        (self.root / "333.ai/escape-dir").symlink_to(self.root / "raw", target_is_directory=True)
        original = k.read_file
        seen = []
        def guarded(root, name):
            seen.append(name)
            self.assertFalse(name.startswith(("raw/", "template/")))
            return original(root, name)
        with patch.object(k, "read_file", guarded):
            c = self.corpus()
            self.assertEqual(len(c.notes), 3)
            self.assertEqual(k.search(c, "sentinel", 10), [])
            for p in ("../raw/Secret.md", "raw/Secret.md", "333.ai/AI-Escape.md"):
                with self.assertRaises(k.KnowledgeError):
                    k.get_note(c, p)
            c.outputs()
        self.assertNotIn("raw/Secret.md", seen)

    def test_bad_policy_cannot_include_sources(self):
        for root in ("raw", "RAW", "333.ai/Raw"):
            with self.subTest(root=root):
                self.config["domains"]["source"] = root
                self.put(k.POLICY, json.dumps(self.config))
                with self.assertRaises(k.KnowledgeError):
                    self.corpus()

    def test_live_search_and_read_do_not_write(self):
        before = self.tree()
        index = self.git("ls-files", "--stage", "-z")
        c = self.corpus()
        results = k.search(c, "coding harness context architecture", 6)
        self.assertEqual(results[0]["path"], "333.ai/AI-Harness.md")
        self.assertIn("supported", note().casefold())
        r = k.get_note(c, results[0]["path"], "Content")
        self.assertIn("Memory", str(r["lines"]))
        self.assertEqual(before, self.tree())
        self.assertEqual(index, self.git("ls-files", "--stage", "-z"))

    def test_metadata_modes_and_multiline_aliases(self):
        self.put("333.ai/AI-Atom.md", note("An atom.", "atom", "\n  - 原子筆記\n  - 'quoted, alias'"))
        self.put("333.ai/AI-Thesis.md", note("An argument.", "thesis"))
        c = self.corpus()
        self.assertEqual(c.issues(), [])
        self.assertEqual(k.search(c, "原子筆記", 1)[0]["path"], "333.ai/AI-Atom.md")
        self.assertEqual(k.search(c, "上下文", 1)[0]["path"], "333.ai/AI-Harness.md")
        self.put("333.ai/AI-Bad.md", note(extra="Type: permanent\n"))
        self.assertTrue(any(x["rule"] == "metadata" for x in self.corpus().issues()))

    def test_link_resolution_graph_and_code_fences(self):
        self.put("333.ai/AI-Harness.md", note("[[Web-Memory#Content]]\n[[AI-Harness#^b1]]\ntext ^b1\n```md\n[[Not-A-Note]]\n```\n![[image.png]]\n[[raw/Secret]]"))
        c = self.corpus()
        self.assertEqual(c.issues(), [])
        self.put("333.ai/sub/Web-Memory.md", note())
        issues = self.corpus().issues()
        self.assertTrue(any(x["rule"] == "link-ambiguous" for x in issues))
        r = k.get_note(self.corpus(), "333.ai/AI-Harness.md")
        self.assertNotIn("raw/Secret", str(r))

    def test_stale_add_change_rename_delete_and_no_evidence(self):
        c = self.corpus()
        k.write_outputs(c.snapshot, c.outputs())
        self.assertEqual(self.corpus().freshness(), "current")
        self.put("333.ai/AI-New.md", note("Novel quuxneedle."))
        self.assertIn("stale", self.corpus().freshness())
        self.assertEqual(k.search(self.corpus(), "quuxneedle", 1)[0]["path"], "333.ai/AI-New.md")
        os.rename(self.root / "333.ai/AI-New.md", self.root / "333.ai/AI-Renamed.md")
        self.assertEqual(k.search(self.corpus(), "quuxneedle", 1)[0]["path"], "333.ai/AI-Renamed.md")
        (self.root / "333.ai/AI-Renamed.md").unlink()
        self.assertEqual(k.search(self.corpus(), "quuxneedle", 1), [])
        self.assertEqual(k.search(self.corpus(), "quantumgalaxyunknown", 1), [])

    def test_determinism_shards_and_commit_cycle(self):
        for i in range(5):
            self.put(f"333.ai/AI-Note-{i}.md", note(f"Topic {i}."))
        c = self.corpus()
        a = c.outputs()
        self.assertEqual(a, self.corpus().outputs())
        self.assertLess(len(a[".claude/index.md"].splitlines()), 40)
        self.assertGreater(sum(p.startswith(".claude/index/ai-") for p in a), 1)
        k.write_outputs(c.snapshot, a)
        self.git("add", ".")
        self.git("commit", "-qm", "catalog")
        self.assertEqual(a, self.corpus().outputs())
        self.assertEqual(k.write_outputs(self.corpus().snapshot, a, check=True), [])
        with tempfile.TemporaryDirectory() as clone:
            subprocess.run(["git", "clone", "-q", "--depth", "1", self.root.as_uri(), clone], check=True)
            self.assertEqual(a, k.Corpus(k.Snapshot(Path(clone))).outputs())

    def initialize_catalog(self):
        c = self.corpus()
        k.write_outputs(c.snapshot, c.outputs())
        self.put(k.BASELINE, k.encoded(k.baseline_data(c)).decode())
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")

    def test_partial_staging_and_unrelated_index_preserved(self):
        self.initialize_catalog()
        self.put("333.ai/AI-Harness.md", note("stagedneedle context"))
        self.git("add", "333.ai/AI-Harness.md")
        self.put("333.ai/AI-Harness.md", note("unstagedneedle context"))
        self.put("unrelated.txt", "keep me staged")
        self.git("add", "unrelated.txt")
        report, status = k.run_hook(self.root, "ratchet")
        self.assertEqual(status, 0, report)
        self.assertIn(b"unstagedneedle", (self.root / "333.ai/AI-Harness.md").read_bytes())
        self.assertIn(b"stagedneedle", self.git("show", ":333.ai/AI-Harness.md"))
        manifest = json.loads(self.git("show", ":" + k.MANIFEST))
        self.assertEqual(manifest["files"]["333.ai/AI-Harness.md"], k.digest(self.git("show", ":333.ai/AI-Harness.md")))
        self.assertEqual(self.git("show", ":unrelated.txt"), b"keep me staged")
        self.assertIn("stale", self.corpus().freshness())

    def test_failed_gate_preserves_worktree_and_index(self):
        self.initialize_catalog()
        self.put("333.ai/AI-Harness.md", note("[[Missing-Target]]"))
        self.git("add", "333.ai/AI-Harness.md")
        before, index = self.tree(), self.git("ls-files", "--stage", "-z")
        report, code = k.run_hook(self.root, "ratchet")
        self.assertEqual(code, 1)
        self.assertTrue(report["new_issues"])
        self.assertEqual(before, self.tree())
        self.assertEqual(index, self.git("ls-files", "--stage", "-z"))

    def test_rename_breaks_unchanged_inbound_link(self):
        self.initialize_catalog()
        self.git("mv", "333.ai/AI-Harness.md", "333.ai/AI-Renamed.md")
        report, code = k.run_hook(self.root, "ratchet")
        self.assertEqual(code, 1)
        self.assertTrue(any(i["path"] == "000.Index/AI-Map.md" for i in report["new_issues"]))

    def test_legacy_debt_ratchet_and_no_expansion(self):
        self.put("333.ai/AI-Harness.md", note("[[Legacy-Target]]"))
        self.git("add", ".")
        self.git("commit", "-qm", "legacy defect")
        self.initialize_catalog()
        self.put("333.ai/AI-Harness.md", note("[[Legacy-Target]]\nNew valid paragraph."))
        self.git("add", "333.ai/AI-Harness.md")
        self.assertEqual(k.run_hook(self.root, "ratchet")[1], 0)
        self.git("commit", "-qm", "unchanged defect")
        self.put("333.ai/AI-Harness.md", note("[[New-Target]]"))
        self.put(k.BASELINE, k.encoded(k.baseline_data(self.corpus())).decode())
        self.git("add", ".")
        with self.assertRaises(k.KnowledgeError):
            k.run_hook(self.root, "ratchet")

    def test_report_only_never_stages(self):
        self.initialize_catalog()
        self.put("333.ai/AI-Harness.md", note("[[Missing]]"))
        self.git("add", "333.ai/AI-Harness.md")
        index = self.git("ls-files", "--stage", "-z")
        self.assertEqual(k.run_hook(self.root, "report-only")[1], 0)
        self.assertEqual(index, self.git("ls-files", "--stage", "-z"))

    def test_manual_generated_edits_are_not_overwritten(self):
        self.initialize_catalog()
        self.put(".claude/index.md", "manual edit")
        before = self.tree()
        with self.assertRaises(k.KnowledgeError):
            k.run_hook(self.root, "ratchet")
        self.assertEqual(before, self.tree())

    def test_read_budget_and_continuation(self):
        self.put("333.ai/AI-Long.md", note("\n".join("上下文" * 1000 for _ in range(250))))
        c = self.corpus()
        result = k.get_note(c, "333.ai/AI-Long.md", "Content", limit=200)
        self.assertTrue(result["truncated"])
        self.assertTrue(result["clipped_lines"])
        self.assertIsNotNone(result["next_start"])
        self.assertLessEqual(sum(len(s.encode()) for _, s in result["lines"]), 16000)
        self.assertLess(len(k.encoded(result)), 24000)
        first = k.get_note(c, "333.ai/AI-Harness.md", limit=2)
        second = k.get_note(c, "333.ai/AI-Harness.md", start=first["next_start"])
        self.assertEqual(first["lines"][-1][0] + 1, second["lines"][0][0])
        self.assertFalse(second["truncated"])
        with self.assertRaises(k.KnowledgeError):
            k.get_note(c, "333.ai/AI-Harness.md", start=0)

    def test_scoped_inventory_and_full_graph(self):
        self.put("raw/Secret.md", "fixture-only sentinel")
        self.put("333.ai/AI-Harness.md", note("[[Web-Memory]]\n[[raw/Secret]]", extra="Src: '[[raw/Secret]]'\n"))
        self.put("333.ai/artifact.csv", "not eligible")
        c = self.corpus()
        result = k.inventory(c, "333.ai")
        self.assertEqual(result["stats"]["total_notes"], 1)
        self.assertEqual(result["stats"]["broken_links"], [])
        self.assertEqual(result["non_md_files"], [])
        self.assertNotIn("raw/Secret", str(result))
        self.assertNotIn("artifact.csv", str(result))
        for path in ("raw", "333.ai/Raw", "../", "/tmp"):
            with self.assertRaises(k.KnowledgeError):
                k.inventory(c, path)

    def test_git_snapshot_batches_only_eligible_blobs(self):
        self.put("raw/Secret.md", "fixture-only sentinel")
        self.git("add", "raw/Secret.md")
        forbidden = self.git("rev-parse", ":raw/Secret.md").strip()
        with patch.object(k, "git", wraps=k.git) as observed:
            c = self.corpus("staged")
        batches = [x for x in observed.call_args_list if x.args[1:3] == ("cat-file", "--batch")]
        self.assertEqual(len(batches), 1)
        self.assertNotIn(forbidden, batches[0].kwargs["data"])
        self.assertEqual(c.hashes, self.corpus().hashes)

    def test_staged_policy_is_independent_of_unstaged_policy(self):
        self.initialize_catalog()
        self.put(k.POLICY, '{"invalid":true}')
        self.assertEqual(k.run_hook(self.root, "report-only")[1], 0)

    def test_transaction_restores_after_generated_write_failure(self):
        self.initialize_catalog()
        self.put("333.ai/AI-Harness.md", note(aliases="[Changed]"))
        self.git("add", "333.ai/AI-Harness.md")
        before, index = self.tree(), (self.root / ".git/index").read_bytes()
        original = Path.write_bytes
        failed = False
        def failing(path, data):
            nonlocal failed
            if path.resolve() == (self.root / k.MANIFEST).resolve() and not failed:
                failed = True
                raise OSError("injected write failure")
            return original(path, data)
        with patch.object(Path, "write_bytes", failing), self.assertRaises(OSError):
            k.run_hook(self.root, "ratchet")
        self.assertTrue(failed)
        self.assertEqual(before, self.tree())
        self.assertEqual(index, (self.root / ".git/index").read_bytes())
        self.assertFalse((self.root / ".git/index.lock").exists())

    def test_existing_index_lock_is_preserved(self):
        self.initialize_catalog()
        self.put(".git/index.lock", "other git process")
        before, index = self.tree(), (self.root / ".git/index").read_bytes()
        with self.assertRaises(k.KnowledgeError):
            k.run_hook(self.root, "ratchet")
        self.assertEqual(before, self.tree())
        self.assertEqual(index, (self.root / ".git/index").read_bytes())
        self.assertEqual((self.root / ".git/index.lock").read_text(), "other git process")

    def test_build_manifest_cannot_claim_baseline_ownership(self):
        self.initialize_catalog()
        original = (self.root / k.BASELINE).read_bytes()
        manifest = json.loads((self.root / k.MANIFEST).read_text())
        manifest['outputs'][k.BASELINE] = k.digest(original)
        self.put(k.MANIFEST, json.dumps(manifest))
        c = self.corpus()
        k.write_outputs(c.snapshot, c.outputs())
        self.assertEqual(original, (self.root / k.BASELINE).read_bytes())

    def test_index_change_during_validation_is_not_overwritten(self):
        self.initialize_catalog()
        generated = {p: b for p, b in self.tree().items() if p.startswith('.claude/')}
        original = k.stage_outputs
        concurrent_index = None
        def concurrent(*args, **kwargs):
            nonlocal concurrent_index
            self.put('333.ai/AI-Harness.md', note('[[Concurrent-Broken-Link]]'))
            self.git('add', '333.ai/AI-Harness.md')
            concurrent_index = (self.root / '.git/index').read_bytes()
            return original(*args, **kwargs)
        with patch.object(k, 'stage_outputs', concurrent), self.assertRaisesRegex(k.KnowledgeError, 'index changed'):
            k.run_hook(self.root, 'ratchet')
        self.assertEqual(concurrent_index, (self.root / '.git/index').read_bytes())
        self.assertEqual(generated, {p: b for p, b in self.tree().items() if p.startswith('.claude/')})

    def test_unborn_head_has_no_inherited_debt(self):
        self.git('checkout', '--orphan', 'first-commit')
        report, status = k.run_hook(self.root, 'ratchet')
        self.assertEqual(status, 0, report)
        self.assertEqual(json.loads(self.git('show', ':' + k.BASELINE))['issues'], [])

    def test_spaced_chinese_phrase_retrieval(self):
        self.config['synonyms'].append(['context management', '上下文管理'])
        self.put(k.POLICY, json.dumps(self.config))
        self.put('333.ai/AI-Context-Management.md', note('Context budgets.'))
        c = self.corpus()
        for query in ('上下文管理', '上下文 管理', 'context   management'):
            self.assertEqual(k.search(c, query, 1)[0]['path'], '333.ai/AI-Context-Management.md')

    def test_repair_hints_are_specific_and_approval_gated(self):
        self.put('333.ai/AI-Harness.md', note().replace('### Links', '').replace("Before: ''\n", ''))
        self.put('333.ai/Loose.md', note())
        issues = self.corpus().issues()
        fixes = {(i['rule'], i['detail']): i['fix'] for i in issues}
        self.assertIn('### Links', fixes[('heading', 'Links')])
        self.assertIn("Before: ''", fixes[('field', 'Before')])
        self.assertIn('AI-Loose.md', fixes[('filename', 'Loose.md')])
        self.assertTrue(all('approval' in i['fix'] for i in issues))

    def test_plugin_hooks_use_scope_without_redirecting(self):
        hooks = Path(__file__).parents[1] / "hooks"
        def run(script, path):
            return subprocess.run(["bash", str(hooks / script)], cwd=self.root, text=True,
                input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(self.root / path)}}),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
        self.assertEqual(run("signal-index-update.sh", "raw/Secret.md"), "")
        denied = json.loads(run("validate-zk-structure.sh", "raw/Secret.md"))
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(run("validate-zk-structure.sh", "333.ai/AI-New.md"), "")
        self.assertFalse((self.root / "output").exists())
        signal = json.loads(run("signal-index-update.sh", "000.Index/AI-Map.md"))
        self.assertTrue(signal["index_update_needed"])
        self.assertEqual(run("signal-index-update.sh", "docs/knowledge/query.md"), "")


if __name__ == "__main__":
    unittest.main()
