#!/usr/bin/env python3
"""Run at 4 PM EST to start betting model and send Discord alert."""
import requests
from datetime import datetime, timezone, timedelta
from config import DISCORD_WEBHOOK_URL

# Safety check: only send messages between 3:50 PM and 4:10 PM Eastern Time
now = datetime.now(timezone.utc)

# Check API health first
from api_health import log_api_health
success, errors = log_api_health()
if not success:
    print(f"⚠️ API issues detected: {', '.join(errors)}")
    # Continue anyway but note the issues

# Convert to Eastern Time (handles EST/EDT automatically)
from zoneinfo import ZoneInfo
eastern_time = now.astimezone(ZoneInfo('America/New_York'))
est_hour = eastern_time.hour
est_minute = eastern_time.minute

# Only proceed if between 3:50 PM and 4:10 PM Eastern (15:50 - 16:10)
if not (15 <= est_hour <= 16 and (est_hour == 15 and est_minute >= 50 or est_hour == 16 and est_minute <= 10)):
    print(f"[SAFETY] Not 4 PM Eastern window. Current Eastern time: {est_hour:02d}:{est_minute:02d}")
    print("[SAFETY] Aborting to prevent accidental Discord messages.")
    exit(1)

print(f"[OK] Running at {est_hour:02d}:{est_minute:02d} Eastern - within 4 PM window")

# Send 4 PM alert
if DISCORD_WEBHOOK_URL:
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": "🚀 **4 PM EST — Betting Model Starting**\n\nLive odds analysis in progress..."},
            timeout=10,
        ).raise_for_status()
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")

# Run the betting model (which will send picks)
from main import run
run()
