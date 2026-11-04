"""Run: python3 -B -m unittest discover -s tests -p 'test_clip_note.py' -v"""
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


k = load("knowledge")
c = load("clip_note")

CLIP_META = {"source": "https://neon.com/postgresql/index?utm_source=x", "title": "深入理解 Postgres 索引",
             "author": "[[Ann Lee]], [[Bo Chen]]", "published": "", "created": datetime.date(2026, 10, 23),
             "description": "How indexes work.", "tags": ["row", "performance", "postgres"]}
DISCOVER = {"categories": ["CS", "Database"], "aliases": ["Postgres Index Internals", "深入理解 Postgres 索引"],
            "tags": ["advanced"], "related": ["CS-Harness"], "tag_vocabulary": ["performance", "advanced", "reference"]}
BODY = ("Intro text.\n\n![[deep-postgres-01-hero.avif|Hero]]\n\nSee [below](#filepos1).\n"
        "```md\n![[not-an-embed.png]]\n```\n### Details\n![[deep-postgres-02-chart.png]]\nEnd.\n")


def clip_text(meta, body):
    return "---\n" + k.yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n" + body


class AdaptTest(unittest.TestCase):
    def test_clip_table_maps_provenance_and_classification(self):
        meta, report = c.adapt("clip", CLIP_META, DISCOVER)
        self.assertEqual(list(meta), ["Date", "Type", "Mode", "Categories", "Aliases", "tags", "Link", "Author",
                                      "Description", "Source-Tags"])
        self.assertEqual(meta["Date"], datetime.date(2026, 10, 23))
        self.assertEqual((meta["Type"], meta["Mode"]), ("literature", "clip"))
        self.assertEqual(meta["Link"], CLIP_META["source"])
        self.assertEqual(meta["Author"], ["[[Ann Lee]]", "[[Bo Chen]]"])
        self.assertEqual(meta["Aliases"], ["深入理解 Postgres 索引", "Postgres Index Internals"])
        self.assertEqual(meta["tags"], ["advanced", "performance"])
        self.assertEqual(meta["Source-Tags"], ["postgres"])
        self.assertNotIn("Published", meta)
        self.assertTrue(any("published" in line for line in report))

    def test_unknown_keys_carry_over_in_source_order(self):
        meta, _ = c.adapt("clip", {**CLIP_META, "site": "Neon", "reading_time": 7}, DISCOVER)
        self.assertEqual(list(meta)[-2:], ["site", "reading_time"])
        self.assertEqual(meta["reading_time"], 7)

    def test_collision_with_a_zk_key_aborts(self):
        for key in ("Categories", "date", "Mode"):
            with self.assertRaises(c.AdaptError, msg=key):
                c.adapt("clip", {**CLIP_META, key: "x"}, DISCOVER)

    def test_text_and_video_tables(self):
        meta, _ = c.adapt("text", {}, DISCOVER, today=datetime.date(2026, 11, 4))
        self.assertEqual(meta["Date"], datetime.date(2026, 11, 4))
        self.assertNotIn("Link", meta)
        meta, _ = c.adapt("video", {"title": "Talk", "url": "https://youtu.be/x", "channel": "Conf"}, DISCOVER,
                          today=datetime.date(2026, 11, 4))
        self.assertEqual((meta["Link"], meta["Aliases"][0], meta["Author"]), ("https://youtu.be/x", "Talk", ["Conf"]))

    def test_discover_needs_categories(self):
        with self.assertRaises(c.AdaptError):
            c.adapt("clip", CLIP_META, {**DISCOVER, "categories": []})

    def test_normalize_url(self):
        n = c.normalize_url
        self.assertEqual(n("HTTPS://Neon.com/a/?utm_source=x&b=1#top"), "https://neon.com/a?b=1")
        self.assertEqual(n("https://neon.com/a/"), n("https://neon.com/a"))
        self.assertNotEqual(n("https://neon.com/a?b=1"), n("https://neon.com/a?b=2"))


class FormatTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="clip note 空間 ")
        self.root = Path(self.tmp.name)
        self.put(k.POLICY, json.dumps({"version": 1, "domains": {"cs": "111.cs"}}))
        self.put(".obsidian/app.json", json.dumps({"attachmentFolderPath": "raw/assets"}))
        self.put("111.cs/CS-Harness.md", "---\nDate: 2026-01-01\nType: permanent\nMode: thesis\nCategories: [CS]\n"
                 "---\n### 執行摘要\nx\n### Mental Model\ny\n### Theme\nz\n### Links\n")
        (self.root / "111.cs/database").mkdir(parents=True)
        self.put("raw/深入理解 Postgres 索引.md", clip_text(CLIP_META, BODY))
        adopted = BODY.replace("deep-postgres-01", "CS-Postgres-Index-Internals-01").replace(
            "deep-postgres-02", "CS-Postgres-Index-Internals-02")
        self.put("111.cs/database/CS-Postgres-Index-Internals.md", clip_text(CLIP_META, adopted))
        self.assets = "raw/assets/CS-Postgres-Index-Internals"
        entries = []
        for name, data in (("CS-Postgres-Index-Internals-01-hero.avif", b"avif"), ("CS-Postgres-Index-Internals-02-chart.png", b"png")):
            (self.root / self.assets).mkdir(parents=True, exist_ok=True)
            (self.root / self.assets / name).write_bytes(data)
            entries.append({"file": f"{self.assets}/{name}", "sha256": hashlib.sha256(data).hexdigest()})
        self.put(f"{self.assets}/assets.json", json.dumps({"slug": "CS-Postgres-Index-Internals", "assets": entries}))
        self.put("discover.json", json.dumps(DISCOVER))

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = c.main(["--vault", str(self.root), *args, "--json"])
        return code, json.loads(out.getvalue() or "{}")

    def fmt(self, *extra, source="111.cs/database/CS-Postgres-Index-Internals.md",
            dest="111.cs/database/CS-Postgres-Index-Internals.md"):
        return self.run_cli("format", "--kind", "clip", "--source", source, "--dest", dest,
                            "--original", "raw/深入理解 Postgres 索引.md", "--assets", self.assets,
                            "--discover", str(self.root / "discover.json"), *extra)

    def note(self):
        return (self.root / "111.cs/database/CS-Postgres-Index-Internals.md").read_text(encoding="utf-8")

    def test_formats_adopted_clip_in_place_and_passes_lint(self):
        raw_before = (self.root / "raw/深入理解 Postgres 索引.md").read_bytes()
        code, out = self.fmt()
        self.assertEqual(code, 0, out)
        self.assertTrue(out["written"])
        self.assertEqual(out["lint"], [])
        self.assertEqual(out["embeds"], 2)
        text = self.note()
        meta, body = c.split_frontmatter(text)
        self.assertEqual(meta["Mode"], "clip")
        self.assertTrue(body.startswith(BODY.replace("deep-postgres", "CS-Postgres-Index-Internals")))
        self.assertTrue(body.endswith("\n---\n### Links\n- [[CS-Harness]]\n"))
        self.assertEqual((self.root / "raw/深入理解 Postgres 索引.md").read_bytes(), raw_before)
        self.assertEqual(k.Corpus(k.Snapshot(self.root)).issues(), [])

    def test_dry_run_writes_nothing(self):
        before = self.note()
        code, out = self.fmt("--dry-run")
        self.assertEqual((code, out["written"], out["lint"]), (0, False, []))
        self.assertEqual(self.note(), before)

    def test_changed_body_fails_verification_and_writes_nothing(self):
        self.put("111.cs/database/CS-Postgres-Index-Internals.md",
                 clip_text(CLIP_META, BODY.replace("Intro text.", "Intro text, improved.")))
        before = self.note()
        code, out = self.fmt()
        self.assertEqual(code, 2)
        self.assertEqual(self.note(), before)
        self.assertIn("body", out["error"])

    def test_missing_or_altered_image_fails_verification(self):
        (self.root / self.assets / "CS-Postgres-Index-Internals-02-chart.png").write_bytes(b"other")
        self.assertEqual(self.fmt()[0], 2)
        (self.root / self.assets / "CS-Postgres-Index-Internals-02-chart.png").unlink()
        self.assertEqual(self.fmt()[0], 2)

    def test_duplicate_link_is_refused(self):
        self.put("111.cs/CS-Old-Clip.md", "---\nDate: 2026-01-01\nType: literature\nMode: clip\nCategories: [CS]\n"
                 "Link: 'https://neon.com/postgresql/index/'\n---\nx\n### Links\n")
        code, out = self.run_cli("find-link", "https://neon.com/postgresql/index?utm_source=y")
        self.assertEqual(code, 3)
        self.assertEqual(out["matches"][0]["path"], "111.cs/CS-Old-Clip.md")
        self.assertEqual(self.fmt()[0], 3)
        self.assertEqual(self.run_cli("find-link", "https://neon.com/other")[0], 0)

    def test_destination_rules(self):
        new = "111.cs/database/CS-Brand-New.md"
        self.assertEqual(self.fmt(dest="111.cs/CS-Harness.md")[0], 3)            # exists, not the source
        self.assertEqual(self.fmt(dest="111.cs/database/深入理解.md")[0], 1)       # not Train-Case
        self.assertEqual(self.fmt(dest="raw/CS-Out-Of-Scope.md")[0], 1)          # outside scope
        self.assertEqual(self.fmt(dest="111.cs/missing/CS-New-Folder.md")[0], 1)  # never creates folders
        self.assertEqual(self.fmt(dest="../CS-Escape.md")[0], 1)
        code, out = self.fmt(dest=new)                                           # copy to a new file
        self.assertEqual(code, 0, out)
        self.assertTrue((self.root / new).exists())
        self.assertTrue((self.root / "111.cs/database/CS-Postgres-Index-Internals.md").exists())

    def test_lint_failure_keeps_the_written_note(self):
        self.put("discover.json", json.dumps({**DISCOVER, "related": ["Nowhere-Note"]}))
        code, out = self.fmt()
        self.assertEqual(code, 6)
        self.assertTrue(out["written"])
        self.assertEqual([x["rule"] for x in out["lint"]], ["link-unresolved"])

    def test_text_source_without_assets(self):
        self.put("raw/src-my-notes.md", "Plain text with ![[local.png]] kept as is.\n")
        code, out = self.run_cli("format", "--kind", "text", "--source", "raw/src-my-notes.md",
                                 "--dest", "111.cs/CS-My-Notes.md", "--discover", str(self.root / "discover.json"))
        self.assertEqual(code, 0, out)
        meta, body = c.split_frontmatter((self.root / "111.cs/CS-My-Notes.md").read_text(encoding="utf-8"))
        self.assertNotIn("Link", meta)
        self.assertTrue(body.startswith("Plain text with ![[local.png]] kept as is.\n"))

    def test_release_deletes_only_raw_files(self):
        self.put("raw/src-my-notes.md", "x")
        self.assertEqual(self.run_cli("release", "raw/src-my-notes.md")[0], 0)
        self.assertFalse((self.root / "raw/src-my-notes.md").exists())
        self.assertEqual(self.run_cli("release", "111.cs/CS-Harness.md")[0], 1)
        self.assertEqual(self.run_cli("release", "raw/assets")[0], 1)
        (self.root / "raw/link.md").symlink_to(self.root / "111.cs/CS-Harness.md")
        self.assertEqual(self.run_cli("release", "raw/link.md")[0], 1)
        self.assertTrue((self.root / "111.cs/CS-Harness.md").exists())


if __name__ == "__main__":
    unittest.main()
