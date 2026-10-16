import os, sys, time, tempfile, stat
os.environ["FIXIT_DATA_DIR"] = tempfile.mkdtemp()
os.environ["GEMINI_API_KEY"] = "gem-test"
os.environ.pop("STRIPE_RESTRICTED_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import keyhandoff, credits, app as appmod

def payload(key, ts=None, secret="gem-test"):
    ts = str(ts or int(time.time())); ct = keyhandoff.encrypt(secret, ts, key)
    return {"ts": ts, "key_ct": ct, "sig": keyhandoff.sign(secret, ts, ct)}

def test_roundtrip():
    assert keyhandoff.decrypt("s", "1", keyhandoff.encrypt("s", "1", "rk_live_abc")) == "rk_live_abc"
    assert "rk_live" not in keyhandoff.encrypt("s", "1", "rk_live_abc")

def test_endpoint_writes_file(monkeypatch):
    monkeypatch.setattr(credits, "stripe_key_works", lambda k: True)
    r = appmod.app.test_client().post("/admin/stripe-key", json=payload("rk_test_XYZ123"))
    assert r.status_code == 200 and r.get_json() == {"ok": True, "verified": True}
    assert "rk_test" not in r.get_data(as_text=True)
    assert credits.stripe_key() == "rk_test_XYZ123"
    assert stat.S_IMODE(os.stat(credits.KEY_FILE).st_mode) == 0o600

def test_rejects_bad_sig_and_old_ts():
    c = appmod.app.test_client()
    p = payload("rk_test_A"); p["sig"] = "0" * 64
    assert c.post("/admin/stripe-key", json=p).status_code == 403
    assert c.post("/admin/stripe-key", json=payload("rk_test_A", ts=int(time.time()) - 400)).status_code == 403
    assert c.post("/admin/stripe-key", json=payload("rk_test_A", secret="wrong")).status_code == 403

def test_env_overrides_file(monkeypatch):
    monkeypatch.setenv("STRIPE_RESTRICTED_KEY", "rk_env")
    assert credits.stripe_key() == "rk_env"
