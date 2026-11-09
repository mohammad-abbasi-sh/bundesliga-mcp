"""Domain logic: shape OpenLigaDB responses into compact dicts (stdlib only)."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

# Leagues this server supports. Seasons are resolved live from
# getavailableleagues (latest season per shortcut) — never hardcoded.
CURATED = {
    "bl1": {"name": "1. Fußball-Bundesliga", "sport": "Fußball"},
    "bl2": {"name": "2. Fußball-Bundesliga", "sport": "Fußball"},
    "bl3": {"name": "3. Liga", "sport": "Fußball"},
    "dfb": {"name": "DFB-Pokal", "sport": "Fußball"},
    "del": {"name": "Deutsche Eishockey Liga", "sport": "Eishockey"},
    "bbl": {"name": "Basketball Bundesliga", "sport": "Basketball"},
    "hbl": {"name": "Handball-Bundesliga", "sport": "Handball"},
}


def validate_league(league: str) -> str:
    """Normalise a league shortcut; raise ValueError for unknown ones."""
    key = (league or "").strip().lower()
    if key not in CURATED:
        known = ", ".join(sorted(CURATED))
        raise ValueError(f"unknown league {league!r} (known: {known})")
    return key


def _season_key(season: str) -> tuple:
    # Numeric seasons sort numerically ("2026" > "2025"); others last, by string.
    try:
        return (0, int(season))
    except (TypeError, ValueError):
        return (1, str(season))


def latest_leagues(leagues_json: list) -> list[dict]:
    """Latest season per curated shortcut.

    Returns [{shortcut, name, season, sport}] sorted by shortcut.
    """
    best: dict[str, dict] = {}
    for entry in leagues_json or []:
        shortcut = str(entry.get("leagueShortcut", "")).strip().lower()
        if shortcut not in CURATED:
            continue
        season = str(entry.get("leagueSeason", "")).strip()
        if not season:
            continue
        cur = best.get(shortcut)
        if cur is None or _season_key(season) > _season_key(cur["season"]):
            sport = (entry.get("sport") or {}).get("sportName") or CURATED[shortcut]["sport"]
            best[shortcut] = {
                "shortcut": shortcut,
                "name": entry.get("leagueName") or CURATED[shortcut]["name"],
                "season": season,
                "sport": sport,
            }
    return [best[k] for k in sorted(best)]


def current_season(leagues_json: list, league: str) -> str | None:
    """Latest season for one league shortcut, or None if unpublished."""
    for row in latest_leagues(leagues_json):
        if row["shortcut"] == league:
            return row["season"]
    return None


def _result_score(match: dict, result_type_id: int) -> list[int] | None:
    for r in match.get("matchResults") or []:
        if r.get("resultTypeID") == result_type_id:
            return [r.get("pointsTeam1"), r.get("pointsTeam2")]
    return None


def _final_score(match: dict) -> list[int] | None:
    # The result with the highest order is the final one (After90Minutes,
    # or overtime/shootout for DEL). Half-time is type 1.
    results = match.get("matchResults") or []
    if not results:
        return None
    final = max(results, key=lambda r: r.get("resultOrderID", 0))
    return [final.get("pointsTeam1"), final.get("pointsTeam2")]


def _team(t: dict | None) -> dict:
    t = t or {}
    return {"name": t.get("teamName") or "", "short": t.get("shortName") or ""}


def _goals(match: dict) -> list[dict]:
    out = []
    team_names = {
        (match.get("team1") or {}).get("teamId"): (match.get("team1") or {}).get("teamName"),
        (match.get("team2") or {}).get("teamId"): (match.get("team2") or {}).get("teamName"),
    }
    for g in match.get("goals") or []:
        out.append(
            {
                "minute": g.get("matchMinute"),
                "scorer": g.get("goalGetterName") or "",
                "team": team_names.get(g.get("scoringTeamId")) or "",
                "penalty": bool(g.get("isPenalty")),
                "own_goal": bool(g.get("isOwnGoal")),
            }
        )
    return out


def match_status(match: dict, now: datetime | None = None) -> str:
    """finished | live | scheduled. matchDateTime is local time; naive compare."""
    if match.get("matchIsFinished"):
        return "finished"
    raw = match.get("matchDateTime") or ""
    try:
        kickoff = datetime.fromisoformat(raw)
    except ValueError:
        return "scheduled"
    ref = now or datetime.now()
    return "live" if kickoff <= ref else "scheduled"


def compact_match(match: dict, now: datetime | None = None) -> dict:
    """One match, compact: no icon URLs, no internal ids beyond match_id."""
    group = match.get("group") or {}
    return {
        "match_id": match.get("matchID"),
        "date": match.get("matchDateTime"),
        "matchday": group.get("groupName") or "",
        "team1": _team(match.get("team1")),
        "team2": _team(match.get("team2")),
        "status": match_status(match, now),
        "score": {
            "half": _result_score(match, 1),
            "final": _final_score(match),
        },
        "goals": _goals(match),
    }


def compact_table(rows: list) -> list[dict]:
    """League table, compact and position-ordered as returned by the API."""
    out = []
    for i, r in enumerate(rows or [], start=1):
        out.append(
            {
                "position": i,
                "team": r.get("teamName") or "",
                "short": r.get("shortName") or "",
                "played": r.get("matches"),
                "won": r.get("won"),
                "drawn": r.get("draw"),
                "lost": r.get("lost"),
                "goals_for": r.get("goals"),
                "goals_against": r.get("opponentGoals"),
                "goal_diff": r.get("goalDiff"),
                "points": r.get("points"),
            }
        )
    return out


def top_scorers(matches: list, limit: int = 10) -> list[dict]:
    """Aggregate scorers from a season's match goals.

    The API's own goalscorer endpoint returns 404 (verified 2026-11-09),
    so we count the per-match goal events instead. Own goals are excluded;
    penalties count for the scorer.
    """
    counts: Counter = Counter()
    penalties: Counter = Counter()
    teams: dict[str, str] = {}
    for m in matches or []:
        names = {
            (m.get("team1") or {}).get("teamId"): (m.get("team1") or {}).get("teamName"),
            (m.get("team2") or {}).get("teamId"): (m.get("team2") or {}).get("teamName"),
        }
        for g in m.get("goals") or []:
            if g.get("isOwnGoal"):
                continue
            scorer = (g.get("goalGetterName") or "").strip()
            if not scorer:
                continue
            counts[scorer] += 1
            if g.get("isPenalty"):
                penalties[scorer] += 1
            teams.setdefault(scorer, names.get(g.get("scoringTeamId")) or "")
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [
        {
            "scorer": name,
            "team": teams.get(name, ""),
            "goals": n,
            "penalties": penalties.get(name, 0),
        }
        for name, n in ranked[: max(1, limit)]
    ]
