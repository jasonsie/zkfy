"""Run: python3 -B -m unittest discover -s tests -p 'test_reorg.py' -v"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


k = sys.modules.get("knowledge") or load("knowledge")
r = load("reorg")

THIS = """---
Date: 2026-01-01
Type: literature
Categories: [CS, JavaScript]
Aliases: [this keyword]
Before: ''
Next: ''
---
### Abstract
`this` is decided at call time, not definition time.
### Content
#### Five Binding Rules
The value of `this` depends on how a function is called.

1. Default binding falls back to the global object.
2. Implicit binding uses the call-site object.
3. Explicit binding uses call, apply or bind.

| Rule | Example |
|---|---|
| Default | `f()` |
| Implicit | `obj.f()` |

#### Quick Decision Flowchart
Ask who called the function, then walk the rules in order.

```js
function f() { return this; }
```
### Links
- [[Cs-Javascript-Scope]] - scope decides variables, this decides the receiver
"""

THIS_BINDING = """---
Date: 2026-02-01
Type: literature
Categories: [CS, JavaScript]
Aliases: [this binding]
Before: ''
Next: ''
---
### Abstract
How `this` is bound in JavaScript functions.
### Content
#### Five Binding Rules
The binding of `this` depends on the call site.

#### Interview Questions
What does `this` refer to inside an arrow function?
### Links
- [[Cs-Javascript-Scope]] - related
"""

SCOPE = """---
Date: 2026-01-01
Type: literature
Categories: [CS, JavaScript]
Aliases: []
Before: ''
Next: '[[Cs-Javascript-This]]'
---
### Abstract
Scope decides which variables a function can see.
### Content
See [[Cs-Javascript-This#Five Binding Rules]] for the receiver.
Also [[Cs-Javascript-This|the this note]] and ![[Cs-Javascript-This-Binding]].
### Links
- [[Cs-Javascript-This]] - the receiver
"""

MAP = """---
Type: structure
---
# Web Map
- [[Cs-Javascript-This]] - the this keyword
- [[Cs-Javascript-This-Binding]] - binding rules
- [[Cs-Javascript-Scope]] - scope
"""

RELATIVE = """---
Date: 2026-01-01
Type: literature
Categories: [CS]
Aliases: []
---
### Abstract
A note that links by relative Markdown path.
### Content
See [the this note](../language/javascript/Cs-Javascript-This.md) and [scope](../language/javascript/Cs-Javascript-Scope.md).
### Links
- [[Cs-Javascript-Scope]]
"""


def simple(title, body="Body.", categories="[CS]", extra=""):
    return f"---\nDate: 2026-01-01\nType: literature\nCategories: {categories}\nAliases: []\n{extra}---\n### Abstract\n{title}.\n### Content\n{body}\n### Links\n- [[Cs-Javascript-Scope]]\n"


class ReorgTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="reorg test 空間 ")
        self.root = Path(self.tmp.name)
        self.config = {"version": 1, "domains": {"cs": "111.cs", "web": "222.web"}, "maps": ["000.Index"], "shard_size": 40}
        self.put(k.POLICY, json.dumps(self.config))
        self.put("111.cs/language/javascript/Cs-Javascript-This.md", THIS)
        self.put("111.cs/language/javascript/Cs-Javascript-This-Binding.md", THIS_BINDING)
        self.put("111.cs/language/javascript/Cs-Javascript-Scope.md", SCOPE)
        self.put("111.cs/system-design/Cs-System-Design-Relative.md", RELATIVE)
        self.put("000.Index/Web-Map.md", MAP)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Reorg Test")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def read(self, name):
        return (self.root / name).read_text(encoding="utf-8")

    def git(self, *args):
        return k.git(self.root, *args)

    def corpus(self):
        return k.Corpus(k.Snapshot(self.root, "worktree"))

    # Seam: units — a note body split into the pieces the ledger tracks.
    def test_units_split_paragraphs_lists_tables_code_and_links(self):
        units = r.units(THIS)
        kinds = [u["kind"] for u in units]
        self.assertEqual(kinds, ["paragraph", "paragraph", "list", "table", "paragraph", "code", "links"])
        self.assertEqual(units[2]["text"].splitlines()[0], "1. Default binding falls back to the global object.")
        self.assertEqual(units[0]["heading"], "Abstract")
        self.assertEqual(units[4]["heading"], "Quick Decision Flowchart")
        self.assertTrue(all(u["id"].startswith("u-") and len(u["id"]) == 14 for u in units))
        self.assertEqual(units[0]["line"], 10)
        self.assertEqual(len({u["id"] for u in units}), len(units))

    # Seam: ledger — the preservation check over a cluster, a woven draft and the ledger rows.
    def test_ledger_check_requires_a_row_per_unit_and_verifies_kept_text(self):
        this, binding = r.units(THIS), r.units(THIS_BINDING)
        texts = {"a/Cs-Javascript-This.md": THIS, "a/Cs-Javascript-This-Binding.md": THIS_BINDING}

        def row(path, unit, status, **extra):
            return {"note": path, "unit": unit["id"], "status": status, **extra}

        rows = [row("a/Cs-Javascript-This.md", this[0], "reworded", heading="Abstract")]
        rows += [row("a/Cs-Javascript-This.md", u, "kept") for u in this[1:]]
        rows += [row("a/Cs-Javascript-This-Binding.md", binding[0], "reworded", heading="Abstract"),
                 row("a/Cs-Javascript-This-Binding.md", binding[1], "duplicate", of=this[1]["id"]),
                 row("a/Cs-Javascript-This-Binding.md", binding[2], "kept"),
                 row("a/Cs-Javascript-This-Binding.md", binding[3], "kept")]
        report = r.ledger_check(texts, DRAFT, {"version": 1, "rows": rows})
        self.assertTrue(report["ok"], report)
        self.assertEqual([x["status"] for x in report["review"]], ["reworded", "reworded", "duplicate"])
        self.assertEqual(report["counts"], {"kept": 8, "reworded": 2, "duplicate": 1})

        missing = r.ledger_check(texts, DRAFT, {"version": 1, "rows": rows[:-1]})
        self.assertFalse(missing["ok"])
        self.assertEqual([(m["note"], m["kind"]) for m in missing["missing"]], [("a/Cs-Javascript-This-Binding.md", "links")])

        bad = r.ledger_check(texts, DRAFT.replace("Ask who called the function", "Ask who invoked it"), {"version": 1, "rows": rows})
        self.assertEqual([m["heading"] for m in bad["mismatch"]], ["Quick Decision Flowchart"])

        rows[-3]["of"] = "u-000000000000"
        dangling = r.ledger_check(texts, DRAFT, {"version": 1, "rows": rows})
        self.assertEqual(len(dangling["dangling"]), 1)
        self.assertFalse(dangling["ok"])

    # Seam: survey — deterministic signals and candidate clusters over the eligible corpus.
    def test_survey_reports_signals_and_candidate_clusters(self):
        self.put("111.cs/lonely/Cs-Lonely-Note.md", simple("Alone in a folder"))
        self.put("111.cs/database/postgres/sql/Database-Postgres-Querying.md", simple("Deep and misprefixed"))
        self.put("222.web/Web-Fetch.md", simple("Fetch", extra="Aliases: [HTTP client]\n").replace("Aliases: []\n", ""))
        self.put("222.web/Web-Http-Client.md", simple("HTTP client", extra="Aliases: [http client, XHR]\n").replace("Aliases: []\n", ""))
        self.put("222.web/Web-Long.md", simple("Long", body="\n".join(f"Line {i}." for i in range(130))))
        report = r.survey(self.corpus())
        s = report["signals"]
        self.assertEqual(s["tiny_folders"], [{"folder": "111.cs/database/postgres/sql", "notes": 1},
                                             {"folder": "111.cs/lonely", "notes": 1},
                                             {"folder": "111.cs/system-design", "notes": 1}])
        self.assertEqual(s["deep_paths"], ["111.cs/database/postgres/sql/Database-Postgres-Querying.md"])
        self.assertEqual(s["prefix_mismatch"], ["111.cs/database/postgres/sql/Database-Postgres-Querying.md"])
        self.assertEqual(s["nav_leftovers"], ["111.cs/language/javascript/Cs-Javascript-Scope.md"])
        self.assertEqual(s["oversized"], [])
        clusters = [c["notes"] for c in report["clusters"]]
        self.assertEqual(clusters, [["111.cs/language/javascript/Cs-Javascript-This-Binding.md",
                                     "111.cs/language/javascript/Cs-Javascript-This.md"],
                                    ["222.web/Web-Fetch.md", "222.web/Web-Http-Client.md"]])
        reasons = " | ".join(report["clusters"][0]["reasons"])
        self.assertIn("name stem", reasons)
        self.assertIn("Five Binding Rules", reasons)
        self.assertIn("alias", " | ".join(report["clusters"][1]["reasons"]))
        # The core treats `../` Markdown links as outside references, so only Scope and the map count.
        self.assertEqual(report["clusters"][0]["inbound"]["111.cs/language/javascript/Cs-Javascript-This.md"], 2)

        web_only = r.survey(self.corpus(), target="222.web")
        self.assertEqual([c["notes"] for c in web_only["clusters"]], [["222.web/Web-Fetch.md", "222.web/Web-Http-Client.md"]])
        self.assertEqual(web_only["signals"]["nav_leftovers"], [])

        self.config["reorg"] = {"oversized_lines": 100}
        self.put(k.POLICY, json.dumps(self.config))
        self.assertEqual(r.survey(self.corpus())["signals"]["oversized"], [{"path": "222.web/Web-Long.md", "lines": 141}])

    JS = "111.cs/language/javascript/"

    def weave_mapping(self, draft=None, moves=True):
        """Write the draft and a complete ledger for the This → This-Binding weave; return the mapping."""
        draft = DRAFT if draft is None else draft
        this, binding = r.units(THIS), r.units(THIS_BINDING)
        rows = [{"note": self.JS + "Cs-Javascript-This.md", "unit": this[0]["id"], "status": "reworded", "heading": "Abstract"}]
        rows += [{"note": self.JS + "Cs-Javascript-This.md", "unit": u["id"], "status": "kept"} for u in this[1:]]
        rows += [{"note": self.JS + "Cs-Javascript-This-Binding.md", "unit": binding[0]["id"], "status": "reworded", "heading": "Abstract"},
                 {"note": self.JS + "Cs-Javascript-This-Binding.md", "unit": binding[1]["id"], "status": "duplicate", "of": this[1]["id"]},
                 {"note": self.JS + "Cs-Javascript-This-Binding.md", "unit": binding[2]["id"], "status": "kept"},
                 {"note": self.JS + "Cs-Javascript-This-Binding.md", "unit": binding[3]["id"], "status": "kept"}]
        self.put("docs/plans/reorg/this/draft.md", draft)
        self.put("docs/plans/reorg/this/ledger.json", json.dumps({"version": 1, "rows": rows}))
        mapping = {"version": 1, "scope": self.JS.rstrip("/"),
                   "merges": [{"survivor": self.JS + "Cs-Javascript-This-Binding.md", "absorbed": [self.JS + "Cs-Javascript-This.md"],
                               "draft": "docs/plans/reorg/this/draft.md", "ledger": "docs/plans/reorg/this/ledger.json"}],
                   "moves": [{"from": "111.cs/system-design/Cs-System-Design-Relative.md", "to": "111.cs/Cs-System-Design-Relative.md"}] if moves else []}
        self.put("docs/plans/reorg/this/mapping.json", json.dumps(mapping))
        return mapping

    # Seam: plan — a mapping becomes a dry-run report: operations, every link rewrite, aliases, dirty files.
    def test_plan_lists_every_link_rewrite_and_touched_file(self):
        self.weave_mapping()
        report = r.plan(self.corpus(), r.load_mapping(self.root, "docs/plans/reorg/this/mapping.json"))
        self.assertEqual(report["errors"], [])
        self.assertFalse(report["applied"])
        self.assertEqual(report["ledger"]["ok"], True)
        scope, web_map, relative = self.JS + "Cs-Javascript-Scope.md", "000.Index/Web-Map.md", "111.cs/system-design/Cs-System-Design-Relative.md"
        rewrites = {(x["file"], x["line"], x["action"], x["new"]) for x in report["link_rewrites"]}
        self.assertEqual(rewrites, {
            (scope, 7, "rewrite", "Next: '[[Cs-Javascript-This-Binding]]'"),
            (scope, 12, "rewrite", "See [[Cs-Javascript-This-Binding#Five Binding Rules]] for the receiver."),
            (scope, 13, "rewrite", "Also [[Cs-Javascript-This-Binding|the this note]] and ![[Cs-Javascript-This-Binding]]."),
            (scope, 15, "rewrite", "- [[Cs-Javascript-This-Binding]] - the receiver"),
            (web_map, 5, "drop", ""),
            (relative, 10, "rewrite", "See [the this note](111.cs/language/javascript/Cs-Javascript-This-Binding.md) and [scope](111.cs/language/javascript/Cs-Javascript-Scope.md)."),
        })
        self.assertEqual(report["aliases_to_add"], {})
        self.assertEqual(report["touched"], sorted([web_map, "111.cs/Cs-System-Design-Relative.md", scope, self.JS + "Cs-Javascript-This-Binding.md",
                                                    self.JS + "Cs-Javascript-This.md", relative]))
        self.assertEqual(report["dirty"], [])
        self.assertIn("Cs-Javascript-This-Binding", report["markdown"])

        bare = DRAFT.replace("Aliases: [this keyword, this binding, Cs-Javascript-This]", "Aliases: [this binding]")
        self.weave_mapping(draft=bare)
        report = r.plan(self.corpus(), r.load_mapping(self.root, "docs/plans/reorg/this/mapping.json"))
        self.assertEqual(report["aliases_to_add"], {self.JS + "Cs-Javascript-This-Binding.md": ["Cs-Javascript-This", "this keyword"]})

        self.put(scope, SCOPE + "\nunsaved edit\n")
        report = r.plan(self.corpus(), r.load_mapping(self.root, "docs/plans/reorg/this/mapping.json"))
        self.assertEqual(report["dirty"], [scope])

    def test_plan_rejects_invalid_mappings_without_raising(self):
        self.weave_mapping()
        base = r.load_mapping(self.root, "docs/plans/reorg/this/mapping.json")

        def errors(**changes):
            mapping = json.loads(json.dumps(base))
            for key, value in changes.items():
                mapping[key] = value
            return " | ".join(r.plan(self.corpus(), mapping)["errors"])

        merge = base["merges"][0]
        self.assertIn("not an eligible note", errors(merges=[{**merge, "absorbed": [self.JS + "Cs-Javascript-Missing.md"]}]))
        self.assertIn("move target exists", errors(moves=[{"from": "111.cs/system-design/Cs-System-Design-Relative.md", "to": self.JS + "Cs-Javascript-Scope.md"}]))
        self.assertIn("used more than once", errors(merges=[merge, {**merge, "absorbed": [self.JS + "Cs-Javascript-Scope.md"]}]))
        self.assertIn("duplicate basename", errors(moves=[{"from": "111.cs/system-design/Cs-System-Design-Relative.md", "to": "222.web/Cs-Javascript-Scope.md"}]))
        self.assertIn("maps cannot be woven", errors(merges=[{**merge, "absorbed": ["000.Index/Web-Map.md"]}]))
        self.assertIn("needs a draft", errors(merges=[{key: value for key, value in merge.items() if key != "draft"}]))
        self.assertIn("rename target", errors(merges=[{**merge, "rename": self.JS + "Cs-Javascript-Scope.md"}]))
        with self.assertRaises(k.KnowledgeError):
            r.load_mapping(self.root, "docs/plans/reorg/this/ledger.json")

    # Seam: apply — the mapping is performed, the catalog rebuilt, exactly the touched files staged.
    def test_apply_weaves_moves_rebuilds_and_stages_only_its_own_files(self):
        self.put("222.web/Web-Unrelated.md", simple("Unrelated pending work") + "\nhalf-written paragraph\n")
        self.put("222.web/Web-Untracked.md", simple("Untracked"))
        before_unrelated = self.read("222.web/Web-Unrelated.md")
        mapping = self.weave_mapping()
        result = r.apply(self.corpus(), mapping)
        self.assertTrue(result["changed"])
        survivor = self.JS + "Cs-Javascript-This-Binding.md"
        self.assertFalse((self.root / self.JS / "Cs-Javascript-This.md").exists())
        self.assertIn("#### Interview Questions", self.read(survivor))
        self.assertIn("Aliases: [this keyword, this binding, Cs-Javascript-This]", self.read(survivor))
        scope = self.read(self.JS + "Cs-Javascript-Scope.md")
        self.assertIn("Next: '[[Cs-Javascript-This-Binding]]'", scope)
        self.assertIn("[[Cs-Javascript-This-Binding#Five Binding Rules]]", scope)
        self.assertNotIn("[[Cs-Javascript-This]]", scope)
        self.assertEqual(self.read("000.Index/Web-Map.md"), MAP.replace("- [[Cs-Javascript-This]] - the this keyword\n", ""))
        self.assertFalse((self.root / "111.cs/system-design/Cs-System-Design-Relative.md").exists())
        self.assertIn("(111.cs/language/javascript/Cs-Javascript-This-Binding.md)", self.read("111.cs/Cs-System-Design-Relative.md"))
        self.assertEqual(self.corpus().issues(), [])
        self.assertEqual(self.corpus().freshness(), "current")
        staged = set(os.fsdecode(x) for x in self.git("diff", "--cached", "--name-only", "--no-renames", "-z").split(b"\0") if x)
        self.assertEqual(staged, {survivor, self.JS + "Cs-Javascript-This.md", self.JS + "Cs-Javascript-Scope.md", "000.Index/Web-Map.md",
                                  "111.cs/system-design/Cs-System-Design-Relative.md", "111.cs/Cs-System-Design-Relative.md",
                                  ".claude/index.md", ".claude/QUALITY.md", ".claude/index/manifest.json", ".claude/index/cs-001.md", ".claude/index/maps-001.md",
                                  ".claude/index/web-001.md"})
        self.assertEqual(set(result["staged"]), staged)
        self.assertEqual(self.read("222.web/Web-Unrelated.md"), before_unrelated)
        self.assertIn("weave", result["commit_message"])
        self.assertIn("Cs-Javascript-This-Binding", result["commit_message"])

        again = r.apply(self.corpus(), mapping)
        self.assertFalse(again["changed"])
        self.assertTrue(again["applied"])

    def test_apply_refuses_dirty_touched_files_and_failing_ledgers(self):
        mapping = self.weave_mapping()
        self.put(self.JS + "Cs-Javascript-Scope.md", SCOPE + "\nunsaved edit\n")
        before = self.tree()
        with self.assertRaisesRegex(k.KnowledgeError, "Cs-Javascript-Scope"):
            r.apply(self.corpus(), mapping)
        self.assertEqual(before, self.tree())
        self.git("checkout", "--", self.JS + "Cs-Javascript-Scope.md")
        ledger = json.loads(self.read("docs/plans/reorg/this/ledger.json"))
        ledger["rows"].pop()
        self.put("docs/plans/reorg/this/ledger.json", json.dumps(ledger))
        before = self.tree()
        with self.assertRaisesRegex(k.KnowledgeError, "[Pp]reservation"):
            r.apply(self.corpus(), mapping)
        self.assertEqual(before, self.tree())

    def tree(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts}

    def test_survey_clusters_are_cliques_ranked_by_strength_not_chains(self):
        # A–B share "cache"; B–C share "strategy"; A–C share nothing: two pairs, never one chain of three.
        self.put("222.web/Web-Cache-Policy.md", simple("Cache policy"))
        self.put("222.web/Web-Cache-Strategy.md", simple("Cache strategy", body="#### Eviction\nLRU.", extra="Aliases: [快取策略]\n").replace("Aliases: []\n", ""))
        self.put("222.web/Web-Strategy-Pattern.md", simple("Strategy pattern"))
        self.put("222.web/Web-Caching.md", simple("Caching", body="#### Eviction\nLFU.", extra="Aliases: [快取策略]\n").replace("Aliases: []\n", ""))
        self.put("222.web/Web-Security-And-Auth.md", simple("Security and auth"))
        self.put("222.web/Web-Logging-And-Metrics.md", simple("Logging and metrics"))
        self.put("222.web/Web-Fetch.md", simple("Fetch", extra="Aliases: [HTTP client]\n").replace("Aliases: []\n", ""))
        self.put("222.web/Web-Http-Client.md", simple("HTTP client", extra="Aliases: [http client]\n").replace("Aliases: []\n", ""))
        clusters = r.survey(self.corpus(), target="222.web")["clusters"]
        notes = [c["notes"] for c in clusters]
        self.assertNotIn(["222.web/Web-Cache-Policy.md", "222.web/Web-Cache-Strategy.md", "222.web/Web-Strategy-Pattern.md"], notes)
        self.assertNotIn(["222.web/Web-Logging-And-Metrics.md", "222.web/Web-Security-And-Auth.md"], notes)
        self.assertEqual(notes[0], ["222.web/Web-Cache-Strategy.md", "222.web/Web-Caching.md"])  # shared alias ranks first
        self.assertGreater(clusters[0]["score"], clusters[-1]["score"])
        self.assertTrue(all(len(c["notes"]) == 2 for c in clusters))

    def test_move_that_renames_rewrites_plain_wikilinks_and_keeps_the_old_name_as_alias(self):
        self.put("111.cs/lonely/Cs-Lonely-Note.md", simple("Alone"))
        self.put("111.cs/Cs-Pointer.md", simple("Points", body="See [[Cs-Lonely-Note]] and [[Cs-Lonely-Note#Content|the content]]."))
        self.git("add", ".")
        self.git("commit", "-qm", "lonely")
        mapping = {"version": 1, "moves": [{"from": "111.cs/lonely/Cs-Lonely-Note.md", "to": "111.cs/Cs-Lonely.md"}]}
        report = r.plan(self.corpus(), mapping)
        self.assertEqual(report["errors"], [])
        self.assertEqual([(x["line"], x["new"]) for x in report["link_rewrites"]], [(10, "See [[Cs-Lonely]] and [[Cs-Lonely#Content|the content]].")])
        self.assertEqual(report["aliases_to_add"], {"111.cs/lonely/Cs-Lonely-Note.md": ["Cs-Lonely-Note"]})
        r.apply(self.corpus(), mapping)
        self.assertIn("Aliases: [Cs-Lonely-Note]", self.read("111.cs/Cs-Lonely.md"))
        self.assertIn("[[Cs-Lonely#Content|the content]]", self.read("111.cs/Cs-Pointer.md"))
        self.assertEqual(self.corpus().issues(), [])

    # Seam: the CLI — knowledge.py dispatches `reorg` subcommands with lint-style exit codes.
    def test_cli_reorg_subcommands_and_exit_codes(self):
        import subprocess

        def cli(*args):
            p = subprocess.run([sys.executable, "-B", str(SCRIPTS / "knowledge.py"), "--vault", str(self.root), "reorg", *args],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8")

        self.weave_mapping()
        code, out, err = cli("survey", "--target", "111.cs")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(len(json.loads(out)["clusters"]), 1)
        code, out, _ = cli("units", self.JS + "Cs-Javascript-This.md")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["units"][2]["kind"], "list")
        code, out, _ = cli("plan", "docs/plans/reorg/this/mapping.json")
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)["operations"]), 2)
        code, out, _ = cli("plan", "docs/plans/reorg/this/mapping.json", "--markdown")
        self.assertTrue(out.startswith("# Reorganization plan"))
        code, out, _ = cli("ledger", "docs/plans/reorg/this/mapping.json")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["ok"])
        self.put(self.JS + "Cs-Javascript-Scope.md", SCOPE + "\nunsaved edit\n")
        code, out, _ = cli("plan", "docs/plans/reorg/this/mapping.json")
        self.assertEqual(code, 1)
        code, out, err = cli("apply", "docs/plans/reorg/this/mapping.json")
        self.assertEqual(code, 2)
        self.assertIn("Uncommitted edits", err)
        self.git("checkout", "--", self.JS + "Cs-Javascript-Scope.md")
        code, out, err = cli("apply", "docs/plans/reorg/this/mapping.json")
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(json.loads(out)["changed"])
        code, out, _ = cli("plan", "docs/plans/reorg/this/mapping.json")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["applied"])
        code, _, err = cli("plan", "docs/plans/reorg/this/ledger.json")
        self.assertEqual(code, 2)
        self.assertIn("no operations", err)


DRAFT = """---
Date: 2026-11-04
Type: literature
Categories: [CS, JavaScript]
Aliases: [this keyword, this binding, Cs-Javascript-This]
---
### Abstract
`this` is bound at call time: how a function is called decides its receiver.
### Content
#### Five Binding Rules
The value of `this` depends on how a function is called.

1. Default binding falls back to the global object.
2. Implicit binding uses the call-site object.
3. Explicit binding uses call, apply or bind.

| Rule | Example |
|---|---|
| Default | `f()` |
| Implicit | `obj.f()` |

#### Quick Decision Flowchart
Ask who called the function, then walk the rules in order.

```js
function f() { return this; }
```
#### Interview Questions
What does `this` refer to inside an arrow function?
### Links
- [[Cs-Javascript-Scope]] - scope decides variables, this decides the receiver
"""


if __name__ == "__main__":
    unittest.main()
