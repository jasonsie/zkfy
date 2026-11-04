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
