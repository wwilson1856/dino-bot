"""
Analyzes games and generates bet recommendations.
- Pre-game: uses real team stats (off/def ratings, Pythagorean expectation)
- Live: uses in-game win probability models (score + time remaining)
Compares model probability against book lines to find edge.
"""
from datetime import datetime, timezone, timedelta
from edge import american_to_implied, calculate_edge, expected_value, kelly_units
from config import MIN_EDGE, GAME_DURATION_HOURS, MAX_JUICE, MIN_CONFIDENCE
from models import nhl, nba, mlb, nfl as nfl_model
from models.stats import get_pregame_prob
from calibration import get_model_weight, get_edge_multiplier


def tag_game_mode(game: dict, sport: str, now: datetime) -> None:
    """Tag a game dict with _game_mode and _commence_time in place."""
    # Exclude MLB games before opening day (2026-03-28)
    if sport == "MLB":
        mlb_opening_day = datetime(2026, 3, 28, tzinfo=timezone.utc)
        if now < mlb_opening_day:
            game["_game_mode"] = "excluded"
            return
    
    # Use ESPN status if available
    espn_status = game.get("status", "")
    if espn_status == "post" or game.get("completed"):
        game["_game_mode"] = "finished"
        return
    if espn_status == "in":
        game["_game_mode"] = "live"
        return

    ct = game.get("commence_time", "")
    try:
        start = datetime.fromisoformat(ct.replace("Z", "+00:00"))
        game["_commence_time"] = start
        age_hours = (now - start).total_seconds() / 3600
        max_hours = GAME_DURATION_HOURS.get(sport, 3.5)
        if 0 < age_hours < max_hours:
            game["_game_mode"] = "live"
        elif start > now:
            hours_until = (start - now).total_seconds() / 3600
            # Compare calendar dates in US Eastern time (UTC-5)
            eastern_offset = timedelta(hours=-5)
            local_now = (now + eastern_offset).date()
            local_start = (start + eastern_offset).date()
            days_ahead = (local_start - local_now).days
            if days_ahead >= 2:
                game["_game_mode"] = "future"   # too far out, skip
            elif days_ahead == 1:
                game["_game_mode"] = "tomorrow"
            else:
                game["_game_mode"] = "upcoming"
        else:
            game["_game_mode"] = "finished"
    except Exception:
        game["_game_mode"] = "upcoming"


def _get_pregame_model_prob(sport: str, game: dict, team: str, market_key: str,
                            proj_total: float | None) -> float | None:
    """
    Pre-game stat-based probability for a specific outcome.
    Returns probability or None if stats unavailable.
    """
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    is_home = (team == home)

    result = get_pregame_prob(sport, home, away)
    if result is None:
        return None

    home_prob, away_prob, model_total = result

    if market_key == "h2h":
        return home_prob if is_home else away_prob

    if market_key == "totals" and model_total is not None:
        # team is "Over" or "Under"
        # Use normal distribution around projected total to get over/under prob
        import math
        # Std dev of game totals is roughly 10-12% of the total
        std = model_total * 0.11
        line = proj_total if proj_total is not None else model_total
        # P(actual > line) using logistic approximation
        z = (model_total - line) / (std + 0.001)
        over_prob = 1 / (1 + math.exp(-z * 1.5))
        if team == "Over":
            return over_prob
        elif team == "Under":
            return 1 - over_prob

    return None


def _get_model_prob(sport: str, game: dict, team: str, market_key: str) -> float | None:
    """
    Live in-game win probability using score + time remaining.
    Returns model probability or None to fall back to line-based fair prob.
    """
    if game.get("_game_mode") != "live":
        return None

    home = game.get("home_team", "")
    away = game.get("away_team", "")
    home_score = int(game.get("home_score") or 0)
    away_score = int(game.get("away_score") or 0)
    clock = game.get("clock", {})
    period = int(game.get("period") or 0)

    # Only use live model for moneyline
    if market_key != "h2h":
        return None

    is_home = (team == home)

    try:
        if sport == "NHL" and period > 0:
            period_secs = _clock_to_seconds(clock, period, total_periods=3, period_length=1200)
            game_date = game.get("commence_time", "")
            home_prob, away_prob = nhl.win_probability(home_score, away_score, period_secs, 
                                                       home_team=home, away_team=away, game_date=game_date)
            return home_prob if is_home else away_prob

        elif sport == "NBA" and period > 0:
            period_secs = _clock_to_seconds(clock, period, total_periods=4, period_length=720)
            home_prob, away_prob = nba.win_probability(home_score, away_score, period_secs)
            return home_prob if is_home else away_prob

        elif sport == "MLB" and period > 0:
            top = game.get("top_inning", True)
            home_prob, away_prob = mlb.win_probability(home_score, away_score, period, not top)
            return home_prob if is_home else away_prob

    except Exception:
        pass

    return None


def _clock_to_seconds(clock: dict, period: int, total_periods: int, period_length: int) -> int:
    """Convert ESPN clock data to total seconds remaining in game."""
    if isinstance(clock, dict):
        display = clock.get("displayValue", "0:00")
    else:
        display = str(clock or "0:00")

    try:
        parts = display.split(":")
        mins = int(parts[0])
        secs = int(parts[1]) if len(parts) > 1 else 0
        period_remaining = mins * 60 + secs
    except Exception:
        period_remaining = 0

    periods_left = max(0, total_periods - period)
    return period_remaining + (periods_left * period_length)


def analyze_game(sport: str, game: dict) -> list[dict]:
    """
    Analyze games for TEAM MARKETS ONLY (h2h, totals, spreads).
    Player props are now handled separately.
    """
    from team_analyzer import analyze_team_markets_only
    
    candidates = []
    
    # Analyze team markets only
    candidates.extend(analyze_team_markets_only(sport, game))
    
    # Add Kalshi markets
    candidates.extend(_analyze_kalshi_markets(sport, game))
    
    return candidates

def _analyze_nhl_player_props(game: dict) -> list[dict]:
    """Analyze NHL player props for a game using OddsAPI data."""
    from nhl_props import analyze_nhl_player_prop_simple
    from oddsapi_props import get_nhl_props_smart
    from config import MIN_EDGE
    
    candidates = []
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    
    # Get props from OddsAPI (cached, only fetches once per day)
    all_props = get_nhl_props_smart()
    
    # Filter props for this specific game
    game_props = []
    for prop in all_props:
        # Normalize team names (remove accents, etc.)
        prop_home = prop["home_team"].replace("é", "e").replace("ö", "o")
        prop_away = prop["away_team"].replace("é", "e").replace("ö", "o")
        game_home = home.replace("é", "e").replace("ö", "o")
        game_away = away.replace("é", "e").replace("ö", "o")
        
        if (prop_home == game_home and prop_away == game_away) or \
           (prop_home == game_away and prop_away == game_home):
            game_props.append(prop)
    
    if not game_props:
        return []
    
    print(f"Analyzing {len(game_props)} props for {away} @ {home}")
    
    for prop in game_props:
        player = prop["player"]
        prop_type = prop["prop_type"]
        line = prop["line"]
        odds = prop["odds"]
        
        # Determine which team the player is on (try both)
        best_analysis = None
        for team, opponent in [(home, away), (away, home)]:
            try:
                analysis = analyze_nhl_player_prop_simple(player, team, prop_type, line, odds, opponent)
                if analysis and analysis.get("edge", 0) > (best_analysis.get("edge", 0) if best_analysis else -1):
                    best_analysis = analysis
                    best_analysis["team_used"] = team
            except Exception as e:
                print(f"Error analyzing {player}: {e}")
                continue
        
        if best_analysis and best_analysis.get("edge", 0) > MIN_EDGE:
            # Convert to standard recommendation format
            confidence = min(95, max(50, int(best_analysis["edge"] * 300 + 60)))
            units = min(1.5, best_analysis["edge"] * 6)  # Conservative sizing for props
            
            candidates.append({
                "sport": "NHL",
                "home": home,
                "away": away,
                "bet": f"{player} {prop_type.title()} Over {line}",
                "market": f"player_{prop_type}",
                "odds": odds,
                "edge": best_analysis["edge"],
                "confidence": confidence,
                "units": round(units, 2),
                "game_mode": game.get("_game_mode", "upcoming"),
                "time_label": "",
                "point": line,
                "commence_time": game.get("commence_time", ""),
                "player": player,
                "prop_type": prop_type,
                "projection": best_analysis["projection"],
            })
    
    return candidates

def _format_bet_label(team: str, market_key: str, point) -> str:
    if market_key == "h2h":
        return f"{team} ML"
    if market_key == "spreads":
        sign = "+" if point and point > 0 else ""
        line = f" {sign}{point}" if point is not None else ""
        return f"{team}{line} Spread"
    if market_key == "totals":
        line = f" {point}" if point is not None else ""
        return f"{team}{line}"  # e.g. "Over 8.5" or "Under 225.5"
    return f"{team} {market_key}"


def _format_time_until(hours: float) -> str:
    if hours < 1:
        return f"{int(hours * 60)}m"
    if hours < 24:
        return f"{hours:.1f}h"
    return f"{hours / 24:.1f}d"


def find_best_book_for(bookmakers: list, market_key: str, team: str, target_price: int) -> str:
    """Find which bookmaker is offering the best price."""
    for book in bookmakers:
        for market in book.get("markets", []):
            if market["key"] != market_key:
                continue
            for outcome in market.get("outcomes", []):
                if outcome["name"] == team and outcome["price"] == target_price:
                    return book.get("title", book.get("key", "?"))
    return "?"


def find_best_odds_across_books(bookmakers: list) -> dict:
    best = {}
    for book in bookmakers:
        for market in book.get("markets", []):
            mkey = market["key"]
            if mkey not in best:
                best[mkey] = {}
            for outcome in market.get("outcomes", []):
                name = outcome["name"]
                price = outcome["price"]
                if name not in best[mkey] or _is_better(price, best[mkey][name]):
                    best[mkey][name] = price
    return best


def _is_better(new: int, current: int) -> bool:
    def decimal(o):
        return 1 + o / 100 if o > 0 else 1 + 100 / abs(o)
    return decimal(new) > decimal(current)


def calculate_consensus_odds(bookmakers: list) -> dict:
    totals, counts = {}, {}
    for book in bookmakers:
        for market in book.get("markets", []):
            mkey = market["key"]
            totals.setdefault(mkey, {})
            counts.setdefault(mkey, {})
            for outcome in market.get("outcomes", []):
                name, price = outcome["name"], outcome["price"]
                implied = american_to_implied(price)
                totals[mkey][name] = totals[mkey].get(name, 0) + implied
                counts[mkey][name] = counts[mkey].get(name, 0) + 1

    consensus = {}
    for mkey, outcomes in totals.items():
        consensus[mkey] = {}
        for name, total in outcomes.items():
            avg = total / counts[mkey][name]
            american = -round((avg / (1 - avg)) * 100) if avg >= 0.5 else round(((1 - avg) / avg) * 100)
            consensus[mkey][name] = american
    return consensus

def _analyze_kalshi_markets(sport: str, game: dict) -> list[dict]:
    """Analyze Kalshi prediction markets — disabled when rate-limited."""
    return []
