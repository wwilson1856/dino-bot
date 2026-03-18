# Moneymaker Betting Model

A sophisticated sports betting analysis system with Discord bot integration, featuring real-time odds analysis, player props modeling, and multi-sport coverage.

## 🎯 Features

### Core Analysis
- **Team Markets**: Moneylines, totals, spreads with sport-specific modeling
- **Player Props**: NHL (goals, assists, shots) and MLB (hitting/pitching props)
- **Real-time Data**: Action Network integration with live odds
- **Sharp Line Analysis**: Pinnacle fair value calculations
- **Kelly Sizing**: Optimal unit recommendations based on edge and confidence

### Sports Coverage
- **NHL**: Complete team and player prop analysis with advanced metrics
- **MLB**: Ballpark factors, Statcast integration, hitting/pitching props
- **NBA/NFL**: Basic team market analysis (expandable)

### Discord Bot Commands
- `!analyze` - NHL team markets analysis
- `!props` - NHL player props analysis  
- `!mlb` - MLB team markets with ballpark factors
- `!mlbprops` - MLB player props (hitting & pitching)
- `!game <teams>` - Specific game analysis
- `!baddino` - Comic relief for bad picks
- `!record` - Track betting performance
- `!stats` - System statistics

## 🏗️ Architecture

### Data Sources
- **Action Network**: Live odds and team stats
- **OddsAPI**: Player props with smart caching
- **Baseball Savant**: Real Statcast data and park factors
- **NHL API**: Player statistics and game data
- **Pinnacle**: Sharp line fair value calculations

### Key Components
- **Analyzers**: Sport-specific analysis engines
- **Models**: Statistical models for each sport
- **Edge Calculation**: Kelly criterion and EV calculations
- **Discord Integration**: Real-time betting alerts and commands
- **Data Caching**: Efficient API usage with smart caching

## 📊 Analysis Features

### NHL Analysis
- **Team Markets**: Advanced shot metrics, goalie analysis, situational factors
- **Player Props**: Position-based rates with star multipliers
- **Line Shopping**: Multiple sportsbook integration
- **Closing Line Value**: Performance tracking vs market close

### MLB Analysis  
- **Park Factors**: Real Baseball Savant ballpark adjustments
- **Weather Integration**: Ready for wind/temperature factors
- **Matchup Analysis**: Pitcher vs batter historical data
- **Statcast Metrics**: Exit velocity, barrel rate, launch angle

## 🚀 Getting Started

### Prerequisites
```bash
python 3.8+
pip install -r requirements.txt
```

### Environment Variables
```bash
# Discord
DISCORD_TOKEN=your_discord_bot_token

# APIs
ACTION_NETWORK_KEY=your_action_network_key
ODDS_API_KEY=your_odds_api_key

# Optional
KALSHI_EMAIL=your_kalshi_email
KALSHI_PASSWORD=your_kalshi_password
```

### Installation
```bash
git clone https://github.com/yourusername/moneymaker-betting-model.git
cd moneymaker-betting-model
pip install -r requirements.txt
python discord_bot.py
```

## 📈 Performance Tracking

### Metrics
- **Edge Accuracy**: Model edges vs actual closing line value
- **Hit Rate**: Percentage of profitable recommendations  
- **ROI**: Return on investment tracking
- **Closing Line Value**: Measure of model sharpness

### Logging
- **Picks Log**: All recommendations with timestamps
- **Performance Analytics**: Win/loss tracking by sport and market
- **API Health**: Monitor data source reliability

## 🔧 Configuration

### Thresholds (config.py)
```python
MIN_EDGE = 0.025        # 2.5% minimum edge
MIN_CONFIDENCE = 65     # 65% minimum confidence
MAX_JUICE = -500        # Maximum odds accepted
MAX_UNITS = 3.0         # Maximum Kelly units
```

### Sport-Specific Settings
- **NHL**: Conservative 1.5% edge threshold for totals
- **MLB**: Ballpark-adjusted thresholds (2.0-2.5%)
- **Player Props**: Higher 2.5% threshold due to variance

## 📁 Project Structure

```
moneymaker-betting-model/
├── discord_bot.py          # Main Discord bot
├── analyzer.py             # Core analysis engine
├── team_analyzer.py        # NHL team markets
├── mlb_analyzer.py         # MLB analysis engine
├── edge.py                 # Kelly criterion calculations
├── config.py               # System configuration
├── models/                 # Sport-specific models
│   ├── nhl.py             # NHL modeling
│   ├── mlb.py             # MLB modeling
│   └── stats.py           # Statistical functions
├── context/               # Documentation
│   └── mlb_roadmap.md     # MLB development roadmap
└── cache/                 # Data caching
```

## 🛣️ Roadmap

### Current Status
- ✅ NHL team markets and player props
- ✅ MLB basic analysis with real park factors
- ✅ Discord bot with multiple commands
- ✅ Real-time data integration

### Planned Features
- [ ] NBA player props and advanced metrics
- [ ] NFL analysis with weather factors
- [ ] Live betting integration
- [ ] Advanced ML models
- [ ] Web dashboard interface

## ⚠️ Disclaimer

This software is for educational and research purposes only. Sports betting involves risk and may not be legal in all jurisdictions. Users are responsible for complying with local laws and regulations. Past performance does not guarantee future results.

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For questions or issues, please open a GitHub issue or contact the development team.

---

**Built with ❤️ for the sports betting community**
