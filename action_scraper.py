"""
Action Network public API for live + pre-game odds (free, no auth).
ESPN public API for game state/scores.
Action Network has real-time FanDuel and DraftKings live lines.
"""
import requests
from datetime import datetime, timezone, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"
AN_BASE = "https://api.actionnetwork.com/web/v1"

# Action Network sport slugs
AN_SPORTS = {
    "NBA": "nba",
    "NHL": "nhl",
    "MLB": "mlb",
    "NFL": "nfl",
}

# ESPN sport paths (for game state/scores only)
ESPN_SPORTS = {
    "NBA": ("basketball", "nba"),
    "NHL": ("hockey", "nhl"),
    "MLB": ("baseball", "mlb"),
    "NFL": ("football", "nfl"),
    "WBC": ("baseball", "world-baseball-classic"),
}

# Action Network book IDs
BOOK_IDS = {
    "fanduel": 69,
    "draftkings": 68,
    "pinnacle": 3,
    "consensus": 15,
    "open": 30,       # Opening line - sharpest pre-game reference
    "betmgm": 75,
    "caesars": 13,
    "betrivers": 71,
    "betrivers_ny": 972,
}

# Reverse map: id -> name
BOOK_NAMES = {v: k for k, v in BOOK_IDS.items()}
BOOK_TITLES = {
    69: "FanDuel",
    68: "DraftKings",
    3: "Pinnacle",
    15: "Consensus",
    30: "Open",
    75: "BetMGM",
    13: "Caesars",
    71: "BetRivers",
    972: "BetRivers",
}


def _fetch_an_scoreboard(sport_slug: str, date_str: str) -> list[dict]:
    """Fetch Action Network scoreboard for a sport and date (YYYYMMDD)."""
    url = f"{AN_BASE}/scoreboard/{sport_slug}"
    try:
        resp = requests.get(url, headers=HEADERS, params={"date": date_str}, timeout=10)
        resp.raise_for_status()
        return resp.json().get("games", [])
    except Exception as e:
        print(f"[an] Error fetching {sport_slug} {date_str}: {e}")
        return []


def _fetch_espn_scores(sport_name: str) -> dict:
    """Fetch ESPN scoreboard for live score data. Returns dict keyed by team name pair."""
    category, league = ESPN_SPORTS.get(sport_name, (None, None))
    if not category:
        return {}
    url = f"{ESPN_BASE}/{category}/{league}/scoreboard"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        result = {}
        for event in resp.json().get("events", []):
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
            home_name = home.get("team", {}).get("displayName", "")
            away_name = away.get("team", {}).get("displayName", "")
            key = _team_key(home_name, away_name)
            status = event.get("status", {})
            result[key] = {
                "home_score": int(home.get("score", 0) or 0),
                "away_score": int(away.get("score", 0) or 0),
                "period": status.get("period", 0),
                "clock": status.get("displayClock", "0:00"),
                "state": status.get("type", {}).get("state", "pre"),
                "completed": status.get("type", {}).get("completed", False),
                "top_inning": comp.get("situation", {}).get("isTopHalfInning", True),
            }
        return result
    except Exception:
        return {}


def _build_bookmakers(an_game: dict, home_name: str, away_name: str) -> list[dict]:
    """Convert Action Network odds to our bookmakers format."""
    odds_list = an_game.get("odds", [])
    books = {}

    for o in odds_list:
        book_id = o.get("book_id")
        if book_id not in BOOK_TITLES:
            continue

        otype = o.get("type", "")
        # For live games: prefer 'live' type; for pre-game: use 'game' type
        if otype not in ("game", "live"):
            continue

        book_key = BOOK_NAMES.get(book_id, str(book_id))
        is_live_line = (otype == "live")

        markets = []

        # Moneyline
        ml_away = o.get("ml_away")
        ml_home = o.get("ml_home")
        if ml_away and ml_home:
            markets.append({
                "key": "h2h",
                "outcomes": [
                    {"name": away_name, "price": int(ml_away)},
                    {"name": home_name, "price": int(ml_home)},
                ]
            })

        # Spread
        spread_away = o.get("spread_away")
        spread_away_line = o.get("spread_away_line")
        spread_home_line = o.get("spread_home_line")
        if spread_away is not None and spread_away_line and spread_home_line:
            markets.append({
                "key": "spreads",
                "outcomes": [
                    {"name": away_name, "price": int(spread_away_line), "point": float(spread_away)},
                    {"name": home_name, "price": int(spread_home_line), "point": -float(spread_away)},
                ]
            })

        # Total
        total = o.get("total")
        over_odds = o.get("over")
        under_odds = o.get("under")
        if total and over_odds and under_odds:
            markets.append({
                "key": "totals",
                "outcomes": [
                    {"name": "Over", "price": int(over_odds), "point": float(total)},
                    {"name": "Under", "price": int(under_odds), "point": float(total)},
                ]
            })

        if not markets:
            continue

        # Live lines override game lines for same book
        entry_key = f"{book_key}_live" if is_live_line else book_key
        if is_live_line or book_key not in books:
            books[entry_key] = {
                "key": entry_key,
                "title": BOOK_TITLES[book_id] + (" (Live)" if is_live_line else ""),
                "markets": markets,
                "is_live": is_live_line,
                "_base_key": book_key,
            }

    # Flatten: if we have a live version, use it; otherwise use game version
    result = []
    seen_bases = set()
    # Live lines first
    for k, v in books.items():
        if v.get("is_live"):
            base = v["_base_key"]
            seen_bases.add(base)
            result.append(v)
    # Then pre-game lines for books without live
    for k, v in books.items():
        if not v.get("is_live") and v["_base_key"] not in seen_bases:
            result.append(v)

    return result


def _normalize_an_game(an_game: dict, sport_name: str, espn_scores: dict) -> dict | None:
    """Convert Action Network game to our standard format."""
    teams = an_game.get("teams", [])
    if len(teams) < 2:
        return None

    # Action Network: teams[0] is home, teams[1] is away (based on rotation numbers)
    # Actually need to check - away_team_id vs home_team_id
    home_id = an_game.get("home_team_id")
    away_id = an_game.get("away_team_id")
    home = next((t for t in teams if t.get("id") == home_id), teams[0])
    away = next((t for t in teams if t.get("id") == away_id), teams[1])

    home_name = home.get("full_name", home.get("display_name", "Home"))
    away_name = away.get("full_name", away.get("display_name", "Away"))

    start_time = an_game.get("start_time", "")
    status = an_game.get("status", "scheduled")
    status_display = an_game.get("status_display", "")

    # Map AN status to ESPN-style state
    if status in ("complete", "closed"):
        state = "post"
        completed = True
    elif status == "inprogress":
        state = "in"
        completed = False
    else:
        state = "pre"
        completed = False

    # Get live score data from ESPN
    key = _team_key(home_name, away_name)
    espn = espn_scores.get(key, {})

    home_score = espn.get("home_score", 0)
    away_score = espn.get("away_score", 0)
    period = espn.get("period", 0)
    clock = espn.get("clock", "0:00")
    top_inning = espn.get("top_inning", True)

    # Parse period from AN status_display if ESPN didn't give us data
    if period == 0 and state == "in":
        period = _parse_period(status_display, sport_name)

    bookmakers = _build_bookmakers(an_game, home_name, away_name)

    return {
        "id": str(an_game.get("id", "")),
        "sport_key": sport_name.lower(),
        "home_team": home_name,
        "away_team": away_name,
        "commence_time": start_time,
        "completed": completed,
        "status": state,
        "status_detail": status_display,
        "period": period,
        "clock": clock,
        "top_inning": top_inning,
        "home_score": home_score,
        "away_score": away_score,
        "bookmakers": bookmakers,
    }


def _parse_period(status_display: str, sport: str) -> int:
    """Parse period/quarter/inning from status display string."""
    s = status_display.lower()
    period_map = {
        "1st": 1, "2nd": 2, "3rd": 3, "4th": 4,
        "1st quarter": 1, "2nd quarter": 2, "3rd quarter": 3, "4th quarter": 4,
        "1st period": 1, "2nd period": 2, "3rd period": 3,
        "ot": 4, "overtime": 4,
    }
    for k, v in period_map.items():
        if k in s:
            return v
    # Try to extract number
    import re
    m = re.search(r'(\d+)', s)
    if m:
        return int(m.group(1))
    return 1


def _team_key(home: str, away: str) -> str:
    return f"{_normalize(away)}@{_normalize(home)}"


def _normalize(name: str) -> str:
    return name.strip().split()[-1].lower() if name else ""


def get_games(sport_name: str) -> list[dict]:
    """Fetch today + tomorrow games from Action Network with ESPN score overlay."""
    an_slug = AN_SPORTS.get(sport_name)
    if not an_slug:
        # WBC - fall back to ESPN only
        return _get_espn_only_games(sport_name)

    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).strftime("%Y%m%d")
    today = now.strftime("%Y%m%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")

    # Fetch ESPN scores for live game state
    espn_scores = _fetch_espn_scores(sport_name)

    games = {}
    for date_str in [yesterday, today, tomorrow]:
        an_games = _fetch_an_scoreboard(an_slug, date_str)
        for ag in an_games:
            gid = str(ag.get("id", ""))
            if gid and gid not in games:
                # From yesterday, only keep games still in progress
                if date_str == yesterday and ag.get("status") != "inprogress":
                    continue
                game = _normalize_an_game(ag, sport_name, espn_scores)
                if game:
                    games[gid] = game

    return list(games.values())


def _get_espn_only_games(sport_name: str) -> list[dict]:
    """Fallback: ESPN-only for sports not on Action Network (WBC)."""
    category, league = ESPN_SPORTS.get(sport_name, (None, None))
    if not category:
        return []

    url = f"{ESPN_BASE}/{category}/{league}/scoreboard"
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")

    games = {}
    for params in [{}, {"dates": tomorrow}]:
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            resp.raise_for_status()
            for event in resp.json().get("events", []):
                eid = event.get("id")
                if eid and eid not in games:
                    game = _normalize_espn(event, sport_name)
                    if game:
                        games[eid] = game
        except Exception as e:
            print(f"[espn] Error fetching {sport_name}: {e}")

    return list(games.values())


def _normalize_espn(event: dict, sport_name: str) -> dict | None:
    competitions = event.get("competitions", [])
    if not competitions:
        return None
    comp = competitions[0]
    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        return None

    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
    home_name = home.get("team", {}).get("displayName", "Home")
    away_name = away.get("team", {}).get("displayName", "Away")

    status = event.get("status", {})
    status_type = status.get("type", {})
    state = status_type.get("state", "pre")
    completed = status_type.get("completed", False)

    return {
        "id": str(event.get("id", "")),
        "sport_key": sport_name.lower(),
        "home_team": home_name,
        "away_team": away_name,
        "commence_time": event.get("date", ""),
        "completed": completed,
        "status": state,
        "status_detail": status_type.get("shortDetail", ""),
        "period": status.get("period", 0),
        "clock": status.get("displayClock", "0:00"),
        "top_inning": comp.get("situation", {}).get("isTopHalfInning", True),
        "home_score": int(home.get("score", 0) or 0),
        "away_score": int(away.get("score", 0) or 0),
        "bookmakers": [],
    }


def scrape_all_sports() -> tuple[dict, dict]:
    """Returns (games_by_sport, props_by_sport). Uses Action Network for odds."""
    games_result = {}
    sports = list(AN_SPORTS.keys()) + ["WBC"]

    for sport_name in sports:
        print(f"[an] {sport_name}...", end=" ", flush=True)
        games = get_games(sport_name)
        active = [g for g in games if not g.get("completed")]

        if active:
            games_result[sport_name] = active
            print(f"{len(active)} games")
        else:
            print("none")

    return games_result, {}
