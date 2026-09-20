"""
Data models for Chess Coach.

GameRecord is the contract between the Lichess client (lichess_client.py +
parser.py) and everything downstream (stats, AI coach, API). Keeping this
stable means the stats engine doesn't care whether a GameRecord came from
a live Lichess fetch or a synthetic fallback profile.
"""
from __future__ import annotations
from pydantic import BaseModel
from typing import List, Literal, Optional

Judgment = Literal["Inaccuracy", "Mistake", "Blunder"]
Phase = Literal["opening", "middlegame", "endgame"]


class MoveJudgment(BaseModel):
    ply: int  # half-move number, 1-indexed
    judgment: Judgment
    eval_after: Optional[int] = None  # centipawns, from the mover's perspective, if available


class GameRecord(BaseModel):
    game_id: str
    speed: str  # bullet, blitz, rapid, classical
    rated: bool
    player_color: Literal["white", "black"]
    player_rating: Optional[int] = None
    opponent_name: Optional[str] = None
    opponent_rating: Optional[int] = None
    result: Literal["win", "loss", "draw"]
    opening_name: Optional[str] = None
    opening_eco: Optional[str] = None
    num_plies: int
    analyzed: bool  # whether Lichess computer analysis was available for this game
    judgments: List[MoveJudgment] = []  # only the player's own mistakes/blunders/inaccuracies


class OpeningStat(BaseModel):
    name: str
    games: int
    wins: int
    losses: int
    draws: int
    win_rate: float


class PhaseBreakdown(BaseModel):
    phase: Phase
    inaccuracies: int
    mistakes: int
    blunders: int


class ProfileStats(BaseModel):
    username: str
    games_fetched: int
    games_analyzed: int
    win_rate: float
    draw_rate: float
    loss_rate: float
    avg_blunders_per_game: float
    avg_mistakes_per_game: float
    avg_inaccuracies_per_game: float
    phase_breakdown: List[PhaseBreakdown]
    opening_repertoire: List[OpeningStat]
    best_opening: Optional[OpeningStat] = None
    worst_opening: Optional[OpeningStat] = None
    avg_game_length_plies: float
    data_source: Literal["live", "fallback"]


class CoachingResponse(BaseModel):
    username: str
    summary: str
    strengths: List[str]
    focus_areas: List[str]
    drills: List[str]
