"""Error Encyclopedia: SEO pages loaded from web/content/errors/*.json. Add a batch = drop new JSON files in."""
import os, json, re, html

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content", "errors")
SITE = "https://fixitbot.pythonanywhere.com"
SLUG = re.compile(r"^[a-z0-9-]+$")

def load():
    out = {}
    for f in sorted(os.listdir(DIR)):
        if f.endswith(".json"):
            with open(os.path.join(DIR, f)) as fh: e = json.load(fh)
            assert e["slug"] == f[:-5] and SLUG.match(e["slug"]), f
            out[e["slug"]] = e
    return out

def inline(text):
    """Escape text, then render `code` spans."""
    from markupsafe import Markup
    return Markup(re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text)))

def jsonld(e):
    url = f"{SITE}/errors/{e['slug']}"
    from markupsafe import Markup
    art = {"@context": "https://schema.org", "@type": "TechArticle", "headline": f"How to fix: {e['error']}"[:110],
           "description": e["meaning"], "url": url, "datePublished": e["date"], "dateModified": e.get("updated", e["date"]),
           "about": e["platform"], "author": {"@type": "Organization", "name": "FixIt", "url": SITE + "/"},
           "publisher": {"@type": "Organization", "name": "FixIt", "url": SITE + "/"}}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in e["faq"]]}
    return Markup(json.dumps([art, faq]).replace("<", "\\u003c"))
