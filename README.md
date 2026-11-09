# bundesliga-mcp ⚽

mcp-name: io.github.mohammad-abbasi-sh/bundesliga-mcp

Unofficial **read-only** MCP server for **German football** via the free [OpenLigaDB](https://api.openligadb.de) API — Bundesliga fixtures, live scores, tables and top scorers. No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory" (Sepehr-style pipeline). Not affiliated with OpenLigaDB or the DFL.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "bundesliga": {
      "command": "uvx",
      "args": ["bundesliga-mcp"]
    }
  }
}
```

Or run locally: `python -m bundesliga_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `bundesliga_list_leagues` | Leagues with their current season — bl1, bl2, bl3, dfb, del, bbl, hbl |
| `bundesliga_get_fixtures` | One matchday's fixtures/results — `league` (default bl1), `season` (default current, e.g. "2026"), `matchday` (default current, 1..34) |
| `bundesliga_get_live_scores` | Current matchday: score + status (finished/live/scheduled) per match — `league` |
| `bundesliga_get_table` | League table — `league`, `season` (default current) |
| `bundesliga_get_top_scorers` | Top scorers of a season — `league`, `season` (default current), `limit` 1..50 |
| `bundesliga_get_match_detail` | Full detail of one match (score, goals with minutes/scorers, venue) — `match_id`, `league`, `season` |

Example output (`bundesliga_get_table` / bl1, season 2026):

```json
{"league": "bl1", "season": "2026", "count": 18, "table": [
  {"position": 1, "team": "FC Bayern München", "short": "Bayern",
   "played": 9, "won": 6, "drawn": 3, "lost": 0,
   "goals_for": 29, "goals_against": 9, "goal_diff": 20, "points": 21},
  ...]}
```

Notes:
- A season defaults to the current one (resolved live from the league list); a matchday defaults to the current matchday.
- Top scorers are aggregated from the per-match goal events (own goals excluded) — the API's own goalscorer endpoint returns 404, so the server counts the goals itself.
- `bbl`/`hbl` have no league entry published yet — their tools return empty results until OpenLigaDB publishes them. DEL (ice hockey) works the same way as the football leagues.
- Data: OpenLigaDB public API — no key, no login, read-only. Data under the Open Database License (ODbL).

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_football.py` — offline, parses real captured API fixtures (20 tests)
- `tests/test_live.py` — cautious live requests against api.openligadb.de (7 tests)

Tests: 27/27 green (20 offline + 7 live, 2026-11-09).

## License

MIT
