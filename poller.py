import requests
import time
from datetime import datetime, timezone, timedelta
from config import API_KEY, BASE_URL, SPORTS, MARKETS, UPCOMING_DAYS_AHEAD, GAME_DURATION_HOURS, BOOKMAKER_FILTER, SHARP_BOOK

last_remaining = "unknown"


def _fetch(sport_key: str, extra_params: dict = {}) -> list:
    global last_remaining
    url = f"{BASE_URL}/sports/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": ",".join(MARKETS),
        "oddsFormat": "american",
        # Fetch both FanDuel and Pinnacle in one call
        "bookmakers": f"{BOOKMAKER_FILTER},{SHARP_BOOK}",
        **extra_params,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 429:
            print(f"[poller] Rate limited on {sport_key}, waiting 10s...")
            time.sleep(10)
            return []
        resp.raise_for_status()
        last_remaining = resp.headers.get("x-requests-remaining", last_remaining)
        return resp.json()
    except requests.RequestException as e:
        print(f"[poller] Error fetching {sport_key}: {e}")
        return []


def get_live_odds(sport_key: str, sport_name: str) -> list:
    """Fetch currently in-progress games using sport-specific duration cutoff."""
    all_games = _fetch(sport_key)
    now = datetime.now(timezone.utc)
    max_hours = GAME_DURATION_HOURS.get(sport_name, 3.5)
    live = []
    for g in all_games:
        # Skip if API explicitly marks it completed
        if g.get("completed", False):
            continue

        ct = g.get("commence_time", "")
        try:
            start = datetime.fromisoformat(ct.replace("Z", "+00:00"))
            game_age_hours = (now - start).total_seconds() / 3600
            if 0 < game_age_hours < max_hours:
                # Skip if bookmakers have pulled lines (game likely over)
                active_books = [b for b in g.get("bookmakers", []) if b.get("markets")]
                if len(active_books) < 2:
                    continue
                g["_game_mode"] = "live"
                live.append(g)
        except Exception:
            pass
    return live


def get_upcoming_odds(sport_key: str) -> list:
    """Fetch upcoming games within the configured lookahead window."""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=UPCOMING_DAYS_AHEAD)
    all_games = _fetch(sport_key)
    upcoming = []
    for g in all_games:
        ct = g.get("commence_time", "")
        try:
            start = datetime.fromisoformat(ct.replace("Z", "+00:00"))
            if now < start <= cutoff:
                g["_game_mode"] = "upcoming"
                g["_commence_time"] = start
                upcoming.append(g)
        except Exception:
            pass
    return upcoming


def get_all_games(mode: str = "both") -> dict:
    result = {}
    for sport_name, sport_key in SPORTS.items():
        games = []
        if mode in ("live", "both"):
            games += get_live_odds(sport_key, sport_name)
        if mode in ("upcoming", "both"):
            games += get_upcoming_odds(sport_key)
        if games:
            result[sport_name] = games
    return result
