"""
Run this first to:
1. Verify your API key works
2. See all available sports on your plan
3. See all active/upcoming games with odds
"""
import requests
import sys
from config import API_KEY, BASE_URL


def check_api_key():
    resp = requests.get(f"{BASE_URL}/sports", params={"apiKey": API_KEY}, timeout=10)
    if resp.status_code == 401:
        print("❌ API key is invalid or not set. Check your .env file.")
        sys.exit(1)
    if resp.status_code != 200:
        print(f"❌ API error: {resp.status_code} - {resp.text}")
        sys.exit(1)
    print(f"✅ API key valid. Calls remaining: {resp.headers.get('x-requests-remaining', '?')}\n")
    return resp.json()


def list_sports(sports: list):
    print("=== AVAILABLE SPORTS ON YOUR PLAN ===")
    baseball = []
    for s in sports:
        if not s.get("active"):
            continue
        key = s["key"]
        title = s["title"]
        has_odds = s.get("has_outrights", False)
        print(f"  {key:<45} {title}")
        if "baseball" in key.lower() or "wbc" in key.lower() or "mlb" in key.lower():
            baseball.append(s)
    print()
    if baseball:
        print("=== BASEBALL / WBC KEYS ===")
        for s in baseball:
            print(f"  {s['key']} -> {s['title']}")
    print()


def sample_odds(sport_key: str):
    print(f"=== SAMPLE ODDS: {sport_key} ===")
    resp = requests.get(
        f"{BASE_URL}/sports/{sport_key}/odds",
        params={
            "apiKey": API_KEY,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"  Error: {resp.status_code}")
        return

    games = resp.json()
    print(f"  Found {len(games)} games\n")
    for g in games[:5]:
        print(f"  {g['away_team']} @ {g['home_team']}  |  {g['commence_time']}")
        for book in g.get("bookmakers", [])[:2]:
            for market in book.get("markets", []):
                outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
                print(f"    [{book['title']}] {outcomes}")
        print()


if __name__ == "__main__":
    sports = check_api_key()
    list_sports(sports)

    # Sample MLB odds to confirm pipeline works
    sample_odds("baseball_mlb")

    # Search for WBC - try all likely key formats
    print("=== SEARCHING FOR WBC KEY ===")
    wbc_candidates = [s["key"] for s in sports if any(
        x in s["key"].lower() for x in ["wbc", "world_baseball", "classic", "international"]
    )]
    if wbc_candidates:
        print(f"Likely WBC keys: {wbc_candidates}")
        for key in wbc_candidates:
            sample_odds(key)
    else:
        print("No WBC key found on your plan.")
        print("All active baseball keys:")
        for s in sports:
            if "baseball" in s["key"].lower() and s.get("active"):
                print(f"  {s['key']}")
