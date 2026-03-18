#!/usr/bin/env python3
"""
MLB Player Props Analysis
Handles hitting props (total bases, hits, HRs, RBIs) and pitching props (Ks, innings)
"""

from datetime import datetime, timezone


def analyze_mlb_hitting_prop(player: str, team: str, prop_type: str, line: float, odds: int, opponent: str = None) -> dict | None:
    """Analyze MLB hitting props with real player data from Baseball Savant."""
    from mlb_data_api import get_player_stats
    
    # Get real player stats
    player_stats = get_player_stats(player, "batting")
    if not player_stats:
        return None
    
    # Get opponent adjustment
    opponent_factor = _get_opponent_adjustment(team, opponent, "offensive") if opponent else 1.0
    
    # Map prop types to player stats
    stat_mapping = {
        "total_bases": "total_bases_per_game",
        "hits": "avg",  # Will convert to hits per game
        "home_runs": "hr_rate",
        "rbis": "avg",  # Proxy - would need RBI-specific data
        "runs": "obp"   # Proxy - would need runs-specific data
    }
    
    base_stat = stat_mapping.get(prop_type)
    if not base_stat:
        return None
    
    # Get base rate from real stats
    if prop_type == "total_bases":
        base_rate = player_stats.get("total_bases_per_game", 1.4)
    elif prop_type == "hits":
        avg = player_stats.get("avg", 0.250)
        base_rate = avg * 4.2  # ~4.2 AB per game average
    elif prop_type == "home_runs":
        hr_rate = player_stats.get("hr_rate", 0.025)
        base_rate = hr_rate * 4.2  # Convert to per-game
    elif prop_type == "rbis":
        # Use OPS as proxy for RBI production
        ops = player_stats.get("obp", 0.320) + player_stats.get("slg", 0.420)
        base_rate = (ops - 0.700) * 2 + 0.7  # Scale to reasonable RBI range
    elif prop_type == "runs":
        obp = player_stats.get("obp", 0.320)
        base_rate = (obp - 0.300) * 3 + 0.6  # Scale to runs per game
    else:
        base_rate = 1.0
    
    # Apply opponent adjustment
    adjusted_rate = base_rate * opponent_factor
    
    # Calculate probability of going over the line
    if prop_type in ["total_bases", "hits", "rbis", "runs"]:
        # Use Poisson distribution for counting stats
        import math
        prob_over = 1 - sum(math.exp(-adjusted_rate) * (adjusted_rate ** k) / math.factorial(k) 
                           for k in range(int(line) + 1))
    elif prop_type == "home_runs":
        # Home runs are rarer, use different distribution
        import math
        prob_over = 1 - math.exp(-adjusted_rate * (line + 0.5))
    else:
        return None
    
    # Calculate edge
    from edge import calculate_edge
    edge = calculate_edge(prob_over, odds)
    
    if edge > 0.02:  # 2% minimum edge for props
        return {
            "player": player,
            "prop_type": prop_type,
            "line": line,
            "odds": odds,
            "projection": round(adjusted_rate, 2),
            "probability": prob_over,
            "edge": edge,
            "opponent_factor": opponent_factor,
            "base_stats": player_stats
        }
    
    return None


def _get_opponent_adjustment(team: str, opponent: str, stat_type: str = "offensive") -> float:
    """Get opponent strength adjustment based on real team stats."""
    from mlb_data_api import get_team_stats
    
    if not opponent:
        return 1.0
    
    opponent_stats = get_team_stats(opponent, 2024)
    
    if stat_type == "offensive":
        # Adjust based on opponent's pitching strength (inverse relationship)
        runs_allowed = opponent_stats.get("runs_per_game", 4.3)
        league_avg = 4.3
        
        # If opponent allows fewer runs, they're tougher (factor < 1.0)
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


def analyze_mlb_pitching_prop(pitcher: str, team: str, prop_type: str, line: float, odds: int, opponent: str = None) -> dict | None:
    """Analyze MLB pitching props using real pitcher data from Baseball Savant."""
    from mlb_data_api import get_player_stats
    
    # Get real pitcher stats
    pitcher_stats = get_player_stats(pitcher, "pitching")
    if not pitcher_stats:
        return None
    
    # Get opponent adjustment
    opponent_factor = _get_opponent_adjustment(team, opponent, "pitching") if opponent else 1.0
    
    # Get base rate from real stats
    if prop_type == "strikeouts":
        base_rate = pitcher_stats.get("k_per_game", 6.0)
    elif prop_type == "innings":
        # Estimate innings from ERA and other factors
        era = pitcher_stats.get("era", 4.20)
        whip = pitcher_stats.get("whip", 1.30)
        # Better pitchers tend to go deeper
        base_rate = 6.5 - (era - 3.5) * 0.3 - (whip - 1.1) * 2
        base_rate = max(4.0, min(7.5, base_rate))  # Reasonable bounds
    else:
        return None
    
    # Apply opponent adjustment
    adjusted_rate = base_rate * opponent_factor
    
    # Calculate probability
    if prop_type == "strikeouts":
        import math
        prob_over = 1 - sum(math.exp(-adjusted_rate) * (adjusted_rate ** k) / math.factorial(k) 
                           for k in range(int(line) + 1))
    elif prop_type == "innings":
        # Innings pitched - use normal distribution
        import math
        std = 1.2  # Standard deviation for innings
        z = (adjusted_rate - line) / std
        prob_over = 1 / (1 + math.exp(-z * 2))
    else:
        return None
    
    from edge import calculate_edge
    edge = calculate_edge(prob_over, odds)
    
    if edge > 0.025:  # 2.5% minimum edge for pitching props
        return {
            "pitcher": pitcher,
            "prop_type": prop_type,
            "line": line,
            "odds": odds,
            "projection": round(adjusted_rate, 2),
            "probability": prob_over,
            "edge": edge,
            "opponent_factor": opponent_factor,
            "base_stats": pitcher_stats
        }
    
    return None


def get_mlb_props_from_oddsapi() -> list[dict]:
    """Get MLB props from OddsAPI (placeholder - would implement actual API calls)."""
    # This would integrate with OddsAPI like the NHL props system
    # For now, return sample data structure
    return [
        {
            "player": "Aaron Judge",
            "team": "New York Yankees",
            "opponent": "Boston Red Sox",
            "prop_type": "total_bases",
            "line": 1.5,
            "odds": 120,
            "market": "batter_total_bases"
        },
        {
            "player": "Gerrit Cole", 
            "team": "New York Yankees",
            "opponent": "Boston Red Sox",
            "prop_type": "strikeouts",
            "line": 7.5,
            "odds": -110,
            "market": "pitcher_strikeouts"
        }
    ]


if __name__ == "__main__":
    # Test the prop analyzer
    print("🔍 Testing MLB props...")
    
    # Test hitting prop
    hitting_result = analyze_mlb_hitting_prop(
        "Aaron Judge", "New York Yankees", "total_bases", 1.5, 120, "Boston Red Sox"
    )
    
    if hitting_result:
        print(f"✅ {hitting_result['player']} {hitting_result['prop_type']} Over {hitting_result['line']}")
        print(f"   Projection: {hitting_result['projection']} | Edge: {hitting_result['edge']:.1%}")
    
    # Test pitching prop
    pitching_result = analyze_mlb_pitching_prop(
        "Gerrit Cole", "New York Yankees", "strikeouts", 7.5, -110, "Boston Red Sox"
    )
    
    if pitching_result:
        print(f"✅ {pitching_result['pitcher']} {pitching_result['prop_type']} Over {pitching_result['line']}")
        print(f"   Projection: {pitching_result['projection']} | Edge: {pitching_result['edge']:.1%}")
