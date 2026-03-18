# MLB System Roadmap & Data Strategy

## Current Status (March 2026)
- ✅ Basic MLB analyzer with team markets (h2h, totals, spreads)
- ✅ MLB player props system (hitting & pitching)
- ✅ Real Baseball Savant park factors (2023-2025 data)
- ✅ Real player Statcast data (exit velocity, barrels, etc.)
- ❌ Using outdated 2025 player/team data for 2026 season

## Critical Data Issues Identified

### Problem: Stale Data for Live Betting
- **Player Stats**: Using 2025 stats for players who may have changed teams
- **Team Composition**: Rosters completely different due to trades/free agency
- **Performance Context**: 2025 performance may not reflect 2026 form
- **Injury Status**: No current injury/availability data

### Impact on Prop Accuracy
- **False edges**: Props based on outdated player performance
- **Wrong team context**: Players in different offensive environments
- **Roster gaps**: Betting on players no longer on teams
- **Stale projections**: Not reflecting current season trends

## Roadmap for Production-Ready MLB System

### Phase 1: Current Season Data Integration
- [ ] **2026 MLB Stats API**: Real current season player stats
- [ ] **Current Rosters**: Who's actually playing for each team
- [ ] **Injury Reports**: Daily injury/availability updates
- [ ] **Recent Performance**: Last 15-30 games vs full season stats

### Phase 2: Advanced Data Sources
- [ ] **Starting Pitcher Confirmations**: Daily probable pitchers
- [ ] **Weather Integration**: Real-time weather for outdoor games
- [ ] **Lineup Data**: Actual batting orders and positions
- [ ] **Bullpen Usage**: Recent reliever workload/availability

### Phase 3: Real-Time Optimization
- [ ] **Live Odds Monitoring**: Track line movements
- [ ] **Sharp Money Indicators**: Identify where smart money moves
- [ ] **Closing Line Value**: Measure model performance vs closing odds
- [ ] **Automated Alerts**: Notify when edges exceed thresholds

### Phase 4: Advanced Modeling
- [ ] **Matchup-Specific Models**: Pitcher vs batter history
- [ ] **Situational Adjustments**: Day/night, home/road splits
- [ ] **Platoon Advantages**: Left/right handed matchups
- [ ] **Ballpark-Specific Props**: Venue-adjusted projections

## Data Source Priority

### Immediate Needs (2026 Season)
1. **MLB Stats API** - Current season stats
2. **ESPN/MLB.com** - Current rosters & lineups
3. **RotoWire/FantasyLabs** - Injury reports
4. **Weather APIs** - Game conditions

### Long-term Integrations
1. **FanGraphs API** - Advanced metrics
2. **Statcast Search** - Pitch-by-pitch data
3. **Vegas Insider** - Line movement tracking
4. **Action Network** - Sharp money indicators

## Technical Implementation Notes

### Data Freshness Strategy
```python
# Prioritize data recency for live betting
if game_time < 24_hours:
    use_last_15_games_stats()
else:
    use_season_stats()
```

### Roster Validation
```python
# Verify player is still on team before analysis
if not player_on_current_roster(player, team):
    skip_prop_analysis()
```

### Fallback Hierarchy
```python
# Data source priority
try:
    current_2026_stats = get_mlb_api_stats()
except:
    try:
        recent_stats = get_last_30_games()
    except:
        use_cached_2025_stats()  # Last resort
```

## Success Metrics
- **Edge Accuracy**: Model edges vs actual closing line value
- **Hit Rate**: Percentage of profitable recommendations
- **ROI**: Return on investment over time
- **Data Freshness**: Average age of data used in analysis

## Next Steps
1. Research available 2026 MLB data APIs
2. Implement current roster validation
3. Add data freshness warnings to analysis
4. Build fallback data hierarchy
5. Test with small sample before full deployment

---
*Last Updated: March 18, 2026*
*Status: Development - Not Production Ready*
