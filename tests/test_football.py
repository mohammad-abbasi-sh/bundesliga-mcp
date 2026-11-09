"""Offline tests — parse real captured OpenLigaDB responses, no network."""
import json
import pathlib
import sys
import unittest
from datetime import datetime
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from bundesliga_mcp import football as fb
from bundesliga_mcp import server as srv

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


class TestLeagues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = fb.latest_leagues(_load("leagues.json"))

    def test_curated_shortcuts(self):
        self.assertEqual(
            [r["shortcut"] for r in self.rows],
            ["bl1", "bl2", "bl3", "del", "dfb", "hbl"],
        )

    def test_bl1_latest_season(self):
        bl1 = [r for r in self.rows if r["shortcut"] == "bl1"][0]
        self.assertEqual(bl1["season"], "2026")
        self.assertEqual(bl1["name"], "1. Fußball-Bundesliga 2026/2027")
        self.assertEqual(bl1["sport"], "Fußball")

    def test_current_season(self):
        self.assertEqual(fb.current_season(_load("leagues.json"), "bl1"), "2026")
        self.assertIsNone(fb.current_season(_load("leagues.json"), "bbl"))

    def test_validate_league(self):
        self.assertEqual(fb.validate_league(" BL1 "), "bl1")
        with self.assertRaises(ValueError):
            fb.validate_league("premier-league")


class TestTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = fb.compact_table(_load("table-bl1-2026.json"))

    def test_row_count_and_order(self):
        self.assertEqual(len(self.table), 18)
        self.assertEqual(self.table[0]["position"], 1)
        self.assertEqual(self.table[17]["position"], 18)

    def test_bayern_row(self):
        top = self.table[0]
        self.assertEqual(top["team"], "FC Bayern München")
        self.assertEqual(top["short"], "Bayern")
        self.assertEqual(top["points"], 21)
        self.assertEqual(top["played"], 9)
        self.assertEqual(top["won"], 6)
        self.assertEqual(top["drawn"], 3)
        self.assertEqual(top["lost"], 0)
        self.assertEqual(top["goals_for"], 29)
        self.assertEqual(top["goals_against"], 9)
        self.assertEqual(top["goal_diff"], 20)


class TestMatches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md9 = _load("matchday9-bl1-2026.json")
        cls.compact = [fb.compact_match(m) for m in cls.md9]

    def test_match_count(self):
        self.assertEqual(len(self.compact), 9)

    def test_first_match_shape(self):
        m = self.compact[0]
        self.assertEqual(m["match_id"], 83234)
        self.assertEqual(m["team1"]["name"], "Hamburger SV")
        self.assertEqual(m["team2"]["name"], "Borussia Mönchengladbach")
        self.assertEqual(m["matchday"], "9. Spieltag")
        self.assertEqual(m["status"], "finished")
        self.assertEqual(m["score"]["final"], [3, 1])
        self.assertEqual(m["score"]["half"], [1, 1])
        self.assertEqual(len(m["goals"]), 4)

    def test_goal_shape(self):
        g = self.compact[0]["goals"][0]
        self.assertEqual(g["minute"], 11)
        self.assertEqual(g["scorer"], "M. Muheim")
        self.assertEqual(g["team"], "Hamburger SV")
        self.assertFalse(g["penalty"])
        self.assertFalse(g["own_goal"])

    def test_status_buckets(self):
        pending = {"matchIsFinished": False, "matchDateTime": "2026-11-06T20:30:00"}
        self.assertEqual(
            fb.match_status(pending, datetime(2026, 11, 6, 19, 0)), "scheduled"
        )
        self.assertEqual(
            fb.match_status(pending, datetime(2026, 11, 6, 21, 30)), "live"
        )
        # a finished match stays finished regardless of the reference time
        self.assertEqual(
            fb.match_status(self.md9[0], datetime(2026, 11, 6, 19, 0)), "finished"
        )

    def test_top_scorers_from_matchday(self):
        scorers = fb.top_scorers(self.md9, limit=5)
        # 30 goals total, 1 own goal -> 29 counted; two players on 2
        self.assertEqual(sum(s["goals"] for s in scorers[:5]), 2 + 2 + 1 + 1 + 1)
        self.assertEqual(scorers[0]["goals"], 2)
        self.assertIn(scorers[0]["scorer"], ("F. Nmecha", "J. Burkardt"))
        # own goals never appear as scorers
        self.assertNotIn("own goal", [s["scorer"] for s in scorers])

    def test_top_scorers_limit(self):
        self.assertEqual(len(fb.top_scorers(self.md9, limit=3)), 3)


class TestToolsMocked(unittest.TestCase):
    """Exercise the tool functions with the HTTP layer stubbed."""

    def test_list_leagues(self):
        with mock.patch.object(
            srv._http, "fetch_leagues", return_value=_load("leagues.json")
        ):
            out = json.loads(srv.bundesliga_list_leagues())
        self.assertEqual(out["count"], 6)
        self.assertEqual(out["leagues"][0]["shortcut"], "bl1")

    def test_get_table(self):
        with mock.patch.object(
            srv._http, "fetch_table", return_value=_load("table-bl1-2026.json")
        ):
            out = json.loads(srv.bundesliga_get_table("bl1", "2026"))
        self.assertEqual(out["count"], 18)
        self.assertEqual(out["table"][0]["team"], "FC Bayern München")

    def test_get_fixtures_matchday(self):
        with mock.patch.object(
            srv._http, "fetch_matchday", return_value=_load("matchday9-bl1-2026.json")
        ):
            out = json.loads(srv.bundesliga_get_fixtures("bl1", "2026", 9))
        self.assertEqual(out["matchday"], 9)
        self.assertEqual(out["count"], 9)

    def test_get_live_scores(self):
        with mock.patch.object(
            srv._http,
            "fetch_current_matchday",
            return_value=_load("matchday9-bl1-2026.json"),
        ):
            out = json.loads(srv.bundesliga_get_live_scores("bl1"))
        self.assertEqual(out["matchday"], 9)
        self.assertEqual(out["season"], "2026")
        self.assertTrue(all(m["status"] == "finished" for m in out["matches"]))

    def test_get_match_detail_found(self):
        with mock.patch.object(
            srv._http, "fetch_matches", return_value=_load("matchday9-bl1-2026.json")
        ):
            out = json.loads(srv.bundesliga_get_match_detail(83234, "bl1", "2026"))
        self.assertEqual(out["match_id"], 83234)
        self.assertEqual(out["team1"]["name"], "Hamburger SV")

    def test_get_match_detail_missing(self):
        with mock.patch.object(
            srv._http, "fetch_matches", return_value=_load("matchday9-bl1-2026.json")
        ):
            out = json.loads(srv.bundesliga_get_match_detail(1, "bl1", "2026"))
        self.assertIn("error", out)
        self.assertIn("not found", out["error"])

    def test_unknown_league_error_shape(self):
        out = json.loads(srv.bundesliga_get_table("xxx"))
        self.assertIn("error", out)
        self.assertIn("unknown league", out["error"])

    def test_bad_matchday_error_shape(self):
        out = json.loads(srv.bundesliga_get_fixtures("bl1", "2026", 99))
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
