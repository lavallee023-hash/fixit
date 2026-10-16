import os, sys, json, hashlib, tempfile, time, datetime, threading, uuid, html
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flask import Flask, render_template, request, abort
from fixit.agent import diagnose, Intake, TOOLS
from fixit.llm import LLMUnavailable
from fixit.secrets import redact
import credits

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
DATA = os.environ.get("FIXIT_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA, exist_ok=True)
USAGE, QUEUE = os.path.join(DATA, "usage.json"), os.path.join(DATA, "escalations.jsonl")
FREE_PER_MONTH = int(os.environ.get("FIXIT_FREE_PER_MONTH", "3"))
PLANS = [("1 fix", "$9", os.environ.get("PAY_LINK_SINGLE", "")), ("5 fixes", "$29", os.environ.get("PAY_LINK_5PACK", "")),
         ("Unlimited / month", "$19/mo", os.environ.get("PAY_LINK_MONTHLY", ""))]
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
