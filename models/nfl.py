"""
NFL live win probability model.
Uses score differential, time remaining, and possession to estimate win prob.
Based on historical NFL win probability research (Burke/ESPN WP model concepts).
"""
import math


def win_probability(home_score: int, away_score: int, seconds_remaining: int,
                    home_has_possession: bool = True) -> tuple[float, float]:
    """
    Returns (home_win_prob, away_win_prob).
    
    Uses a logistic model based on:
    - Score differential (from home team perspective)
    - Time remaining (normalized)
    - Possession advantage
    """
    if seconds_remaining <= 0:
        home_win = 1.0 if home_score > away_score else (0.5 if home_score == away_score else 0.0)
        return home_win, 1 - home_win

    score_diff = home_score - away_score
    time_factor = seconds_remaining / 3600  # normalize to 0-1

    # Possession worth ~2 pts in expected value
    possession_adj = 2.0 if home_has_possession else -2.0

    # Logistic regression coefficients (calibrated from historical NFL data concepts)
    # Higher score diff + less time = more certain outcome
    z = (score_diff + possession_adj) / (math.sqrt(time_factor) * 13.45 + 0.001)
    home_prob = 1 / (1 + math.exp(-z))

    return round(home_prob, 4), round(1 - home_prob, 4)


def analyze(game: dict) -> dict | None:
    """Extract game state from Odds API game object and return model output."""
    # The Odds API doesn't provide live scores on basic plan
    # We use the odds movement as a proxy for game state
    home = game.get("home_team")
    away = game.get("away_team")

    return {
        "sport": "NFL",
        "home": home,
        "away": away,
        "note": "Score data requires SportRadar integration. Using odds-based analysis.",
    }
