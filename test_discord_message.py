#!/usr/bin/env python3
"""Test Discord message formatting without sending."""
import random
from config import UNIT_SIZE

DINO_QUOTES = [
    "Just settled a truck case for seven figures. This pick is even more of a lock.",
    "I've taken on Freightliner, Peterbilt, and their whole legal teams. This line doesn't scare me.",
    "Eighteen-wheelers, bad odds — I beat both for a living. Ride with me.",
    "My clients walk away with checks. So will you.",
    "I don't take cases I can't win. I don't bet picks I don't believe in.",
]

# Sample pick
pick = {
    "home": "Lakers",
    "away": "Celtics",
    "bet": "Lakers ML",
    "odds": -110,
    "edge": 0.032,
    "confidence": 78,
    "units": 2.5,
    "best_book": "FanDuel",
    "time_label": "Tomorrow 7:30 PM",
    "sport": "NBA",
}

def _odds_str(price: int) -> str:
    return f"+{price}" if price > 0 else str(price)

home = pick.get("home", "Home")
away = pick.get("away", "Away")
bet = pick.get("bet", "")
odds = _odds_str(pick["odds"])
edge = pick["edge"]
conf = pick["confidence"]
units = pick["units"]
time_label = pick.get("time_label", "")
book = pick.get("best_book", "FanDuel")
quote = random.choice(DINO_QUOTES)

streak_line = f"\n🔥 **3 IN A ROW. Dino is locked in.**"
stats_line = f"\n📊 L5: 4-1 | L10: 8-2 | NBA: 12-5"

message = (
    f"-# *\"{quote}\"*\n"
    f"# 🎯 PICK OF THE DAY\n"
    f"# {bet} — {odds} — {units}u\n\n"
    f"Edge: {edge:.1%} | Conf: {conf}%\n"
    f"{book} · {time_label}"
    f"{streak_line}"
    f"{stats_line}"
)

print("=" * 80)
print("DISCORD MESSAGE PREVIEW (NOT SENT)")
print("=" * 80)
print(message)
print("=" * 80)
