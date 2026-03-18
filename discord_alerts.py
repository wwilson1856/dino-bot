"""
Sends the top pick for tomorrow to Discord via webhook.
Called once per poll cycle when a new best pick is found.
"""
import requests
import random
from config import DISCORD_WEBHOOK_URL, UNIT_SIZE
from picks_log import _load, loss_streak


def _odds_str(price: int) -> str:
    return f"+{price}" if price > 0 else str(price)


DINO_QUOTES = [
    "Just settled a truck case for seven figures. This pick is even more of a lock.",
    "I've taken on Freightliner, Peterbilt, and their whole legal teams. This line doesn't scare me.",
    "Eighteen-wheelers, bad odds — I beat both for a living. Ride with me.",
    "My clients walk away with checks. So will you.",
    "I don't take cases I can't win. I don't bet picks I don't believe in.",
    "Another truck driver tried to lowball us in court today. We don't accept bad value — and neither should you.",
    "Won a wrongful death case against a trucking company this morning. Feeling good. Lock it in.",
    "You think this line is scary? Try cross-examining a fleet safety director. This is easy money.",
    "Morgantown's finest is on this one. Don't overthink it.",
    "I argue for a living and I'm telling you — this pick is airtight.",
    "Semi trucks, insurance companies, bad spreads — I've beaten all three.",
    "The defense never sees it coming. Neither will the books.",
]


def _totals_trend(sport: str, team_name: str, line: float, limit: int = 10) -> str:
    """Return a summary of how often a team's games have gone over a given line."""
    from models.stats import get_team_id, _fetch_team_schedule
    espn_sport = {"NHL": "hockey", "NBA": "basketball", "MLB": "baseball", "NFL": "football"}.get(sport, sport.lower())
    espn_league = sport.lower()
    team_id = get_team_id(espn_sport, espn_league, team_name)
    if not team_id:
        return ""
    games = _fetch_team_schedule(sport, team_id, limit)
    if not games:
        return ""
    overs = sum(1 for g in games if (g["score"] + g["opp_score"]) > line)
    unders = sum(1 for g in games if (g["score"] + g["opp_score"]) < line)
    pushes = len(games) - overs - unders
    push_str = f" ({pushes}P)" if pushes else ""
    return f"{team_name}: {overs}O-{unders}U{push_str} L{len(games)}"


def _build_reasoning(pick: dict) -> str:
    """Generate long-form reasoning for the pick in Dino's voice."""
    market = pick.get("market", "")
    bet = pick.get("bet", "")
    edge = pick.get("edge", 0)
    model_prob = round(pick.get("model_prob", 0) * 100, 1)
    implied_prob = round(pick.get("implied_prob", 0) * 100, 1)
    model_source = pick.get("model_source", "line")
    sharp_source = pick.get("sharp_source", "Consensus")
    away = pick.get("away", "")
    home = pick.get("home", "")
    sport = pick.get("sport", "")
    point = pick.get("point")

    if market == "totals":
        direction = "over" if "over" in bet.lower() else "under"
        opposite = "under" if direction == "over" else "over"
        line_str = f"{point}" if point else ""
        stat_line = (
            f"I've spent 26 years reading numbers that other people miss — "
            f"insurance adjusters, fleet safety reports, accident reconstructions. "
            f"You learn to spot when something doesn't add up. "
            f"This line doesn't add up.\n\n"
            f"The books have this {direction} {line_str} at {implied_prob}%. "
            f"My model, built on both teams' offensive and defensive ratings this season, "
            f"puts it at {model_prob}%. That's a {round(edge*100,1)}-point gap. "
            f"In my courtroom, that's called evidence.\n\n"
        )
        if model_source == "stat_model":
            away_trend = _totals_trend(sport, away, point or 0)
            home_trend = _totals_trend(sport, home, point or 0)
            trends = "\n".join(filter(None, [away_trend, home_trend]))
            trend_block = f"\n\n📊 Last 10 games O/U {point}:\n{trends}" if trends else ""
            stat_line += (
                f"Both {away} and {home} have been playing at a pace that says this game goes {direction} {line_str}. "
                f"The {opposite} bettors are going to be watching the third period wishing they'd listened to Dino."
                f"{trend_block}"
            )
        else:
            stat_line += (
                f"The sharp money from {sharp_source} is quietly leaning {direction}. "
                f"I follow the sharp money. Always have."
            )
        return stat_line

    elif market == "h2h":
        team = bet.replace(" ML", "")
        return (
            f"I don't take cases I can't win. I don't bet picks I don't believe in. "
            f"This is one I believe in.\n\n"
            f"My model gives {team} a {model_prob}% chance to win this game. "
            f"{sharp_source} has them priced at {implied_prob}%. "
            f"That {round(edge*100,1)}-point gap is where the money is made — "
            f"the books are undervaluing {team} and I'm going to take advantage of it.\n\n"
            f"{'The efficiency numbers back this up. This is not a gut call — it is a calculated position.' if model_source == 'stat_model' else f'The sharp money from {sharp_source} agrees with me. When the sharps and my model point the same direction, I bet with confidence.'}"
        )

    elif market == "spreads":
        return (
            f"Covering a spread is like winning on summary judgment — "
            f"you need the facts clearly on your side, and here they are.\n\n"
            f"My model says {model_prob}% chance to cover. The book says {implied_prob}%. "
            f"A {round(edge*100,1)}-point edge on a spread is significant — "
            f"I don't touch spreads unless the number is this clean.\n\n"
            f"{'The stat model is driving this one. Offensive and defensive ratings both point the same direction.' if model_source == 'stat_model' else f'Sharp action from {sharp_source} is what caught my eye here.'}"
        )

    return f"Model: {model_prob}% | Book: {implied_prob}% | Edge: {round(edge*100,1)}%"


def send_top_pick(pick: dict, win_streak: int = 0):
    """Post the single best pick to Discord."""
    if not DISCORD_WEBHOOK_URL:
        return

    if loss_streak() >= 5:
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": "In the words of Connor Stewart, it's all gone."}, timeout=10).raise_for_status()
        except Exception as e:
            print(f"[discord] Failed to send: {e}")
        return

    if random.random() < 1/20:
        henry_msg = (
            "# 😔 No Pick Today\n\n"
            "I've been sitting here staring at these lines for an hour and I just... I can't do it.\n\n"
            "I keep thinking about Henry Dean. Good man. One of the best I know. "
            "And when something's weighing on you like that — really weighing on you — "
            "you can't just pretend everything's fine and start throwing out winners.\n\n"
            "I've spent 26 years fighting for people who got hurt. Trucks, semis, negligent carriers — "
            "I've seen what happens when people don't look out for each other. "
            "Henry Dean deserves better than me half-assing a pick while I'm worried sick about him.\n\n"
            "*No pick today. Thinking of you, Henry.*"
        )
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": henry_msg}, timeout=10).raise_for_status()
        except Exception as e:
            print(f"[discord] Failed to send: {e}")
        return

    home = pick.get("home", "Home")
    away = pick.get("away", "Away")
    bet = pick.get("bet", "")
    odds = _odds_str(pick["odds"])
    edge = pick["edge"]
    conf = pick["confidence"]
    units = pick["units"]
    dollar_amount = round(units * UNIT_SIZE, 2)
    time_label = pick.get("time_label", "")
    book = pick.get("best_book", "FanDuel")
    quote = random.choice(DINO_QUOTES)
    reasoning = _build_reasoning(pick)

    # Format start time in ET
    start_time_str = ""
    commence_time = pick.get("commence_time") or pick.get("_commence_time")
    if commence_time:
        try:
            from zoneinfo import ZoneInfo
            from datetime import datetime
            if isinstance(commence_time, str):
                commence_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            et = commence_time.astimezone(ZoneInfo("America/New_York"))
            start_time_str = f" · {et.strftime('%-I:%M %p ET')}"
        except Exception:
            pass

    resolved = [p for p in _load() if p["result"] in ("win", "loss")]

    def record(picks):
        w = sum(1 for p in picks if p["result"] == "win")
        return f"{w}-{len(picks)-w}"

    last5 = resolved[-5:] if len(resolved) >= 5 else None
    last10 = resolved[-10:] if len(resolved) >= 10 else None
    sport_picks = [p for p in resolved if p["sport"] == pick["sport"]]

    stats_lines = []
    if last5:
        stats_lines.append(f"L5: {record(last5)}")
    if last10:
        stats_lines.append(f"L10: {record(last10)}")
    if sport_picks:
        stats_lines.append(f"{pick['sport']}: {record(sport_picks)}")
    stats_line = f"\n📊 {' | '.join(stats_lines)}" if stats_lines else ""

    streak_line = f"\n🔥 **{win_streak} IN A ROW. Dino is locked in.**" if win_streak >= 3 else ""

    message = (
        f"-# *\"{quote}\"*\n"
        f"# 🎯 PICK OF THE DAY\n"
        f"### {away} @ {home}\n"
        f"# {bet} — {odds} — {units}u\n\n"
        f"{reasoning}\n\n"
        f"Edge: {edge:.1%} | Conf: {conf}%\n"
        f"{book}{start_time_str}"
        f"{streak_line}"
        f"{stats_line}"
    )

    try:
        resp = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"[discord] Sent: {away} @ {home} — {bet}")
    except Exception as e:
        print(f"[discord] Failed to send: {e}")


DINO_WIN_QUOTES = [
    "Just like in court — when you've got the facts on your side, you win. Cash it.",
    "I've never lost a case I believed in. Tonight's no different.",
    "Another W. The books are starting to feel like the insurance companies I sue.",
    "Morgantown's finest doesn't miss. Get that money.",
    "I told you it was airtight. It always is.",
    "Semi trucks, bad spreads, and now this line — all three go down the same way.",
    "The defense rests. We win again.",
]


def send_result_notification(pick: dict):
    """Send a win/loss result notification to Discord."""
    if not DISCORD_WEBHOOK_URL:
        return

    result = pick.get("result")
    profit = pick.get("profit", 0)
    bet = pick.get("bet", "")
    odds = _odds_str(pick["odds"])
    units = pick["units"]

    if result == "win":
        quote = random.choice(DINO_WIN_QUOTES)
        message = (
            f"-# *\"{quote}\"*\n"
            f"# ✅ WINNER — {bet} {odds}\n"
            f"**+{profit:.2f}u** on {units}u bet\n"
            f"{pick['away']} @ {pick['home']}"
        )
    elif result == "loss":
        message = (
            f"# ❌ LOSS — {bet} {odds}\n"
            f"**{profit:.2f}u** on {units}u bet\n"
            f"{pick['away']} @ {pick['home']}\n"
            f"-# *We'll get it back. We always do.*"
        )
    else:  # push
        message = (
            f"# ➖ PUSH — {bet} {odds}\n"
            f"Units returned. {pick['away']} @ {pick['home']}"
        )

    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10).raise_for_status()
        print(f"[discord] Result sent: {result}")
    except Exception as e:
        print(f"[discord] Failed to send result: {e}")


def send_daily_card(picks: list[dict]):
    """Post all tomorrow picks as a single daily card to Discord."""
    if not DISCORD_WEBHOOK_URL or not picks:
        return

    lines = ["📋 **TOMORROW'S CARD**\n```"]
    for i, p in enumerate(picks, 1):
        odds_s = _odds_str(p["odds"])
        dollar_amount = round(p["units"] * UNIT_SIZE, 2)
        lines.append(
            f"{i}. {p['sport']} | {p['away']} @ {p['home']}\n"
            f"   {p['bet']} {odds_s} | {p['edge']:.1%} edge | "
            f"{p['confidence']}% conf | {p['units']}u (${dollar_amount})"
        )
    lines.append("```")

    try:
        resp = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": "\n".join(lines)},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"[discord] Sent daily card ({len(picks)} picks)")
    except Exception as e:
        print(f"[discord] Failed to send card: {e}")
