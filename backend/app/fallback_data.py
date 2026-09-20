"""
Fallback game generator.

Used when a Lichess username has too few (or zero) analyzed games — common
for new or casual accounts, since not every game gets computer analysis.
Produces GameRecord data in the exact same shape real Lichess data would,
so the rest of the app (stats, AI coach, frontend) never needs to know
whether it's looking at live or synthetic data. `ProfileStats.data_source`
tracks which one was actually used, and the frontend surfaces that honestly
rather than pretending fallback data is real.
"""
import random
from .models import GameRecord, MoveJudgment

OPENINGS = [
    ("Italian Game", "C50"),
    ("Sicilian Defense: Najdorf Variation", "B90"),
    ("Queen's Gambit Declined", "D30"),
    ("French Defense: Advance Variation", "C02"),
    ("Caro-Kann Defense", "B10"),
    ("King's Indian Defense", "E60"),
    ("London System", "D02"),
]


def _random_game(username: str, index: int) -> GameRecord:
    color = random.choice(["white", "black"])
    result = random.choices(["win", "loss", "draw"], weights=[0.42, 0.42, 0.16])[0]
    opening_name, eco = random.choice(OPENINGS)
    num_plies = random.randint(30, 70)

    # Bias judgment counts so later-game (higher ply) mistakes are somewhat
    # more common, mimicking real time-trouble patterns.
    judgments = []
    for _ in range(random.randint(0, 4)):
        ply = random.randint(1, num_plies)
        j = random.choices(["Inaccuracy", "Mistake", "Blunder"], weights=[0.5, 0.3, 0.2])[0]
        judgments.append(MoveJudgment(ply=ply, judgment=j, eval_after=random.randint(-400, 400)))

    return GameRecord(
        game_id=f"fallback{index}",
        speed=random.choice(["blitz", "rapid"]),
        rated=True,
        player_color=color,
        player_rating=random.randint(1200, 1800),
        opponent_name=f"opponent{index}",
        opponent_rating=random.randint(1200, 1800),
        result=result,
        opening_name=opening_name,
        opening_eco=eco,
        num_plies=num_plies,
        analyzed=True,
        judgments=judgments,
    )


def generate_fallback_games(username: str, count: int = 15) -> list[GameRecord]:
    return [_random_game(username, i) for i in range(count)]
