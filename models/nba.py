"""
NBA live win probability model.
NBA games are high-scoring so score diff matters less early, more late.
"""
import math


def win_probability(home_score: int, away_score: int, seconds_remaining: int,
                    home_has_possession: bool = True) -> tuple[float, float]:
    """
    Returns (home_win_prob, away_win_prob).
    NBA averages ~100 pts/game, so scoring rate is ~2.22 pts/min.
    """
    if seconds_remaining <= 0:
        home_win = 1.0 if home_score > away_score else (0.5 if home_score == away_score else 0.0)
        return home_win, 1 - home_win

    score_diff = home_score - away_score
    time_factor = seconds_remaining / 2880  # 48 min game

    # Possession worth ~1 pt in NBA
    possession_adj = 1.0 if home_has_possession else -1.0

    # NBA scoring std dev scales with time remaining
    std_dev = math.sqrt(time_factor) * 11.0 + 0.001
    z = (score_diff + possession_adj) / std_dev
    home_prob = 1 / (1 + math.exp(-z * 1.7))

    return round(home_prob, 4), round(1 - home_prob, 4)


def analyze(game: dict) -> dict | None:
    home = game.get("home_team")
    away = game.get("away_team")
    return {
        "sport": "NBA",
        "home": home,
        "away": away,
        "note": "Score data requires live score integration.",
    }
