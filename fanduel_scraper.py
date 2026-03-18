"""
FanDuel scraper - intercepts FanDuel's internal API calls to get live odds
and player props. Uses a persistent browser session so 20s refreshes are fast.
"""
import re
import threading
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, Browser, BrowserContext

SPORT_URLS = {
    "NBA": "https://sportsbook.fanduel.com/basketball/nba",
    "NHL": "https://sportsbook.fanduel.com/hockey/nhl",
    "MLB": "https://sportsbook.fanduel.com/baseball/mlb",
    "NFL": "https://sportsbook.fanduel.com/football/nfl",
}

PROP_URLS = {
    "NBA": "https://sportsbook.fanduel.com/basketball/nba/player-props",
    "NHL": "https://sportsbook.fanduel.com/hockey/nhl/player-props",
    "MLB": "https://sportsbook.fanduel.com/baseball/mlb/player-props",
    "NFL": "https://sportsbook.fanduel.com/football/nfl/player-props",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Shared playwright instance - stays alive between refreshes
_pw = None
_browser: Browser = None
_context: BrowserContext = None
_lock = threading.Lock()


def _get_browser():
    global _pw, _browser, _context
    if _browser is None or not _browser.is_connected():
        if _pw is None:
            _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(
            headless=False,  # visible browser bypasses most bot detection
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--start-maximized",
            ]
        )
        _context = _browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        # Hide webdriver flag
        _context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return _context


def _capture_responses(url: str, wait_ms: int = 3000) -> list[dict]:
    """Load a URL and capture all FanDuel API responses."""
    captured = []
    context = _get_browser()
    page = context.new_page()

    def handle_response(response):
        try:
            if "sbapi.fanduel.com" in response.url or "api.fanduel.com" in response.url:
                data = response.json()
                if data:
                    captured.append({"url": response.url, "data": data})
        except Exception:
            pass

    page.on("response", handle_response)
    try:
        # Use domcontentloaded - faster and works better than networkidle on SPAs
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(wait_ms)
    except Exception as e:
        print(f"[scraper] Error loading {url}: {e}")
    finally:
        page.close()

    return captured


def scrape_sport(sport_name: str) -> list[dict]:
    """Scrape game odds for a sport."""
    url = SPORT_URLS.get(sport_name)
    if not url:
        return []
    with _lock:
        responses = _capture_responses(url, wait_ms=5000)
    return parse_fanduel_responses(sport_name, responses, prop_mode=False)


def scrape_props(sport_name: str) -> list[dict]:
    """Scrape player props for a sport."""
    url = PROP_URLS.get(sport_name)
    if not url:
        return []
    with _lock:
        responses = _capture_responses(url, wait_ms=5000)
    if not responses:
        print(f"[scraper] {sport_name} props: no API responses captured (possible bot block)")
        return []
    return parse_fanduel_responses(sport_name, responses, prop_mode=True)


def scrape_all_sports(include_props: bool = True) -> tuple[dict, dict]:
    """
    Scrape all sports. Returns (games_by_sport, props_by_sport).
    """
    games_result = {}
    props_result = {}

    for sport_name in SPORT_URLS:
        print(f"[scraper] {sport_name} odds...", end=" ", flush=True)
        games = scrape_sport(sport_name)
        if games:
            games_result[sport_name] = games
            print(f"{len(games)} games")
        else:
            print("none")

        if include_props:
            print(f"[scraper] {sport_name} props...", end=" ", flush=True)
            props = scrape_props(sport_name)
            if props:
                props_result[sport_name] = props
                print(f"{len(props)} prop markets")
            else:
                print("none")

    return games_result, props_result


def shutdown():
    """Clean up browser on exit."""
    global _browser, _pw
    try:
        if _browser:
            _browser.close()
        if _pw:
            _pw.stop()
    except Exception:
        pass


def parse_fanduel_responses(sport_name: str, responses: list[dict],
                             prop_mode: bool = False) -> list[dict]:
    games = {}

    for resp in responses:
        data = resp["data"]
        attachments = data.get("attachments", data)

        events = attachments.get("events", {})
        markets = attachments.get("markets", {})
        runners = attachments.get("runners", {})

        if isinstance(events, dict):
            events = list(events.values())
        if isinstance(markets, dict):
            markets = list(markets.values())
        if isinstance(runners, dict):
            runners = list(runners.values())

        markets_by_event = {}
        for m in markets:
            eid = str(m.get("eventId", ""))
            markets_by_event.setdefault(eid, []).append(m)

        runners_by_market = {}
        for r in runners:
            mid = str(r.get("marketId", ""))
            runners_by_market.setdefault(mid, []).append(r)

        for event in events:
            eid = str(event.get("eventId", event.get("id", "")))
            if not eid:
                continue

            home = event.get("homeName", event.get("home", ""))
            away = event.get("awayName", event.get("away", ""))
            start_time = event.get("openDate", event.get("startTime", ""))

            if eid not in games:
                games[eid] = {
                    "id": eid,
                    "sport_key": sport_name.lower(),
                    "home_team": home,
                    "away_team": away,
                    "commence_time": start_time,
                    "bookmakers": [{"key": "fanduel", "title": "FanDuel", "markets": []}],
                }

            for market in markets_by_event.get(eid, []):
                mid = str(market.get("marketId", market.get("id", "")))
                market_type = market.get("marketType", "").lower()
                market_name = market.get("marketName", "").lower()

                if prop_mode:
                    market_key = _map_prop_type(market_type, market_name)
                else:
                    market_key = _map_market_type(market_type, market_name)

                if not market_key:
                    continue

                outcomes = []
                for runner in runners_by_market.get(mid, []):
                    american = _extract_american(runner)
                    if american == 0:
                        continue
                    outcomes.append({
                        "name": runner.get("runnerName", runner.get("name", "")),
                        "price": american,
                        "point": runner.get("handicap"),
                        "description": runner.get("runnerName", ""),
                    })

                if outcomes:
                    games[eid]["bookmakers"][0]["markets"].append({
                        "key": market_key,
                        "outcomes": outcomes,
                    })

    return list(games.values())


def _extract_american(runner: dict) -> int:
    odds = runner.get("winRunnerOdds", {})
    # Try American display odds first
    american = odds.get("americanDisplayOdds", {}).get("americanOdds", 0)
    if american:
        return int(american)
    # Fall back to decimal conversion
    decimal = odds.get("trueOdds", {}).get("decimalOdds", {}).get("decimalOdds", 0)
    return _decimal_to_american(decimal)


def _map_market_type(market_type: str, market_name: str = "") -> str | None:
    combined = f"{market_type} {market_name}"
    if any(x in combined for x in ["moneyline", "match_winner", "1x2", "winner", "money line"]):
        return "h2h"
    if any(x in combined for x in ["spread", "handicap", "run_line", "puck_line", "point spread"]):
        return "spreads"
    if any(x in combined for x in ["total", "over_under", "over/under"]):
        return "totals"
    return None


def _map_prop_type(market_type: str, market_name: str = "") -> str | None:
    combined = f"{market_type} {market_name}"
    prop_map = {
        "player_points": ["points", "pts"],
        "player_rebounds": ["rebounds", "reb"],
        "player_assists": ["assists", "ast"],
        "player_threes": ["three", "3-point", "3pt"],
        "player_points_rebounds_assists": ["pts+reb+ast", "pra"],
        "player_steals": ["steals"],
        "player_blocks": ["blocks", "blk"],
        "player_shots_on_goal": ["shots on goal", "shots on net"],
        "player_goals": ["goal scorer", "to score"],
        "pitcher_strikeouts": ["strikeouts", "pitcher k"],
        "batter_hits": ["hits", "batter hits"],
        "batter_home_runs": ["home run", "hr"],
        "player_pass_yds": ["passing yards", "pass yds"],
        "player_rush_yds": ["rushing yards", "rush yds"],
        "player_reception_yds": ["receiving yards", "rec yds"],
        "player_receptions": ["receptions", "catches"],
    }
    for key, keywords in prop_map.items():
        if any(kw in combined for kw in keywords):
            return key
    return None


def _decimal_to_american(decimal: float) -> int:
    if not decimal or decimal <= 1:
        return 0
    if decimal >= 2.0:
        return int((decimal - 1) * 100)
    return int(-100 / (decimal - 1))
