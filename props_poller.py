"""
Player props use a separate Odds API endpoint per event.
Each event costs 1 API call, so we batch carefully.
"""
import requests
from config import API_KEY, BASE_URL, PROP_MARKETS, BOOKMAKER_FILTER
import poller


def get_event_ids(sport_key: str) -> list[dict]:
    """Get all event IDs for a sport (cheap call, returns metadata only)."""
    url = f"{BASE_URL}/sports/{sport_key}/events"
    params = {"apiKey": API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[props] Error fetching events for {sport_key}: {e}")
        return []


def get_props_for_event(sport_key: str, event_id: str, markets: list[str]) -> dict:
    """Fetch player props for a single event. Costs 1 API call."""
    url = f"{BASE_URL}/sports/{sport_key}/events/{event_id}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": ",".join(markets),
        "oddsFormat": "american",
        "bookmakers": BOOKMAKER_FILTER,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        poller.last_remaining = resp.headers.get("x-requests-remaining", poller.last_remaining)
        return resp.json()
    except requests.RequestException as e:
        print(f"[props] Error fetching props for event {event_id}: {e}")
        return {}


def get_all_props(sport_name: str, sport_key: str, live_game_ids: list[str]) -> list[dict]:
    """
    Fetch props only for currently active games to save API calls.
    Returns list of prop recommendations.
    """
    markets = PROP_MARKETS.get(sport_name, [])
    if not markets:
        return []

    results = []
    for event_id in live_game_ids:
        data = get_props_for_event(sport_key, event_id, markets)
        if data:
            data["_sport_name"] = sport_name
            results.append(data)

    return results
