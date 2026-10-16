"""Regenerate web/static/sitemap.xml, the Error Encyclopedia section of llms.txt, and deploy/indexnow_urls.txt. Run after adding a batch."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web"))
import encyclopedia as enc
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
E = enc.load(); S = enc.SITE; today = datetime.date.today().isoformat()
urls = [f"{S}/errors/"] + [f"{S}/errors/{k}" for k in E]
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
      f'  <url><loc>{S}/</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>',
      f'  <url><loc>{S}/llms.txt</loc><lastmod>{today}</lastmod></url>',
      f'  <url><loc>{S}/errors/</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>']
sm += [f'  <url><loc>{S}/errors/{k}</loc><lastmod>{e.get("updated", e["date"])}</lastmod><priority>0.8</priority></url>' for k, e in E.items()]
open(os.path.join(ROOT, "web/static/sitemap.xml"), "w").write("\n".join(sm + ["</urlset>", ""]))
p = os.path.join(ROOT, "web/static/llms.txt"); txt = open(p).read().split("\n## Error Encyclopedia")[0].rstrip()
sec = ["", "## Error Encyclopedia", f"Index: {S}/errors/"] + [f"- [{e['error']}]({S}/errors/{k}) ({e['platform']}): {e['meaning'].split('. ')[0].rstrip('.')}." for k, e in E.items()]
open(p, "w").write(txt + "\n" + "\n".join(sec) + "\n")
open(os.path.join(ROOT, "deploy/indexnow_urls.txt"), "w").write("\n".join(urls + [f"{S}/sitemap.xml", f"{S}/llms.txt"]) + "\n")
print(len(E), "pages")
