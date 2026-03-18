#!/usr/bin/env python3
"""Test 4 PM flow locally WITHOUT sending Discord messages."""
import os
from datetime import datetime

# Temporarily disable Discord
os.environ["DISCORD_WEBHOOK_URL"] = ""

print("=" * 80)
print("4 PM FLOW TEST (NO DISCORD MESSAGES)")
print("=" * 80)
print()

# Show what would be sent
startup_msg = "🚀 **4 PM EST — Betting Model Starting**\n\nLive odds analysis in progress..."
print("[4 PM] Startup message (NOT SENT):")
print(startup_msg)
print()

# Run the model
print("[MODEL] Starting betting analysis with live data...")
print()

from main import run
run()
