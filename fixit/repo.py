"""Read-only fetch of a PUBLIC GitHub repo's file tree + key config files. No auth, nothing stored."""
import json, re, urllib.request
from .secrets import redact
KEY_FILES = ["package.json", "vite.config.ts", "vite.config.js", "next.config.js", "next.config.mjs", "next.config.ts",
             "tsconfig.json", "netlify.toml", "vercel.json", ".replit", "supabase/config.toml", "requirements.txt", "README.md"]
def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "fixit-agent"}), timeout=30).read()
def fetch_repo_context(url, max_chars=12000):
    m = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)", url or "")
    if not m: return "(repo URL not a public github.com URL; skipped)"
    owner, name = m.group(1), m.group(2).removesuffix(".git")
    try:
        meta = json.loads(_get(f"https://api.github.com/repos/{owner}/{name}"))
        br = meta["default_branch"]
        tree = json.loads(_get(f"https://api.github.com/repos/{owner}/{name}/git/trees/{br}?recursive=1"))
    except Exception as e:
        return f"(could not read repo: {e})"
    paths = [t["path"] for t in tree.get("tree", []) if t["type"] == "blob" and "node_modules" not in t["path"]]
    out = ["FILE TREE (first 300):"] + paths[:300]
    for f in KEY_FILES:
        if f in paths:
            try:
                txt = _get(f"https://raw.githubusercontent.com/{owner}/{name}/{br}/{f}").decode(errors="replace")[:3000]
                out.append(f"\n--- {f} ---\n{redact(txt)[0]}")
            except Exception: pass
    if any(p.startswith(".env") and not p.endswith("example") for p in paths):
        out.append("\nWARNING: repo contains a committed .env file (not read).")
    return "\n".join(out)[:max_chars]
