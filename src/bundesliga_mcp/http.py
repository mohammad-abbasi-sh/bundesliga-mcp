"""HTTP layer for bundesliga_mcp — plain httpx against the free OpenLigaDB API.

No key, no login. OpenLigaDB (api.openligadb.de) is a free community
project; data is under the Open Database License (ODbL).
"""
from __future__ import annotations

import os
import ssl

import httpx

BASE = "https://api.openligadb.de"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
TIMEOUT = 20.0


class BundesligaError(RuntimeError):
    pass


def _verify():
    """TLS trust store: the OS bundle when present, else httpx/certifi.

    The OS bundle matters behind MITM egress proxies (their CA is in the
    system store, not in certifi) and is the right default on Linux
    anyway; on systems without it we fall back to certifi.
    """
    for path in (
        "/etc/ssl/certs/ca-certificates.crt",
        ssl.get_default_verify_paths().openssl_cafile,
    ):
        if path and os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return True


def _client() -> httpx.Client:
    # NOTE: we read the proxy URL from the environment but never log it.
    # trust_env=False because httpx fails to parse bracketed IPv6 entries
    # (e.g. [::1]) that some environments put in no_proxy.
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    return httpx.Client(
        headers={"User-Agent": UA},
        timeout=TIMEOUT,
        proxy=proxy or None,
        trust_env=False,
        verify=_verify(),
    )


def _get_json(url: str) -> list:
    try:
        with _client() as c:
            r = c.get(url)
    except httpx.HTTPError as e:
        raise BundesligaError(f"network error fetching {url}: {e}") from e
    if r.status_code == 404:
        raise BundesligaError(
            f"OpenLigaDB returned 404 for {url} (no data published for this "
            "league/season yet)"
        )
    if r.status_code != 200:
        raise BundesligaError(f"OpenLigaDB returned HTTP {r.status_code} for {url}")
    try:
        data = r.json()
    except ValueError as e:
        raise BundesligaError(f"OpenLigaDB returned invalid JSON for {url}") from e
    if not isinstance(data, list):
        raise BundesligaError(f"unexpected OpenLigaDB response shape for {url}")
    return data


def fetch_leagues() -> list:
    """All leagues known to OpenLigaDB (getavailableleagues)."""
    return _get_json(f"{BASE}/getavailableleagues")


def fetch_matches(league: str, season: str) -> list:
    """All matches of a league season (getmatchdata/{league}/{season})."""
    return _get_json(f"{BASE}/getmatchdata/{league}/{season}")


def fetch_matchday(league: str, season: str, matchday: int) -> list:
    """One matchday (getmatchdata/{league}/{season}/{matchday})."""
    return _get_json(f"{BASE}/getmatchdata/{league}/{season}/{matchday}")


def fetch_current_matchday(league: str) -> list:
    """The current matchday's matches (getmatchdata/{league})."""
    return _get_json(f"{BASE}/getmatchdata/{league}")


def fetch_table(league: str, season: str) -> list:
    """League table (getbltable/{league}/{season})."""
    return _get_json(f"{BASE}/getbltable/{league}/{season}")
