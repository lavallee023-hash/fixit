"""Paid credits. Stored in DATA/credits.json keyed by hashed email: {"fixes": int, "unlimited_until": "YYYY-MM-DD", "sessions": [...]}.
Stripe: verifies a Checkout Session server-side with STRIPE_RESTRICTED_KEY (Checkout Sessions: Read). No webhook."""
import os, json, hashlib, threading, datetime, urllib.request, urllib.error, re

DATA = os.environ.get("FIXIT_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA, exist_ok=True)
CREDITS = os.path.join(DATA, "credits.json"); LEDGER = os.path.join(DATA, "payments.jsonl")
_lock = threading.Lock()

def h(email): return hashlib.sha256(("fixit:" + email.strip().lower()).encode()).hexdigest()[:24]
def _load():
    try: return json.load(open(CREDITS))
    except Exception: return {}
def _save(d):
    tmp = CREDITS + ".tmp"; json.dump(d, open(tmp, "w")); os.replace(tmp, CREDITS)

def status(email):
    r = _load().get(h(email), {})
    unl = r.get("unlimited_until")
    active = bool(unl and unl >= datetime.date.today().isoformat())
    return {"fixes": r.get("fixes", 0), "unlimited_until": unl if active else None}

def grant(email, fixes=0, unlimited_days=0, source="manual", ref=None):
    with _lock:
        d = _load(); r = d.setdefault(h(email), {})
        if ref and ref in r.get("sessions", []): return False          # idempotent per Stripe session
        r["fixes"] = r.get("fixes", 0) + int(fixes)
        if unlimited_days:
            base = max(datetime.date.today(), datetime.date.fromisoformat(r.get("unlimited_until") or "1970-01-01"))
            r["unlimited_until"] = (base + datetime.timedelta(days=int(unlimited_days))).isoformat()
        if ref: r.setdefault("sessions", []).append(ref)
        _save(d)
        with open(LEDGER, "a") as f:
            f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "email_hash": h(email),
                                "fixes": fixes, "unlimited_days": unlimited_days, "source": source, "ref": ref}) + "\n")
        return True

def can_use_paid(email):
    s = status(email); return bool(s["unlimited_until"]) or s["fixes"] > 0

def consume(email):
    """Call after a successful paid diagnosis. Unlimited users aren't decremented."""
    with _lock:
        d = _load(); r = d.get(h(email))
        if not r: return
        if r.get("unlimited_until") and r["unlimited_until"] >= datetime.date.today().isoformat(): return
        if r.get("fixes", 0) > 0: r["fixes"] -= 1; _save(d)

# ---- Stripe ----
def _plan_for(session):
    """Map a Checkout Session to a plan. Prefer Payment Link ids from env, fall back to amount/mode."""
    pl = session.get("payment_link")
    ids = {os.environ.get("STRIPE_PL_SINGLE"): "single", os.environ.get("STRIPE_PL_5PACK"): "5pack", os.environ.get("STRIPE_PL_MONTHLY"): "monthly"}
    if pl and pl in ids and pl: return ids[pl]
    if session.get("mode") == "subscription": return "monthly"
    amt = session.get("amount_total")
    return {900: "single", 2900: "5pack", 1900: "monthly"}.get(amt)

PLAN_GRANTS = {"single": dict(fixes=1), "5pack": dict(fixes=5), "monthly": dict(unlimited_days=30)}

class PaymentError(Exception): pass

def verify_session(session_id):
    key = os.environ.get("STRIPE_RESTRICTED_KEY")
    if not key: raise PaymentError("Payments aren't configured yet.")
    if not re.fullmatch(r"cs_(live|test)_[A-Za-z0-9]{10,200}", session_id or ""): raise PaymentError("Invalid session id.")
    req = urllib.request.Request(f"https://api.stripe.com/v1/checkout/sessions/{session_id}", headers={"Authorization": "Bearer " + key})
    try: s = json.load(urllib.request.urlopen(req, timeout=20))
    except urllib.error.HTTPError as e: raise PaymentError(f"Couldn't verify payment with Stripe ({e.code}).")
    if s.get("status") != "complete" or s.get("payment_status") not in ("paid", "no_payment_required"):
        raise PaymentError("This checkout isn't paid yet.")
    email = (s.get("customer_details") or {}).get("email") or s.get("customer_email")
    plan = _plan_for(s)
    if not email or not plan: raise PaymentError("Paid, but we couldn't match the plan/email. We've logged it; email us and we'll credit you.")
    new = grant(email, source="stripe:" + plan, ref=session_id, **PLAN_GRANTS[plan])
    return {"email": email, "plan": plan, "new": new, "livemode": s.get("livemode")}
