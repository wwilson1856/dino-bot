"""
Betting Model - Action Network public API (no auth, no limits).
Finds edge on FanDuel lines using Pinnacle as sharp reference.
Refreshes every 120 seconds. Sends daily Discord card once per day.
"""
import time
import sys
import threading
import random
from datetime import datetime, timezone, date
from action_scraper import scrape_all_sports
from props_analyzer import analyze_props
from analyzer import analyze_game, tag_game_mode
from alerts import render_dashboard, console
from discord_alerts import send_top_pick, send_daily_card
from picks_log import log_pick, resolve_picks, streak
from config import POLL_INTERVAL_LIVE, MODE


def _warm_stat_cache(games_by_sport: dict):
    """Pre-fetch team stats in background threads so analysis doesn't block."""
    from models.stats import get_pregame_prob
    threads = []
    seen = set()
    for sport, games in games_by_sport.items():
        for game in games:
            key = f"{sport}:{game.get('home_team')}:{game.get('away_team')}"
            if key not in seen:
                seen.add(key)
                t = threading.Thread(
                    target=get_pregame_prob,
                    args=(sport, game.get("home_team", ""), game.get("away_team", "")),
                    daemon=True,
                )
                threads.append(t)
                t.start()
    deadline = time.time() + 15
    for t in threads:
        t.join(timeout=max(0, deadline - time.time()))


def run():
    console.print("[bold cyan]Betting Model — Action Network Live Odds[/bold cyan]")
    console.print(f"Refreshing every [yellow]{POLL_INTERVAL_LIVE}s[/yellow] | "
                  f"Edge: FanDuel vs DraftKings (live lines) | Press Ctrl+C to stop.\n")
    time.sleep(1)

    cache_warmed = False
    # Persist across restarts — don't re-send if a pick was already logged today
    from picks_log import _load
    _today_str = date.today().isoformat()
    last_discord_date = date.today() if any(p["date"] == _today_str for p in _load()) else None

    while True:
        try:
            now = datetime.now(timezone.utc)
            all_games, all_props = scrape_all_sports()

            if not cache_warmed:
                console.print("[dim]Warming stat cache...[/dim]")
                _warm_stat_cache(all_games)
                cache_warmed = True

            recommendations = []
            prop_recommendations = []

            for sport, games in all_games.items():
                for game in games:
                    tag_game_mode(game, sport, now)
                    if game.get("_game_mode") == "excluded":
                        continue
                    recs = analyze_game(sport, game)
                    recommendations.extend(recs)

            for sport, prop_events in all_props.items():
                for event_data in prop_events:
                    prop_recs = analyze_props(event_data)
                    prop_recommendations.extend(prop_recs)

            render_dashboard(recommendations, prop_recommendations, "∞", mode=MODE)

            # Send Discord card once per day with today's top picks
            today = now.date()
            if last_discord_date != today:
                today_picks = sorted(
                    [r for r in recommendations if r["game_mode"] in ("live", "upcoming") and r["odds"] >= -150],
                    key=lambda x: x["confidence"],
                    reverse=True,
                )
                if today_picks:
                    top = today_picks[0]
                    if random.random() < 0.25:
                        top = {**top, "units": round(top["units"] * 10, 2)}
                    resolve_picks()
                    log_pick(top)
                    send_top_pick(top, win_streak=streak())
                    last_discord_date = today

        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped.[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

        time.sleep(POLL_INTERVAL_LIVE)


if __name__ == "__main__":
    run()
