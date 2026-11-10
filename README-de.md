# bundesliga-mcp ⚽

**Deutscher Fußball** über die kostenlose [OpenLigaDB](https://api.openligadb.de)-API — inoffizieller, **nur lesender** MCP-Server: Bundesliga-Spielpläne, Live-Ergebnisse, Tabellen und Torschützen. Kein Schlüssel, keine Anmeldung.

> Gebaut von Mohammad Abbasi im Rahmen der „Germany MCP factory“ (Sepehr-Stil). Keine Verbindung zu OpenLigaDB oder der DFL.

## Für KI-Agenten

In die MCP-Konfiguration eintragen (stdio):

```json
{
  "mcpServers": {
    "bundesliga": {
      "command": "uvx",
      "args": ["bundesliga-mcp==0.1.0"]
    }
  }
}
```

Oder lokal starten: `python -m bundesliga_mcp.server` (benötigt `mcp<2`, `httpx`).

## Werkzeuge

| Werkzeug | Beschreibung |
|------|-------------|
| `bundesliga_list_leagues` | Ligen mit aktueller Saison — bl1, bl2, bl3, dfb, del, bbl, hbl |
| `bundesliga_get_fixtures` | Spiele eines Spieltags — `league` (Standard: bl1), `season` (Standard: aktuell, z. B. „2026“), `matchday` (Standard: aktuell, 1..34) |
| `bundesliga_get_live_scores` | Aktueller Spieltag: Ergebnis + Status (finished/live/scheduled) pro Spiel — `league` |
| `bundesliga_get_table` | Tabelle — `league`, `season` (Standard: aktuell) |
| `bundesliga_get_top_scorers` | Torschützen einer Saison — `league`, `season` (Standard: aktuell), `limit` 1..50 |
| `bundesliga_get_match_detail` | Details eines Spiels (Ergebnis, Tore mit Minute und Torschütze, Spielort) — `match_id`, `league`, `season` |

Hinweise:
- Die Saison ist standardmäßig die aktuelle (wird live aus der Ligaliste ermittelt); der Spieltag standardmäßig der aktuelle.
- Torschützen werden aus den Tor-Ereignissen der Spiele gezählt (Eigentore ausgenommen) — der eigene Torschützen-Endpunkt der API liefert 404.
- `bbl`/`hbl` haben noch keinen Liga-Eintrag — ihre Werkzeuge liefern leere Ergebnisse, bis OpenLigaDB sie veröffentlicht. Die DEL (Eishockey) funktioniert wie die Fußball-Ligen.
- Daten: öffentliche OpenLigaDB-API — kein Schlüssel, keine Anmeldung, nur lesend. Daten unter der Open Database License (ODbL).

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_football.py` — offline, mit echten aufgezeichneten API-Antworten (20 Tests)
- `tests/test_live.py` — wenige vorsichtige Live-Anfragen an api.openligadb.de (7 Tests)

Tests: 27/27 grün (20 offline + 7 live, 09.11.2026).

## Lizenz

MIT
