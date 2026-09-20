"""
Parses raw Lichess API game dicts into GameRecord models.

This is the one place that knows about Lichess's specific JSON shape.
Everything downstream (stats.py, ai_coach.py) only knows about GameRecord.
"""
import logging
from typing import List, Dict, Any, Optional
from .models import GameRecord, MoveJudgment

logger = logging.getLogger(__name__)


def _player_color(game: Dict[str, Any], username: str) -> Optional[str]:
    username_lower = username.lower()
    for color in ("white", "black"):
        user = game.get("players", {}).get(color, {}).get("user", {})
        if user.get("name", "").lower() == username_lower:
            return color
    return None


def _result_for_player(game: Dict[str, Any], player_color: str) -> str:
    winner = game.get("winner")
    if winner is None:
        return "draw"
    return "win" if winner == player_color else "loss"


def _extract_judgments(game: Dict[str, Any], player_color: str) -> List[MoveJudgment]:
    """
    Lichess's `analysis` array has one entry per ply (half-move), starting
    at ply 1 = white's first move. White's moves are odd plies, black's are
    even plies. We only keep judgments for the target player's own moves.
    """
    analysis = game.get("analysis") or []
    is_white = player_color == "white"
    judgments = []
    for idx, entry in enumerate(analysis):
        ply = idx + 1
        player_ply = (ply % 2 == 1) if is_white else (ply % 2 == 0)
        if not player_ply:
            continue
        judgment = entry.get("judgment")
        if judgment and judgment.get("name") in ("Inaccuracy", "Mistake", "Blunder"):
            judgments.append(MoveJudgment(
                ply=ply,
                judgment=judgment["name"],
                eval_after=entry.get("eval"),
            ))
    return judgments


def parse_game(game: Dict[str, Any], username: str) -> Optional[GameRecord]:
    """Returns None if the game can't be attributed to `username` (shouldn't
    normally happen given how we queried, but defensive parsing matters)."""
    color = _player_color(game, username)
    if color is None:
        logger.warning("Game %s does not list %s as a player — skipping", game.get("id"), username)
        return None

    opponent_color = "black" if color == "white" else "white"
    player_info = game.get("players", {}).get(color, {})
    opponent_info = game.get("players", {}).get(opponent_color, {})
    opening = game.get("opening") or {}
    analysis = game.get("analysis")
    moves_str = game.get("moves", "")
    num_plies = len(moves_str.split()) if moves_str else 0

    return GameRecord(
        game_id=game.get("id", "unknown"),
        speed=game.get("speed", "unknown"),
        rated=bool(game.get("rated", False)),
        player_color=color,
        player_rating=player_info.get("rating"),
        opponent_name=opponent_info.get("user", {}).get("name"),
        opponent_rating=opponent_info.get("rating"),
        result=_result_for_player(game, color),
        opening_name=opening.get("name"),
        opening_eco=opening.get("eco"),
        num_plies=num_plies,
        analyzed=analysis is not None,
        judgments=_extract_judgments(game, color) if analysis else [],
    )


def parse_games(raw_games: List[Dict[str, Any]], username: str) -> List[GameRecord]:
    parsed = [parse_game(g, username) for g in raw_games]
    return [g for g in parsed if g is not None]
