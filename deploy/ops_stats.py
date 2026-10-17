#!/usr/bin/env python3
"""Box-side: fetch aggregate usage stats from the live app (signed). Prints JSON, never secrets."""
import json, time, sys, os, urllib.request, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web")); sys.path.insert(0, os.path.dirname(__file__))
import keyhandoff
from push_stripe_key import read_var, FILES
URL = os.environ.get("FIXIT_URL", "https://fixitbot.pythonanywhere.com") + "/admin/stats"
gem = read_var(FILES[0], "GEMINI_API_KEY"); ts = str(int(time.time()))
body = json.dumps({"ts": ts, "key_ct": "stats", "sig": keyhandoff.sign(gem, ts, "stats")}).encode()
try: print(urllib.request.urlopen(urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"}), timeout=30).read().decode())
except urllib.error.HTTPError as e: print("HTTP", e.code, e.read().decode()[:200])
