import re
PATTERNS = [
 (r"sk-(?:proj-|live_|test_)?[A-Za-z0-9_\-]{16,}", "OpenAI/Stripe secret key"),
 (r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}", "Stripe secret key"),
 (r"whsec_[A-Za-z0-9]{16,}", "Stripe webhook secret"),
 (r"sb_secret_[A-Za-z0-9_\-]{10,}", "Supabase secret key"),
 (r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}", "JWT / Supabase key (service_role keys are secret)"),
 (r"AIza[0-9A-Za-z_\-]{35}", "Google API key"),
 (r"gh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
 (r"AKIA[0-9A-Z]{16}", "AWS access key"),
 (r"xox[abprs]-[A-Za-z0-9\-]{10,}", "Slack token"),
 (r"(?i)(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{12,}", "credential assignment"),
 (r"postgres(?:ql)?://[^\s:]+:[^\s@]+@", "database URL with password"),
]
def redact(text):
    found = []
    for pat, label in PATTERNS:
        if re.search(pat, text or ""):
            found.append(label); text = re.sub(pat, "[REDACTED]", text)
    return text, sorted(set(found))
