#!/usr/bin/env python3
"""Test 4 PM flow locally without sending Discord messages."""
import os
os.environ["DISCORD_WEBHOOK_URL"] = ""  # Disable Discord

print("=" * 80)
print("4 PM FLOW TEST (LOCAL - NO DISCORD MESSAGES)")
print("=" * 80)

# Simulate 4 PM message
print("\n[4 PM] Sending startup message...")
print("Message: 🚀 **4 PM EST — Betting Model Starting**\n\nLive odds analysis in progress...")

# Run model
print("\n[MODEL] Starting betting analysis...")
print("(Model would run and find picks here)")

print("\n[PICK] If a pick is found, it would send:")
print("-" * 80)
print("-# \"My clients walk away with checks. So will you.\"")
print("# 🎯 PICK OF THE DAY")
print("# Lakers ML — -110 — 2.5u")
print("")
print("Edge: 3.2% | Conf: 78%")
print("FanDuel · Tomorrow 7:30 PM")
print("🔥 **3 IN A ROW. Dino is locked in.**")
print("📊 L5: 4-1 | L10: 8-2 | NBA: 12-5")
print("-" * 80)

print("\n✓ Test complete - no Discord messages sent")
