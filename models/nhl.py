"""
NHL live win probability model.
Hockey is low-scoring so each goal is massive, especially late.
"""
import math
from scipy.stats import poisson  # type: ignore


def win_probability(home_score: int, away_score: int, seconds_remaining: int,
                    home_has_possession: bool = False, home_team: str = "", away_team: str = "",
                    game_date: str = "") -> tuple[float, float]:
    """
    Returns (home_win_prob, away_win_prob).
    Uses Poisson distribution for remaining goal scoring.
    Adjusts lambda based on recent form and back-to-back status.
    """
    if seconds_remaining <= 0:
        home_win = 1.0 if home_score > away_score else (0.5 if home_score == away_score else 0.0)
        return home_win, 1 - home_win

    total_seconds = 3600
    time_fraction = seconds_remaining / total_seconds

    # Base expected goals per team
    avg_goals_per_team = 1.5
    
    # Adjust for recent form if team names provided
    if home_team:
        from models.stats import get_recent_form, is_back_to_back
        home_form = get_recent_form("NHL", home_team, 10)
        home_lambda = (home_form.get("avg_scored", 1.5) / 2.8) * avg_goals_per_team * time_fraction
        # Penalty for back-to-back
        if is_back_to_back("NHL", home_team, game_date):
            home_lambda *= 0.92
    else:
        home_lambda = avg_goals_per_team * time_fraction
    
    if away_team:
        from models.stats import get_recent_form, is_back_to_back
        away_form = get_recent_form("NHL", away_team, 10)
        away_lambda = (away_form.get("avg_scored", 1.5) / 2.8) * avg_goals_per_team * time_fraction
        # Penalty for back-to-back
        if is_back_to_back("NHL", away_team, game_date):
            away_lambda *= 0.92
    else:
        away_lambda = avg_goals_per_team * time_fraction

    score_diff = home_score - away_score
    max_goals = 10

    home_win_prob = 0.0
    tie_prob = 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            p = poisson.pmf(h, home_lambda) * poisson.pmf(a, away_lambda)
            final_diff = score_diff + h - a
            if final_diff > 0:
                home_win_prob += p
            elif final_diff == 0:
                tie_prob += p

    # In regulation ties go to OT - split 50/50
    home_win_prob += tie_prob * 0.5

    return round(home_win_prob, 4), round(1 - home_win_prob, 4)


def analyze(game: dict) -> dict | None:
    home = game.get("home_team")
    away = game.get("away_team")
    return {
        "sport": "NHL",
        "home": home,
        "away": away,
        "note": "Score data requires live score integration.",
    }
