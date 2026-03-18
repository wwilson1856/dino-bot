"""
OddsAPI Player Props - Efficient fetching with request counting.
Free tier: 500 requests/month, so we're very selective.
"""
import requests
import json
from datetime import datetime
from config import API_KEY

REQUEST_LOG_FILE = "oddsapi_requests.log"

def log_request(endpoint: str, success: bool):
    """Log API request for tracking usage."""
    try:
        with open(REQUEST_LOG_FILE, "a") as f:
            f.write(f"{datetime.now().isoformat()},{endpoint},{success}\n")
    except Exception:
        pass

def get_request_count_today() -> int:
    """Get number of requests made today."""
    try:
        today = datetime.now().date().isoformat()
        count = 0
        with open(REQUEST_LOG_FILE, "r") as f:
            for line in f:
                if line.startswith(today):
                    count += 1
        return count
    except FileNotFoundError:
        return 0

def get_nhl_player_props_oddsapi() -> list:
    """
    Fetch NHL player props from OddsAPI.
    Only call this once per day to conserve requests.
    """
    # Check request budget
    requests_today = get_request_count_today()
    if requests_today >= 10:  # Daily limit to conserve monthly quota
        print(f"OddsAPI: Daily limit reached ({requests_today} requests)")
        return []
    
    props = []
    
    try:
        # First get NHL events (1 request)
        events_url = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/events"
        params = {"apiKey": API_KEY}
        
        r = requests.get(events_url, params=params, timeout=10)
        log_request("nhl_events", r.status_code == 200)
        
        if r.status_code != 200:
            print(f"OddsAPI events failed: {r.status_code}")
            return []
        
        events = r.json()
        print(f"OddsAPI: Found {len(events)} NHL events")
        
        # Get props for first 2 games only (2 more requests)
        for event in events[:2]:
            event_id = event["id"]
            home_team = event["home_team"]
            away_team = event["away_team"]
            
            # Get player props for this event
            props_url = f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/events/{event_id}/odds"
            params = {
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "player_goals,player_assists,player_shots_on_goal",
                "oddsFormat": "american"
            }
            
            r = requests.get(props_url, params=params, timeout=10)
            log_request(f"nhl_props_{event_id}", r.status_code == 200)
            
            if r.status_code == 200:
                event_props = r.json()
                
                # Parse props
                for bookmaker in event_props.get("bookmakers", []):
                    if bookmaker["key"] != "fanduel":
                        continue
                    
                    for market in bookmaker.get("markets", []):
                        market_key = market["key"]
                        prop_type = {
                            "player_goals": "goals",
                            "player_assists": "assists", 
                            "player_shots_on_goal": "shots"
                        }.get(market_key)
                        
                        if not prop_type:
                            continue
                        
                        for outcome in market.get("outcomes", []):
                            if "Over" in outcome["name"]:
                                props.append({
                                    "player": outcome["description"].replace(" Over", ""),
                                    "prop_type": prop_type,
                                    "line": outcome["point"],
                                    "odds": outcome["price"],
                                    "home_team": home_team,
                                    "away_team": away_team,
                                    "event_id": event_id,
                                })
            
            print(f"OddsAPI: Got props for {home_team} vs {away_team}")
    
    except Exception as e:
        print(f"OddsAPI error: {e}")
        log_request("nhl_props_error", False)
    
    print(f"OddsAPI: Total {len(props)} props found, {get_request_count_today()} requests used today")
    return props

def get_cached_props() -> list:
    """Get cached props from file to avoid repeated API calls."""
    try:
        with open("cached_props.json", "r") as f:
            data = json.load(f)
        
        # Check if cache is from today
        cache_date = data.get("date", "")
        if cache_date == datetime.now().date().isoformat():
            return data.get("props", [])
    except FileNotFoundError:
        pass
    
    return []

def cache_props(props: list):
    """Cache props to file."""
    try:
        data = {
            "date": datetime.now().date().isoformat(),
            "props": props,
            "timestamp": datetime.now().isoformat()
        }
        with open("cached_props.json", "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def get_nhl_props_smart() -> list:
    """
    Smart prop fetching - use cache if available, otherwise fetch fresh.
    Only fetches once per day to conserve API requests.
    """
    # Try cache first
    cached = get_cached_props()
    if cached:
        print(f"Using cached props: {len(cached)} props")
        return cached
    
    # Fetch fresh if no cache
    props = get_nhl_player_props_oddsapi()
    if props:
        cache_props(props)
    
    return props
