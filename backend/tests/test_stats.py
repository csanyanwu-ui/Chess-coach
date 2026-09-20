import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.parser import parse_games, parse_game
from app.stats import compute_profile_stats

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample_games.ndjson")


def load_fixture():
    with open(FIXTURE_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def test_parse_games_returns_all_games():
    raw = load_fixture()
    games = parse_games(raw, "TestPlayer")
    assert len(games) == 5


def test_parse_game_assigns_correct_color_and_result():
    raw = load_fixture()
    games = parse_games(raw, "TestPlayer")
    by_id = {g.game_id: g for g in games}

    assert by_id["abc12345"].player_color == "white"
    assert by_id["abc12345"].result == "win"

    assert by_id["def67890"].player_color == "black"
    assert by_id["def67890"].result == "win"

    assert by_id["ghi11111"].player_color == "white"
    assert by_id["ghi11111"].result == "loss"

    assert by_id["jkl22222"].result == "draw"


def test_parse_game_unknown_player_returns_none():
    raw = load_fixture()
    result = parse_game(raw[0], "SomeoneNotInThisGame")
    assert result is None


def test_judgments_only_include_players_own_moves():
    raw = load_fixture()
    games = parse_games(raw, "TestPlayer")
    by_id = {g.game_id: g for g in games}

    # In ghi11111, TestPlayer is white (odd plies). Judgments in fixture are
    # at plies 6, 12, 14 — all even (black's moves) — so TestPlayer should
    # have zero judgments in this game, and the opponent's mistakes should
    # not be attributed to the player.
    assert all(j.ply % 2 == 1 for j in by_id["ghi11111"].judgments)


def test_compute_profile_stats_basic_shape():
    raw = load_fixture()
    games = parse_games(raw, "TestPlayer")
    stats = compute_profile_stats("TestPlayer", games, data_source="live")

    assert stats.username == "TestPlayer"
    assert stats.games_fetched == 5
    assert stats.games_analyzed == 5
    assert stats.data_source == "live"
    # 2 wins (abc12345, def67890), 2 losses (ghi11111, mno33333), 1 draw (jkl22222)
    assert stats.win_rate == 40.0
    assert stats.loss_rate == 40.0
    assert stats.draw_rate == 20.0


def test_opening_repertoire_groups_correctly():
    raw = load_fixture()
    games = parse_games(raw, "TestPlayer")
    stats = compute_profile_stats("TestPlayer", games, data_source="live")

    italian = next(o for o in stats.opening_repertoire if o.name == "Italian Game")
    assert italian.games == 2
    assert italian.wins == 2
    assert italian.win_rate == 100.0


def test_phase_breakdown_sums_to_total_judgments():
    raw = load_fixture()
    games = parse_games(raw, "TestPlayer")
    stats = compute_profile_stats("TestPlayer", games, data_source="live")

    total_from_phases = sum(p.blunders + p.mistakes + p.inaccuracies for p in stats.phase_breakdown)
    total_judgments = sum(len(g.judgments) for g in games)
    assert total_from_phases == total_judgments


def test_empty_games_list_does_not_crash():
    stats = compute_profile_stats("NoGamesPlayer", [], data_source="fallback")
    assert stats.games_fetched == 0
    assert stats.win_rate == 0.0
    assert stats.best_opening is None
