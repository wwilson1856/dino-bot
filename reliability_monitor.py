"""
API reliability monitoring and alerting.
Tracks success rates and sends Discord alerts on failures.
"""
import json
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List

MONITOR_FILE = "api_monitor.json"

def log_api_call(endpoint: str, success: bool, error: str = None):
    """Log API call result for monitoring."""
    if not os.path.exists(MONITOR_FILE):
        data = {"calls": []}
    else:
        with open(MONITOR_FILE, "r") as f:
            data = json.load(f)
    
    data["calls"].append({
        "endpoint": endpoint,
        "success": success,
        "error": error,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only last 100 calls per endpoint
    calls_by_endpoint = {}
    for call in data["calls"]:
        ep = call["endpoint"]
        if ep not in calls_by_endpoint:
            calls_by_endpoint[ep] = []
        calls_by_endpoint[ep].append(call)
    
    # Trim to last 100 per endpoint
    trimmed = []
    for ep, calls in calls_by_endpoint.items():
        trimmed.extend(calls[-100:])
    
    data["calls"] = trimmed
    
    with open(MONITOR_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_reliability_stats() -> Dict:
    """Get success rates for each API endpoint."""
    if not os.path.exists(MONITOR_FILE):
        return {}
    
    with open(MONITOR_FILE, "r") as f:
        data = json.load(f)
    
    # Group by endpoint
    stats = {}
    for call in data["calls"]:
        ep = call["endpoint"]
        if ep not in stats:
            stats[ep] = {"total": 0, "success": 0, "recent_failures": []}
        
        stats[ep]["total"] += 1
        if call["success"]:
            stats[ep]["success"] += 1
        else:
            # Track recent failures (last 24h)
            call_time = datetime.fromisoformat(call["timestamp"])
            if datetime.now() - call_time < timedelta(hours=24):
                stats[ep]["recent_failures"].append({
                    "time": call["timestamp"],
                    "error": call["error"]
                })
    
    # Calculate success rates
    for ep in stats:
        total = stats[ep]["total"]
        success = stats[ep]["success"]
        stats[ep]["success_rate"] = success / total if total > 0 else 0
    
    return stats

def check_api_health() -> List[str]:
    """Check if any APIs are having issues. Returns list of alerts."""
    stats = get_reliability_stats()
    alerts = []
    
    for endpoint, data in stats.items():
        success_rate = data["success_rate"]
        recent_failures = len(data["recent_failures"])
        
        # Alert if success rate < 80% and we have recent data
        if data["total"] >= 5 and success_rate < 0.8:
            alerts.append(f"⚠️ {endpoint}: {success_rate:.1%} success rate ({recent_failures} failures in 24h)")
        
        # Alert if 3+ failures in last hour
        recent_hour_failures = [
            f for f in data["recent_failures"] 
            if datetime.now() - datetime.fromisoformat(f["time"]) < timedelta(hours=1)
        ]
        if len(recent_hour_failures) >= 3:
            alerts.append(f"🚨 {endpoint}: {len(recent_hour_failures)} failures in last hour")
    
    return alerts

def send_reliability_alert(message: str):
    """Send reliability alert to Discord."""
    try:
        from discord_alerts import send_alert
        send_alert(f"🔧 **API Reliability Alert**\n{message}")
    except Exception:
        print(f"Failed to send reliability alert: {message}")
