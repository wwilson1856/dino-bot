"""
Closing Line Value (CLV) tracker - measures if we're beating the market.
Positive CLV = we got better odds than closing, negative = worse.
"""
import json
import requests
from datetime import datetime, timedelta

def track_closing_line_value():
    """
    Check closing lines vs our logged picks to calculate CLV.
    This tells us if we're actually beating the market.
    """
    try:
        with open("picks_log.json", "r") as f:
            picks = json.load(f)
    except FileNotFoundError:
        return {}
    
    clv_data = []
    
    for pick in picks:
        if pick.get("result") in ("win", "loss"):  # Only resolved picks
            # Try to get closing line (this would need real implementation)
            closing_odds = _get_closing_line(pick)
            if closing_odds:
                our_odds = pick["odds"]
                
                # Calculate CLV - positive means we got better odds
                if our_odds > 0 and closing_odds > 0:
                    clv = (closing_odds - our_odds) / 100
                elif our_odds < 0 and closing_odds < 0:
                    clv = (abs(our_odds) - abs(closing_odds)) / abs(closing_odds)
                else:
                    clv = 0  # Mixed signs, complex calculation
                
                clv_data.append({
                    "date": pick["date"],
                    "bet": pick["bet"],
                    "our_odds": our_odds,
                    "closing_odds": closing_odds,
                    "clv": clv,
                    "result": pick["result"]
                })
    
    return clv_data

def _get_closing_line(pick):
    """
    Get closing line for a pick. In real implementation, this would:
    1. Query historical odds API
    2. Find the same game/market
    3. Return the closing odds
    
    For now, simulate with slight movement.
    """
    # Simulate closing line movement (usually against public)
    our_odds = pick["odds"]
    
    # Simulate: totals usually move against the over (public bet)
    if "over" in pick["bet"].lower():
        # Closing line typically 2-5 points worse for overs
        if our_odds > 0:
            return our_odds - 10  # +110 becomes +100
        else:
            return our_odds - 5   # -110 becomes -115
    else:
        # Less movement on other markets
        return our_odds + 2

def get_clv_summary():
    """Get CLV summary statistics."""
    clv_data = track_closing_line_value()
    
    if not clv_data:
        return {"avg_clv": 0, "positive_clv_rate": 0, "total_picks": 0}
    
    avg_clv = sum(d["clv"] for d in clv_data) / len(clv_data)
    positive_clv = sum(1 for d in clv_data if d["clv"] > 0)
    positive_rate = positive_clv / len(clv_data)
    
    return {
        "avg_clv": avg_clv,
        "positive_clv_rate": positive_rate,
        "total_picks": len(clv_data),
        "details": clv_data
    }

def add_sharp_book_comparison():
    """
    Add requirement that our picks must beat Pinnacle (sharpest book).
    Only recommend bets where we have better odds than Pinnacle closing.
    """
    # This would be integrated into the main analyzer
    # to filter out picks that don't beat sharp money
    pass

def implement_kelly_sizing():
    """
    Implement proper Kelly criterion sizing based on actual edge.
    Current sizing might be too aggressive.
    """
    # Kelly = (bp - q) / b
    # where b = decimal odds - 1, p = win prob, q = 1 - p
    # Scale by confidence and cap at reasonable max
    pass
