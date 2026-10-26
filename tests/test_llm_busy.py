import io, urllib.error
import fixit.llm as L

def test_503_skips_without_retry_and_benches(monkeypatch):
    calls = []
    def fake_urlopen(req, timeout=0):
        calls.append(req.full_url)
        if "busy-model" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, io.BytesIO(b'{"error":"high demand"}'))
        return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"{\\"ok\\": true}"}]}}]}')
    monkeypatch.setattr(L.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(L.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("should not sleep on 503")))
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("FIXIT_CHAIN", "gemini:busy-model,gemini:good-model")
    L._bench.clear()
    r, tag = L.complete_json("sys", "user")
    assert r == {"ok": True} and tag == "gemini:good-model"
    assert sum("busy-model" in u for u in calls) == 1
    assert L._bench["gemini:busy-model"] > L.time.time()
    calls.clear(); L.complete_json("sys", "user")
    assert not any("busy-model" in u for u in calls)   # benched, skipped on next request
    L._bench.clear()
