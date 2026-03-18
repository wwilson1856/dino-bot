"""
Quick API health check for the main flow.
"""
import requests
from datetime import datetime

def check_critical_apis():
    """Check if critical APIs are responding. Returns (success, errors)."""
    errors = []
    
    # Action Network
    try:
        r = requests.get("https://api.actionnetwork.com/web/v1/scoreboard/nhl", timeout=5)
        if r.status_code != 200:
            errors.append(f"Action Network: HTTP {r.status_code}")
    except Exception as e:
        errors.append(f"Action Network: {str(e)[:50]}")
    
    # ESPN
    try:
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard", timeout=5)
        if r.status_code != 200:
            errors.append(f"ESPN: HTTP {r.status_code}")
    except Exception as e:
        errors.append(f"ESPN: {str(e)[:50]}")
    
    return len(errors) == 0, errors

def log_api_health():
    """Log API health to file for monitoring."""
    success, errors = check_critical_apis()
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "errors": errors
    }
    
    try:
        import json
        with open("api_health.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
    
    return success, errors
