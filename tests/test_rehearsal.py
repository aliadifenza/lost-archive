"""The deterministic rehearsal is reproducible, and its shipped outputs regenerate exactly.

The outcome is pinned: if a code change alters any rehearsal result, this test
fails and the change must be reviewed against the predictions.
"""

import json
import os
import unittest

from lostarchive.rehearsal import run_rehearsal

ROOT = os.path.join(os.path.dirname(__file__), "..")


class TestRehearsal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results, cls.evaluated = run_rehearsal()

    def test_every_prediction_resolves(self):
        self.assertEqual(len(self.evaluated), 56)
        self.assertEqual([e["id"] for e in self.evaluated if e["error"]], [])

    def test_reproducible(self):
        _, again = run_rehearsal()
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.evaluated, sort_keys=True))

    def test_shipped_results_regenerate(self):
        with open(os.path.join(ROOT, "rehearsal", "RESULTS.json"), encoding="utf-8") as f:
            shipped = json.load(f)
        self.assertEqual(json.loads(json.dumps(self.evaluated, sort_keys=True)), shipped)

    def test_outcome_pinned(self):
        # 55/56 held; the single miss (P23) is a prediction error documented in FINDINGS.md.
        self.assertEqual([e["id"] for e in self.evaluated if not e["holds"]], ["P23"])

    def test_predictions_file_unchanged_since_commit(self):
        # Guard against editing predictions after seeing results.
        with open(os.path.join(ROOT, "rehearsal", "predictions.json"), encoding="utf-8") as f:
            spec = json.load(f)
        self.assertIn("before any rehearsal scenario was implemented", spec["written"])
        p23 = next(p for p in spec["predictions"] if p["id"] == "P23")
        self.assertEqual(p23["value"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
