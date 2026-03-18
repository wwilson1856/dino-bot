"""
Analyzes player props from FanDuel using vig removal to find edge.
Over/Under props are paired - we remove vig across the pair to get fair prob.
"""
from edge import american_to_implied, expected_value
from config import MIN_EDGE


def analyze_props(event_data: dict) -> list[dict]:
    """
    Takes a single event's prop data and returns value bets.
    """
    sport = event_data.get("_sport_name", "?")
    home = event_data.get("home_team", "Home")
    away = event_data.get("away_team", "Away")
    bookmakers = event_data.get("bookmakers", [])

    if not bookmakers:
        return []

    fanduel = bookmakers[0]
    candidates = []

    for market in fanduel.get("markets", []):
        market_key = market["key"]
        outcomes = market.get("outcomes", [])

        # Group outcomes by player name (each player has Over + Under)
        players = {}
        for o in outcomes:
            name = o.get("description") or o.get("name", "")
            side = o["name"]  # "Over" or "Under"
            price = o["price"]
            point = o.get("point")

            if name not in players:
                players[name] = {}
            players[name][side] = {"price": price, "point": point}

        for player, sides in players.items():
            if "Over" not in sides or "Under" not in sides:
                continue

            over_price = sides["Over"]["price"]
            under_price = sides["Under"]["price"]
            line = sides["Over"].get("point", "?")

            # Remove vig to get fair probabilities
            over_implied = american_to_implied(over_price)
            under_implied = american_to_implied(under_price)
            total = over_implied + under_implied

            fair_over = over_implied / total
            fair_under = under_implied / total

            # Edge = fair prob - line implied prob
            over_edge = fair_over - over_implied
            under_edge = fair_under - under_implied

            for side, fair_prob, price, edge in [
                ("Over", fair_over, over_price, over_edge),
                ("Under", fair_under, under_price, under_edge),
            ]:
                if edge >= MIN_EDGE:
                    prop_label = market_key.replace("player_", "").replace("batter_", "").replace("pitcher_", "").replace("_", " ").title()
                    candidates.append({
                        "sport": sport,
                        "home": home,
                        "away": away,
                        "player": player,
                        "bet": f"{player} {side} {line} {prop_label}",
                        "market": market_key,
                        "odds": price,
                        "model_prob": round(fair_prob, 4),
                        "implied_prob": round(american_to_implied(price), 4),
                        "edge": round(edge, 4),
                        "ev": expected_value(fair_prob, price),
                        "game_mode": "live",
                        "time_label": "LIVE",
                        "best_book": "FanDuel",
                        "is_prop": True,
                    })

    return sorted(candidates, key=lambda x: x["edge"], reverse=True)
