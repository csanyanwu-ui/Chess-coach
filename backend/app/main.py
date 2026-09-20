from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

from .lichess_client import fetch_recent_analyzed_games, LichessError
from .parser import parse_games
from .fallback_data import generate_fallback_games
from .stats import compute_profile_stats
from .ai_coach import generate_coaching
from .models import ProfileStats

logger = logging.getLogger(__name__)
app = FastAPI(title="Chess Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MIN_GAMES_FOR_LIVE_DATA = 5

# In-memory store keyed by username — fine for a demo.
PROFILES: dict[str, ProfileStats] = {}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/profile")
def build_profile(username: str, max_games: int = 20):
    """
    Fetches a Lichess user's recent analyzed games and computes coaching stats.
    Falls back to synthetic data if Lichess has too few analyzed games for this
    user (common for new/casual accounts) or the API is unreachable.
    """
    data_source = "live"
    try:
        raw_games = fetch_recent_analyzed_games(username, max_games=max_games)
        games = parse_games(raw_games, username)
        if len(games) < MIN_GAMES_FOR_LIVE_DATA:
            raise LichessError(f"Only {len(games)} analyzed games found — using fallback data")
    except LichessError as e:
        logger.info("Falling back to synthetic data for '%s': %s", username, e)
        games = generate_fallback_games(username, count=15)
        data_source = "fallback"

    stats = compute_profile_stats(username, games, data_source)
    PROFILES[username] = stats
    return {"username": username, "data_source": data_source, "games_fetched": stats.games_fetched}


@app.get("/api/profile/{username}/stats")
def get_stats(username: str):
    stats = PROFILES.get(username)
    if not stats:
        raise HTTPException(status_code=404, detail="Profile not found — call POST /api/profile first")
    return stats


@app.get("/api/profile/{username}/coaching")
def get_coaching(username: str):
    stats = PROFILES.get(username)
    if not stats:
        raise HTTPException(status_code=404, detail="Profile not found — call POST /api/profile first")
    return generate_coaching(stats)


frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
