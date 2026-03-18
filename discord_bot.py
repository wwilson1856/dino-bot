#!/usr/bin/env python3
"""
Discord bot for Moneymaker - Interactive betting model commands
Run this alongside the main model for user interaction
"""
import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from picks_log import record, streak, total_profit, resolve_picks
from models.stats import get_recent_form
from action_scraper import get_games
from analyzer import analyze_game, tag_game_mode
from datetime import datetime, timezone

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True  # Required for commands - enable in Discord Developer Portal
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✓ Bot connected as {bot.user}')
    print(f'  Servers: {len(bot.guilds)}')
    print(f'  Commands: !pick, !analyze, !analyzegame, !game, !mlb, !mlbprops, !props, !baddino, !record, !stats, !recent, !health, !kalshi, !teamstats, !profit, !commands')

@bot.command(name='pick')
async def get_pick(ctx):
    """Get today's top pick from the 4 PM log"""
    try:
        import json
        from datetime import date
        
        with open('picks_log.json') as f:
            picks = json.load(f)
        
        # Get today's pick
        today = str(date.today())
        today_picks = [p for p in picks if p['date'] == today]
        
        if not today_picks:
            await ctx.send("📭 No pick logged for today yet. Check back at 4 PM!")
            return
        
        pick = today_picks[-1]  # Most recent
        game = f"{pick['away']} @ {pick['home']}"
        bet = pick['bet']
        odds = pick['odds']
        units = pick['units']
        
        embed = discord.Embed(title="🎯 Today's Pick", color=0x00ff00)
        embed.add_field(name="Game", value=game, inline=False)
        embed.add_field(name="Bet", value=f"**{bet}** ({odds:+d})", inline=True)
        embed.add_field(name="Units", value=f"{units:.2f}u", inline=True)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error fetching pick: {str(e)}")

@bot.command(name='baddino')
async def bad_dino(ctx):
    """Comic relief for when Dino loses a pick"""
    import random
    
    # Dino's excuses and reactions
    excuses = [
        "🦕 The refs were clearly paid off!",
        "🦕 That was just variance, trust the process!",
        "🦕 My model didn't account for the moon phase",
        "🦕 The sharp money came in late and ruined everything",
        "🦕 That goalie was playing like he was possessed",
        "🦕 I blame the weather in a dome stadium",
        "🦕 The books obviously have inside information",
        "🦕 That was a 2% edge, we just got unlucky",
        "🦕 My calculations were perfect, reality was wrong",
        "🦕 The ice was clearly tilted toward their goal",
        "🦕 I forgot to carry the 1 in my Kelly calculation",
        "🦕 That player wasn't supposed to be that good",
        "🦕 The puck had magnets in it, I'm sure of it",
        "🦕 My computer must have been hacked by Vegas",
        "🦕 That was just a bad beat, happens to the best of us"
    ]
    
    # Dino's coping mechanisms
    coping = [
        "🎯 Time to double down on the next pick!",
        "📊 Let me recalibrate my models real quick...",
        "🔥 This is why we bet units, not the house!",
        "⚡ The next one is guaranteed 99.9% confidence!",
        "🎲 Variance is temporary, my genius is forever",
        "💎 Diamond hands on the next play!",
        "🚀 We're due for a heater, trust me",
        "🧠 My brain is too big for these simple games",
        "⭐ Even Einstein was wrong sometimes",
        "🎪 Welcome to the circus, folks!"
    ]
    
    # Random dino reactions
    reactions = [
        "🦕💸", "🦕😭", "🦕🤡", "🦕📉", "🦕💀", 
        "🦕🔥", "🦕😤", "🦕🎭", "🦕💔", "🦕🤯"
    ]
    
    excuse = random.choice(excuses)
    cope = random.choice(coping)
    reaction = random.choice(reactions)
    
    embed = discord.Embed(
        title=f"{reaction} BAD DINO ALERT {reaction}",
        description=f"{excuse}\n\n{cope}",
        color=0xff4444
    )
    
    embed.add_field(
        name="🎪 Dino's Current Mood",
        value="Definitely not tilted, just recalculating...",
        inline=False
    )
    
    embed.set_footer(text="Remember: Past performance does not guarantee future results*")
    
    await ctx.send(embed=embed)

@bot.command(name='mlbprops')
async def analyze_mlb_props(ctx):
    """MLB player props analysis (hitting & pitching)"""
    try:
        from mlb_analyzer import analyze_mlb_player_props
        from action_scraper import scrape_all_sports
        
        embed = discord.Embed(title="⚾ MLB Props", description="Analyzing player props...", color=0x1f8b4c)
        await ctx.send(embed=embed)
        
        all_games, _ = scrape_all_sports()
        now = datetime.now(timezone.utc)
        
        prop_picks = []
        for game in all_games.get("MLB", []):
            tag_game_mode(game, "MLB", now)
            if game.get("_game_mode") in ("upcoming", "live"):
                props = analyze_mlb_player_props(game)
                prop_picks.extend(props)
        
        if not prop_picks:
            embed = discord.Embed(title="⚾ MLB Props", description="❌ No value props found", color=0xff0000)
            await ctx.send(embed=embed)
            return
            
        # Sort by edge
        prop_picks.sort(key=lambda x: x["edge"], reverse=True)
        
        embed = discord.Embed(title="⚾ MLB Player Props", color=0x00ff00)
        
        for i, pick in enumerate(prop_picks[:6], 1):  # Top 6 props
            embed.add_field(
                name=f"{i}. {pick['bet']}",
                value=f"**({pick['odds']:+d})** — {pick['units']:.2f}u\nProj: {pick['projection']} | Edge: {pick['edge']:.1%}",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ MLB props error: {str(e)}")

@bot.command(name='mlb')
async def analyze_mlb(ctx):
    """MLB team markets analysis with baseball-specific modeling"""
    try:
        from mlb_analyzer import analyze_mlb_team_markets
        from action_scraper import scrape_all_sports
        
        embed = discord.Embed(title="⚾ MLB Analysis", description="Analyzing baseball markets...", color=0x1f8b4c)
        await ctx.send(embed=embed)
        
        all_games, _ = scrape_all_sports()
        now = datetime.now(timezone.utc)
        
        mlb_picks = []
        for game in all_games.get("MLB", []):
            tag_game_mode(game, "MLB", now)
            if game.get("_game_mode") in ("upcoming", "live"):
                picks = analyze_mlb_team_markets(game)
                mlb_picks.extend(picks)
        
        if not mlb_picks:
            embed = discord.Embed(title="⚾ MLB Markets", description="❌ No value picks found", color=0xff0000)
            await ctx.send(embed=embed)
            return
            
        # Sort by edge
        mlb_picks.sort(key=lambda x: x["edge"], reverse=True)
        
        embed = discord.Embed(title="⚾ MLB Value Picks", color=0x00ff00)
        
        for i, pick in enumerate(mlb_picks[:8], 1):  # Top 8 picks
            embed.add_field(
                name=f"{i}. {pick['away']} @ {pick['home']}",
                value=f"**{pick['bet']}** ({pick['odds']:+d}) — {pick['units']:.2f}u\nEdge: {pick['edge']:.1%} | Conf: {pick['confidence']}%",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ MLB analysis error: {str(e)}")

@bot.command(name='game')
async def analyze_game_cmd(ctx, *, teams):
    """Analyze specific game for value picks. Usage: !game Boston Montreal"""
    try:
        from action_scraper import scrape_all_sports
        
        # Parse team names
        team_parts = teams.strip().split()
        if len(team_parts) < 2:
            await ctx.send("❌ Usage: `!game <team1> <team2>` (e.g., `!game Boston Montreal`)")
            return
            
        search_terms = [part.lower() for part in team_parts]
        
        # Find matching game
        all_games, _ = scrape_all_sports()
        target_game = None
        
        for sport, games in all_games.items():
            for game in games:
                home = game.get("home_team", "").lower()
                away = game.get("away_team", "").lower()
                
                # Check if search terms match either team
                if any(term in home or term in away for term in search_terms):
                    target_game = (sport, game)
                    break
            if target_game:
                break
                
        if not target_game:
            await ctx.send(f"❌ No game found matching: {teams}")
            return
            
        sport, game = target_game
        now = datetime.now(timezone.utc)
        tag_game_mode(game, sport, now)
        
        # Analyze the game
        picks = analyze_game(sport, game)
        team_picks = [p for p in picks if not p.get('player')]
        
        if not team_picks:
            await ctx.send(f"📊 **{game['away_team']} @ {game['home_team']}**\n❌ No value picks found")
            return
            
        # Format results
        embed = discord.Embed(
            title=f"🎯 {game['away_team']} @ {game['home_team']}",
            color=0x00ff00
        )
        
        for pick in team_picks:
            embed.add_field(
                name=f"{pick['bet']} ({pick['odds']:+d})",
                value=f"Edge: {pick['edge']:.1%} | Conf: {pick['confidence']}% | {pick['units']:.2f}u",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error analyzing game: {str(e)}")

@bot.command(name='analyzegame')
async def analyze_game_full(ctx, *, teams):
    """Top 3 picks for a specific game including player props. Usage: !analyzegame Boston Celtics"""
    import asyncio
    import threading

    msg = await ctx.send(f"🔄 Analyzing game... (please allow 1-2 minutes)")

    def run():
        from action_scraper import scrape_all_sports
        from team_analyzer import analyze_team_markets_only
        import models.stats as stats_mod
        stats_mod.ESPN_TIMEOUT = 5

        search_terms = [p.lower() for p in teams.strip().split()]
        all_games, all_props = scrape_all_sports()
        now = datetime.now(timezone.utc)

        # Find matching game
        target_game = None
        target_sport = None
        for sport, games in all_games.items():
            for game in games:
                home = game.get("home_team", "").lower()
                away = game.get("away_team", "").lower()
                if any(t in home or t in away for t in search_terms):
                    target_game = game
                    target_sport = sport
                    break
            if target_game:
                break

        if not target_game:
            return None, None, None, teams

        tag_game_mode(target_game, target_sport, now)

        home_n = target_game.get("home_team", "")
        away_n = target_game.get("away_team", "")

        # Warm stat cache
        from models.stats import get_pregame_prob
        get_pregame_prob(target_sport, home_n, away_n)

        # Team picks — pass min_edge=0 to always return results ranked by edge
        team_picks = analyze_team_markets_only(target_sport, target_game, min_edge=0)
        team_picks = sorted(team_picks, key=lambda x: x["edge"], reverse=True)

        # Player prop picks
        prop_picks = []
        try:
            from oddsapi_props import get_nhl_props_smart
            from nhl_props import analyze_nhl_player_prop_simple

            if target_sport == "NHL":
                all_nhl_props = get_nhl_props_smart()
                game_props = [
                    p for p in all_nhl_props
                    if (p["home_team"].replace("é","e") == home_n.replace("é","e") and
                        p["away_team"].replace("é","e") == away_n.replace("é","e")) or
                       (p["home_team"].replace("é","e") == away_n.replace("é","e") and
                        p["away_team"].replace("é","e") == home_n.replace("é","e"))
                ]
                for prop in game_props:
                    best = None
                    for team, opp in [(home_n, away_n), (away_n, home_n)]:
                        try:
                            a = analyze_nhl_player_prop_simple(
                                prop["player"], team, prop["prop_type"], prop["line"], prop["odds"], opp
                            )
                            if a and a.get("edge", 0) > (best.get("edge", 0) if best else -999):
                                best = a
                        except Exception:
                            continue
                    if best:
                        confidence = min(95, max(50, int(best["edge"] * 300 + 60)))
                        prop_picks.append({
                            "player": prop["player"],
                            "bet": f"{prop['player']} {prop['prop_type'].title()} Over {prop['line']}",
                            "odds": prop["odds"],
                            "edge": best["edge"],
                            "confidence": confidence,
                            "projection": best.get("projection", ""),
                            "units": round(min(1.5, best["edge"] * 6), 2),
                        })
            else:
                # NBA/MLB — fetch props from OddsAPI event-odds endpoint
                try:
                    from config import API_KEY, BASE_URL, PROP_MARKETS
                    import requests as _req
                    sport_key = {"NBA": "basketball_nba", "MLB": "baseball_mlb"}.get(target_sport)
                    if sport_key:
                        # Get events list to find event ID
                        r = _req.get(
                            f"{BASE_URL}/sports/{sport_key}/events",
                            params={"apiKey": API_KEY},
                            timeout=10
                        )
                        if r.status_code == 200:
                            events = r.json()
                            # Match event to our game — try partial name match
                            event_id = None
                            for ev in events:
                                eh = ev.get("home_team", "").lower()
                                ea = ev.get("away_team", "").lower()
                                # Match if any search term appears in either team name
                                if any(t in eh or t in ea for t in search_terms):
                                    event_id = ev.get("id")
                                    break
                            if event_id:
                                markets = ",".join(PROP_MARKETS.get(target_sport, [])[:5])
                                pr = _req.get(
                                    f"{BASE_URL}/sports/{sport_key}/events/{event_id}/odds",
                                    params={"apiKey": API_KEY, "regions": "us",
                                            "markets": markets, "bookmakers": "fanduel",
                                            "oddsFormat": "american"},
                                    timeout=10
                                )
                                if pr.status_code == 200:
                                    from props_analyzer import analyze_props_no_filter as _ap
                                    event_data = pr.json()
                                    event_data["_sport_name"] = target_sport
                                    raw = _ap(event_data)
                                    # Add confidence + units fields expected by display code
                                    for p in raw:
                                        p.setdefault("confidence", min(95, max(50, int(p["edge"] * 700 + 50))))
                                        p.setdefault("units", round(min(1.5, p["edge"] * 6), 2))
                                        p.setdefault("projection", "")
                                    prop_picks.extend(raw)
                except Exception as _e:
                    print(f"[analyzegame] {target_sport} props error: {_e}")

            prop_picks = sorted(prop_picks, key=lambda x: x.get("edge", 0), reverse=True)
        except Exception:
            prop_picks = []

        return target_game, target_sport, team_picks, prop_picks

    try:
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(loop.run_in_executor(None, run), timeout=120.0)
    except asyncio.TimeoutError:
        await msg.edit(content="⏱️ Analysis timed out. Try again in a minute.")
        return
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)}")
        return

    game, sport, team_picks, prop_picks = result

    if game is None:
        await msg.edit(content=f"❌ No game found matching: **{teams}**")
        return

    home = game.get("home_team")
    away = game.get("away_team")

    # Build top 3: slot 1 = best team pick, slot 2 = best prop, slot 3 = next best of either
    best_team = team_picks[0] if team_picks else None
    best_prop = prop_picks[0] if prop_picks else None

    used = set()
    all_picks = []

    # Slot 1: best team market pick
    if best_team:
        all_picks.append(("team", best_team))
        used.add(id(best_team))

    # Slot 2: best player prop (guaranteed if available)
    if best_prop:
        all_picks.append(("prop", best_prop))
        used.add(id(best_prop))

    # Slot 3: next best from either pool
    remaining = []
    for p in team_picks[1:]:
        if id(p) not in used:
            remaining.append(("team", p))
    for p in prop_picks[1:]:
        if id(p) not in used:
            remaining.append(("prop", p))
    remaining.sort(key=lambda item: item[1].get("confidence", 0), reverse=True)

    all_picks = (all_picks + remaining)[:3]

    await msg.delete()

    if not all_picks:
        await ctx.send(f"📊 **{away} @ {home}**\n❌ No picks available for this game.")
        return

    sport_emoji = {"NHL": "🏒", "NBA": "🏀", "MLB": "⚾", "NFL": "🏈"}.get(sport, "🎯")
    embed = discord.Embed(
        title=f"{sport_emoji} {away} @ {home} — Top Picks",
        color=0x00ff00
    )

    for i, (kind, pick) in enumerate(all_picks, 1):
        if kind == "team":
            name = f"{i}. {pick['bet']} ({pick['odds']:+d})"
            value = f"Edge: {pick['edge']:.1%} | Conf: {pick['confidence']}% | {pick['units']:.2f}u | {pick.get('time_label', '')}"
        else:
            proj = f" | Proj: {pick['projection']}" if pick.get('projection') else ""
            name = f"{i}. 👤 {pick['bet']} ({pick['odds']:+d})"
            value = f"Edge: {pick['edge']:.1%} | Conf: {pick['confidence']}%{proj}"
        embed.add_field(name=name, value=value, inline=False)

    await ctx.send(embed=embed)

@bot.command(name='analyze')
async def analyze_now(ctx):
    """Run live analysis for TEAM MARKETS only (h2h, totals, spreads)"""
    import asyncio
    import threading
    from action_scraper import scrape_all_sports

    msg = await ctx.send("🔄 Running team market analysis... (please allow 1-2 minutes)")

    def run_analysis():
        all_games, _ = scrape_all_sports()
        now = datetime.now(timezone.utc)

        # Pre-warm stat cache in parallel (same as main.py) with short timeout
        from models.stats import get_pregame_prob
        import models.stats as stats_mod
        stats_mod.ESPN_TIMEOUT = 5  # tight per-call timeout
        threads = []
        seen = set()
        for sport, games in all_games.items():
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
        deadline = __import__("time").time() + 20
        for t in threads:
            t.join(timeout=max(0, deadline - __import__("time").time()))

        recommendations = []
        for sport, games in all_games.items():
            for game in games:
                tag_game_mode(game, sport, now)
                if game.get("_game_mode") == "excluded":
                    continue
                recommendations.extend(analyze_game(sport, game))
        return recommendations

    try:
        loop = asyncio.get_event_loop()
        recommendations = await asyncio.wait_for(
            loop.run_in_executor(None, run_analysis), timeout=120.0
        )
    except asyncio.TimeoutError:
        await msg.edit(content="⏱️ Analysis timed out. Try again in a minute.")
        return
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)}")
        return

    top_picks = sorted(
        [r for r in recommendations if r["game_mode"] in ("live", "upcoming") and r["odds"] >= -150],
        key=lambda x: x["confidence"],
        reverse=True,
    )

    # Exclude today's Pick of the Day
    from datetime import date
    today = date.today().isoformat()
    try:
        with open("picks_log.json", "r") as f:
            picks = json.load(f)
        todays_pick = next((p for p in picks if p["date"] == today), None)
        if todays_pick:
            top_picks = [p for p in top_picks if not (
                p["home"] == todays_pick["home"] and
                p["away"] == todays_pick["away"] and
                p["bet"] == todays_pick["bet"] and
                p.get("point") == todays_pick.get("point")
            )]
    except Exception:
        pass

    # Best pick per sport for diversity
    best_by_sport = {}
    for r in top_picks:
        if r["sport"] not in best_by_sport:
            best_by_sport[r["sport"]] = r
    diverse = sorted(best_by_sport.values(), key=lambda x: x["confidence"], reverse=True)
    used = {(p["home"], p["away"], p["bet"]) for p in diverse}

    # Try to add a spread pick if none in diverse set
    has_spread = any(p["market"] == "spreads" for p in diverse)
    if not has_spread:
        spread_pick = next((r for r in top_picks if r["market"] == "spreads" and (r["home"], r["away"], r["bet"]) not in used), None)
        if spread_pick:
            diverse.append(spread_pick)
            used.add((spread_pick["home"], spread_pick["away"], spread_pick["bet"]))

    # Fill remaining slots from any sport/market
    extras = [r for r in top_picks if (r["home"], r["away"], r["bet"]) not in used]
    top_picks = (diverse + extras)[:3]

    await msg.delete()

    if not top_picks:
        await ctx.send("📭 No team market picks available right now.")
        return

    embed = discord.Embed(title="🎯 Top 3 Team Market Picks", color=0x00ff00)
    for i, pick in enumerate(top_picks, 1):
        game = f"{pick['away']} @ {pick['home']}"
        value = (
            f"**{pick['bet']}** ({pick['odds']:+d}) — {pick['units']:.2f}u\n"
            f"Edge: {round(pick['edge'] * 100, 1)}% | Conf: {pick['confidence']}% | {pick['time_label']}"
        )
        embed.add_field(name=f"{i}. {game}", value=value, inline=False)

    await ctx.send(embed=embed)

@bot.command(name='props')
async def analyze_props(ctx):
    """Run live analysis for PLAYER PROPS only"""
    import asyncio
    from oddsapi_props import get_nhl_props_smart
    from config import MIN_EDGE

    msg = await ctx.send("🔄 Running player props analysis...")

    def run_props_analysis():
        from action_scraper import scrape_all_sports
        from nhl_props import analyze_nhl_player_prop_simple
        from datetime import datetime, timezone
        
        all_games, _ = scrape_all_sports()
        now = datetime.now(timezone.utc)
        all_props = get_nhl_props_smart()
        candidates = []
        
        for sport, games in all_games.items():
            if sport != "NHL":
                continue
                
            for game in games:
                tag_game_mode(game, sport, now)
                if game.get("_game_mode") not in ("upcoming", "live"):
                    continue
                    
                home = game.get("home_team", "")
                away = game.get("away_team", "")
                
                # Filter props for this game
                game_props = []
                for prop in all_props:
                    prop_home = prop["home_team"].replace("é", "e")
                    prop_away = prop["away_team"].replace("é", "e")
                    game_home = home.replace("é", "e")
                    game_away = away.replace("é", "e")
                    
                    if (prop_home == game_home and prop_away == game_away) or \
                       (prop_home == game_away and prop_away == game_home):
                        game_props.append(prop)
                
                # Analyze each prop
                for prop in game_props:
                    player = prop["player"]
                    prop_type = prop["prop_type"]
                    line = prop["line"]
                    odds = prop["odds"]
                    
                    # Try both teams
                    best_analysis = None
                    for team, opponent in [(home, away), (away, home)]:
                        try:
                            analysis = analyze_nhl_player_prop_simple(player, team, prop_type, line, odds, opponent)
                            if analysis and analysis.get("edge", 0) > (best_analysis.get("edge", 0) if best_analysis else -1):
                                best_analysis = analysis
                        except Exception:
                            continue
                    
                    if best_analysis and best_analysis.get("edge", 0) > MIN_EDGE:
                        confidence = min(95, max(50, int(best_analysis["edge"] * 300 + 60)))
                        units = min(1.5, best_analysis["edge"] * 6)
                        
                        candidates.append({
                            "sport": "NHL",
                            "home": home,
                            "away": away,
                            "bet": f"{player} {prop_type.title()} Over {line}",
                            "odds": odds,
                            "edge": best_analysis["edge"],
                            "confidence": confidence,
                            "units": round(units, 2),
                            "player": player,
                            "projection": best_analysis["projection"],
                        })
        
        return candidates

    try:
        loop = asyncio.get_event_loop()
        recommendations = await asyncio.wait_for(
            loop.run_in_executor(None, run_props_analysis), timeout=45.0
        )
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)}")
        return

    top_picks = sorted(recommendations, key=lambda x: x["confidence"], reverse=True)[:5]

    await msg.delete()

    if not top_picks:
        await ctx.send("📭 No player props available right now.")
        return

    embed = discord.Embed(title="🏒 Top 5 Player Props", color=0xff6600)
    for i, pick in enumerate(top_picks, 1):
        game = f"{pick['away']} @ {pick['home']}"
        value = (
            f"**{pick['bet']}** ({pick['odds']:+d}) — {pick['units']:.2f}u\n"
            f"Proj: {pick['projection']} | Edge: {round(pick['edge'] * 100, 1)}%"
        )
        embed.add_field(name=f"{i}. {game}", value=value, inline=False)

    await ctx.send(embed=embed)
    import asyncio
    from action_scraper import scrape_all_sports

    msg = await ctx.send("🔄 Running analysis... (~30 seconds)")

    def run_analysis():
        all_games, _ = scrape_all_sports()
        now = datetime.now(timezone.utc)
        recommendations = []
        for sport, games in all_games.items():
            for game in games:
                tag_game_mode(game, sport, now)
                if game.get("_game_mode") == "excluded":
                    continue
                recommendations.extend(analyze_game(sport, game))
        return recommendations

    try:
        loop = asyncio.get_event_loop()
        recommendations = await asyncio.wait_for(
            loop.run_in_executor(None, run_analysis), timeout=120.0
        )
    except asyncio.TimeoutError:
        await msg.edit(content="⏱️ Analysis timed out. Try again in a minute.")
        return
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)}")
        return

    top_picks = sorted(
        [r for r in recommendations if r["game_mode"] in ("live", "upcoming") and r["odds"] >= -150],
        key=lambda x: x["confidence"],
        reverse=True,
    )
    
    # Exclude today's Pick of the Day
    from datetime import date
    today = date.today().isoformat()
    try:
        with open("picks_log.json", "r") as f:
            picks = json.load(f)
        todays_pick = next((p for p in picks if p["date"] == today), None)
        if todays_pick:
            # Filter out the exact same pick (same teams, same bet, same point)
            top_picks = [p for p in top_picks if not (
                p["home"] == todays_pick["home"] and 
                p["away"] == todays_pick["away"] and
                p["bet"] == todays_pick["bet"] and
                p.get("point") == todays_pick.get("point")
            )]
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # No picks log yet
    
    top_picks = top_picks[:3]

    await msg.delete()

    if not top_picks:
        await ctx.send("📭 No picks available right now.")
        return

    embed = discord.Embed(title="🎯 Top 3 Picks Right Now", color=0x00ff00)
    for i, pick in enumerate(top_picks, 1):
        game = f"{pick['away']} @ {pick['home']}"
        
        # Format differently for player props
        if pick.get("player"):
            bet_display = f"**{pick['bet']}** ({pick['odds']:+d})"
            extra_info = f"Proj: {pick.get('projection', 'N/A')} | {pick['units']:.2f}u"
        else:
            bet_display = f"**{pick['bet']}** ({pick['odds']:+d}) — {pick['units']:.2f}u"
            extra_info = f"Edge: {round(pick['edge'] * 100, 1)}% | Conf: {pick['confidence']}% | {pick['time_label']}"
        
        embed.add_field(
            name=f"{i}. {game}", 
            value=f"{bet_display}\n{extra_info}", 
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command(name='record')
async def get_record(ctx):
    """Show win/loss record and stats for Pick of the Day"""
    resolve_picks()
    rec = record()
    win_streak = streak()
    
    embed = discord.Embed(title="📊 Pick of the Day Record", color=0x00ff00 if rec['profit'] > 0 else 0xff0000)
    embed.add_field(name="Record", value=rec['record'], inline=True)
    embed.add_field(name="Total Profit", value=f"{rec['profit']:+.2f}u", inline=True)
    embed.add_field(name="Win Streak", value=f"🔥 {win_streak}" if win_streak >= 3 else str(win_streak), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='stats')
async def get_stats(ctx):
    """Show detailed performance statistics for Pick of the Day"""
    resolve_picks()
    
    with open("picks_log.json", "r") as f:
        picks = json.load(f)
    
    if not picks:
        await ctx.send("📭 No picks logged yet.")
        return
    
    resolved = [p for p in picks if p.get("result") in ("win", "loss")]
    if not resolved:
        await ctx.send("📊 No resolved picks yet.")
        return
    
    wins = sum(1 for p in resolved if p["result"] == "win")
    losses = len(resolved) - wins
    total_profit = sum(p.get("profit", 0) for p in resolved)
    win_rate = wins / len(resolved) * 100
    
    # Market breakdown
    totals_picks = [p for p in resolved if p.get("market") == "totals"]
    totals_wins = sum(1 for p in totals_picks if p["result"] == "win")
    
    embed = discord.Embed(title="📊 Pick of the Day Statistics", color=0x0099ff)
    embed.add_field(name="Overall", value=f"{wins}-{losses} ({win_rate:.1f}%)\n{total_profit:+.2f}u profit", inline=True)
    
    if totals_picks:
        totals_wr = totals_wins / len(totals_picks) * 100
        embed.add_field(name="Totals", value=f"{totals_wins}-{len(totals_picks)-totals_wins} ({totals_wr:.1f}%)", inline=True)
    
    # Recent form (last 5)
    recent = resolved[-5:]
    recent_results = "".join("✅" if p["result"] == "win" else "❌" for p in recent)
    embed.add_field(name="Recent Form", value=recent_results or "None", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='kalshi')
async def check_kalshi(ctx):
    """Check Kalshi prediction markets for sports arbitrage"""
    try:
        from kalshi_api import get_kalshi_sports_summary, find_kalshi_arbitrage
        
        msg = await ctx.send("🔍 Checking Kalshi markets...")
        
        # Get summary
        summary = get_kalshi_sports_summary()
        
        # Find arbitrage opportunities
        arb_ops = find_kalshi_arbitrage()
        
        embed = discord.Embed(title="📊 Kalshi Sports Markets", color=0x9932cc)
        
        # Summary
        embed.add_field(
            name="Market Summary",
            value=f"Events: {summary['total_events']}\nMarkets: {summary['total_markets']}",
            inline=True
        )
        
        # By sport
        if summary['by_sport']:
            sports_text = "\n".join([f"{sport}: {count}" for sport, count in summary['by_sport'].items()])
            embed.add_field(name="By Sport", value=sports_text, inline=True)
        
        # Arbitrage opportunities
        if arb_ops:
            arb_text = ""
            for opp in arb_ops[:3]:
                arb_text += f"**{opp['event']}**\n{opp['market']}\nEdge: {opp['edge']:.1%}\n\n"
            embed.add_field(name="🎯 Arbitrage Opportunities", value=arb_text or "None found", inline=False)
        else:
            embed.add_field(name="🎯 Arbitrage Opportunities", value="None found", inline=False)
        
        await msg.edit(content="", embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Kalshi check failed: {str(e)}")

@bot.command(name='clv')
async def check_clv(ctx):
    """Check Closing Line Value - are we beating the market?"""
    try:
        from closing_line_value import get_clv_summary
        
        clv_data = get_clv_summary()
        
        if clv_data["total_picks"] == 0:
            await ctx.send("📊 No CLV data yet - need resolved picks to calculate.")
            return
        
        avg_clv = clv_data["avg_clv"]
        positive_rate = clv_data["positive_clv_rate"]
        
        embed = discord.Embed(title="📈 Closing Line Value Analysis", color=0x00ff00 if avg_clv > 0 else 0xff0000)
        
        embed.add_field(
            name="Average CLV",
            value=f"{avg_clv:+.2%}",
            inline=True
        )
        
        embed.add_field(
            name="Positive CLV Rate", 
            value=f"{positive_rate:.1%}",
            inline=True
        )
        
        embed.add_field(
            name="Sample Size",
            value=f"{clv_data['total_picks']} picks",
            inline=True
        )
        
        # Interpretation
        if avg_clv > 0.02:
            interpretation = "🔥 Excellent - beating closing lines!"
        elif avg_clv > 0:
            interpretation = "✅ Good - positive CLV indicates skill"
        elif avg_clv > -0.02:
            interpretation = "⚠️ Neutral - roughly market efficiency"
        else:
            interpretation = "❌ Poor - losing to closing lines"
        
        embed.add_field(name="Assessment", value=interpretation, inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ CLV check failed: {str(e)}")

@bot.command(name='health')
async def check_health(ctx):
    """Check API health status"""
    from api_health import check_critical_apis
    
    success, errors = check_critical_apis()
    
    if success:
        embed = discord.Embed(title="🟢 API Health Status", description="All systems operational", color=0x00ff00)
    else:
        embed = discord.Embed(title="🔴 API Health Status", description="Issues detected", color=0xff0000)
        for error in errors:
            embed.add_field(name="Error", value=error, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='recent')
async def get_recent(ctx):
    """Show last 10 Pick of the Day results"""
    resolve_picks()
    
    with open("picks_log.json", "r") as f:
        picks = json.load(f)
    
    if not picks:
        await ctx.send("📭 No picks logged yet.")
        return
    
    recent_picks = picks[-10:]
    
    embed = discord.Embed(title="📋 Recent Pick of the Day Results", color=0x9932cc)
    
    for pick in reversed(recent_picks):  # Most recent first
        game = f"{pick['away']} @ {pick['home']}"
        bet_info = f"{pick['bet']} ({pick['odds']:+d}) — {pick['units']:.2f}u"
        
        if pick.get("result") == "win":
            result = f"✅ +{pick.get('profit', 0):.2f}u"
        elif pick.get("result") == "loss":
            result = f"❌ {pick.get('profit', 0):.2f}u"
        else:
            result = "⏳ Pending"
        
        embed.add_field(
            name=f"{pick['date']} - {game}",
            value=f"{bet_info}\n{result}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='profit')
async def get_profit(ctx):
    """Show total units profit/loss"""
    profit = total_profit()
    rec = record()
    
    if profit > 0:
        msg = f"💰 **Total Profit: +{profit:.2f} units**\n\nRecord: {rec['record']}"
    elif profit < 0:
        msg = f"📉 **Total Loss: {profit:.2f} units**\n\nRecord: {rec['record']}"
    else:
        msg = f"➖ **Break Even: 0.00 units**\n\nRecord: {rec['record']}"
    
    await ctx.send(msg)

@bot.command(name='teamstats')
async def get_team_stats(ctx, sport: str, *, team_name: str):
    """Get recent form for a team (e.g., !teamstats NHL Buffalo Sabres)"""
    try:
        # Normalize sport input
        sport = sport.upper()
        valid_sports = ["NHL", "NBA", "MLB", "NFL"]
        
        if sport not in valid_sports:
            await ctx.send(f"❌ Invalid sport. Use: {', '.join(valid_sports)}\n**Example:** `!teamstats NHL Buffalo Sabres`")
            return
        
        form = get_recent_form(sport, team_name, 10)
        
        if form['record'] == "0-0":
            await ctx.send(f"❌ No recent data found for **{team_name}** ({sport})")
            return
        
        embed = discord.Embed(title=f"📈 {team_name} ({sport}) - Last 10 Games", color=0x0099ff)
        embed.add_field(name="Record", value=form['record'], inline=True)
        
        if sport in ["NHL", "NBA", "MLB"]:
            embed.add_field(name="Avg Scored", value=f"{form['avg_scored']:.2f}", inline=True)
            embed.add_field(name="Avg Allowed", value=f"{form['avg_allowed']:.2f}", inline=True)
        elif sport == "NFL":
            embed.add_field(name="Avg Points Scored", value=f"{form['avg_scored']:.1f}", inline=True)
            embed.add_field(name="Avg Points Allowed", value=f"{form['avg_allowed']:.1f}", inline=True)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error fetching stats: {str(e)}")

@bot.command(name='prop')
async def get_prop(ctx, player_name: str, *, stat: str = "total bases"):
    """Get player prop analysis (e.g., !prop Acuna total bases)"""
    try:
        from player_props import find_player_prop
        
        await ctx.send(f"🔍 Searching for {player_name} {stat} prop...")
        
        # Map stat names to API market keys
        stat_map = {
            "total bases": "batter_total_bases",
            "hits": "batter_hits",
            "home runs": "batter_home_runs",
            "rbis": "batter_rbis",
            "runs": "batter_runs_scored",
            "strikeouts": "batter_strikeouts"
        }
        
        market = stat_map.get(stat.lower(), "batter_total_bases")
        result = find_player_prop(player_name, market=market)
        
        if not result:
            await ctx.send(f"❌ No {stat} prop found for {player_name}. Try MLB players only.")
            return
        
        embed = discord.Embed(title=f"⚾ {result['player']}", color=0x0099ff)
        embed.add_field(name="Game", value=result['game'], inline=False)
        embed.add_field(name="Prop", value=f"Over {result['line']} {stat}", inline=True)
        embed.add_field(name="Odds", value=f"{result['odds']:+d}", inline=True)
        embed.add_field(name="Implied Prob", value=f"{result['implied_prob']:.1f}%", inline=True)
        embed.add_field(name="Book", value=result['bookmaker'], inline=True)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name='dean')
async def dean(ctx):
    await ctx.send("Deaner Beaner")

@bot.command(name='commands')
async def commands_list(ctx):
    """Show available commands"""
    help_text = """
**🤖 Dino Bot Commands**

**📊 Analysis & Picks:**
`!pick` - Get today's official Pick of the Day (4PM automation)
`!analyze` - Live team market analysis (h2h, totals, spreads)
`!props` - Live player props analysis (goals, assists, shots)

**📈 Performance Tracking:**
`!record` - Pick of the Day win/loss record and profit
`!stats` - Detailed Pick of the Day statistics and trends
`!recent` - Last 10 Pick of the Day results
`!profit` - Total units profit/loss summary

**🔍 Research Tools:**
`!teamstats <sport> <team>` - Team recent form (e.g., `!teamstats NHL Boston Bruins`)
`!health` - Check API status and system health
`!kalshi` - Check Kalshi prediction markets for arbitrage
`!clv` - Closing Line Value analysis (are we beating the market?)

**Examples:**
`!analyze` - Get live top picks with player props
`!teamstats NHL Buffalo Sabres` - Sabres last 10 games
`!health` - System status check
    """
    await ctx.send(help_text)

# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ DISCORD_BOT_TOKEN not found in .env")
        print("   Add: DISCORD_BOT_TOKEN=your_token_here")
        exit(1)
    
    print("Starting Discord bot...")
    bot.run(token)
