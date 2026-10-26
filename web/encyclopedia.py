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
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "FixIt", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Error Encyclopedia", "item": SITE + "/errors/"},
        {"@type": "ListItem", "position": 3, "name": e["error"][:110], "item": url}]}
    return Markup(json.dumps([art, faq, crumbs]).replace("<", "\\u003c"))

def index_jsonld(errors):
    """CollectionPage + ItemList for /errors/ so AI search and rich results see every page."""
    from markupsafe import Markup
    col = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "FixIt Error Encyclopedia",
           "url": SITE + "/errors/", "description": "Plain-English fixes for common errors in apps built with Lovable, Bolt, Cursor, v0, Replit and Supabase.",
           "dateModified": max(e.get("updated", e["date"]) for e in errors.values()),
           "mainEntity": {"@type": "ItemList", "numberOfItems": len(errors), "itemListElement": [
               {"@type": "ListItem", "position": i, "url": f"{SITE}/errors/{k}", "name": e["error"][:110]}
               for i, (k, e) in enumerate(errors.items(), 1)]}}
    return Markup(json.dumps(col).replace("<", "\\u003c"))
