import os, sys, json, hashlib, tempfile, time, datetime, threading, uuid, html
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flask import Flask, render_template, request, abort, redirect
from fixit.agent import diagnose, Intake, TOOLS
from fixit.llm import LLMUnavailable
from fixit.secrets import redact
import credits
import encyclopedia
import keyhandoff

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
DATA = os.environ.get("FIXIT_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))


@app.context_processor
def _site_verification():
    """Read site-verification tokens fresh on each request (no reload needed)."""
    try:
        with open(os.path.join(DATA, "impact-verify.txt")) as f:
            tok = f.read().strip()
    except OSError:
        tok = ""
    return {"impact_verify": tok}
os.makedirs(DATA, exist_ok=True)
USAGE, QUEUE = os.path.join(DATA, "usage.json"), os.path.join(DATA, "escalations.jsonl")
FREE_PER_MONTH = int(os.environ.get("FIXIT_FREE_PER_MONTH", "3"))
PLANS = [("1 fix", "$9", os.environ.get("PAY_LINK_SINGLE", "https://buy.stripe.com/8x24gz4RD0LOeB6b59g3600")), ("5 fixes", "$29", os.environ.get("PAY_LINK_5PACK", "https://buy.stripe.com/5kQeVdesd0LOboUflpg3601")),
         ("Unlimited / month", "$19/mo", os.environ.get("PAY_LINK_MONTHLY", "https://buy.stripe.com/3cIeVddo9cuwfFa6OTg3602"))]
_lock = threading.Lock()
INDEXNOW_KEY = "7f3c9a1e5b2d4f6a8c0e1b3d5f7a9c2e"

def _hash(email): return hashlib.sha256(("fixit:" + email.strip().lower()).encode()).hexdigest()[:24]
def _month(): return datetime.date.today().strftime("%Y-%m")
def _usage():
    try: return json.load(open(USAGE))
    except Exception: return {}
def used(email): return _usage().get(_hash(email), {}).get(_month(), 0)
def bump(email):
    with _lock:
        u = _usage(); h = _hash(email); u.setdefault(h, {})[_month()] = u.get(h, {}).get(_month(), 0) + 1
        json.dump(u, open(USAGE, "w"))

def enqueue(email, tool, err, repo, result, reason):
    rec = {"id": uuid.uuid4().hex[:8], "ts": datetime.datetime.now().isoformat(timespec="seconds"), "email": email, "tool": tool,
           "error_redacted": redact(err)[0][:4000], "repo": repo, "reason": reason,
           "root_cause": (result or {}).get("root_cause"), "confidence": (result or {}).get("confidence"), "status": "open"}
    with _lock, open(QUEUE, "a") as f: f.write(json.dumps(rec) + "\n")
    return rec["id"]

@app.get("/")
def index(): return render_template("index.html", tools=TOOLS, free=FREE_PER_MONTH, plans=PLANS)

@app.get("/healthz")
def health(): return "ok"

@app.post("/diagnose")
def do_diagnose():
    email = (request.form.get("email") or "").strip()
    tool = request.form.get("tool", "")
    err = (request.form.get("error") or "").strip()[:8000]
    repo = (request.form.get("repo") or "").strip() or None
    if "@" not in email or tool not in TOOLS or (not err and not request.files.get("screenshot")):
        return render_template("index.html", tools=TOOLS, free=FREE_PER_MONTH, plans=PLANS, error="Please give your email, tool, and the error text or a screenshot."), 400
    if repo and not repo.startswith("https://github.com/"):
        return render_template("index.html", tools=TOOLS, free=FREE_PER_MONTH, plans=PLANS, error="Repo must be a public https://github.com/... URL."), 400
    paid = used(email) >= FREE_PER_MONTH
    if paid and not credits.can_use_paid(email):
        return render_template("paywall.html", plans=PLANS, free=FREE_PER_MONTH)
    shot = None; f = request.files.get("screenshot")
    try:
        if f and f.filename:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in (".png", ".jpg", ".jpeg", ".webp"): abort(400)
            fd, shot = tempfile.mkstemp(suffix=ext); os.close(fd); f.save(shot)
        try:
            r = diagnose(Intake(tool, err or "(see screenshot)", shot, repo, request.form.get("context")))
        except LLMUnavailable:
            qid = enqueue(email, tool, err, repo, None, "all free AI models busy/out of quota")
            return render_template("busy.html", qid=qid)
    finally:
        if shot and os.path.exists(shot): os.remove(shot)   # screenshots are never kept
    if paid: credits.consume(email)
    else: bump(email)
    qid = enqueue(email, tool, err, repo, r, "; ".join(r["escalate_reasons"])) if r["escalate"] else None
    return render_template("result.html", r=r, qid=qid, left=max(0, FREE_PER_MONTH - used(email)), cs=credits.status(email))

@app.get("/paid")
def paid():
    try: info = credits.verify_session(request.args.get("session_id", ""))
    except credits.PaymentError as e: return render_template("paid.html", error=str(e)), 400
    return render_template("paid.html", info=info, cs=credits.status(info["email"]))

ERRORS = encyclopedia.load()

@app.get("/errors/")
def errors_index():
    groups = {}
    for e in ERRORS.values(): groups.setdefault(e["platform"], []).append(e)
    return render_template("errors_index.html", errors=ERRORS, groups=sorted(groups.items()))
@app.get("/errors")
def errors_noslash(): return redirect("/errors/", 301)
@app.get("/errors/<slug>")
def error_page(slug):
    e = ERRORS.get(slug)
    if not e: abort(404)
    related = [r for r in ERRORS.values() if r["platform"] == e["platform"] and r["slug"] != slug][:5]
    return render_template("error_page.html", e=e, ld=encyclopedia.jsonld(e), inline=encyclopedia.inline, related=related)

@app.get("/robots.txt")
def robots(): return app.send_static_file("robots.txt")
@app.get("/sitemap.xml")
def sitemap(): return app.send_static_file("sitemap.xml")
@app.get("/llms.txt")
def llms(): return app.send_static_file("llms.txt")
@app.get("/<key>.txt")
def indexnow_key(key):
    if key == INDEXNOW_KEY: return INDEXNOW_KEY, 200, {"Content-Type": "text/plain"}
    abort(404)

@app.route("/admin/stripe-key", methods=["POST"])
def admin_stripe_key():
    secret = os.environ.get("GEMINI_API_KEY", "")
    d = request.get_json(silent=True) or {}
    ts, ct, sig = d.get("ts"), d.get("key_ct"), d.get("sig")
    if not keyhandoff.check(secret, ts, ct, sig): return {"ok": False, "error": "unauthorized"}, 403
    try: key = keyhandoff.decrypt(secret, ts, ct).strip()
    except Exception: return {"ok": False, "error": "bad payload"}, 400
    if not key.startswith(("rk_", "sk_")): return {"ok": False, "error": "bad key format"}, 400
    credits.save_stripe_key(key)
    return {"ok": True, "verified": credits.stripe_key_works(key)}

TEST_EMAIL_MARKERS = ("smoketest", "test@example.com", "@mail.grokbot.com")

def _stats():
    """Aggregate-only usage stats (no emails or error text)."""
    now = datetime.datetime.now(); m = _month(); day_ago = (now - datetime.timedelta(days=1)).isoformat(timespec="seconds")
    usage = _usage()
    q = []
    try:
        for l in open(QUEUE): q.append(json.loads(l))
    except OSError: pass
    def real(r): return not any(t in (r.get("email") or "").lower() for t in TEST_EMAIL_MARKERS)
    rq = [r for r in q if real(r)]
    reasons = {}
    for r in rq:
        k = "busy" if "busy" in (r.get("reason") or "") else ("low confidence" if "confidence" in (r.get("reason") or "") else "other")
        reasons[k] = reasons.get(k, 0) + 1
    try: cr = json.load(open(credits.CREDITS))
    except Exception: cr = {}
    pays = 0
    try: pays = sum(1 for l in open(credits.LEDGER) if '"source": "stripe' in l)
    except OSError: pass
    return {"users_this_month": sum(1 for v in usage.values() if v.get(m)), "free_fixes_this_month": sum(v.get(m, 0) for v in usage.values()),
            "users_all_time": len(usage), "escalations_real_total": len(rq), "escalations_real_open": sum(1 for r in rq if r.get("status") == "open"),
            "escalations_real_24h": sum(1 for r in rq if (r.get("ts") or "") >= day_ago), "escalation_reasons": reasons,
            "busy_24h_all": sum(1 for r in q if "busy" in (r.get("reason") or "") and (r.get("ts") or "") >= day_ago),
            "paid_accounts": len(cr), "stripe_credits_granted": pays, "server_time": now.isoformat(timespec="seconds")}

@app.route("/admin/stats", methods=["POST"])
def admin_stats():
    """Signed with the same HMAC as /admin/stripe-key: key_ct must be the literal string "stats"."""
    d = request.get_json(silent=True) or {}
    if d.get("key_ct") != "stats" or not keyhandoff.check(os.environ.get("GEMINI_API_KEY", ""), d.get("ts"), "stats", d.get("sig")):
        return {"ok": False, "error": "unauthorized"}, 403
    return {"ok": True, **_stats()}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
