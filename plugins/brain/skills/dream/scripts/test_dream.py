#!/usr/bin/env python3
"""Tests for dream.py - the deterministic transforms + idempotence guarantee.

Run: python3 test_dream.py    (pure stdlib, no deps)
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("dream", Path(__file__).with_name("dream.py"))
dream = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dream)

EMDASH = "—"

FIXTURE_INDEX = f"""# Memory

## Process Shortcuts
- [Real pointer](topic_real.md) - a real topic file {EMDASH} with an em-dash
- [Ghost pointer](topic_missing.md) - target does not exist on disk

## Voice Rules
- inline prose line one, not a file pointer
- inline prose line two
- inline prose line three
- inline prose line four
- inline prose line five
- inline prose line six

## Voice Rules (cont)
- continued prose line seven

# Environment

You have been invoked in the following environment:

- Primary working directory: /Users/example/project
- You are powered by the model named Sonnet 4.6.

- Model IDs {EMDASH} Opus 4.6.
"""


class DreamTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "MEMORY.md").write_text(FIXTURE_INDEX, encoding="utf-8")
        (self.d / "topic_real.md").write_text(
            "---\nname: topic_real\ndescription: real one\n---\nbody\n", encoding="utf-8")
        # an orphan: on disk, not referenced by the index
        (self.d / "topic_orphan.md").write_text(
            "---\nname: topic_orphan\ndescription: orphan desc\n---\nbody\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_env_trailer_stripped(self):
        new, _, rep = dream.build_new_index(self.d)
        self.assertNotIn("invoked in the following environment", new)
        self.assertNotIn("Sonnet 4.6", new)
        self.assertTrue(any("Environment" in a for a in rep["actions"]))

    def test_no_emdash_remains(self):
        new, files, _ = dream.build_new_index(self.d)
        self.assertNotIn(EMDASH, new)
        for text in files.values():
            self.assertNotIn(EMDASH, text)

    def test_cont_section_merged(self):
        new, _, rep = dream.build_new_index(self.d)
        self.assertNotIn("(cont)", new)
        self.assertIn("continued prose line seven", new)  # content preserved

    def test_orphan_reindexed(self):
        new, _, rep = dream.build_new_index(self.d)
        self.assertIn("topic_orphan.md", new)
        self.assertEqual(rep["orphans"], ["topic_orphan.md"])

    def test_ghost_link_dropped(self):
        new, _, rep = dream.build_new_index(self.d)
        self.assertNotIn("topic_missing.md", new)
        self.assertIn("topic_missing.md", rep["ghost_links"])

    def test_demotion_lossless(self):
        # force a tiny budget so the inline "Voice Rules" section must demote
        orig = dream.LINE_LIMIT
        dream.LINE_LIMIT = 12
        try:
            new, files, rep = dream.build_new_index(self.d)
        finally:
            dream.LINE_LIMIT = orig
        self.assertTrue(rep["demoted"], "expected a demotion under tiny budget")
        moved = files[rep["demoted"][0]["file"]]
        self.assertIn("inline prose line one", moved)      # content preserved in topic file
        self.assertIn("continued prose line seven", moved)  # merged content rode along

    def test_idempotent(self):
        new1, files1, _ = dream.build_new_index(self.d)
        for name, text in files1.items():
            (self.d / name).write_text(text, encoding="utf-8")
        (self.d / "MEMORY.md").write_text(new1, encoding="utf-8")
        new2, files2, rep2 = dream.build_new_index(self.d)
        self.assertEqual(new1, new2, "second rebuild must be byte-identical")
        self.assertEqual(files2, {}, "second rebuild must create no new files")


if __name__ == "__main__":
    unittest.main(verbosity=2)
