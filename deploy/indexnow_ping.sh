#!/bin/sh
# Run AFTER deploying (key file + pages must be live). Submits site URLs to IndexNow (Bing, Yandex, Seznam, Naver...).
# URL list: homepage, llms.txt, plus deploy/indexnow_urls.txt (regenerate with: python3 deploy/build_seo.py)
cd "$(dirname "$0")"
URLS=$(python3 -c 'import json;u=["https://fixitbot.pythonanywhere.com/"]+[l.strip() for l in open("indexnow_urls.txt") if l.strip()];print(json.dumps(sorted(set(u))))')
curl -s -o /dev/null -w "IndexNow HTTP %{http_code}\n" -X POST https://api.indexnow.org/indexnow -H "Content-Type: application/json; charset=utf-8" -d "{
 \"host\":\"fixitbot.pythonanywhere.com\",\"key\":\"7f3c9a1e5b2d4f6a8c0e1b3d5f7a9c2e\",
 \"keyLocation\":\"https://fixitbot.pythonanywhere.com/7f3c9a1e5b2d4f6a8c0e1b3d5f7a9c2e.txt\",
 \"urlList\":$URLS}"
