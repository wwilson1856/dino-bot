"""
Pre-game win probability models using real team stats from ESPN.
Fetches offensive/defensive ratings and computes matchup-based probabilities.
Results are cached per session to avoid hammering the API.
"""
import math
import requests
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
ESPN_CORE = "https://sports.core.api.espn.com/v2/sports"
ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports"

# Tight timeout — if ESPN is slow, skip stat model rather than block the dashboard
ESPN_TIMEOUT = 10

# Cache invalidates after this many seconds (1 hour - stats don't change mid-day)
_cache_time = {}
_cache_data = {}
CACHE_TTL = 3600
_current_season = None


def _get_current_season(sport: str = "hockey", league: str = "nhl") -> int:
    """Get the current season year from ESPN."""
    global _current_season
    if _current_season:
        return _current_season
    
    try:
        url = f"{ESPN_SITE}/{sport}/{league}"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        leagues = r.json().get("sports", [{}])[0].get("leagues", [{}])
        if leagues:
            season = leagues[0].get("season", {}).get("year", 2026)
            _current_season = season
            return season
    except Exception:
        pass
    
    return 2026  # Fallback


def _cached(key: str, fetch_fn):
    now = datetime.now().timestamp()
    if key in _cache_data and now - _cache_time.get(key, 0) < CACHE_TTL:
        return _cache_data[key]
    try:
        result = fetch_fn()
    except Exception:
        result = None
    # Only cache non-None, non-empty results so we retry on failure
    if result is not None and result != {} and result != []:
        _cache_data[key] = result
        _cache_time[key] = now
    return result


# ---------------------------------------------------------------------------
# Team ID lookups
# ---------------------------------------------------------------------------

def _fetch_team_ids(sport: str, league: str) -> dict:
    """Returns {display_name_lower: espn_team_id}"""
    url = f"{ESPN_SITE}/{sport}/{league}/teams?limit=50"
    try:
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        teams = r.json().get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        result = {}
        for t in teams:
            team = t.get("team", {})
            tid = team.get("id", "")
            name = team.get("displayName", "")
            short = team.get("shortDisplayName", "")
            location = team.get("location", "")
            nickname = team.get("name", "")
            # Index by multiple name variants for fuzzy matching
            for n in [name, short, location, nickname, team.get("abbreviation", "")]:
                if n:
                    result[n.lower()] = tid
        return result
    except Exception:
        return {}


def get_team_id(sport: str, league: str, team_name: str) -> str | None:
    key = f"team_ids_{sport}_{league}"
    ids = _cached(key, lambda: _fetch_team_ids(sport, league))
    name_lower = team_name.lower()
    # Exact match first
    if name_lower in ids:
        return ids[name_lower]
    # Partial match - check if any key is contained in the team name or vice versa
    for k, v in ids.items():
        if k in name_lower or name_lower in k:
            return v
    # Last word match (team nickname)
    last_word = name_lower.split()[-1] if name_lower else ""
    for k, v in ids.items():
        if k == last_word or k.split()[-1] == last_word:
            return v
    return None


# ---------------------------------------------------------------------------
# NBA stats
# ---------------------------------------------------------------------------

def _fetch_nba_team_stats(team_id: str) -> dict:
    """Returns full team stats including off/def ratings, pace, home/away splits."""
    try:
        url = f"{ESPN_CORE}/basketball/leagues/nba/seasons/2026/types/2/teams/{team_id}/statistics"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        cats = r.json().get("splits", {}).get("categories", [])
        stats = {}
        for cat in cats:
            for s in cat.get("stats", []):
                stats[s["name"]] = s.get("value", 0)

        url2 = f"{ESPN_CORE}/basketball/leagues/nba/seasons/2026/types/2/teams/{team_id}/record"
        r2 = requests.get(url2, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r2.raise_for_status()
        for item in r2.json().get("items", []):
            if item.get("type") == "total":
                for s in item.get("stats", []):
                    stats[s["name"]] = s.get("value", 0)
                break

        ppg = stats.get("avgPoints", 110.0)
        opp_ppg = stats.get("avgPointsAgainst", 110.0)
        possessions = stats.get("avgEstimatedPossessions", 100.0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 1)
        games = wins + losses or 1

        off_rtg = (ppg / possessions) * 100 if possessions > 0 else 110.0
        def_rtg = (opp_ppg / possessions) * 100 if possessions > 0 else 110.0

        return {
            "off_rtg": off_rtg,
            "def_rtg": def_rtg,
            "pace": possessions,
            "ppg": ppg,
            "opp_ppg": opp_ppg,
            "win_pct": wins / games,
            "games": games,
        }
    except Exception:
        return {"off_rtg": 110.0, "def_rtg": 110.0, "pace": 100.0,
                "ppg": 110.0, "opp_ppg": 110.0, "win_pct": 0.5, "games": 0}


def _fetch_nba_home_away_stats(team_id: str) -> dict:
    """Fetch home and away PPG/opp-PPG splits from team schedule."""
    try:
        url = f"{ESPN_SITE}/basketball/nba/teams/{team_id}/schedule?season=2026"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        events = r.json().get("events", [])
        home_pts, home_opp, home_n = 0, 0, 0
        away_pts, away_opp, away_n = 0, 0, 0
        for e in events:
            comp = e.get("competitions", [{}])[0]
            if not comp.get("status", {}).get("type", {}).get("completed"):
                continue
            competitors = comp.get("competitors", [])
            team = next((c for c in competitors if c.get("id") == team_id), None)
            opp  = next((c for c in competitors if c.get("id") != team_id), None)
            if not team or not opp:
                continue
            try:
                gf = int(float(team.get("score", 0)))
                ga = int(float(opp.get("score", 0)))
            except Exception:
                continue
            if team.get("homeAway") == "home":
                home_pts += gf; home_opp += ga; home_n += 1
            else:
                away_pts += gf; away_opp += ga; away_n += 1
        return {
            "home_ppg":     home_pts / home_n if home_n else None,
            "home_opp_ppg": home_opp / home_n if home_n else None,
            "away_ppg":     away_pts / away_n if away_n else None,
            "away_opp_ppg": away_opp / away_n if away_n else None,
        }
    except Exception:
        return {}


def _fetch_nba_last_n(team_id: str, n: int = 10) -> dict:
    """Recent form: avg pts scored/allowed over last N completed games."""
    try:
        url = f"{ESPN_SITE}/basketball/nba/teams/{team_id}/schedule?season=2026"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        events = r.json().get("events", [])
        results = []
        for e in events:
            comp = e.get("competitions", [{}])[0]
            if not comp.get("status", {}).get("type", {}).get("completed"):
                continue
            competitors = comp.get("competitors", [])
            team = next((c for c in competitors if c.get("id") == team_id), None)
            opp  = next((c for c in competitors if c.get("id") != team_id), None)
            if not team or not opp:
                continue
            try:
                results.append({
                    "pts": int(float(team.get("score", 0))),
                    "opp": int(float(opp.get("score", 0))),
                    "date": e.get("date", ""),
                })
            except Exception:
                continue
        recent = results[-n:] if results else []
        if not recent:
            return {}
        return {
            "avg_pts":     round(sum(g["pts"] for g in recent) / len(recent), 1),
            "avg_opp_pts": round(sum(g["opp"] for g in recent) / len(recent), 1),
            "last_date":   recent[-1]["date"] if recent else None,
        }
    except Exception:
        return {}


def _nba_is_back_to_back(team_id: str, game_date: str) -> bool:
    """True if team played yesterday."""
    try:
        from datetime import timedelta
        game_dt = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
        yesterday = (game_dt - timedelta(days=1)).date()
        recent = _fetch_nba_last_n(team_id, 5)
        last = recent.get("last_date")
        if not last:
            return False
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return last_dt.date() == yesterday
    except Exception:
        return False


def nba_pregame_prob(home_name: str, away_name: str) -> tuple[float, float, float] | None:
    """
    Full NBA pre-game model matching NHL model depth.
    Factors: off/def ratings, pace, home/away splits, recent form (last 10),
             back-to-back penalty, rest-days advantage.
    Returns (home_win_prob, away_win_prob, proj_total).
    """
    home_id = get_team_id("basketball", "nba", home_name)
    away_id = get_team_id("basketball", "nba", away_name)
    if not home_id or not away_id:
        return None

    home_stats = _cached(f"nba_{home_id}", lambda: _fetch_nba_team_stats(home_id))
    away_stats = _cached(f"nba_{away_id}", lambda: _fetch_nba_team_stats(away_id))

    if home_stats["games"] < 5 or away_stats["games"] < 5:
        return None

    # --- Home/away splits (same pattern as NHL) ---
    home_splits = _cached(f"nba_splits_{home_id}", lambda: _fetch_nba_home_away_stats(home_id))
    away_splits = _cached(f"nba_splits_{away_id}", lambda: _fetch_nba_home_away_stats(away_id))

    league_avg_pts = 113.0
    home_ppg     = home_splits.get("home_ppg")     or home_stats["ppg"]
    home_opp_ppg = home_splits.get("home_opp_ppg") or home_stats["opp_ppg"]
    away_ppg     = away_splits.get("away_ppg")     or away_stats["ppg"]
    away_opp_ppg = away_splits.get("away_opp_ppg") or away_stats["opp_ppg"]

    # Attack/defense strength relative to league average
    home_attack  = home_ppg     / league_avg_pts
    home_defense = home_opp_ppg / league_avg_pts
    away_attack  = away_ppg     / league_avg_pts
    away_defense = away_opp_ppg / league_avg_pts

    # Expected points each team scores
    home_xpts = home_attack * away_defense * league_avg_pts * 1.025  # small home court boost
    away_xpts = away_attack * home_defense * league_avg_pts

    # --- Pace adjustment ---
    league_avg_pace = 100.0
    pace_factor = ((home_stats["pace"] + away_stats["pace"]) / 2) / league_avg_pace
    home_xpts *= pace_factor
    away_xpts *= pace_factor

    # --- Recent form adjustment (last 10 games, weighted 30%) ---
    home_recent = _cached(f"nba_recent_{home_id}", lambda: _fetch_nba_last_n(home_id, 10))
    away_recent = _cached(f"nba_recent_{away_id}", lambda: _fetch_nba_last_n(away_id, 10))

    if home_recent.get("avg_pts"):
        home_xpts = home_xpts * 0.7 + (home_recent["avg_pts"] / league_avg_pts) * league_avg_pts * pace_factor * 0.3
    if away_recent.get("avg_pts"):
        away_xpts = away_xpts * 0.7 + (away_recent["avg_pts"] / league_avg_pts) * league_avg_pts * pace_factor * 0.3

    # --- Back-to-back penalty (-4% scoring, NBA fatigue is less than NHL) ---
    today = datetime.now().date().isoformat()
    if _nba_is_back_to_back(home_id, today):
        home_xpts *= 0.96
    if _nba_is_back_to_back(away_id, today):
        away_xpts *= 0.96

    proj_total = home_xpts + away_xpts

    # Win probability via Pythagorean expectation (NBA exponent ~13.91 per Morey)
    exp = 13.91
    home_prob = home_xpts ** exp / (home_xpts ** exp + away_xpts ** exp)

    return round(home_prob, 4), round(1 - home_prob, 4), round(proj_total, 1)


# ---------------------------------------------------------------------------
# NHL stats
# ---------------------------------------------------------------------------

def _fetch_nhl_team_stats(team_id: str) -> dict:
    try:
        url = f"{ESPN_CORE}/hockey/leagues/nhl/seasons/2026/types/2/teams/{team_id}/statistics"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        cats = r.json().get("splits", {}).get("categories", [])
        stats = {}
        for cat in cats:
            for s in cat.get("stats", []):
                stats[s["name"]] = s.get("value", 0)

        url2 = f"{ESPN_CORE}/hockey/leagues/nhl/seasons/2026/types/2/teams/{team_id}/record"
        r2 = requests.get(url2, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r2.raise_for_status()
        for item in r2.json().get("items", []):
            if item.get("type") == "total":
                for s in item.get("stats", []):
                    stats[s["name"]] = s.get("value", 0)
                break

        wins = stats.get("wins", 0)
        losses = stats.get("losses", 1)
        ot_losses = stats.get("overtimeLosses", 0)
        games = wins + losses + ot_losses or 1

        return {
            "gf_pg": stats.get("avgGoals", 2.8),
            "ga_pg": stats.get("avgGoalsAgainst", 2.8),
            "shots_pg": stats.get("avgShots", 30.0),
            "shots_against_pg": stats.get("avgShotsAgainst", 30.0),
            "pp_pct": stats.get("powerPlayPct", 20.0),
            "pk_pct": stats.get("penaltyKillPct", 80.0),
            "save_pct": stats.get("savePct", 0.900),
            "win_pct": (wins + ot_losses * 0.5) / games,
            "games": games,
        }
    except Exception:
        return {"gf_pg": 2.8, "ga_pg": 2.8, "shots_pg": 30.0,
                "shots_against_pg": 30.0, "pp_pct": 20.0, "pk_pct": 80.0,
                "save_pct": 0.900, "win_pct": 0.5, "games": 0}


def _fetch_nhl_home_away_stats(team_id: str) -> dict:
    """Fetch home and away GF/GA splits from team schedule."""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/teams/{team_id}/schedule?season=2026"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        events = r.json().get("events", [])
        home_gf, home_ga, home_n = 0, 0, 0
        away_gf, away_ga, away_n = 0, 0, 0
        for e in events:
            comp = e.get("competitions", [{}])[0]
            if comp.get("status", {}).get("type", {}).get("completed") is not True:
                continue
            competitors = comp.get("competitors", [])
            team = next((c for c in competitors if c.get("id") == team_id), None)
            opp = next((c for c in competitors if c.get("id") != team_id), None)
            if not team or not opp:
                continue
            try:
                gf = int(float(team.get("score", {}).get("value", 0)))
                ga = int(float(opp.get("score", {}).get("value", 0)))
            except Exception:
                continue
            if team.get("homeAway") == "home":
                home_gf += gf; home_ga += ga; home_n += 1
            else:
                away_gf += gf; away_ga += ga; away_n += 1
        return {
            "home_gf_pg": home_gf / home_n if home_n else None,
            "home_ga_pg": home_ga / home_n if home_n else None,
            "away_gf_pg": away_gf / away_n if away_n else None,
            "away_ga_pg": away_ga / away_n if away_n else None,
        }
    except Exception:
        return {}


def _fetch_goalie_save_pct(game_id: str, home_team_id: str, away_team_id: str) -> dict:
    """Fetch probable goalie season save% for both teams from game summary."""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary?event={game_id}"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        goalies = r.json().get("goalies", {})
        result = {}
        for side, key in [("homeTeam", "home"), ("awayTeam", "away")]:
            athletes = goalies.get(side, {}).get("athletes", [])
            if not athletes:
                continue
            goalie_id = athletes[0].get("id")
            if not goalie_id:
                continue
            gr = requests.get(
                f"https://sports.core.api.espn.com/v2/sports/hockey/leagues/nhl/seasons/2026/types/2/athletes/{goalie_id}/statistics",
                headers=HEADERS, timeout=ESPN_TIMEOUT
            )
            gr.raise_for_status()
            for cat in gr.json().get("splits", {}).get("categories", []):
                for s in cat.get("stats", []):
                    if s["name"] == "savePct":
                        result[key] = s.get("value")
        return result
    except Exception:
        return {}


def _get_nhl_game_id(home_name: str, away_name: str, date_str: str = None) -> str | None:
    """Find ESPN game ID for an upcoming NHL game."""
    try:
        from datetime import date
        d = date_str or date.today().strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={d}"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        for event in r.json().get("events", []):
            name = event.get("name", "")
            if any(w in name for w in home_name.split()[-1:]) and any(w in name for w in away_name.split()[-1:]):
                return event.get("id")
    except Exception:
        pass
    return None


def nhl_pregame_prob(home_name: str, away_name: str) -> tuple[float, float, float] | None:
    """
    Returns (home_win_prob, away_win_prob, proj_total).
    Adjusts for: home/away splits, goalie save%, back-to-back, pace.
    """
    home_id = get_team_id("hockey", "nhl", home_name)
    away_id = get_team_id("hockey", "nhl", away_name)
    if not home_id or not away_id:
        return None

    home_stats = _cached(f"nhl_{home_id}", lambda: _fetch_nhl_team_stats(home_id))
    away_stats = _cached(f"nhl_{away_id}", lambda: _fetch_nhl_team_stats(away_id))

    if home_stats["games"] < 5 or away_stats["games"] < 5:
        return None

    # --- Home/away splits ---
    home_splits = _cached(f"nhl_splits_{home_id}", lambda: _fetch_nhl_home_away_stats(home_id))
    away_splits = _cached(f"nhl_splits_{away_id}", lambda: _fetch_nhl_home_away_stats(away_id))

    league_avg_gf = 2.8
    # Use home split for home team, away split for away team; fall back to season avg
    home_gf = home_splits.get("home_gf_pg") or home_stats["gf_pg"]
    home_ga = home_splits.get("home_ga_pg") or home_stats["ga_pg"]
    away_gf = away_splits.get("away_gf_pg") or away_stats["gf_pg"]
    away_ga = away_splits.get("away_ga_pg") or away_stats["ga_pg"]

    home_attack = home_gf / league_avg_gf
    home_defense = home_ga / league_avg_gf
    away_attack = away_gf / league_avg_gf
    away_defense = away_ga / league_avg_gf

    home_xg = home_attack * away_defense * league_avg_gf * 1.03  # reduced home ice (splits already capture it)
    away_xg = away_attack * home_defense * league_avg_gf

    # --- Pace adjustment ---
    # Normalize by league avg shots (30/game); high-pace games score more
    league_avg_shots = 30.0
    home_pace = home_stats["shots_pg"] / league_avg_shots
    away_pace = away_stats["shots_pg"] / league_avg_shots
    pace_factor = (home_pace + away_pace) / 2  # blended pace
    home_xg *= pace_factor
    away_xg *= pace_factor

    # --- Goalie save% adjustment ---
    # League avg save% ~0.900; better goalie suppresses goals
    league_avg_sv = 0.900
    game_id = _get_nhl_game_id(home_name, away_name)
    if game_id:
        goalie_sv = _cached(f"nhl_goalies_{game_id}", lambda: _fetch_goalie_save_pct(game_id, home_id, away_id))
        home_sv = goalie_sv.get("home", league_avg_sv)
        away_sv = goalie_sv.get("away", league_avg_sv)
        # Adjust xG against based on goalie quality vs league avg
        home_xg *= (1 - away_sv) / (1 - league_avg_sv)   # away goalie faces home shots
        away_xg *= (1 - home_sv) / (1 - league_avg_sv)   # home goalie faces away shots

    # --- Back-to-back adjustment (-8% scoring) ---
    from datetime import date
    today = date.today().isoformat()
    if is_back_to_back("NHL", home_name, today):
        home_xg *= 0.92
        away_xg *= 0.92  # home team fatigue affects both sides slightly
    if is_back_to_back("NHL", away_name, today):
        away_xg *= 0.92

    proj_total = home_xg + away_xg

    exp = 2.15
    home_pyth = home_xg ** exp / (home_xg ** exp + away_xg ** exp)

    return round(home_pyth, 4), round(1 - home_pyth, 4), round(proj_total, 2)


# ---------------------------------------------------------------------------
# MLB stats
# ---------------------------------------------------------------------------

def _fetch_mlb_team_stats(team_id: str) -> dict:
    try:
        url = f"{ESPN_CORE}/baseball/leagues/mlb/seasons/2026/types/2/teams/{team_id}/statistics"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        cats = r.json().get("splits", {}).get("categories", [])
        stats = {}
        for cat in cats:
            for s in cat.get("stats", []):
                stats[s["name"]] = s.get("value", 0)

        url2 = f"{ESPN_CORE}/baseball/leagues/mlb/seasons/2026/types/2/teams/{team_id}/record"
        r2 = requests.get(url2, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r2.raise_for_status()
        for item in r2.json().get("items", []):
            if item.get("type") == "total":
                for s in item.get("stats", []):
                    stats[s["name"]] = s.get("value", 0)
                break

        wins = stats.get("wins", 0)
        losses = stats.get("losses", 1)
        games = wins + losses or 1

        return {
            "runs_pg": stats.get("avgRuns", 4.5),
            "runs_allowed_pg": stats.get("avgRunsAllowed", stats.get("avgEarnedRunsAllowed", 4.5)),
            "ops": stats.get("OPS", stats.get("onBasePlusSlugging", 0.720)),
            "era": stats.get("ERA", stats.get("earnedRunAvg", 4.20)),
            "win_pct": wins / games,
            "games": games,
        }
    except Exception:
        return {"runs_pg": 4.5, "runs_allowed_pg": 4.5, "ops": 0.720,
                "era": 4.20, "win_pct": 0.5, "games": 0}


def mlb_pregame_prob(home_name: str, away_name: str) -> tuple[float, float, float] | None:
    """
    Returns (home_win_prob, away_win_prob, proj_total).
    Uses Pythagorean expectation with runs scored/allowed.
    """
    home_id = get_team_id("baseball", "mlb", home_name)
    away_id = get_team_id("baseball", "mlb", away_name)
    if not home_id or not away_id:
        return None

    home_stats = _cached(f"mlb_{home_id}", lambda: _fetch_mlb_team_stats(home_id))
    away_stats = _cached(f"mlb_{away_id}", lambda: _fetch_mlb_team_stats(away_id))

    if home_stats["games"] < 5 or away_stats["games"] < 5:
        return None

    league_avg = 4.5
    home_attack = home_stats["runs_pg"] / league_avg
    home_defense = home_stats["runs_allowed_pg"] / league_avg
    away_attack = away_stats["runs_pg"] / league_avg
    away_defense = away_stats["runs_allowed_pg"] / league_avg

    home_xr = home_attack * away_defense * league_avg * 1.03  # +3% home field
    away_xr = away_attack * home_defense * league_avg

    proj_total = home_xr + away_xr

    # Pythagorean expectation for baseball (exponent ~1.83)
    exp = 1.83
    home_prob = home_xr ** exp / (home_xr ** exp + away_xr ** exp)

    return round(home_prob, 4), round(1 - home_prob, 4), round(proj_total, 2)


# ---------------------------------------------------------------------------
# Unified interface
# ---------------------------------------------------------------------------

def get_pregame_prob(sport: str, home_name: str, away_name: str) -> tuple | None:
    """
    Returns (home_prob, away_prob, proj_total) or None if stats unavailable.
    proj_total is the model's projected game total (points/goals/runs).
    Result is cached at this level so analyze_game never re-runs the full model.
    """
    cache_key = f"pregame_{sport}_{home_name}_{away_name}"
    if cache_key in _cache_data:
        return _cache_data[cache_key]
    try:
        if sport == "NBA":
            result = nba_pregame_prob(home_name, away_name)
        elif sport == "NHL":
            result = nhl_pregame_prob(home_name, away_name)
        elif sport == "MLB":
            result = mlb_pregame_prob(home_name, away_name)
        else:
            result = None
    except Exception:
        result = None
    if result is not None:
        _cache_data[cache_key] = result
        _cache_time[cache_key] = datetime.now().timestamp()
    return result


# ---------------------------------------------------------------------------
# Recent form and back-to-back detection
# ---------------------------------------------------------------------------

def _fetch_team_schedule(sport: str, team_id: str, limit: int = 10) -> list:
    """Fetch last N games for a team. Returns list of {date, opponent, score, result}."""
    if sport != "NHL":
        return []
    
    try:
        # ESPN team ID -> NHL API abbreviation
        team_abbrev_map = {
            1: "BOS", 2: "BUF", 3: "CGY", 4: "CHI", 5: "DET", 6: "EDM", 7: "CAR",
            8: "LAK", 9: "DAL", 10: "MTL", 11: "NJD", 12: "NYI", 13: "NYR", 14: "OTT",
            15: "PHI", 16: "PIT", 17: "COL", 18: "SJS", 19: "STL", 20: "TBL", 21: "TOR",
            22: "VAN", 23: "WSH", 25: "ANA", 26: "FLA", 27: "NSH", 28: "WPG", 29: "CBJ",
            30: "MIN", 37: "VGK", 124292: "SEA", 129764: "UTA",
        }
        
        team_id_int = int(team_id)
        team_abbrev = team_abbrev_map.get(team_id_int)
        if not team_abbrev:
            return []
        
        # Fetch full season schedule
        url = f"https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/now"
        r = requests.get(url, headers=HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        games_data = r.json().get("games", [])
        
        games = []
        for game in games_data:
            try:
                state = game.get("gameState", "")
                # Filter for OFF (finished) games, not FINAL
                if state != "OFF":
                    continue
                
                date_str = game.get("gameDate", "")
                away = game.get("awayTeam", {})
                home = game.get("homeTeam", {})
                
                # Determine if our team is home or away
                our_team = home if home.get("id") == int(team_id) else away
                opp_team = away if home.get("id") == int(team_id) else home
                
                our_score = our_team.get("score", 0)
                opp_score = opp_team.get("score", 0)
                opp_name = f"{opp_team.get('city', '')} {opp_team.get('abbrev', '')}"
                opp_id = str(opp_team.get("id", ""))
                
                games.append({
                    "date": date_str,
                    "opponent": opp_name,
                    "opponent_id": opp_id,
                    "score": our_score,
                    "opp_score": opp_score,
                    "result": "W" if our_score > opp_score else ("L" if our_score < opp_score else "T"),
                })
            except Exception:
                continue
        
        return games[-limit:] if games else []
    except Exception:
        return []


def get_recent_form(sport: str, team_name: str, limit: int = 10) -> dict:
    """
    Returns {avg_scored, avg_allowed, record, last_game_date}.
    Used to adjust Poisson lambda for recent performance.
    """
    # Map sport to ESPN sport name
    sport_map = {"NHL": "hockey", "NBA": "basketball", "MLB": "baseball", "NFL": "football"}
    espn_sport = sport_map.get(sport, sport.lower())
    league = sport.lower()
    
    team_id = get_team_id(espn_sport, league, team_name)
    if not team_id:
        return {"avg_scored": 0, "avg_allowed": 0, "record": "0-0", "last_game_date": None}
    
    key = f"schedule_{sport}_{team_id}"
    games = _cached(key, lambda: _fetch_team_schedule(sport, team_id, limit))
    
    if not games:
        return {"avg_scored": 0, "avg_allowed": 0, "record": "0-0", "last_game_date": None}
    
    total_scored = sum(g["score"] for g in games)
    total_allowed = sum(g["opp_score"] for g in games)
    wins = sum(1 for g in games if g["result"] == "W")
    losses = sum(1 for g in games if g["result"] == "L")
    
    return {
        "avg_scored": round(total_scored / len(games), 2) if games else 0,
        "avg_allowed": round(total_allowed / len(games), 2) if games else 0,
        "record": f"{wins}-{losses}",
        "last_game_date": games[-1]["date"] if games else None,
    }


def is_back_to_back(sport: str, team_name: str, game_date: str) -> bool:
    """Check if team played yesterday (back-to-back game)."""
    espn_sport = {"NHL": "hockey", "NBA": "basketball", "MLB": "baseball", "NFL": "football"}.get(sport, sport.lower())
    team_id = get_team_id(espn_sport, sport.lower(), team_name)
    if not team_id:
        return False
    
    key = f"schedule_{sport}_{team_id}"
    games = _cached(key, lambda: _fetch_team_schedule(sport, team_id, 5))
    
    if not games:
        return False
    
    try:
        from datetime import datetime, timedelta
        game_dt = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
        yesterday = (game_dt - timedelta(days=1)).date()
        
        for game in games:
            last_game_dt = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
            if last_game_dt.date() == yesterday:
                return True
    except Exception:
        pass
    
    return False


def get_head_to_head(sport: str, home_team: str, away_team: str, limit: int = 10) -> dict:
    """
    Returns {home_wins, away_wins, home_avg_scored, away_avg_scored, record}.
    Analyzes last N matchups between two teams.
    """
    # Map sport name to ESPN league
    league_map = {"NHL": "nhl", "NBA": "nba", "MLB": "mlb", "NFL": "nfl"}
    sport_map = {"NHL": "hockey", "NBA": "basketball", "MLB": "baseball", "NFL": "football"}
    
    league = league_map.get(sport, sport.lower())
    espn_sport = sport_map.get(sport, sport.lower())
    
    home_id = get_team_id(espn_sport, league, home_team)
    away_id = get_team_id(espn_sport, league, away_team)
    
    if not home_id or not away_id:
        return {"home_wins": 0, "away_wins": 0, "home_avg_scored": 0, "away_avg_scored": 0, "record": "0-0", "games_played": 0}
    
    key = f"schedule_{sport}_{home_id}"
    home_games = _cached(key, lambda: _fetch_team_schedule(sport, home_id, 50))
    
    # Filter for matchups against away_team using opponent_id
    h2h = []
    for game in home_games:
        if game.get("opponent_id") == away_id:
            h2h.append(game)
    
    if not h2h:
        return {"home_wins": 0, "away_wins": 0, "home_avg_scored": 0, "away_avg_scored": 0, "record": "0-0", "games_played": 0}
    
    h2h = h2h[-limit:]  # Last N matchups
    
    home_wins = sum(1 for g in h2h if g["result"] == "W")
    away_wins = len(h2h) - home_wins
    home_avg_scored = round(sum(g["score"] for g in h2h) / len(h2h), 2) if h2h else 0
    away_avg_scored = round(sum(g["opp_score"] for g in h2h) / len(h2h), 2) if h2h else 0
    
    return {
        "home_wins": home_wins,
        "away_wins": away_wins,
        "home_avg_scored": home_avg_scored,
        "away_avg_scored": away_avg_scored,
        "record": f"{home_wins}-{away_wins}",
        "games_played": len(h2h),
    }
