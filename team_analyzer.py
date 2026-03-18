"""
Team Markets Only Analyzer - Separated from player props for cleaner analysis.
Focuses on moneylines, totals, and spreads without player prop interference.
"""
from datetime import datetime, timezone, timedelta
from edge import american_to_implied, calculate_edge, expected_value, kelly_units
from config import MIN_EDGE, GAME_DURATION_HOURS, MAX_JUICE, MIN_CONFIDENCE
from models import nhl, nba, mlb, nfl as nfl_model
from models.stats import get_pregame_prob
from calibration import get_model_weight, get_edge_multiplier

def analyze_team_markets_only(sport: str, game: dict) -> list[dict]:
    """
    Analyze ONLY team markets (h2h, totals, spreads) - NO player props.
    """
    home = game.get("home_team", "Home")
    away = game.get("away_team", "Away")
    bookmakers = game.get("bookmakers", [])
    game_mode = game.get("_game_mode", "upcoming")
    commence_time = game.get("_commence_time")

    if not bookmakers:
        return []

    if game_mode in ("finished", "future"):
        return []

    candidates = []

    # Find books by key - live lines have _live suffix
    def _find_book(keys):
        for k in keys:
            b = next((b for b in bookmakers if b.get("key", "") == k), None)
            if b:
                return b
        return None

    fd_live = _find_book(["fanduel_live"])
    fd_pregame = _find_book(["fanduel"])
    dk_live = _find_book(["draftkings_live"])
    dk_pregame = _find_book(["draftkings"])
    pinnacle = _find_book(["pinnacle_live", "pinnacle"])
    open_line = _find_book(["open"])
    consensus = _find_book(["consensus_live", "consensus"])

    # For betting: prefer FanDuel live > FanDuel pre-game > DK live > DK pre-game
    fanduel = fd_live or fd_pregame or dk_live or dk_pregame or (bookmakers[0] if bookmakers else None)

    if game_mode == "live":
        sharp = dk_live or consensus or fd_live or (bookmakers[0] if bookmakers else None)
    else:
        sharp = open_line or pinnacle or consensus or dk_pregame or fanduel

    if not sharp or not fanduel:
        return []

    time_label = ""
    if game_mode in ("upcoming", "tomorrow") and commence_time:
        hours_until = (commence_time - datetime.now(timezone.utc)).total_seconds() / 3600
        time_label = _format_time_until(hours_until)

    # Fetch pre-game stat model result once per game (cached)
    pregame_result = None
    if game_mode in ("upcoming", "tomorrow"):
        pregame_result = get_pregame_prob(sport, home, away)

    for fd_market in fanduel.get("markets", []):
        market_key = fd_market["key"]
        
        # ONLY analyze team markets
        if market_key not in ["h2h", "totals", "spreads"]:
            continue
            
        fd_outcomes = {o["name"]: o["price"] for o in fd_market.get("outcomes", [])}

        # Get sharp reference probability (vig-removed from sharp book)
        pin_fair = {}
        if sharp and sharp != fanduel:
            pin_market = next((m for m in sharp.get("markets", []) if m["key"] == market_key), None)
            if pin_market:
                pin_implied = {o["name"]: american_to_implied(o["price"]) for o in pin_market["outcomes"]}
                total = sum(pin_implied.values())
                if total > 0:
                    pin_fair = {name: prob / total for name, prob in pin_implied.items()}

        # Fall back to vig removal on betting book
        if not pin_fair:
            fd_implied = {name: american_to_implied(price) for name, price in fd_outcomes.items()}
            total = sum(fd_implied.values())
            if total > 0:
                pin_fair = {name: prob / total for name, prob in fd_implied.items()}

        # Skip if we don't have clean probabilities
        if not pin_fair:
            continue

        # Analyze each outcome in this market
        for team, fd_price in fd_outcomes.items():
            if abs(fd_price) > abs(MAX_JUICE):
                continue

            # Get model probability for this outcome
            model_prob = _get_model_prob(sport, game, team, market_key)
            if model_prob is None and pregame_result:
                # Get the actual line point for totals
                line_point = None
                if market_key == "totals":
                    for outcome in fd_market.get("outcomes", []):
                        if outcome.get("name") == team:
                            line_point = outcome.get("point")
                            break
                
                model_prob = _get_pregame_model_prob(sport, game, team, market_key, line_point)

            if model_prob is None:
                continue

            # Blend model with sharp line probability
            model_weight = get_model_weight(market_key)
            line_prob = pin_fair.get(team, 0.5)
            blended_prob = model_prob * model_weight + line_prob * (1 - model_weight)

            # Calculate edge with RELAXED thresholds for team markets
            edge = calculate_edge(blended_prob, fd_price)
            edge_multiplier = get_edge_multiplier(market_key)
            
            # RELAXED THRESHOLDS FOR TEAM MARKETS
            if market_key == "totals":
                required_edge = 0.015  # 1.5% for totals
            elif market_key == "h2h":
                required_edge = 0.018  # 1.8% for moneylines  
            elif market_key == "spreads":
                required_edge = 0.020  # 2.0% for spreads
            else:
                required_edge = 0.025  # Default
            
            if edge > required_edge * edge_multiplier:
                confidence = min(95, max(50, int(edge * 400 + blended_prob * 50)))
                
                # Relaxed confidence requirement for team markets
                if confidence < 55:
                    continue
                
                # Skip heavy juice without substantial edge
                if abs(fd_price) > 140 and edge < 0.03:
                    continue
                
                units = kelly_units(blended_prob, fd_price, confidence)
                
                # Skip tiny unit sizes
                if units < 0.15:
                    continue

                candidates.append({
                    "sport": sport,
                    "home": home,
                    "away": away,
                    "bet": _format_bet_label(team, market_key, fd_market.get("outcomes", [{}])[0].get("point")),
                    "market": market_key,
                    "odds": fd_price,
                    "edge": edge,
                    "confidence": confidence,
                    "units": units,
                    "game_mode": game_mode,
                    "time_label": time_label,
                    "point": fd_market.get("outcomes", [{}])[0].get("point"),
                    "commence_time": game.get("commence_time", ""),
                })

    return candidates

def _get_model_prob(sport: str, game: dict, team: str, market_key: str) -> float | None:
    """Live in-game win probability using score + time remaining."""
    if game.get("_game_mode") != "live":
        return None
    
    # Live model logic would go here
    return None

def _get_pregame_model_prob(sport: str, game: dict, team: str, market_key: str, proj_total: float | None) -> float | None:
    """Pre-game stat-based probability for a specific outcome."""
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    is_home = (team == home)

    result = get_pregame_prob(sport, home, away)
    if result is None:
        return None

    home_prob, away_prob, model_total = result

    if market_key == "h2h":
        return home_prob if is_home else away_prob

    if market_key == "totals" and model_total is not None:
        # team is "Over" or "Under", proj_total is the LINE point
        import math
        std = model_total * 0.11
        line = proj_total if proj_total is not None else 6.5  # Default line if missing
        z = (model_total - line) / (std + 0.001)
        over_prob = 1 / (1 + math.exp(-z * 1.5))
        if team == "Over":
            return over_prob
        elif team == "Under":
            return 1 - over_prob

    return None

def _format_bet_label(team: str, market_key: str, point) -> str:
    """Format bet label for display."""
    if market_key == "h2h":
        return team
    elif market_key == "totals":
        return f"{team} {point}" if point else team
    elif market_key == "spreads":
        if point:
            sign = "+" if point > 0 else ""
            return f"{team} {sign}{point}"
        return team
    return f"{team} {market_key}"

def _format_time_until(hours: float) -> str:
    """Format time until game starts."""
    if hours < 1:
        return f"{int(hours * 60)}m"
    elif hours < 24:
        return f"{hours:.1f}h"
    else:
        return f"{int(hours / 24)}d"
