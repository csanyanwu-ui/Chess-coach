"""
AI coaching layer.

Same pattern as before: build a prompt from computed stats, call Claude,
fall back to a deterministic template if no API key is set or the call
fails. See ai_coach.py's chess-specific prompt below for what makes the
feedback actually reference real numbers instead of generic advice.
"""
import os
import json
import logging
from .models import ProfileStats, CoachingResponse

logger = logging.getLogger(__name__)

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """You are an expert chess coach reviewing a student's recent games on Lichess. \
You're given aggregate stats: blunder/mistake/inaccuracy rates broken down by game phase \
(opening/middlegame/endgame), their opening repertoire with win rates, and overall results. \
Give specific, actionable coaching feedback that references the actual numbers you were given \
— never generic advice like "study more" or "be more careful".

Respond ONLY with valid JSON matching this exact shape, no markdown fences, no preamble:
{
  "summary": "2-3 sentence overview of their recent play",
  "strengths": ["specific strength referencing a stat", "..."],
  "focus_areas": ["specific issue referencing a stat", "..."],
  "drills": ["one concrete, specific practice recommendation per focus area"]
}
Keep strengths and focus_areas to 2-3 items each. Be direct and specific, not generic.
If blunder rate is notably higher in one phase, call that out by name. If there's a clearly
underperforming opening (low win rate over multiple games), name it and suggest what to study.
"""


def _build_user_prompt(stats: ProfileStats) -> str:
    lines = [
        f"Player: {stats.username}",
        f"Games analyzed: {stats.games_analyzed} of {stats.games_fetched} fetched",
        f"Record: {stats.win_rate}% wins, {stats.draw_rate}% draws, {stats.loss_rate}% losses",
        f"Average per game — Blunders: {stats.avg_blunders_per_game}, Mistakes: {stats.avg_mistakes_per_game}, Inaccuracies: {stats.avg_inaccuracies_per_game}",
        "Mistakes by game phase:",
    ]
    for p in stats.phase_breakdown:
        lines.append(f"  {p.phase}: {p.blunders} blunders, {p.mistakes} mistakes, {p.inaccuracies} inaccuracies")

    if stats.best_opening:
        lines.append(f"Best opening: {stats.best_opening.name} ({stats.best_opening.win_rate}% win rate over {stats.best_opening.games} games)")
    if stats.worst_opening:
        lines.append(f"Worst opening: {stats.worst_opening.name} ({stats.worst_opening.win_rate}% win rate over {stats.worst_opening.games} games)")

    lines.append(f"Average game length: {stats.avg_game_length_plies} plies")
    return "\n".join(lines)


def _fallback_coaching(stats: ProfileStats) -> CoachingResponse:
    strengths, focus_areas, drills = [], [], []

    if stats.win_rate >= 50:
        strengths.append(f"Solid overall results: {stats.win_rate}% win rate across {stats.games_fetched} games.")

    worst_phase = max(stats.phase_breakdown, key=lambda p: p.blunders + p.mistakes) if stats.phase_breakdown else None
    if worst_phase and (worst_phase.blunders + worst_phase.mistakes) > 0:
        focus_areas.append(
            f"Most mistakes happen in the {worst_phase.phase}: {worst_phase.blunders} blunders and "
            f"{worst_phase.mistakes} mistakes across recent analyzed games."
        )
        if worst_phase.phase == "endgame":
            drills.append("Practice basic king-and-pawn and rook endgames — Lichess's Practice section has structured endgame drills.")
        elif worst_phase.phase == "opening":
            drills.append("Review your most-played opening lines 8-10 moves deep to reduce early inaccuracies.")
        else:
            drills.append("Work through tactics puzzles focused on mid-game calculation to cut down on middlegame blunders.")

    if stats.worst_opening and stats.worst_opening.win_rate < 40:
        focus_areas.append(
            f"{stats.worst_opening.name} is underperforming: {stats.worst_opening.win_rate}% win rate over "
            f"{stats.worst_opening.games} games."
        )
        drills.append(f"Study a few master games in the {stats.worst_opening.name} to find where your understanding breaks down.")

    if stats.best_opening:
        strengths.append(f"{stats.best_opening.name} is a strength: {stats.best_opening.win_rate}% win rate over {stats.best_opening.games} games.")

    if not strengths:
        strengths.append("Consistent game length suggests steady time management overall.")
    if not focus_areas:
        focus_areas.append("No major red flags in this sample — focus on tactical sharpness and calculation depth.")
        drills.append("Daily tactics puzzles (10-15 min) to keep pattern recognition sharp.")

    summary = (
        f"{stats.username} played {stats.games_fetched} recent games ({stats.win_rate}% wins). "
        f"{'The main pattern worth addressing is phase-specific mistakes.' if focus_areas else 'Solid, consistent play overall.'}"
    )

    return CoachingResponse(
        username=stats.username,
        summary=summary,
        strengths=strengths[:3],
        focus_areas=focus_areas[:3],
        drills=drills[:3] or ["Daily tactics puzzles to build calculation speed."],
    )


def generate_coaching(stats: ProfileStats) -> CoachingResponse:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("No ANTHROPIC_API_KEY set — using fallback template coaching.")
        return _fallback_coaching(stats)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=MODEL,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(stats)}],
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        return CoachingResponse(
            username=stats.username,
            summary=data["summary"],
            strengths=data["strengths"],
            focus_areas=data["focus_areas"],
            drills=data["drills"],
        )
    except Exception:
        logger.exception("Claude API call failed — falling back to template coaching.")
        return _fallback_coaching(stats)
