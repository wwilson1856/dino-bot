"""
Model calibration — learns from resolved picks to adjust blend weights and edge thresholds.

For each market type, tracks:
- Predicted model_prob vs actual win rate (calibration error)
- ROI to detect if edge is real or noise

Outputs adjustments used by the analyzer.
"""
import json
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "picks_log.json")
MIN_SAMPLE = 10  # minimum resolved picks before adjusting


def _load_resolved() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        picks = json.load(f)
    return [p for p in picks if p.get("result") in ("win", "loss") and p.get("model_prob")]


def get_calibration() -> dict:
    """
    Returns per-market calibration data:
    {
      "totals":  {"model_weight": 0.6, "edge_multiplier": 1.0, "win_rate": 0.xx, "roi": 0.xx, "n": N},
      "h2h":     {...},
      "spreads":  {...},
    }
    Defaults to neutral (no adjustment) when sample is too small.
    """
    resolved = _load_resolved()
    markets = ["totals", "h2h", "spreads"]
    result = {}

    for market in markets:
        picks = [p for p in resolved if p.get("market") == market]
        n = len(picks)

        if n < MIN_SAMPLE:
            result[market] = {"model_weight": None, "edge_multiplier": 1.0, "win_rate": None, "roi": None, "n": n}
            continue

        wins = sum(1 for p in picks if p["result"] == "win")
        win_rate = wins / n

        # Average predicted probability
        avg_pred = sum(p["model_prob"] for p in picks) / n

        # Calibration error: how far off is the model from reality
        # Positive = model over-predicts (overconfident), negative = under-predicts
        cal_error = avg_pred - win_rate

        # Adjust model weight: reduce if overconfident, increase if under-confident
        # Base weight 0.6, clamp between 0.2 and 0.8
        model_weight = max(0.2, min(0.8, 0.6 - cal_error))

        # ROI = profit / units risked
        total_profit = sum(p.get("profit", 0) or 0 for p in picks)
        total_units = sum(p.get("units", 1) for p in picks)
        roi = total_profit / total_units if total_units > 0 else 0

        # Edge multiplier: if ROI is negative, tighten edge threshold (require more edge)
        # If ROI is positive, keep or slightly loosen
        if roi < -0.1:
            edge_multiplier = 1.5  # require 50% more edge
        elif roi < 0:
            edge_multiplier = 1.2
        elif roi > 0.1:
            edge_multiplier = 0.9  # slightly loosen
        else:
            edge_multiplier = 1.0

        result[market] = {
            "model_weight": round(model_weight, 3),
            "edge_multiplier": edge_multiplier,
            "win_rate": round(win_rate, 3),
            "roi": round(roi, 3),
            "n": n,
        }

    return result


def get_model_weight(market: str) -> float:
    """Return the calibrated model blend weight for a market. Defaults to base if insufficient data."""
    defaults = {"totals": 0.45, "h2h": 0.40, "spreads": 0.55}
    cal = get_calibration().get(market, {})
    return cal.get("model_weight") or defaults.get(market, 0.6)


def get_edge_multiplier(market: str) -> float:
    """Return the edge threshold multiplier for a market."""
    cal = get_calibration().get(market, {})
    return cal.get("edge_multiplier", 1.0)
