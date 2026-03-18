"""
NHL Player Props - Simplified version using team averages and positional adjustments.
Full player stat integration requires more ESPN API research.
"""
from edge import american_to_implied, calculate_edge
from models.stats import get_pregame_prob
import math

# Positional scoring rates (goals per game) based on typical NHL production
POSITION_RATES = {
    "C": 0.45,   # Centers - highest scoring
    "LW": 0.35,  # Left wing
    "RW": 0.35,  # Right wing  
    "D": 0.15,   # Defensemen
    "G": 0.01,   # Goalies (rare)
}

# Top players get multipliers (simplified star system)
STAR_PLAYERS = {
    "Connor McDavid": 2.2,
    "Leon Draisaitl": 1.8,
    "David Pastrnak": 1.7,
    "Auston Matthews": 1.9,
    "Nathan MacKinnon": 1.6,
    "Nikita Kucherov": 1.5,
    "Erik Karlsson": 1.4,  # High-scoring D
    "Cale Makar": 1.3,
    # Add more as needed
}

def analyze_nhl_player_prop_simple(player_name: str, team_name: str, prop_type: str, line: float, odds: int, opponent: str = None) -> dict:
    """
    Simplified NHL player prop analysis using team stats + positional rates.
    """
    # Get team offensive strength
    from models.stats import get_pregame_prob
    result = get_pregame_prob("NHL", team_name if team_name else "Team", opponent if opponent else "Opponent")
    
    if not result:
        return {}
    
    home_prob, away_prob, proj_total = result
    
    # Estimate team goals (half of projected total, adjusted for home/away)
    team_goals = proj_total * 0.5
    
    # Base projection by prop type
    if prop_type == "goals":
        # Assume player position based on name (simplified)
        position = _guess_position(player_name)
        base_rate = POSITION_RATES.get(position, 0.3)
        
        # Star player multiplier
        star_mult = STAR_PLAYERS.get(player_name, 1.0)
        
        # Player's share of team goals
        proj = base_rate * star_mult
        
    elif prop_type == "assists":
        # Assists typically 1.5x goals for top players
        position = _guess_position(player_name)
        base_rate = POSITION_RATES.get(position, 0.3) * 1.5
        star_mult = STAR_PLAYERS.get(player_name, 1.0)
        proj = base_rate * star_mult
        
    elif prop_type == "shots":
        # Shots are ~4-5x goals for most players
        position = _guess_position(player_name)
        base_rate = POSITION_RATES.get(position, 0.3) * 4.5
        star_mult = STAR_PLAYERS.get(player_name, 1.0)
        proj = base_rate * star_mult
        
    elif prop_type == "saves":
        # Goalie saves based on opponent shots
        if opponent:
            # Opponent shots per game (rough estimate)
            proj = 28.0  # League average shots against
        else:
            proj = 28.0
    else:
        return {}
    
    # Matchup adjustment (basic)
    if opponent and prop_type in ("goals", "assists", "shots"):
        # Playing weak defense = more production
        proj *= 1.05  # Small boost vs average opponent
    
    # Convert to over probability
    over_prob = _poisson_over_prob(proj, line)
    edge = calculate_edge(over_prob, odds)
    
    return {
        "player": player_name,
        "team": team_name,
        "prop_type": prop_type,
        "line": line,
        "odds": odds,
        "projection": round(proj, 2),
        "over_prob": round(over_prob, 3),
        "edge": round(edge, 3),
        "star_mult": STAR_PLAYERS.get(player_name, 1.0),
    }

def _guess_position(player_name: str) -> str:
    """Guess player position based on name (very simplified)."""
    # This is a hack - in reality we'd get this from roster data
    centers = ["McDavid", "Draisaitl", "Matthews", "MacKinnon", "Barkov", "Point"]
    defensemen = ["Karlsson", "Makar", "Hedman", "Josi", "Fox"]
    
    for center in centers:
        if center.lower() in player_name.lower():
            return "C"
    
    for dman in defensemen:
        if dman.lower() in player_name.lower():
            return "D"
    
    # Default to winger
    return "LW"

def _poisson_over_prob(projection: float, line: float) -> float:
    """Calculate P(X > line) using Poisson distribution."""
    if projection <= 0:
        return 0.0
    
    # P(X > line) = 1 - P(X <= line)
    prob_under = 0.0
    k = 0
    while k <= int(line) and k < 20:  # Cap at 20 to avoid infinite loops
        prob_k = (projection ** k) * math.exp(-projection) / math.factorial(k)
        prob_under += prob_k
        k += 1
    
    return max(0.0, min(1.0, 1 - prob_under))

def get_nhl_player_props_from_action(game: dict) -> list:
    """Extract NHL player props from Action Network game data."""
    props = []
    
    for bookmaker in game.get("bookmakers", []):
        if "fanduel" not in bookmaker.get("key", "").lower():
            continue
        
        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "")
            
            # Map Action Network prop keys to our prop types
            prop_mapping = {
                "player_goals": "goals",
                "player_assists": "assists", 
                "player_shots_on_goal": "shots",
                "goalie_saves": "saves",
            }
            
            if market_key not in prop_mapping:
                continue
            
            prop_type = prop_mapping[market_key]
            
            for outcome in market.get("outcomes", []):
                player_name = outcome.get("description", "").replace(" Over", "").replace(" Under", "")
                line = outcome.get("point")
                odds = outcome.get("price")
                is_over = "Over" in outcome.get("name", "")
                
                if line and odds and is_over:  # Only analyze overs for now
                    props.append({
                        "player": player_name,
                        "prop_type": prop_type,
                        "line": line,
                        "odds": odds,
                        "home_team": game.get("home_team"),
                        "away_team": game.get("away_team"),
                    })
    
    return props
