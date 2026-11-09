"""Live tests — hit the real api.openligadb.de. Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set BUNDESLIGA_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from bundesliga_mcp import football as fb
from bundesliga_mcp import http as _http
from bundesliga_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("BUNDESLIGA_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="BUNDESLIGA_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_leagues_live(self):
        rows = fb.latest_leagues(_http.fetch_leagues())
        bl1 = [r for r in rows if r["shortcut"] == "bl1"]
        self.assertTrue(bl1, "bl1 should be in the league list")
        self.assertTrue(bl1[0]["season"].isdigit())
        self.assertGreaterEqual(int(bl1[0]["season"]), 2026)
        print(f"\nLIVE bl1 current season: {bl1[0]['season']}")

    def test_table_live(self):
        out = json.loads(srv.bundesliga_get_table("bl1"))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 18)
        self.assertGreater(out["table"][0]["points"], 0)
        print(f"\nLIVE bl1 table top: {out['table'][0]['team']} "
              f"{out['table'][0]['points']} pts")

    def test_live_scores_live(self):
        out = json.loads(srv.bundesliga_get_live_scores("bl1"))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(m["team1"]["name"] for m in out["matches"]))
        self.assertTrue(
            all(m["status"] in ("finished", "live", "scheduled") for m in out["matches"])
        )
        print(f"\nLIVE current matchday: {out['matchday']} "
              f"({out['count']} matches, season {out['season']})")

    def test_top_scorers_live(self):
        out = json.loads(srv.bundesliga_get_top_scorers("bl1", limit=5))
        self.assertNotIn("error", out)
        self.assertTrue(out["scorers"], "scorers should be non-empty mid-season")
        self.assertGreaterEqual(out["scorers"][0]["goals"], 1)
        print(f"\nLIVE top scorer: {out['scorers'][0]['scorer']} "
              f"({out['scorers'][0]['team']}) {out['scorers'][0]['goals']} goals")

    def test_match_detail_live(self):
        live = json.loads(srv.bundesliga_get_live_scores("bl1"))
        mid = live["matches"][0]["match_id"]
        out = json.loads(srv.bundesliga_get_match_detail(mid, "bl1"))
        self.assertNotIn("error", out)
        self.assertEqual(out["match_id"], mid)
        self.assertIn("venue", out)

    def test_del_table_live(self):
        out = json.loads(srv.bundesliga_get_table("del"))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 14)

    def test_bbl_returns_list(self):
        # bbl has no league entry published yet — the API answers with an
        # empty list for the current season, not an error.
        matches = _http.fetch_matches("bbl", "2026")
        self.assertIsInstance(matches, list)
