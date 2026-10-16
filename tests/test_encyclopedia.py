import os, sys, json, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "web"))
os.environ.setdefault("FIXIT_DATA_DIR", "/tmp/fixit-test-data")
import app as appmod
import encyclopedia
C = appmod.app.test_client()
E = encyclopedia.load()

def test_count_and_fields():
    assert len(E) >= 25
    for e in E.values():
        for k in ("slug", "error", "platform", "meaning", "causes", "steps", "prompt", "faq", "date"):
            assert e[k], (e["slug"], k)
        assert len(e["steps"]) >= 3 and len(e["causes"]) >= 2 and len(e["faq"]) >= 2

def test_index_lists_all():
    r = C.get("/errors/"); assert r.status_code == 200
    body = r.get_data(as_text=True)
    for s in E: assert f'/errors/{s}"' in body
    assert C.get("/errors").status_code == 301

def test_pages_render_with_jsonld():
    for s, e in E.items():
        r = C.get(f"/errors/{s}"); assert r.status_code == 200, s
        b = r.get_data(as_text=True)
        assert "<h1>" in b and "Try FixIt free" in b
        assert f'rel="canonical" href="https://fixitbot.pythonanywhere.com/errors/{s}"' in b
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', b, re.S).group(1))
        assert {x["@type"] for x in ld} == {"TechArticle", "FAQPage"}

def test_unknown_404():
    assert C.get("/errors/nope-not-real").status_code == 404

def test_sitemap_llms_home_link():
    sm = open(os.path.join(ROOT, "web/static/sitemap.xml")).read()
    llms = open(os.path.join(ROOT, "web/static/llms.txt")).read()
    for s in E:
        assert f"/errors/{s}</loc>" in sm and f"/errors/{s})" in llms
    home = C.get("/").get_data(as_text=True)
    assert home.count('href="/errors/"') >= 2

def test_csv_matches():
    rows = open(os.path.join(ROOT, "marketing/encyclopedia.csv")).read()
    for s in E: assert s in rows
