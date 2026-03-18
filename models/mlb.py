"""
MLB live win probability model.
Uses run differential, inning, outs, and base state.
Based on run expectancy matrix concepts.
"""
import math

# Run expectancy by (outs, base_state) - simplified
# base_state: 0=empty, 1=1st, 2=2nd, 3=3rd, 4=1st+2nd, 5=1st+3rd, 6=2nd+3rd, 7=loaded
RUN_EXPECTANCY = {
    (0, 0): 0.544, (0, 1): 0.941, (0, 2): 1.170, (0, 3): 1.341,
    (0, 4): 1.556, (0, 5): 1.902, (0, 6): 2.050, (0, 7): 2.417,
    (1, 0): 0.291, (1, 1): 0.562, (1, 2): 0.721, (1, 3): 0.908,
    (1, 4): 1.211, (1, 5): 1.429, (1, 6): 1.556, (1, 7): 1.630,
    (2, 0): 0.112, (2, 1): 0.245, (2, 2): 0.344, (2, 3): 0.387,
    (2, 4): 0.531, (2, 5): 0.622, (2, 6): 0.761, (2, 7): 0.798,
}


def win_probability(home_score: int, away_score: int, inning: int,
                    top_of_inning: bool = False, outs: int = 0,
                    base_state: int = 0) -> tuple[float, float]:
    """
    Returns (home_win_prob, away_win_prob).
    innings_remaining is from home team perspective.
    """
    total_innings = 9
    score_diff = home_score - away_score

    # Innings remaining for home team
    if top_of_inning:
        home_innings_left = total_innings - inning + 1
        away_innings_left = total_innings - inning + 1
    else:
        home_innings_left = total_innings - inning
        away_innings_left = total_innings - inning + 1

    home_innings_left = max(0, home_innings_left)
    away_innings_left = max(0, away_innings_left)

    # Expected runs remaining (avg ~0.5 runs/inning simplified)
    runs_per_inning = 0.5
    expected_home = home_innings_left * runs_per_inning
    expected_away = away_innings_left * runs_per_inning

    # Add run expectancy for current half-inning
    re = RUN_EXPECTANCY.get((outs, base_state), 0.3)
    if not top_of_inning:
        expected_home += re

    # Adjusted score diff
    adj_diff = score_diff + expected_home - expected_away
    total_variance = math.sqrt((home_innings_left + away_innings_left) * 0.8 + 0.001)

    z = adj_diff / total_variance
    home_prob = 1 / (1 + math.exp(-z * 1.5))

    return round(home_prob, 4), round(1 - home_prob, 4)


def analyze(game: dict) -> dict | None:
    home = game.get("home_team")
    away = game.get("away_team")
    return {
        "sport": "MLB",
        "home": home,
        "away": away,
        "note": "Score data requires live score integration.",
    }
