#!/usr/bin/env python3
"""
Baseball Savant API Explorer
Discover available endpoints and data formats
"""

import requests
import json
from datetime import datetime


def explore_savant_endpoints():
    """Explore Baseball Savant API endpoints."""
    
    print("🔍 BASEBALL SAVANT API ENDPOINTS")
    print("=" * 50)
    
    # Known endpoints from network inspection
    endpoints = {
        "Statcast Leaderboard": {
            "url": "https://baseballsavant.mlb.com/leaderboard/statcast",
            "params": {
                "type": "batter",
                "year": 2024,
                "position": "",
                "team": "",
                "min": "q",  # qualified
                "sort": "exit_velocity_avg",
                "sortDir": "desc"
            }
        },
        
        "Expected Statistics": {
            "url": "https://baseballsavant.mlb.com/leaderboard/expected_statistics", 
            "params": {
                "type": "batter",
                "year": 2024,
                "position": "",
                "team": "",
                "min": "q"
            }
        },
        
        "Park Factors": {
            "url": "https://baseballsavant.mlb.com/leaderboard/statcast-park-factors",
            "params": {
                "type": "batter",
                "year": 2024,
                "batSide": "All",
                "stat": "woba",
                "condition": "All"
            }
        },
        
        "Player Search": {
            "url": "https://baseballsavant.mlb.com/statcast_search",
            "params": {
                "hfPT": "",
                "hfAB": "",
                "hfBBT": "",
                "hfPR": "",
                "hfZ": "",
                "stadium": "",
                "hfBBL": "",
                "hfNewZones": "",
                "hfGT": "R%7C",
                "hfC": "",
                "hfSea": "2024%7C",
                "hfSit": "",
                "player_type": "batter",
                "hfOuts": "",
                "opponent": "",
                "pitcher_throws": "",
                "batter_stands": "",
                "hfSA": "",
                "game_date_gt": "",
                "game_date_lt": "",
                "hfInfield": "",
                "team": "",
                "position": "",
                "hfOutfield": "",
                "hfRO": "",
                "home_road": "",
                "batters_lookup%5B%5D": "592450",  # Aaron Judge ID
                "hfFlag": "",
                "hfPull": "",
                "metric_1": "",
                "hfInn": "",
                "min_pitches": "0",
                "min_results": "0",
                "group_by": "name",
                "sort_col": "pitches",
                "player_event_sort": "h_launch_speed",
                "sort_order": "desc",
                "min_abs": "0",
                "type": "details"
            }
        }
    }
    
    for name, endpoint in endpoints.items():
        print(f"\n📊 {name}")
        print(f"URL: {endpoint['url']}")
        print("Parameters:")
        for key, value in endpoint['params'].items():
            print(f"  {key}: {value}")
    
    return endpoints


def test_savant_request(endpoint_name: str, endpoints: dict):
    """Test a specific Baseball Savant endpoint."""
    
    if endpoint_name not in endpoints:
        print(f"❌ Endpoint '{endpoint_name}' not found")
        return
    
    endpoint = endpoints[endpoint_name]
    
    try:
        print(f"\n🔍 Testing {endpoint_name}...")
        
        # Make request with headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(
            endpoint['url'], 
            params=endpoint['params'],
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type', 'unknown')}")
        print(f"Response Size: {len(response.content)} bytes")
        
        # Try to detect if it's JSON
        if 'json' in response.headers.get('content-type', '').lower():
            try:
                data = response.json()
                print(f"JSON Keys: {list(data.keys()) if isinstance(data, dict) else 'Array'}")
                return data
            except:
                print("❌ Failed to parse JSON")
        else:
            print("📄 HTML/Text response (not JSON API)")
            
        return response.text[:500] + "..." if len(response.text) > 500 else response.text
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def discover_data_structure():
    """Discover what data is actually available."""
    
    print("\n🎯 AVAILABLE DATA CATEGORIES")
    print("=" * 40)
    
    categories = {
        "Batting Metrics": [
            "Exit Velocity", "Launch Angle", "Barrels", "Hard Hit Rate",
            "Expected BA", "Expected SLG", "Expected wOBA", "Sweet Spot %"
        ],
        
        "Bat Tracking": [
            "Bat Speed", "Attack Angle", "Swing Length", "Fast Swing Rate",
            "Squared-Up Rate", "Blasts", "Swing Path Tilt"
        ],
        
        "Pitching Metrics": [
            "Pitch Velocity", "Spin Rate", "Pitch Movement", "Active Spin",
            "Release Point", "Extension", "Approach Angle"
        ],
        
        "Fielding Metrics": [
            "Outs Above Average", "Catch Probability", "Jump", "Arm Strength",
            "Pop Time", "Framing", "Blocking"
        ],
        
        "Running Metrics": [
            "Sprint Speed", "Baserunning Run Value", "Stolen Base Success",
            "90ft Splits", "Home to First"
        ],
        
        "Park Factors": [
            "wOBA Factor", "HR Factor", "Hit Factor", "Doubles Factor",
            "Triples Factor", "BB Factor", "SO Factor"
        ]
    }
    
    for category, metrics in categories.items():
        print(f"\n📈 {category}:")
        for metric in metrics:
            print(f"  • {metric}")
    
    return categories


def test_csv_download():
    """Test Baseball Savant CSV download endpoints."""
    
    print("\n🔍 TESTING CSV DOWNLOAD ENDPOINTS")
    print("=" * 40)
    
    # CSV download endpoints (discovered from network inspection)
    csv_endpoints = {
        "Exit Velocity Leaderboard": {
            "url": "https://baseballsavant.mlb.com/leaderboard/statcast",
            "params": {
                "type": "batter",
                "year": 2024,
                "position": "",
                "team": "",
                "min": "q",
                "sort": "exit_velocity_avg",
                "sortDir": "desc",
                "csv": "true"  # Key parameter for CSV
            }
        },
        
        "Expected Stats CSV": {
            "url": "https://baseballsavant.mlb.com/leaderboard/expected_statistics",
            "params": {
                "type": "batter", 
                "year": 2024,
                "position": "",
                "team": "",
                "min": "q",
                "csv": "true"
            }
        },
        
        "Park Factors CSV": {
            "url": "https://baseballsavant.mlb.com/leaderboard/statcast-park-factors",
            "params": {
                "type": "batter",
                "year": 2024,
                "batSide": "All", 
                "stat": "woba",
                "condition": "All",
                "csv": "true"
            }
        }
    }
    
    for name, endpoint in csv_endpoints.items():
        try:
            print(f"\n📊 Testing {name}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(
                endpoint['url'],
                params=endpoint['params'], 
                headers=headers,
                timeout=15
            )
            
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"Size: {len(response.content)} bytes")
            
            # Check if it's CSV data
            if 'csv' in response.headers.get('content-type', '').lower() or response.text.startswith('player_name') or ',' in response.text[:100]:
                print("✅ CSV data detected!")
                lines = response.text.split('\n')[:5]  # First 5 lines
                for i, line in enumerate(lines):
                    print(f"  Line {i+1}: {line[:80]}{'...' if len(line) > 80 else ''}")
                return response.text
            else:
                print("❌ Not CSV format")
                print(f"Sample: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return None


if __name__ == "__main__":
    # Explore available endpoints
    endpoints = explore_savant_endpoints()
    
    # Discover data structure
    discover_data_structure()
    
    # Test CSV downloads
    csv_data = test_csv_download()
    
    if csv_data:
        print(f"\n✅ SUCCESS: Found working CSV endpoint!")
        print("🎯 Ready to integrate real Baseball Savant data")
    else:
        print(f"\n💡 May need to use pybaseball library as intermediary")
        print("🔧 Or implement web scraping with proper session handling")
