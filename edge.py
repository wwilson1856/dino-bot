"""
Edge calculator: converts American odds to implied probability,
compares against our model probability, and returns edge.
"""


def american_to_implied(american_odds: int) -> float:
    """Convert American odds to implied probability (0-1)."""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def calculate_edge(model_prob: float, american_odds: int) -> float:
    """
    Edge = model probability - implied probability from the line.
    Positive edge means the bet has value.
    """
    implied = american_to_implied(american_odds)
    return model_prob - implied


def expected_value(model_prob: float, american_odds: int, bet_amount: float = 25) -> float:
    """Calculate expected value of a bet at $25 unit size."""
    if american_odds > 0:
        profit = (american_odds / 100) * bet_amount
    else:
        profit = (100 / abs(american_odds)) * bet_amount

    ev = (model_prob * profit) - ((1 - model_prob) * bet_amount)
    return round(ev, 2)


def kelly_units(model_prob: float, american_odds: int, confidence: int = 50, fraction: float = 1.0, max_units: float = 3.0) -> float:
    """
    Kelly Criterion scaled by confidence score - MORE CONSERVATIVE.
    confidence 50-95 scales the fraction from 0.3x to 1.0x full Kelly.
    max_units=3 (was 15) for better bankroll management.

    Kelly formula: f = (b*p - q) / b
      b = decimal odds - 1 (profit per unit risked)
      p = model win probability
      q = 1 - p
    """
    if american_odds > 0:
        b = american_odds / 100
    else:
        b = 100 / abs(american_odds)

    p = model_prob
    q = 1 - p
    kelly = (b * p - q) / b

    if kelly <= 0:
        return 0.0

    # More conservative scaling: 50% conf = 0.3x Kelly, 95%+ conf = 1.0x Kelly
    conf_scale = 0.3 + 0.7 * ((confidence - 50) / 45)
    conf_scale = max(0.3, min(1.0, conf_scale))

    units = kelly * fraction * conf_scale
    return round(min(units, max_units), 2)
    """
    Pull the best available odds for a market from bookmakers.
    Returns dict with home/away odds or None if not found.
    """
    bookmakers = game.get("bookmakers", [])
    if not bookmakers:
        return None

    # Try preferred bookmaker first, fall back to first available
    target = next((b for b in bookmakers if b["key"] == bookmaker_pref), bookmakers[0])

    for market in target.get("markets", []):
        if market["key"] == market_key:
            outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
            return outcomes

    return None
