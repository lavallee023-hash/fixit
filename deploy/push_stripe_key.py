#!/usr/bin/env python3
"""Box-side: pick the Stripe key that can read Checkout Sessions and hand it to the live app. Never prints secrets."""
import json, time, sys, os, urllib.request, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
import keyhandoff

URL = os.environ.get("FIXIT_URL", "https://fixitbot.pythonanywhere.com") + "/admin/stripe-key"
FILES = ["/home/box/secure/fixit-accounts.txt", "/home/box/secure/fixit-stripe.txt"]

def read_var(path, name):
    try:
        for line in open(path):
            if line.strip().startswith(name + "="): return line.split("=", 1)[1].strip() or None
    except OSError: pass

def stripe_ok(key):
    req = urllib.request.Request("https://api.stripe.com/v1/checkout/sessions?limit=1", headers={"Authorization": "Bearer " + key})
    try: return urllib.request.urlopen(req, timeout=20).status
    except urllib.error.HTTPError as e: return e.code
    except Exception: return 0

def pick_key(verbose=True):
    for p in FILES:
        k = read_var(p, "STRIPE_RESTRICTED_KEY")
        st = stripe_ok(k) if k else None
        if verbose: print(f"{p}: {'no key' if not k else 'HTTP %s' % st}")
        if st == 200: return p, k
    return None, None

def main():
    gem = read_var(FILES[0], "GEMINI_API_KEY")
    if not gem: sys.exit("GEMINI_API_KEY missing")
    src, key = pick_key()
    if not key: sys.exit("No Stripe key passed the Checkout Sessions check")
    if "--check" in sys.argv: print("would use", src); return
    ts = str(int(time.time())); ct = keyhandoff.encrypt(gem, ts, key)
    body = json.dumps({"ts": ts, "key_ct": ct, "sig": keyhandoff.sign(gem, ts, ct)}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try: r = urllib.request.urlopen(req, timeout=30); print(r.status, r.read().decode()[:200])
    except urllib.error.HTTPError as e: print("HTTP", e.code, e.read().decode()[:200])

if __name__ == "__main__": main()
