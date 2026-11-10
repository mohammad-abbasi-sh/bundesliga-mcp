"""MCP server: unofficial read-only access to German football via OpenLigaDB."""
from __future__ import annotations

import json
from datetime import datetime, timezone
import sys

from mcp.server.fastmcp import FastMCP

from . import football as _fb
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for German football via the free \
OpenLigaDB API (api.openligadb.de) — no key, no login. Leagues: 1. \
Bundesliga (bl1), 2. Bundesliga (bl2), 3. Liga (bl3), DFB-Pokal (dfb), \
Deutsche Eishockey Liga (del), Basketball Bundesliga (bbl) and \
Handball-Bundesliga (hbl). A season defaults to the current one \
(resolved live from the league list); a matchday defaults to the \
current matchday. Scores come from the match results (half-time and \
final); top scorers are aggregated from the per-match goal events, \
because the API's own goalscorer endpoint returns 404. Data is under \
the Open Database License (ODbL). Built by Mohammad Abbasi \
(mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — Germany MCP factory.\
"""


_SOURCE = "api.openligadb.de"
_DISCLAIMER = "Unofficial read-only data from api.openligadb.de; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)

mcp = FastMCP("bundesliga-mcp", instructions=INSTRUCTIONS)

_SEASON_CACHE: dict[str, str] = {}


def _resolve_season(league: str) -> str:
    if league in _SEASON_CACHE:
        return _SEASON_CACHE[league]
    season = _fb.current_season(_http.fetch_leagues(), league)
    if not season:
        raise _http.BundesligaError(
            f"no current season published for league {league!r} yet "
            "(bbl/hbl publish later in the year) — pass season explicitly "
            "or try another league"
        )
    _SEASON_CACHE[league] = season
    return season


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})



@mcp.tool()
def bundesliga_list_leagues() -> str:
    """Leagues this server knows, with their current season (bl1, bl2, \
bl3, dfb, del, bbl, hbl)."""
    try:
        rows = _fb.latest_leagues(_http.fetch_leagues())
    except _http.BundesligaError as e:
        return _err(e)
    return _ok({
            "count": len(rows),
            "leagues": rows,
            "note": "bbl/hbl have no league entry published yet — their "
            "tools return empty results until the API publishes them.",
        })


@mcp.tool()
def bundesliga_get_fixtures(
    league: str = "bl1", season: str | None = None, matchday: int | None = None
) -> str:
    """Fixtures/results of one matchday. league: bl1/bl2/bl3/dfb/del/bbl/hbl. \
season: e.g. "2026" (default: current). matchday: 1..34 (default: current)."""
    try:
        lg = _fb.validate_league(league)
        se = season.strip() if season else _resolve_season(lg)
        if matchday is None:
            matches = _http.fetch_current_matchday(lg)
            md = (matches[0].get("group") or {}).get("groupOrderID") if matches else None
        else:
            if not 1 <= matchday <= 40:
                return _ok({"error": f"matchday out of range: {matchday} (expected 1..40)"})
            matches = _http.fetch_matchday(lg, se, matchday)
            md = matchday
    except (_http.BundesligaError, ValueError) as e:
        return _err(e)
    return _ok({
            "league": lg,
            "season": se,
            "matchday": md,
            "count": len(matches),
            "matches": [_fb.compact_match(m) for m in matches],
        })


@mcp.tool()
def bundesliga_get_live_scores(league: str = "bl1") -> str:
    """Current matchday: scores and status (finished/live/scheduled) for \
each match. league: bl1/bl2/bl3/dfb/del/bbl/hbl."""
    try:
        lg = _fb.validate_league(league)
        matches = _http.fetch_current_matchday(lg)
    except (_http.BundesligaError, ValueError) as e:
        return _err(e)
    season = str(matches[0].get("leagueSeason")) if matches else ""
    md = (matches[0].get("group") or {}).get("groupOrderID") if matches else None
    return _ok({
            "league": lg,
            "season": season,
            "matchday": md,
            "count": len(matches),
            "matches": [_fb.compact_match(m) for m in matches],
        })


@mcp.tool()
def bundesliga_get_table(league: str = "bl1", season: str | None = None) -> str:
    """League table. league: bl1/bl2/bl3/dfb/del/bbl/hbl. season: e.g. \
"2026" (default: current)."""
    try:
        lg = _fb.validate_league(league)
        se = season.strip() if season else _resolve_season(lg)
        rows = _http.fetch_table(lg, se)
    except (_http.BundesligaError, ValueError) as e:
        return _err(e)
    return _ok({"league": lg, "season": se, "count": len(rows), "table": _fb.compact_table(rows)})


@mcp.tool()
def bundesliga_get_top_scorers(
    league: str = "bl1", season: str | None = None, limit: int = 10
) -> str:
    """Top scorers of a season, aggregated from match goal events (own \
goals excluded). league: bl1/bl2/bl3/dfb/del/bbl/hbl. season: e.g. "2026" \
(default: current). limit: 1..50."""
    try:
        lg = _fb.validate_league(league)
        se = season.strip() if season else _resolve_season(lg)
        if not 1 <= limit <= 50:
            return _ok({"error": f"limit out of range: {limit} (expected 1..50)"})
        matches = _http.fetch_matches(lg, se)
    except (_http.BundesligaError, ValueError) as e:
        return _err(e)
    return _ok({
            "league": lg,
            "season": se,
            "count": len(matches),
            "scorers": _fb.top_scorers(matches, limit),
        })


@mcp.tool()
def bundesliga_get_match_detail(
    match_id: int, league: str = "bl1", season: str | None = None
) -> str:
    """Full detail of one match: score, goals with minutes and scorers, \
venue. match_id: from get_fixtures / get_live_scores. league: \
bl1/bl2/bl3/dfb/del/bbl/hbl. season: e.g. "2026" (default: current)."""
    try:
        lg = _fb.validate_league(league)
        se = season.strip() if season else _resolve_season(lg)
        matches = _http.fetch_matches(lg, se)
    except (_http.BundesligaError, ValueError) as e:
        return _err(e)
    for m in matches:
        if m.get("matchID") == match_id:
            detail = _fb.compact_match(m)
            loc = m.get("location") or {}
            detail["venue"] = loc.get("locationCity") or ""
            detail["stadium"] = loc.get("locationStadium") or ""
            detail["viewers"] = m.get("numberOfViewers")
            return _ok({"league": lg, "season": se, **detail})
    return _ok({
            "error": f"match {match_id} not found in {lg} season {se}",
            "hint": "use bundesliga_get_fixtures first to get a valid match_id",
        })


@mcp.tool()
def bundesliga_health() -> str:
    """Check whether api.openligadb.de is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
