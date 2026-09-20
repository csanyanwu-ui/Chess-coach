"""
Lichess API client.

Pulls a user's recent analyzed games from Lichess's public API — no auth
required for public game data. Docs: https://lichess.org/api#tag/Games

We request `analysed=true` so we only get games that already have Lichess's
own computer analysis (eval + judgment per move) attached. Not every game a
user plays gets analyzed, so for very inactive or brand-new accounts this
can return few or zero games — that's handled by falling back to
`fallback_data.py` in main.py, not here.
"""
import httpx
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

LICHESS_BASE = "https://lichess.org"
TIMEOUT_SECONDS = 12


class LichessError(Exception):
    pass


def fetch_recent_analyzed_games(username: str, max_games: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch up to `max_games` recent rated, analyzed games for a Lichess user.
    Returns a list of raw game dicts (Lichess's NDJSON schema, one dict per line).
    Raises LichessError on network failure, unknown user, or empty results.
    """
    url = f"{LICHESS_BASE}/api/games/user/{username}"
    params = {
        "max": max_games,
        "analysed": "true",
        "evals": "true",
        "opening": "true",
        "moves": "true",
        "rated": "true",
        "perfType": "bullet,blitz,rapid,classical",
    }
    headers = {"Accept": "application/x-ndjson"}

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params, headers=headers)
    except httpx.RequestError as e:
        raise LichessError(f"Network error contacting Lichess: {e}") from e

    if resp.status_code == 404:
        raise LichessError(f"Lichess user '{username}' not found")
    if resp.status_code == 429:
        raise LichessError("Rate limited by Lichess — try again shortly")
    if resp.status_code != 200:
        raise LichessError(f"Lichess API returned status {resp.status_code}")

    games = []
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            games.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Skipping malformed NDJSON line from Lichess")

    if not games:
        raise LichessError(f"No analyzed games found for '{username}'")

    return games
