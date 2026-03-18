"""
NHL API integration as backup/supplement to ESPN data.
Only used when ESPN fails or for specific data not available via ESPN.
"""
import requests
from datetime import datetime

NHL_API_BASE = "https://statsapi.web.nhl.com/api/v1"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_nhl_team_stats(team_id: int, season: str = "20252026") -> dict:
    """Get team stats from NHL API. Returns empty dict on failure."""
    try:
        url = f"{NHL_API_BASE}/teams/{team_id}/stats?season={season}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.raise_for_status()
        
        stats = r.json().get("stats", [{}])[0].get("splits", [{}])[0].get("stat", {})
        return {
            "gf_pg": float(stats.get("goalsPerGame", 0)),
            "ga_pg": float(stats.get("goalsAgainstPerGame", 0)),
            "shots_pg": float(stats.get("shotsPerGame", 0)),
            "games": int(stats.get("gamesPlayed", 0))
        }
    except Exception:
        return {}

def get_nhl_game_live_data(game_id: int) -> dict:
    """Get live game data from NHL API."""
    try:
        url = f"{NHL_API_BASE}/game/{game_id}/liveData"
        r = requests.get(url, headers=HEADERS, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

def get_nhl_schedule(date: str = None) -> list:
    """Get NHL schedule. Date format: YYYY-MM-DD"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        url = f"{NHL_API_BASE}/schedule?date={date}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.raise_for_status()
        
        games = []
        for date_entry in r.json().get("dates", []):
            for game in date_entry.get("games", []):
                games.append({
                    "id": game.get("gamePk"),
                    "home": game.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                    "away": game.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                    "status": game.get("status", {}).get("abstractGameState")
                })
        return games
    except Exception:
        return []

# ESPN team name -> NHL API team ID mapping
ESPN_TO_NHL_ID = {
    "Boston Bruins": 6, "Buffalo Sabres": 7, "Calgary Flames": 20, "Chicago Blackhawks": 16,
    "Detroit Red Wings": 17, "Edmonton Oilers": 22, "Carolina Hurricanes": 12, "Los Angeles Kings": 26,
    "Dallas Stars": 25, "Montreal Canadiens": 8, "New Jersey Devils": 1, "New York Islanders": 2,
    "New York Rangers": 3, "Ottawa Senators": 9, "Philadelphia Flyers": 4, "Pittsburgh Penguins": 5,
    "Colorado Avalanche": 21, "San Jose Sharks": 28, "St. Louis Blues": 19, "Tampa Bay Lightning": 14,
    "Toronto Maple Leafs": 10, "Vancouver Canucks": 23, "Washington Capitals": 15, "Anaheim Ducks": 24,
    "Florida Panthers": 13, "Nashville Predators": 18, "Winnipeg Jets": 52, "Columbus Blue Jackets": 29,
    "Minnesota Wild": 30, "Vegas Golden Knights": 54, "Seattle Kraken": 55, "Utah Hockey Club": 59
}
