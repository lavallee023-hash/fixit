import os, sys, time, tempfile, json
os.environ["FIXIT_DATA_DIR"] = tempfile.mkdtemp(); os.environ["GEMINI_API_KEY"] = "gem-test"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import keyhandoff, app as appmod

def test_stats_signed_and_aggregate():
    appmod.bump("real@user.com"); appmod.bump("smoketest+1@mail.grokbot.com")
    appmod.enqueue("real@user.com", "lovable", "err", None, None, "all free AI models busy/out of quota")
    c = appmod.app.test_client(); ts = str(int(time.time()))
    assert c.post("/admin/stats", json={"ts": ts, "key_ct": "stats", "sig": "0" * 64}).status_code == 403
    r = c.post("/admin/stats", json={"ts": ts, "key_ct": "stats", "sig": keyhandoff.sign("gem-test", ts, "stats")})
    d = r.get_json(); assert r.status_code == 200 and d["users_this_month"] == 2 and d["escalations_real_total"] == 1
    assert "real@user.com" not in r.get_data(as_text=True)
