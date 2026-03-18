"""
Kalshi API integration for sports prediction markets.
Kalshi offers binary outcome markets on sports events.
"""
import requests
from datetime import datetime
import json

KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_DEMO_URL = "https://api.elections.kalshi.com/trade-api/v2"

class KalshiAPI:
    def __init__(self, email=None, password=None, demo=True):
        self.base_url = KALSHI_DEMO_URL if demo else KALSHI_BASE_URL
        self.session = requests.Session()
        self.token = None
        
        if email and password:
            self.login(email, password)
    
    def login(self, email: str, password: str) -> bool:
        """Login to Kalshi API."""
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={"email": email, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                return True
            else:
                print(f"Kalshi login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"Kalshi login error: {e}")
            return False
    
    def get_sports_markets(self, limit: int = 100) -> list:
        """Get active sports markets from Kalshi."""
        try:
            params = {
                "limit": limit,
                "status": "open"
            }
            
            response = self.session.get(
                f"{self.base_url}/events",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                events = response.json().get("events", [])
                # Filter for sports-related events
                sports_events = []
                for event in events:
                    title = event.get("title", "").upper()
                    category = event.get("category", "").upper()
                    
                    if any(sport in title for sport in ["NHL", "NBA", "NFL", "MLB", "SPORT", "GAME", "MATCH", "CHAMPIONSHIP"]) or \
                       "SPORT" in category:
                        sports_events.append(event)
                
                return sports_events
            else:
                print(f"Kalshi markets request failed: {response.status_code}")
                return []
        except Exception as e:
            print(f"Kalshi markets error: {e}")
            return []
    
    def get_market_orderbook(self, ticker: str) -> dict:
        """Get orderbook for a specific market."""
        try:
            response = self.session.get(
                f"{self.base_url}/markets/{ticker}/orderbook",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Kalshi orderbook request failed: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Kalshi orderbook error: {e}")
            return {}
    
    def analyze_sports_markets(self) -> list:
        """
        Analyze Kalshi sports markets for arbitrage opportunities.
        Compare Kalshi prices to our model probabilities.
        """
        markets = self.get_sports_markets()
        opportunities = []
        
        for event in markets:
            event_ticker = event.get("event_ticker", "")
            title = event.get("title", "")
            
            # Look for NHL/NBA/NFL markets
            if any(sport in title.upper() for sport in ["NHL", "NBA", "NFL", "MLB"]):
                # Get markets for this event
                for market in event.get("markets", []):
                    ticker = market.get("ticker", "")
                    subtitle = market.get("subtitle", "")
                    
                    # Get current prices
                    orderbook = self.get_market_orderbook(ticker)
                    if orderbook:
                        yes_price = self._get_best_price(orderbook, "yes")
                        no_price = self._get_best_price(orderbook, "no")
                        
                        if yes_price and no_price:
                            # Kalshi prices are in cents (0-100)
                            yes_prob = yes_price / 100
                            no_prob = no_price / 100
                            
                            opportunities.append({
                                "event": title,
                                "market": subtitle,
                                "ticker": ticker,
                                "yes_price": yes_price,
                                "no_price": no_price,
                                "yes_prob": yes_prob,
                                "no_prob": no_prob,
                                "total_prob": yes_prob + no_prob,
                                "arbitrage": yes_prob + no_prob < 0.95,  # Potential arb if < 95%
                            })
        
        return opportunities
    
    def _get_best_price(self, orderbook: dict, side: str) -> int:
        """Get best bid/ask price from orderbook."""
        try:
            if side == "yes":
                asks = orderbook.get("orderbook", {}).get("yes", [])
                if asks:
                    return min(ask[0] for ask in asks)  # Best ask (lowest price to buy yes)
            else:  # no
                asks = orderbook.get("orderbook", {}).get("no", [])
                if asks:
                    return min(ask[0] for ask in asks)  # Best ask (lowest price to buy no)
        except Exception:
            pass
        return None

def find_kalshi_arbitrage() -> list:
    """
    Find arbitrage opportunities between Kalshi and traditional sportsbooks.
    """
    kalshi = KalshiAPI(demo=True)  # Use demo for now
    opportunities = kalshi.analyze_sports_markets()
    
    arbitrage_ops = []
    for opp in opportunities:
        if opp["arbitrage"]:
            # Calculate potential profit
            yes_prob = opp["yes_prob"]
            no_prob = opp["no_prob"]
            total_prob = yes_prob + no_prob
            
            if total_prob < 0.95:  # 5%+ edge
                edge = 1.0 - total_prob
                arbitrage_ops.append({
                    "event": opp["event"],
                    "market": opp["market"],
                    "ticker": opp["ticker"],
                    "edge": edge,
                    "strategy": f"Buy both YES@{opp['yes_price']}¢ and NO@{opp['no_price']}¢",
                    "profit_pct": edge * 100,
                })
    
    return sorted(arbitrage_ops, key=lambda x: x["edge"], reverse=True)

def compare_kalshi_to_model(sport: str, home_team: str, away_team: str) -> dict:
    """
    Compare Kalshi market prices to our model probabilities.
    Look for markets like "Will [team] win?" or "Will total be over X?"
    """
    kalshi = KalshiAPI(demo=True)
    markets = kalshi.get_sports_markets()
    
    # Look for markets matching this game
    game_markets = []
    for event in markets:
        title = event.get("title", "")
        if home_team.split()[-1] in title or away_team.split()[-1] in title:
            game_markets.append(event)
    
    comparisons = []
    if game_markets:
        # Get our model prediction
        from models.stats import get_pregame_prob
        model_result = get_pregame_prob(sport, home_team, away_team)
        
        if model_result:
            home_prob, away_prob, total = model_result
            
            for event in game_markets:
                for market in event.get("markets", []):
                    ticker = market.get("ticker", "")
                    subtitle = market.get("subtitle", "")
                    
                    orderbook = kalshi.get_market_orderbook(ticker)
                    if orderbook:
                        yes_price = kalshi._get_best_price(orderbook, "yes")
                        if yes_price:
                            kalshi_prob = yes_price / 100
                            
                            # Compare to model
                            if "win" in subtitle.lower() and home_team.split()[-1] in subtitle:
                                model_prob = home_prob
                                edge = model_prob - kalshi_prob
                            elif "win" in subtitle.lower() and away_team.split()[-1] in subtitle:
                                model_prob = away_prob
                                edge = model_prob - kalshi_prob
                            else:
                                model_prob = None
                                edge = None
                            
                            if model_prob and abs(edge) > 0.05:  # 5%+ difference
                                comparisons.append({
                                    "market": subtitle,
                                    "ticker": ticker,
                                    "kalshi_prob": kalshi_prob,
                                    "model_prob": model_prob,
                                    "edge": edge,
                                    "recommendation": "BUY YES" if edge > 0 else "BUY NO",
                                })
    
    return {
        "game": f"{away_team} @ {home_team}",
        "comparisons": comparisons,
        "total_opportunities": len(comparisons),
    }

def get_kalshi_sports_summary() -> dict:
    """Get summary of available Kalshi sports markets."""
    kalshi = KalshiAPI(demo=True)
    markets = kalshi.get_sports_markets()
    
    sports_count = {}
    total_markets = 0
    
    for event in markets:
        title = event.get("title", "")
        market_count = len(event.get("markets", []))
        total_markets += market_count
        
        # Categorize by sport
        if "NHL" in title.upper():
            sports_count["NHL"] = sports_count.get("NHL", 0) + market_count
        elif "NBA" in title.upper():
            sports_count["NBA"] = sports_count.get("NBA", 0) + market_count
        elif "NFL" in title.upper():
            sports_count["NFL"] = sports_count.get("NFL", 0) + market_count
        elif "MLB" in title.upper():
            sports_count["MLB"] = sports_count.get("MLB", 0) + market_count
        else:
            sports_count["Other"] = sports_count.get("Other", 0) + market_count
    
    return {
        "total_events": len(markets),
        "total_markets": total_markets,
        "by_sport": sports_count,
        "timestamp": datetime.now().isoformat(),
    }
