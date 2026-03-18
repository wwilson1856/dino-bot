#!/usr/bin/env python3
"""Test 4 PM flow with actual data but no Discord messages."""
import os
os.environ["DISCORD_WEBHOOK_URL"] = ""  # Disable Discord

print("=" * 80)
print("4 PM FLOW TEST (LIVE DATA - NO DISCORD)")
print("=" * 80)

# Simulate 4 PM message
print("\n[4 PM] Sending startup message...")
print("Message: 🚀 **4 PM EST — Betting Model Starting**\n\nLive odds analysis in progress...")

# Run model
print("\n[MODEL] Starting betting analysis with live data...\n")

from action_scraper import scrape_all_sports
from analyzer import analyze_game, tag_game_mode
from alerts import render_dashboard
from datetime import datetime, timezone
from config import MODE

now = datetime.now(timezone.utc)
all_games, all_props = scrape_all_sports()

recommendations = []
for sport, games in all_games.items():
    for game in games:
        tag_game_mode(game, sport, now)
        recs = analyze_game(sport, game)
        recommendations.extend(recs)

render_dashboard(recommendations, [], "∞", mode=MODE)

print("\n✓ Test complete - no Discord messages sent")
