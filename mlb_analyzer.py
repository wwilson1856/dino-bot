#!/usr/bin/env python3
"""
MLB-specific analyzer for team markets and player props
Handles baseball-specific logic, ballpark factors, weather, etc.
"""

from datetime import datetime, timezone
from config import MIN_EDGE, MIN_CONFIDENCE, MAX_JUICE
from edge import calculate_edge, kelly_units
from models.stats import mlb_pregame_prob


def analyze_mlb_team_markets(game: dict) -> list[dict]:
    """Analyze MLB team markets (h2h, totals, spreads) with baseball-specific logic."""
    candidates = []
    
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    game_mode = game.get("_game_mode", "unknown")
    time_label = game.get("_time_label", "")
    
    # Get MLB pregame probabilities
    pregame_result = mlb_pregame_prob(home, away)
    if not pregame_result:
        return candidates
    
    home_prob, away_prob, model_total = pregame_result
    
    # Process FanDuel markets
    fd_markets = game.get("fanduel_markets", {})
    
    for market_key in ["h2h", "totals", "spreads"]:
        fd_market = fd_markets.get(market_key)
        if not fd_market:
            continue
            
        # Extract outcomes and prices
        fd_outcomes = {}
        for outcome in fd_market.get("outcomes", []):
            name = outcome.get("name")
            price = outcome.get("price")
            if name and price:
                fd_outcomes[name] = price
        
        if not fd_outcomes:
            continue
            
        # Analyze each outcome
        for team, fd_price in fd_outcomes.items():
            if abs(fd_price) > abs(MAX_JUICE):
                continue
                
            # Get model probability
            model_prob = _get_mlb_model_prob(game, team, market_key, model_total, home_prob, away_prob)
            if model_prob is None:
                continue
                
            # Calculate edge with MLB-specific adjustments
            edge = calculate_edge(model_prob, fd_price)
            
            # MLB-specific thresholds (more conservative due to variance)
            if market_key == "totals":
                required_edge = 0.025  # 2.5% for totals (weather/ballpark sensitive)
            elif market_key == "h2h":
                required_edge = 0.020  # 2.0% for moneylines
            elif market_key == "spreads":
                required_edge = 0.022  # 2.2% for spreads
            else:
                required_edge = MIN_EDGE
                
            if edge > required_edge:
                confidence = min(95, max(50, int(edge * 300 + model_prob * 60)))
                
                if confidence >= MIN_CONFIDENCE:
                    units = kelly_units(model_prob, fd_price, confidence)
                    
                    if units >= 0.2:  # Minimum unit threshold
                        candidates.append({
                            "sport": "MLB",
                            "home": home,
                            "away": away,
                            "bet": _format_mlb_bet_label(team, market_key, fd_market.get("outcomes", [{}])[0].get("point")),
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


def _get_mlb_model_prob(game: dict, team: str, market_key: str, model_total: float, home_prob: float, away_prob: float) -> float | None:
    """Get MLB model probability with baseball-specific adjustments."""
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    is_home = (team == home)
    
    if market_key == "h2h":
        return home_prob if is_home else away_prob
        
    if market_key == "totals" and model_total is not None:
        # Get actual line from market
        line_point = None
        fd_market = game.get("fanduel_markets", {}).get("totals", {})
        for outcome in fd_market.get("outcomes", []):
            if outcome.get("name") == team:
                line_point = outcome.get("point")
                break
                
        if line_point is None:
            return None
            
        # Apply ballpark factors
        adjusted_total = _apply_ballpark_factors(model_total, home)
        
        # MLB totals calculation with ballpark/weather factors
        import math
        std = adjusted_total * 0.12  # Slightly higher variance than NHL
        z = (adjusted_total - line_point) / (std + 0.001)
        over_prob = 1 / (1 + math.exp(-z * 1.4))  # Slightly less aggressive than NHL
        
        if team == "Over":
            return over_prob
        elif team == "Under":
            return 1 - over_prob
            
    if market_key == "spreads":
        # MLB spread logic (run lines, typically ±1.5)
        line_point = None
        fd_market = game.get("fanduel_markets", {}).get("spreads", {})
        for outcome in fd_market.get("outcomes", []):
            if outcome.get("name") == team:
                line_point = outcome.get("point")
                break
                
        if line_point is None:
            return None
            
        # Adjust team probability based on spread
        base_prob = home_prob if is_home else away_prob
        
        # Simple spread adjustment (can be enhanced with more sophisticated modeling)
        if line_point > 0:  # Getting runs
            return min(0.85, base_prob + 0.15)
        elif line_point < 0:  # Giving runs
            return max(0.15, base_prob - 0.15)
        else:
            return base_prob
    
    return None


def _apply_ballpark_factors(model_total: float, home_team: str) -> float:
    """Apply real ballpark-specific run environment adjustments from Baseball Savant."""
    from mlb_data_api import get_park_factors
    
    # Get real park factors from Baseball Savant data
    park_factors = get_park_factors(2024)
    factor = park_factors.get(home_team, 1.0)  # Default to neutral if team not found
    
    return model_total * factor


def _get_opponent_adjustment(team: str, opponent: str, stat_type: str = "offensive") -> float:
    """Get opponent strength adjustment based on real team stats."""
    from mlb_data_api import get_team_stats
    
    opponent_stats = get_team_stats(opponent, 2024)
    
    if stat_type == "offensive":
        # Adjust based on opponent's pitching strength (inverse relationship)
        # Strong pitching staff = lower offensive numbers expected
        runs_allowed = opponent_stats.get("runs_per_game", 4.3)
        league_avg = 4.3
        
        # If opponent allows fewer runs, they're tougher (factor < 1.0)
        # If opponent allows more runs, they're easier (factor > 1.0)
        adjustment = league_avg / runs_allowed
        return max(0.85, min(1.15, adjustment))  # Cap adjustments at ±15%
        
    elif stat_type == "pitching":
        # Adjust based on opponent's offensive strength
        runs_scored = opponent_stats.get("runs_per_game", 4.3)
        league_avg = 4.3
        
        # Strong offense = more strikeouts/harder for pitcher
        adjustment = runs_scored / league_avg
        return max(0.90, min(1.10, adjustment))  # Smaller adjustment for pitching
    
    return 1.0


def _format_mlb_bet_label(team: str, market_key: str, point) -> str:
    """Format MLB bet label for display."""
    if market_key == "h2h":
        return team
    elif market_key == "totals":
        return f"{team} {point}" if point else team
    elif market_key == "spreads":
        if point:
            sign = "+" if point > 0 else ""
            return f"{team} {sign}{point}"
        return team
    return team


def analyze_mlb_player_props(game: dict) -> list[dict]:
    """Analyze MLB player props with baseball-specific modeling."""
    from mlb_props import get_mlb_props_from_oddsapi, analyze_mlb_hitting_prop, analyze_mlb_pitching_prop
    
    candidates = []
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    
    # Get props for this game (placeholder - would filter by teams)
    props = get_mlb_props_from_oddsapi()
    
    for prop in props:
        if prop["team"] in [home, away]:
            opponent = away if prop["team"] == home else home
            
            # Analyze hitting props
            if prop["prop_type"] in ["total_bases", "hits", "home_runs", "rbis", "runs"]:
                result = analyze_mlb_hitting_prop(
                    prop["player"], prop["team"], prop["prop_type"], 
                    prop["line"], prop["odds"], opponent
                )
                
                if result:
                    candidates.append({
                        "sport": "MLB",
                        "home": home,
                        "away": away,
                        "player": prop["player"],
                        "bet": f"{prop['player']} {prop['prop_type'].replace('_', ' ').title()} Over {prop['line']}",
                        "market": "player_props",
                        "odds": prop["odds"],
                        "edge": result["edge"],
                        "confidence": min(85, max(60, int(result["edge"] * 300))),
                        "units": min(2.0, result["edge"] * 8),  # Conservative sizing
                        "projection": result["projection"],
                        "prop_type": prop["prop_type"]
                    })
            
            # Analyze pitching props
            elif prop["prop_type"] in ["strikeouts", "innings"]:
                result = analyze_mlb_pitching_prop(
                    prop["player"], prop["team"], prop["prop_type"],
                    prop["line"], prop["odds"], opponent
                )
                
                if result:
                    candidates.append({
                        "sport": "MLB",
                        "home": home,
                        "away": away,
                        "player": prop["player"],
                        "bet": f"{prop['player']} {prop['prop_type'].title()} Over {prop['line']}",
                        "market": "player_props", 
                        "odds": prop["odds"],
                        "edge": result["edge"],
                        "confidence": min(85, max(60, int(result["edge"] * 300))),
                        "units": min(2.0, result["edge"] * 8),
                        "projection": result["projection"],
                        "prop_type": prop["prop_type"]
                    })
    
    return candidates


if __name__ == "__main__":
    # Test the analyzer
    from action_scraper import scrape_all_sports
    from analyzer import tag_game_mode
    
    all_games, _ = scrape_all_sports()
    now = datetime.now(timezone.utc)
    
    for sport, games in all_games.items():
        if sport == "MLB":
            for game in games[:2]:  # Test first 2 games
                tag_game_mode(game, sport, now)
                if game.get("_game_mode") not in ("upcoming", "live"):
                    continue
                    
                print(f"\n🔍 {game['away_team']} @ {game['home_team']}")
                results = analyze_mlb_team_markets(game)
                
                if results:
                    for r in results:
                        print(f"  ✅ {r['bet']} {r['odds']:+d} | {r['edge']:.1%} edge | {r['units']:.2f}u")
                else:
                    print("  ❌ No value found")
            break
