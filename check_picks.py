"""Run: python check_picks.py"""
from picks_log import _load, streak

picks = _load()
if not picks:
    print("No picks logged yet.")
else:
    wins = sum(1 for p in picks if p["result"] == "win")
    losses = sum(1 for p in picks if p["result"] == "loss")
    pending = sum(1 for p in picks if p["result"] is None)
    units = sum(p["units"] for p in picks if p["result"] == "win") - \
            sum(p["units"] for p in picks if p["result"] == "loss")

    print(f"\n{'DATE':<12} {'BET':<30} {'ODDS':>6} {'UNITS':>6} {'RESULT'}")
    print("-" * 65)
    for p in picks:
        print(f"{p['date']:<12} {p['bet']:<30} {p['odds']:>6} {p['units']:>6} {p['result'] or 'pending'}")

    print("-" * 65)
    print(f"Record: {wins}W - {losses}L | Units: {units:+.2f} | Pending: {pending} | Streak: {streak()}")
