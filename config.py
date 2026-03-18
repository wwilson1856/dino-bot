import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = "df12eb627927c5af0e348d66ba624cbc"
BASE_URL = "https://api.the-odds-api.com/v4"

# Sports keys for The Odds API
SPORTS = {
    "NBA": "basketball_nba",
    "NHL": "icehockey_nhl",
    "MLB": "baseball_mlb",
    "NFL": "americanfootball_nfl",
}

# Only look at these game markets
MARKETS = ["h2h", "spreads", "totals"]

# Player prop markets per sport (The Odds API event-odds endpoint)
PROP_MARKETS = {
    "NBA": [
        "player_points", "player_rebounds", "player_assists",
        "player_threes", "player_points_rebounds_assists",
        "player_steals", "player_blocks",
    ],
    "NFL": [
        "player_pass_yds", "player_pass_tds", "player_rush_yds",
        "player_reception_yds", "player_receptions",
    ],
    "MLB": [
        "batter_hits", "batter_home_runs", "batter_rbis",
        "batter_strikeouts", "pitcher_strikeouts", "pitcher_hits_allowed",
    ],
    "NHL": [
        "player_points", "player_goals", "player_assists",
        "player_shots_on_goal",
    ],
    "WBC": [
        "batter_hits", "batter_home_runs", "pitcher_strikeouts",
    ],
}

# Minimum edge % to recommend a bet
MIN_EDGE = 0.025  # 2.5% - RAISED for better selectivity

# Minimum confidence score (1-100) to show a pick
MIN_CONFIDENCE = 65  # RAISED from 50 for better selectivity

# Unit size in dollars
UNIT_SIZE = 25

# How often to poll in seconds
POLL_INTERVAL_LIVE = 120

# Preferred bookmaker (used for odds comparison)
BOOKMAKER = "fanduel"

# Only pull odds from this bookmaker for betting
BOOKMAKER_FILTER = "fanduel"

# Sharp reference book used as "true line" (Pinnacle is the sharpest market)
SHARP_BOOK = "pinnacle"

# How many days ahead to look for upcoming games
UPCOMING_DAYS_AHEAD = 2

# Max hours a game can be "in progress" before we consider it finished
GAME_DURATION_HOURS = {
    "NBA": 2.5,
    "NHL": 3.0,
    "NFL": 3.5,
    "MLB": 4.0,
    "WBC": 4.0,
    "MLB_PRE": 4.0,
}

# Filter out any odds longer than this (e.g. -500 = skip heavy favorites)
MAX_JUICE = -500

# Modes: "live", "upcoming", "both"
MODE = "both"

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
