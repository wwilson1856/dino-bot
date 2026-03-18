#!/usr/bin/env python3
"""Send apology message to Discord."""
import requests
from config import DISCORD_WEBHOOK_URL

if DISCORD_WEBHOOK_URL:
    message = "🙏 My apologies for the earlier Discord message with missing team info. That's been fixed. Back to normal operations."
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=10,
        ).raise_for_status()
        print("✓ Apology sent to Discord")
    except Exception as e:
        print(f"Failed to send: {e}")
else:
    print("No Discord webhook configured")
