"""
Run this to sniff every network request FanDuel makes.
It will print all URLs so we can find the right API endpoints to intercept.
python sniff.py
"""
from playwright.sync_api import sync_playwright

URL = "https://sportsbook.fanduel.com/basketball/nba"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
    )
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page = context.new_page()

    print(f"Loading {URL} ...\n")
    print("ALL NETWORK REQUESTS:")
    print("-" * 80)

    def log_request(request):
        if any(x in request.url for x in ["api", "odds", "event", "market", "sport", "bet"]):
            print(f"[{request.method}] {request.url}")

    def log_response(response):
        if any(x in response.url for x in ["api", "odds", "event", "market", "sport", "bet"]):
            print(f"  -> {response.status} {response.url}")

    page.on("request", log_request)
    page.on("response", log_response)

    try:
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        print("\nPage loaded. Waiting 8 seconds for all API calls to fire...\n")
        page.wait_for_timeout(8000)
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "-" * 80)
    print("Done. Look above for API URLs containing odds/events data.")
    browser.close()
