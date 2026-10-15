from dataclasses import dataclass
from typing import Optional
import os, re
from .llm import complete_json
from .secrets import redact
from .repo import fetch_repo_context

TOOLS = ["lovable", "bolt", "cursor", "replit", "v0", "supabase", "other"]
ESCALATE_BELOW = float(os.environ.get("FIXIT_ESCALATE_BELOW", "0.7"))

SYSTEM = """You are FixIt, a senior engineer who helps non-coders whose AI-built apps (Lovable, Bolt, Cursor, Replit, v0, Supabase) broke.
Diagnose the ROOT CAUSE from the evidence. Be concrete and correct.

KNOWN PITFALLS (check these first when relevant):
- Supabase "new row violates row-level security policy" (42501/403) on insert: either no INSERT policy, OR the client chains .select()/.single() after .insert() (Lovable does this by default) which ALSO needs a SELECT policy that lets the user read the new row. Storage uploads do INSERT...RETURNING, so storage.objects needs a SELECT policy mirroring the INSERT policy. If the user says an insert policy already exists, the missing SELECT policy is the most likely cause.
- Supabase select returns [] with no error: RLS on and no SELECT policy matching the role (or user not logged in).
- Supabase Edge Function 401 "Invalid JWT" after moving to new sb_publishable_/sb_secret_ keys: those keys are not JWTs; the function's built-in verify_jwt gate rejects them. Fix: set verify_jwt = false for that function (supabase/config.toml [functions.<name>] or deploy --no-verify-jwt) and check auth inside the function (e.g. supabase.auth.getUser with the user's token).
- Edge Function CORS: if the message mentions "preflight", the function doesn't answer OPTIONS -> return corsHeaders on OPTIONS. If it says "No 'Access-Control-Allow-Origin' header" WITHOUT "preflight" (or broke after adding a new integration/secret), the function is most likely CRASHING (e.g. missing secret like RESEND_API_KEY) and the 500 has no CORS headers -> read the function logs, set the missing secret, add corsHeaders to error responses too.
- Vite env vars must start with VITE_ and are baked in at build time (redeploy after changing). SPA 404 on refresh -> _redirects (Netlify) or vercel.json rewrite.
- Google OAuth redirect_uri_mismatch with Supabase: the Google client's Authorized redirect URI must be https://<project-ref>.supabase.co/auth/v1/callback; app domains go in Supabase Auth Site URL / Redirect URLs.

SAFETY RULES:
- Never ask for API keys/passwords/secrets. Never tell users to paste secrets into chats.
- NEVER suggest disabling RLS, making a table/bucket public, "allow public read", "using (true)" for user data, or putting service_role/secret keys in frontend code, even "temporarily for testing".
- Plain English for a non-developer. Steps doable in their tool or dashboards.
- tool_prompt: ready-to-paste prompt for the user's AI builder. Name the exact file/function/table/setting if known, state the root cause, what to change, what NOT to touch, how to verify; tell it to diagnose before editing and not rewrite unrelated files.

CALIBRATION: List your top 3 candidate causes with probabilities summing to <=1. confidence = probability of the top one. Set input_quality to "vague" if there is no concrete error message/log (e.g. "it's broken", "login doesn't work") or key context is missing.
Return JSON: {"top_causes":[{"cause":str,"probability":float}], "root_cause": str, "explanation": str, "fix_steps": [str], "tool_prompt": str, "confidence": float, "input_quality": "clear"|"vague", "missing_info": [str], "category": str}"""

UNSAFE = re.compile(r"disabl\w*\s+(row[- ]level security|rls)|(make|set)\s+(the\s+)?(table|bucket|data)\s+public|public read|allow (public|anyone|everyone)|service[_ ]role\s+key\s+(in|on)\s+(the\s+)?(frontend|client|browser)", re.I)
ERRORISH = re.compile(r"error|exception|failed|\b[45]\d\d\b|denied|violat|undefined|not found|cannot|can't resolve|refused|invalid|timeout|mismatch|blocked", re.I)

@dataclass
class Intake:
    tool: str
    error_text: str
    screenshot_path: Optional[str] = None
    repo_url: Optional[str] = None
    context: Optional[str] = None

NEG = re.compile(r"(not|never|n't|avoid|without|instead of|rather than|no need to)\W+(\w+\W+){0,4}$", re.I)
def _unsafe(text):
    for m in UNSAFE.finditer(text or ""):
        if not NEG.search(text[max(0, m.start()-40):m.start()]): return True
    return False

def _vague(text, has_shot):
    return not has_shot and (len(text.strip()) < 40 or not ERRORISH.search(text))

def diagnose(intake: Intake, model=None) -> dict:
    tool = intake.tool.lower().strip()
    if tool not in TOOLS: raise ValueError(f"tool must be one of {TOOLS}")
    err, found = redact(intake.error_text or "")
    ctx, found2 = redact(intake.context or "")
    found = sorted(set(found + found2))
    parts = [f"TOOL: {intake.tool}", f"ERROR / WHAT THE USER SEES:\n{err}"]
    if ctx: parts.append(f"USER CONTEXT:\n{ctx}")
    if intake.repo_url: parts.append("PUBLIC REPO (read-only snapshot):\n" + fetch_repo_context(intake.repo_url))
    if intake.screenshot_path: parts.append("A screenshot is attached; read any error text in it.")
    r, used = complete_json(SYSTEM, "\n\n".join(parts), image_path=intake.screenshot_path, model=model)
    conf = max(0.0, min(1.0, float(r.get("confidence", 0) or 0)))
    reasons = []
    tc = sorted(r.get("top_causes") or [], key=lambda c: -float(c.get("probability", 0) or 0))
    if conf < ESCALATE_BELOW: reasons.append(f"low confidence {conf:.2f}")
    if len(tc) >= 2 and float(tc[0].get("probability", 0)) - float(tc[1].get("probability", 0)) < 0.25:
        reasons.append("top causes disagree"); conf = min(conf, 0.6)
    if r.get("input_quality") == "vague" or _vague(err + " " + ctx, bool(intake.screenshot_path)):
        reasons.append("vague input (no concrete error)"); conf = min(conf, 0.5)
    # safety filter: drop unsafe steps, flag
    steps = r.get("fix_steps") or []
    safe = [s for s in steps if not _unsafe(s)]
    if len(safe) != len(steps) or _unsafe(r.get("tool_prompt", "")):
        reasons.append("unsafe advice removed")
        r["tool_prompt"] = UNSAFE.sub("[removed: never weaken security]", r.get("tool_prompt", ""))
        safe.append("Do NOT disable Row Level Security or make tables public to 'test' - add the specific policy instead.")
    r["fix_steps"] = safe
    r["confidence"], r["escalate"], r["escalate_reasons"] = conf, bool(reasons), reasons
    r["secret_warning"] = (f"You pasted what looks like a secret ({', '.join(found)}). We removed it before analysis and never stored it. "
                           "Rotate (regenerate) that key now in its dashboard and treat it as leaked.") if found else None
    r["tool"], r["model_used"] = tool, used
    return r
