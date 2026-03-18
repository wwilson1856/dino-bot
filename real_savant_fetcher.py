#!/usr/bin/env python3
"""
REAL Baseball Savant Data Fetcher
Actually pulls live data from Baseball Savant CSV endpoints
"""

import requests
import csv
from io import StringIO
import json
import os
from datetime import datetime


def fetch_real_park_factors(year: int = 2025) -> dict:
    """Fetch REAL park factors from Baseball Savant CSV endpoint."""
    
    print(f"🔍 FETCHING REAL PARK FACTORS FROM BASEBALL SAVANT ({year})")
    print("=" * 60)
    
    url = "https://baseballsavant.mlb.com/leaderboard/statcast-park-factors"
    params = {
        "type": "batter",
        "year": year,
        "batSide": "All",
        "stat": "woba",
        "condition": "All",
        "csv": "true"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return {}
        
        print(f"✅ Got {len(response.content)} bytes of CSV data")
        
        # Parse CSV
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        
        park_factors = {}
        
        for row in reader:
            # Extract venue name and factor
            venue = row.get('venue_name', '').strip()
            factor_str = row.get('factor', '100')  # Default to 100 (neutral)
            
            if venue and factor_str:
                try:
                    factor = float(factor_str) / 100.0  # Convert 105 -> 1.05
                    
                    # Map venue names to team names
                    venue_to_team = {
                        'Coors Field': 'Colorado Rockies',
                        'Fenway Park': 'Boston Red Sox',
                        'Yankee Stadium': 'New York Yankees',
                        'Great American Ball Park': 'Cincinnati Reds',
                        'Globe Life Field': 'Texas Rangers',
                        'Camden Yards': 'Baltimore Orioles',
                        'Target Field': 'Minnesota Twins',
                        'Citizens Bank Park': 'Philadelphia Phillies',
                        'Wrigley Field': 'Chicago Cubs',
                        'Nationals Park': 'Washington Nationals',
                        'Truist Park': 'Atlanta Braves',
                        'Minute Maid Park': 'Houston Astros',
                        'Dodger Stadium': 'Los Angeles Dodgers',
                        'Busch Stadium': 'St. Louis Cardinals',
                        'Citi Field': 'New York Mets',
                        'American Family Field': 'Milwaukee Brewers',
                        'Angel Stadium': 'Los Angeles Angels',
                        'Chase Field': 'Arizona Diamondbacks',
                        'Rogers Centre': 'Toronto Blue Jays',
                        'Kauffman Stadium': 'Kansas City Royals',
                        'Comerica Park': 'Detroit Tigers',
                        'PNC Park': 'Pittsburgh Pirates',
                        'Guaranteed Rate Field': 'Chicago White Sox',
                        'loanDepot park': 'Miami Marlins',
                        'Tropicana Field': 'Tampa Bay Rays',
                        'Progressive Field': 'Cleveland Guardians',
                        'Oakland Coliseum': 'Oakland Athletics',
                        'T-Mobile Park': 'Seattle Mariners',
                        'Oracle Park': 'San Francisco Giants',
                        'Petco Park': 'San Diego Padres'
                    }
                    
                    team_name = venue_to_team.get(venue)
                    if team_name:
                        park_factors[team_name] = factor
                        print(f"  {venue} ({team_name}): {factor:.3f}")
                    else:
                        print(f"  ⚠️ Unknown venue: {venue}")
                        
                except ValueError:
                    print(f"  ❌ Invalid factor for {venue}: {factor_str}")
        
        print(f"\\n📊 Retrieved {len(park_factors)} park factors")
        
        # Cache the real data
        cache_dir = "cache"
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = f"{cache_dir}/real_park_factors_{year}.json"
        
        with open(cache_file, 'w') as f:
            json.dump({
                'data': park_factors,
                'fetched_at': datetime.now().isoformat(),
                'source': 'Baseball Savant CSV API'
            }, f, indent=2)
        
        print(f"💾 Cached to {cache_file}")
        
        return park_factors
        
    except Exception as e:
        print(f"❌ Error fetching real park factors: {e}")
        return {}


def fetch_real_player_stats(year: int = 2025) -> dict:
    """Fetch REAL player stats from Baseball Savant."""
    
    print(f"\\n🔍 FETCHING REAL PLAYER STATS FROM BASEBALL SAVANT ({year})")
    print("=" * 60)
    
    url = "https://baseballsavant.mlb.com/leaderboard/statcast"
    params = {
        "type": "batter",
        "year": year,
        "min": "q",  # qualified only
        "csv": "true"
    }
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return {}
        
        # Fix CSV header
        csv_text = response.text.replace('﻿"last_name, first_name"', 'player_name')
        csv_data = StringIO(csv_text)
        reader = csv.DictReader(csv_data)
        
        player_stats = {}
        
        for row in reader:
            player_name = row.get('player_name', '').strip()
            
            if player_name:
                # Extract key stats
                stats = {
                    'exit_velocity_avg': float(row.get('avg_hit_speed', 0) or 0),
                    'barrel_percent': float(row.get('brl_percent', 0) or 0),
                    'hard_hit_percent': float(row.get('ev95percent', 0) or 0),
                    'sweet_spot_percent': float(row.get('anglesweetspotpercent', 0) or 0),
                    'max_exit_velocity': float(row.get('max_hit_speed', 0) or 0),
                    'batted_ball_events': int(row.get('attempts', 0) or 0)
                }
                
                player_stats[player_name] = stats
        
        print(f"📊 Retrieved stats for {len(player_stats)} qualified players")
        
        # Show sample of top players
        print("\\n🌟 Sample players:")
        for i, (name, stats) in enumerate(list(player_stats.items())[:5]):
            print(f"  {name}: {stats['exit_velocity_avg']:.1f} mph avg, {stats['barrel_percent']:.1f}% barrels")
        
        return player_stats
        
    except Exception as e:
        print(f"❌ Error fetching real player stats: {e}")
        return {}


if __name__ == "__main__":
    print("🚀 FETCHING REAL BASEBALL SAVANT DATA")
    print("=" * 50)
    
    # Fetch real park factors
    real_park_factors = fetch_real_park_factors(2025)
    
    # Fetch real player stats  
    real_player_stats = fetch_real_player_stats(2025)
    
    if real_park_factors and real_player_stats:
        print("\\n✅ SUCCESS: Retrieved real Baseball Savant data!")
        print("🎯 This is ACTUAL live data, not hardcoded estimates")
    else:
        print("\\n❌ Failed to retrieve real data")
        print("💡 May need to implement web scraping or use pybaseball library")
