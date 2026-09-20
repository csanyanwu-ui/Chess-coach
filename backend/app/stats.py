"""
Stats engine for chess coaching.

Deliberately relies on Lichess's own Inaccuracy/Mistake/Blunder judgments
rather than recomputing centipawn-loss thresholds ourselves — those
thresholds are Lichess's own well-established standard, and re-deriving
them from raw eval numbers would just be reinventing (and probably getting
subtly wrong) something already done correctly upstream.

Game phase is approximated by ply count (opening = first 10 plies,
middlegame = plies 11-30, endgame = beyond that) rather than board
material. That's a simplification — a more accurate version would look at
piece count on the board — but it's a reasonable proxy given the timeline,
and it's called out explicitly here rather than left silent.
"""
from collections import defaultdict
from typing import List, Optional
from .models import GameRecord, ProfileStats, OpeningStat, PhaseBreakdown, Phase, MoveJudgment

MIN_GAMES_FOR_OPENING_RANKING = 2


def _phase_for_ply(ply: int) -> Phase:
    if ply <= 10:
        return "opening"
    if ply <= 30:
        return "middlegame"
    return "endgame"


def _phase_breakdown(games: List[GameRecord]) -> List[PhaseBreakdown]:
    counts = {p: {"Inaccuracy": 0, "Mistake": 0, "Blunder": 0} for p in ("opening", "middlegame", "endgame")}
    for game in games:
        for j in game.judgments:
            phase = _phase_for_ply(j.ply)
            counts[phase][j.judgment] += 1

    return [
        PhaseBreakdown(
            phase=phase,
            inaccuracies=counts[phase]["Inaccuracy"],
            mistakes=counts[phase]["Mistake"],
            blunders=counts[phase]["Blunder"],
        )
        for phase in ("opening", "middlegame", "endgame")
    ]


def _opening_repertoire(games: List[GameRecord]) -> List[OpeningStat]:
    grouped: dict[str, List[GameRecord]] = defaultdict(list)
    for g in games:
        if g.opening_name:
            grouped[g.opening_name].append(g)

    stats = []
    for name, group in grouped.items():
        wins = sum(1 for g in group if g.result == "win")
        losses = sum(1 for g in group if g.result == "loss")
        draws = sum(1 for g in group if g.result == "draw")
        stats.append(OpeningStat(
            name=name, games=len(group), wins=wins, losses=losses, draws=draws,
            win_rate=round(wins / len(group) * 100, 1),
        ))
    return sorted(stats, key=lambda s: s.games, reverse=True)


def compute_profile_stats(username: str, games: List[GameRecord], data_source: str) -> ProfileStats:
    analyzed_games = [g for g in games if g.analyzed]
    n = len(games)
    n_analyzed = len(analyzed_games)

    wins = sum(1 for g in games if g.result == "win")
    losses = sum(1 for g in games if g.result == "loss")
    draws = sum(1 for g in games if g.result == "draw")

    total_blunders = sum(sum(1 for j in g.judgments if j.judgment == "Blunder") for g in analyzed_games)
    total_mistakes = sum(sum(1 for j in g.judgments if j.judgment == "Mistake") for g in analyzed_games)
    total_inaccuracies = sum(sum(1 for j in g.judgments if j.judgment == "Inaccuracy") for g in analyzed_games)

    repertoire = _opening_repertoire(games)
    ranked = [o for o in repertoire if o.games >= MIN_GAMES_FOR_OPENING_RANKING]
    best_opening = max(ranked, key=lambda o: o.win_rate) if ranked else None
    worst_opening = min(ranked, key=lambda o: o.win_rate) if ranked else None

    return ProfileStats(
        username=username,
        games_fetched=n,
        games_analyzed=n_analyzed,
        win_rate=round(wins / n * 100, 1) if n else 0.0,
        draw_rate=round(draws / n * 100, 1) if n else 0.0,
        loss_rate=round(losses / n * 100, 1) if n else 0.0,
        avg_blunders_per_game=round(total_blunders / n_analyzed, 2) if n_analyzed else 0.0,
        avg_mistakes_per_game=round(total_mistakes / n_analyzed, 2) if n_analyzed else 0.0,
        avg_inaccuracies_per_game=round(total_inaccuracies / n_analyzed, 2) if n_analyzed else 0.0,
        phase_breakdown=_phase_breakdown(analyzed_games),
        opening_repertoire=repertoire,
        best_opening=best_opening,
        worst_opening=worst_opening,
        avg_game_length_plies=round(sum(g.num_plies for g in games) / n, 1) if n else 0.0,
        data_source=data_source,
    )
