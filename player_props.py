"""
Player prop analyzer for baseball
Fetches and analyzes batter total bases props
"""
import requests
from config import API_KEY

def get_player_props(sport="baseball_mlb", market="batter_total_bases"):
    """
    Fetch player props for a given sport and market
    Returns list of games with player prop odds
    """
    # First get list of events
    events_url = f"https://api.the-odds-api.com/v4/sports/{sport}/events"
    params = {
        "apiKey": API_KEY,
    }
    
    response = requests.get(events_url, params=params, timeout=10)
    if response.status_code != 200:
        print(f"Error fetching events: {response.status_code}")
        return []
    
    events = response.json()
    all_props = []
    
    # Fetch props for each event
    for event in events[:5]:  # Limit to first 5 games to save API calls
        event_id = event['id']
        props_url = f"https://api.the-odds-api.com/v4/sports/{sport}/events/{event_id}/odds"
        params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": market,
            "oddsFormat": "american"
        }
        
        response = requests.get(props_url, params=params, timeout=10)
        if response.status_code == 200:
            prop_data = response.json()
            if prop_data.get('bookmakers'):
                all_props.append(prop_data)
    
    return all_props


def analyze_total_bases_prop(player_name, line, odds):
    """
    Analyze a total bases prop
    For now, returns basic info - can be enhanced with player stats
    """
    # Convert odds to implied probability
    if odds > 0:
        implied_prob = 100 / (odds + 100)
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)
    
    return {
        "player": player_name,
        "line": line,
        "odds": odds,
        "implied_prob": implied_prob * 100,
        "recommendation": "PASS"  # Default - needs stat analysis
    }


def find_player_prop(player_name, market="batter_total_bases", line=None):
    """
    Find a specific player's prop
    """
    props = get_player_props(market=market)
    
    for game in props:
        home = game['home_team']
        away = game['away_team']
        
        for bookmaker in game.get('bookmakers', []):
            for mkt in bookmaker.get('markets', []):
                if mkt['key'] == market:
                    for outcome in mkt['outcomes']:
                        desc = outcome.get('description', '')
                        if player_name.lower() in desc.lower() and outcome['name'] == 'Over':
                            prop_line = outcome.get('point')
                            prop_odds = outcome['price']
                            
                            # If line specified, match it
                            if line is not None and prop_line != line:
                                continue
                            
                            analysis = analyze_total_bases_prop(
                                desc,
                                prop_line,
                                prop_odds
                            )
                            
                            analysis['game'] = f"{away} @ {home}"
                            analysis['bookmaker'] = bookmaker['title']
                            
                            return analysis
    
    return None


if __name__ == "__main__":
    # Test with Acuña
    result = find_player_prop("Acuna", line=2.5)
    if result:
        print(f"\n{result['player']}")
        print(f"Game: {result['game']}")
        print(f"Line: Over {result['line']} total bases")
        print(f"Odds: {result['odds']:+d}")
        print(f"Implied prob: {result['implied_prob']:.1f}%")
        print(f"Book: {result['bookmaker']}")
    else:
        print("Prop not found")
