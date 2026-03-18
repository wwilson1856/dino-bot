"""
Logs pick of the day and resolves results from ESPN scores.
"""
import json
import os
from datetime import datetime, timezone
from action_scraper import get_games

LOG_PATH = os.path.join(os.path.dirname(__file__), "picks_log.json")


def _load() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        return json.load(f)


def _save(picks: list):
    with open(LOG_PATH, "w") as f:
        json.dump(picks, f, indent=2)


def _extract_point(pick: dict) -> float | None:
    """Extract point value from pick dict or parse from bet string."""
    if pick.get("point") is not None:
        return pick["point"]
    import re
    m = re.search(r"[-+]?\d+\.?\d*", pick.get("bet", ""))
    return float(m.group()) if m else None


def log_pick(pick: dict):
    picks = _load()
    entry = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sport": pick["sport"],
        "home": pick["home"],
        "away": pick["away"],
        "bet": pick["bet"],
        "market": pick["market"],
        "odds": pick["odds"],
        "units": pick["units"],
        "point": _extract_point(pick),
        "model_prob": pick.get("model_prob"),
        "edge": pick.get("edge"),
        "result": None,
        "profit": None,
    }
    picks.append(entry)
    _save(picks)


SPORT_ESPN_MAP = {
    "NHL": ("hockey", "nhl"),
    "NBA": ("basketball", "nba"),
    "MLB": ("baseball", "mlb"),
    "NFL": ("football", "nfl"),
}


def _get_espn_scores(sport: str, date_str: str) -> dict:
    """Fetch completed scores from ESPN for a given sport and date (YYYY-MM-DD)."""
    import requests
    league_sport, league = SPORT_ESPN_MAP.get(sport, (None, None))
    if not league:
        return {}
    espn_date = date_str.replace("-", "")
    url = f"https://site.api.espn.com/apis/site/v2/sports/{league_sport}/{league}/scoreboard?dates={espn_date}"
    try:
        data = requests.get(url, timeout=10).json()
    except Exception:
        return {}
    scores = {}
    for event in data.get("events", []):
        comp = event["competitions"][0]
        if not comp["status"]["type"]["completed"]:
            continue
        home = next((c for c in comp["competitors"] if c["homeAway"] == "home"), None)
        away = next((c for c in comp["competitors"] if c["homeAway"] == "away"), None)
        if home and away:
            scores[_key(away["team"]["displayName"], home["team"]["displayName"])] = {
                "home_score": int(home["score"]),
                "away_score": int(away["score"]),
                "completed": True,
            }
    return scores


def resolve_picks():
    """Check unresolved picks against ESPN final scores."""
    picks = _load()
    changed = False

    unresolved = [p for p in picks if p["result"] is None]
    if not unresolved:
        return

    # Group by sport to minimize API calls
    sports = set(p["sport"] for p in unresolved)
    scores = {}
    for sport in sports:
        for game in get_games(sport):
            if game.get("completed"):
                scores[_key(game["away_team"], game["home_team"])] = game

    for pick in unresolved:
        game = scores.get(_key(pick["away"], pick["home"]))
        if not game:
            # Fallback to ESPN scores for the pick's date
            espn = _get_espn_scores(pick["sport"], pick["date"])
            game = espn.get(_key(pick["away"], pick["home"]))
        if not game:
            continue

        home_score = game["home_score"]
        away_score = game["away_score"]
        market = pick["market"]
        bet = pick["bet"]
        point = pick.get("point")

        result = _resolve(bet, market, pick["home"], pick["away"], home_score, away_score, point)
        if result:
            pick["result"] = result
            # Calculate profit/loss
            if result == "win":
                # Calculate payout based on odds
                odds = pick["odds"]
                units = pick["units"]
                if odds > 0:
                    pick["profit"] = round(units * (odds / 100), 2)
                else:
                    pick["profit"] = round(units * (100 / abs(odds)), 2)
            elif result == "loss":
                pick["profit"] = -pick["units"]
            else:  # push
                pick["profit"] = 0
            changed = True
            try:
                from discord_alerts import send_result_notification
                send_result_notification(pick)
            except Exception as e:
                print(f"[resolve] Failed to send result notification: {e}")

    if changed:
        _save(picks)


def _resolve(bet: str, market: str, home: str, away: str, home_score: int, away_score: int, point) -> str | None:
    if market == "h2h":
        if home in bet:
            return "win" if home_score > away_score else "loss"
        else:
            return "win" if away_score > home_score else "loss"

    if market == "totals" and point is not None:
        total = home_score + away_score
        if "over" in bet.lower():
            return "win" if total > point else ("push" if total == point else "loss")
        else:
            return "win" if total < point else ("push" if total == point else "loss")

    if market == "spreads" and point is not None:
        # bet is on the team with the spread applied
        if home in bet:
            margin = home_score - away_score
        else:
            margin = away_score - home_score
        covered = margin + point
        if covered > 0:
            return "win"
        elif covered < 0:
            return "loss"
        else:
            return "push"

    return None


def streak() -> int:
    """Return current consecutive win streak (positive) or 0."""
    picks = [p for p in _load() if p["result"] in ("win", "loss")]
    count = 0
    for p in reversed(picks):
        if p["result"] == "win":
            count += 1
        else:
            break
    return count


def loss_streak() -> int:
    """Return current consecutive loss streak."""
    picks = [p for p in _load() if p["result"] in ("win", "loss")]
    count = 0
    for p in reversed(picks):
        if p["result"] == "loss":
            count += 1
        else:
            break
    return count


def total_profit() -> float:
    """Return total units profit/loss."""
    picks = [p for p in _load() if p.get("profit") is not None]
    return round(sum(p["profit"] for p in picks), 2)


def record() -> dict:
    """Return overall record and profit."""
    picks = [p for p in _load() if p["result"] in ("win", "loss", "push")]
    wins = sum(1 for p in picks if p["result"] == "win")
    losses = sum(1 for p in picks if p["result"] == "loss")
    pushes = sum(1 for p in picks if p["result"] == "push")
    profit = total_profit()
    
    return {
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "record": f"{wins}-{losses}-{pushes}" if pushes else f"{wins}-{losses}",
        "profit": profit,
    }


def _key(away: str, home: str) -> str:
    def norm(n): return n.strip().split()[-1].lower()
    return f"{norm(away)}@{norm(home)}"
