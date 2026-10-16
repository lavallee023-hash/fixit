"""Manual admin: python3 web/admin.py credit EMAIL --fixes 5 | --unlimited-days 30
                   python3 web/admin.py status EMAIL
                   python3 web/admin.py verify cs_live_...   (re-run Stripe verification)
                   python3 web/admin.py queue               (open escalations)"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
envf = os.path.expanduser("~/fixit.env")
if os.path.exists(envf):
    for l in open(envf):
        if "=" in l and not l.strip().startswith("#"): k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
if os.path.isdir(os.path.expanduser("~/fixit-data")): os.environ.setdefault("FIXIT_DATA_DIR", os.path.expanduser("~/fixit-data"))
import credits
p = argparse.ArgumentParser(); sp = p.add_subparsers(dest="cmd", required=True)
c = sp.add_parser("credit"); c.add_argument("email"); c.add_argument("--fixes", type=int, default=0); c.add_argument("--unlimited-days", type=int, default=0); c.add_argument("--note", default="")
s = sp.add_parser("status"); s.add_argument("email")
v = sp.add_parser("verify"); v.add_argument("session_id")
sp.add_parser("queue")
a = p.parse_args()
if a.cmd == "credit":
    credits.grant(a.email, fixes=a.fixes, unlimited_days=a.unlimited_days, source="manual:" + a.note); print(credits.status(a.email))
elif a.cmd == "status": print(credits.status(a.email))
elif a.cmd == "verify": print(credits.verify_session(a.session_id)); 
elif a.cmd == "queue":
    q = os.path.join(credits.DATA, "escalations.jsonl")
    for l in (open(q) if os.path.exists(q) else []):
        r = json.loads(l)
        if r.get("status") == "open": print(r["id"], r["ts"], r["email"], r["tool"], "|", r["reason"], "|", (r["error_redacted"] or "")[:120])
