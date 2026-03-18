# Moneymaker - Sports Betting Edge-Finding Model

## Overview
Moneymaker is an automated sports betting model that identifies profitable betting opportunities by comparing model-predicted probabilities against market odds. It runs live analysis and sends daily picks via Discord at 4 PM EST.

## Core Methodology

### 1. Data Collection
- **Action Network API** — Live odds from FanDuel, DraftKings, Pinnacle
- **ESPN API** — Game scores, status, team stats
- **NHL.com API** — Team schedules, recent game results

### 2. Game Classification
- **LIVE** — Game in progress (0-3.5 hours old)
- **UPCOMING** — Today's games (starts within 6 hours)
- **TOMORROW** — Next day's games
- **FINISHED** — Game completed
- **EXCLUDED** — MLB before opening day (March 28)

### 3. Win Probability Models

**For LIVE games (Poisson-based):**
- Base: 1.5 goals/team per game
- **Recent form adjustment:** Last 10 games avg goals scored/allowed
  - Formula: (team_avg_goals / 2.8) × base_lambda
- **Back-to-back penalty:** 8% reduction if team played yesterday
- **Result:** Probability of Over/Under using Poisson distribution

**For UPCOMING games (Pre-game stats):**
- Offensive/defensive ratings from ESPN
- Pythagorean expectation formula
- Home field advantage (+3% for home team)
- Result: Win probability for moneyline

### 4. Edge Calculation
```
Edge = Model Probability - Market Implied Probability
Minimum edge threshold: 1.5%
```

Example: Model says 75% Over, market implies 55% → 20% edge

### 5. Confidence Scoring
- Based on model certainty and data quality
- Minimum threshold: 50%
- Affects unit sizing multiplier

### 6. Unit Sizing (Kelly Criterion)
```
Kelly = (b×p - q) / b
  where b = decimal odds - 1
        p = model probability
        q = 1 - p

Confidence scaling: 50% conf = 0.5x Kelly, 95%+ = 1.0x
Multiplier: 1.5x Kelly (aggressive)
Max units: 15
```

### 7. Pick Selection
- Rank all picks by confidence score
- Select top pick from today's games (live + upcoming)
- Send to Discord with stats

### 8. Performance Tracking
- Log all picks with results
- Calculate win streak
- Track L5, L10, per-sport records
- Resolve picks against final scores

## Supported Sports
- **NHL** — Full support with recent form
- **NBA** — Full support
- **MLB** — Full support (excluded until opening day)
- **NFL** — Full support
- **WBC** — World Baseball Classic
- **SOCCER** — EPL (English Premier League)

## Daily Workflow (4 PM EST)

1. **3:50 PM - 4:10 PM EST window check** (safety mechanism)
2. **Send startup message** — "🚀 4 PM EST — Betting Model Starting"
3. **Run model analysis** — Fetch live odds, calculate edges
4. **Select top pick** — Highest confidence from today's games
5. **Send pick to Discord** with:
   - Dino quote (random)
   - Bet details (team, odds, units)
   - Edge % and confidence
   - Win streak (if 3+ wins)
   - Record stats (L5, L10, sport-specific)

## Discord Message Format
```
-# "<Dino quote>"
# 🎯 PICK OF THE DAY
# <BET> — <ODDS> — <UNITS>u

Edge: <EDGE>% | Conf: <CONFIDENCE>%
<BOOK> · <TIME>
🔥 <STREAK> (if 3+ wins)
📊 <STATS> (L5, L10, sport record)
```

## Project Structure
```
/moneymaker/betting_model/
├── main.py                 # Main entry point (continuous analysis)
├── run_4pm.py             # 4 PM EST job with safety check
├── config.py              # Configuration (sports, thresholds)
├── analyzer.py            # Game analysis & edge calculation
├── discord_alerts.py       # Discord messaging
├── action_scraper.py       # Odds fetching
├── edge.py                # Edge & unit sizing calculations
├── models/
│   ├── nhl.py             # Poisson-based win probability
│   ├── nba.py, nfl.py, mlb.py
│   ├── soccer.py          # EPL model
│   └── stats.py           # Team stats, recent form, schedules
├── venv/                  # Python virtual environment
├── .env                   # API keys
├── picks_log.json         # Pick tracking
└── PROJECT_CONTEXT.md     # This file
```

## Key Configuration
- **MIN_EDGE**: 1.5% (minimum edge to recommend)
- **MIN_CONFIDENCE**: 50% (minimum confidence score)
- **UNIT_SIZE**: $25 per unit
- **GAME_DURATION_HOURS**: Sport-specific (NHL = 3.0, Soccer = 2.0)
- **POLL_INTERVAL_LIVE**: 120 seconds
- **MODE**: "both" (live + upcoming games)
- **KELLY_FRACTION**: 1.5x (aggressive sizing)
- **MAX_UNITS**: 15

## Recent Enhancements

### Recent Form Integration
- Fetches last 10 finished games from NHL.com API
- Calculates avg goals scored/allowed
- Adjusts Poisson lambda: (team_avg / 2.8) × base_lambda
- Improves accuracy for hot/cold teams

### Back-to-Back Detection
- Checks if team played yesterday
- Applies 8% penalty to scoring expectation
- Accounts for fatigue factor

### Safety Mechanisms
- 4 PM EST time window check (3:50 PM - 4:10 PM)
- Prevents accidental Discord messages outside window
- Aborts if run at wrong time

### ESPN to NHL API Mapping
- Converts ESPN team IDs to NHL.com abbreviations
- Handles new teams (e.g., Utah Hockey Club ID 129764 → UTA)
- Ensures schedule data retrieval works for all teams

## Git History (Recent Commits)
- `56f18bb` — Add ESPN to NHL API ID mapping for Utah
- `5db605a` — Fix NHL API filter to use OFF state
- `a4caf8f` — Fix get_recent_form sport mapping
- `293c1d7` — Update to new NHL API (api-web.nhle.com)
- `f07301d` — Add 4 PM EST time window safety check
- `dd6bed5` — Add head-to-head matchup history infrastructure
- `d520a55` — Remove discord alert from 4pm job on add-soccer
- `9a2439d` — Pass team names and game date to NHL win_probability
- `67ed9c0` — Add recent form and back-to-back detection
- `7eee4cf` — Increase kelly fraction to 1.5x and max units to 15

## Deployment Status
✅ **Production Ready**
- All code compiles
- Recent form working with internet access
- 4 PM safety check active
- Discord integration tested
- Cron job configured: `0 21 * * * cd /moneymaker/betting_model && source venv/bin/activate && python3 run_4pm.py`

## Next Steps
1. Monitor 4 PM EST cron job execution
2. Verify Discord messages send correctly
3. Track pick performance over time
4. Refine confidence thresholds based on results
5. Consider adding goaltender quality factor
6. Expand to additional sportsbooks for line shopping

## Testing
- `test_4pm_no_discord.py` — Full flow without Discord messages
- `test_discord_message.py` — Preview Discord format locally
- `test_4pm_flow.py` — Simulate 4 PM flow with mock data

## Notes
- Model uses conservative 1.5% edge threshold (high quality picks)
- Recent form data requires internet access to NHL.com
- Back-to-back detection works with current game date
- Head-to-head infrastructure ready (awaiting ESPN schedule data)
- All picks logged for performance tracking
