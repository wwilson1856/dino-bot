"""
Run this to see exactly what the model is seeing and why bets are/aren't firing.
python diagnose.py
"""
from action_scraper import scrape_all_sports
from analyzer import analyze_game, tag_game_mode
from edge import american_to_implied
from config import MIN_EDGE
from datetime import datetime, timezone

print(f"\nMIN_EDGE threshold: {MIN_EDGE:.1%}\n")

now = datetime.now(timezone.utc)
all_games, all_props = scrape_all_sports()

if not all_games:
    print("❌ No games returned. Checking raw API...")
    from action_scraper import get_games
    for sport in ["NBA", "NHL", "MLB", "NFL"]:
        games = get_games(sport)
        print(f"  {sport}: {len(games)} raw games")
        for g in games[:2]:
            print(f"    {g['away_team']} @ {g['home_team']} | status={g['status']} | books={[b['key'] for b in g['bookmakers']]}")
else:
    for sport, games in all_games.items():
        print(f"\n{'='*60}")
        print(f"  {sport} — {len(games)} game(s)")
        print(f"{'='*60}")
        for game in games:
            tag_game_mode(game, sport, now)
            mode = game.get("_game_mode", "?")
            print(f"\n  [{mode.upper()}] {game['away_team']} @ {game['home_team']}")
            print(f"  Books: {[b['key'] for b in game['bookmakers']]}")

            for book in game["bookmakers"]:
                for market in book.get("markets", []):
                    outcomes = market["outcomes"]
                    print(f"\n  [{book['key']}][{market['key']}]")
                    for o in outcomes:
                        print(f"    {o['name']:<32} {o['price']:>6}")

            recs = analyze_game(sport, game)
            if recs:
                r = recs[0]
                print(f"\n  🎯 BET: {r['bet']} @ {r['odds']} | edge={r['edge']:.2%} | EV=${r['ev']}")
            else:
                print(f"\n  — No bet fires")

