#!/usr/bin/env python3
"""
Get Aaron Judge's real Baseball Savant stats from CSV endpoints
"""

import requests
import csv
from io import StringIO


def get_judge_savant_stats():
    """Get Aaron Judge's real Statcast data from Baseball Savant CSV endpoint."""
    
    print("🔍 FETCHING AARON JUDGE'S REAL SAVANT STATS")
    print("=" * 50)
    
    # Baseball Savant CSV endpoint for Exit Velocity & Barrels leaderboard
    url = "https://baseballsavant.mlb.com/leaderboard/statcast"
    params = {
        "type": "batter",
        "year": 2024,
        "position": "",
        "team": "",
        "min": "q",  # qualified batters only
        "sort": "exit_velocity_avg",
        "sortDir": "desc",
        "csv": "true"  # Key parameter to get CSV data
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        print("📡 Making request to Baseball Savant...")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        print(f"✅ Response: {response.status_code} ({len(response.content)} bytes)")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        # Fix the malformed CSV header
        csv_text = response.text
        # Replace the problematic first column header
        csv_text = csv_text.replace('﻿"last_name, first_name"', 'player_name')
        
        # Parse CSV data
        csv_data = StringIO(csv_text)
        reader = csv.DictReader(csv_data)
        
        # Find Aaron Judge in the data
        judge_data = None
        total_players = 0
        
        print("🔍 Searching for Aaron Judge...")
        for row in reader:
            total_players += 1
            # Look for Judge by name
            player_name = row.get('player_name', '').lower()
            if 'judge' in player_name and 'aaron' in player_name:
                judge_data = row
                print(f"✅ Found Aaron Judge! (Player #{total_players})")
                break
            
            # Debug: Show first few players
            if total_players <= 5:
                print(f"  Player {total_players}: {row.get('player_name', 'Unknown')}")
        
        print(f"📊 Searched {total_players} qualified batters")
        
        if judge_data:
            print(f"\n🎯 AARON JUDGE - 2024 STATCAST DATA")
            print("=" * 40)
            
            # Display key Statcast metrics with correct column names
            key_stats = {
                'Player Name': 'player_name',
                'Player ID': 'player_id',
                'Batted Ball Events': 'attempts',
                'Avg Launch Angle': 'avg_hit_angle', 
                'Sweet Spot %': 'anglesweetspotpercent',
                'Max Exit Velocity': 'max_hit_speed',
                'Avg Exit Velocity': 'avg_hit_speed',
                'EV50 (Top 50%)': 'ev50',
                'Max Distance': 'max_distance',
                'Avg Distance': 'avg_distance',
                'Avg HR Distance': 'avg_hr_distance',
                '95+ mph %': 'ev95plus'
            }
            
            for label, key in key_stats.items():
                value = judge_data.get(key, 'N/A')
                if value and value != 'N/A':
                    if 'percent' in key.lower() or '%' in label:
                        print(f"  {label}: {value}%")
                    elif 'velocity' in key.lower() or 'speed' in key.lower():
                        print(f"  {label}: {value} mph")
                    elif 'angle' in key.lower():
                        print(f"  {label}: {value}°")
                    elif 'distance' in key.lower():
                        print(f"  {label}: {value} ft")
                    else:
                        print(f"  {label}: {value}")
                else:
                    print(f"  {label}: {value}")
            
            # Show all available columns for reference
            print(f"\n📋 ALL AVAILABLE COLUMNS ({len(judge_data)} total):")
            for i, column in enumerate(judge_data.keys(), 1):
                print(f"  {i:2d}. {column}")
            
            return judge_data
            
        else:
            print("❌ Aaron Judge not found in qualified batters")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None


def get_judge_expected_stats():
    """Get Aaron Judge's expected statistics (xBA, xSLG, xwOBA)."""
    
    print(f"\n🔍 FETCHING JUDGE'S EXPECTED STATS")
    print("=" * 35)
    
    url = "https://baseballsavant.mlb.com/leaderboard/expected_statistics"
    params = {
        "type": "batter",
        "year": 2024,
        "position": "",
        "team": "",
        "min": "q",
        "csv": "true"
    }
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        
        for row in reader:
            full_name = row.get('last_name, first_name', '').lower()
            if 'judge' in full_name and 'aaron' in full_name:
                print("📈 Expected Statistics:")
                expected_stats = {
                    'xBA': 'xba',
                    'xSLG': 'xslg', 
                    'xwOBA': 'xwoba',
                    'xwOBAcon': 'xwobacon',
                    'xISO': 'xiso'
                }
                
                for label, key in expected_stats.items():
                    value = row.get(key, 'N/A')
                    print(f"  {label}: {value}")
                
                return row
                
        print("❌ Judge not found in expected stats")
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    # Get Judge's Statcast data
    judge_statcast = get_judge_savant_stats()
    
    # Get Judge's expected stats
    judge_expected = get_judge_expected_stats()
    
    if judge_statcast or judge_expected:
        print(f"\n✅ SUCCESS: Retrieved Aaron Judge's real Baseball Savant data!")
        print("🎯 This data can now be integrated into your MLB prop analysis")
    else:
        print(f"\n❌ Could not retrieve Judge's data")
        print("💡 May need to adjust search parameters or try different endpoints")
