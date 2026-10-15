"""Pluggable LLM backend with free-tier rotation.
FIXIT_CHAIN (comma list) controls order. Entries: "gemini:<model>", "groq:<model>", "openrouter:<model>", "openai:<model>".
Entries whose key is missing are skipped. A model that returns 429 (quota) is benched for FIXIT_BENCH_SECONDS (default 1h)
and the next one is tried. Keys: GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY (+FIXIT_BASE_URL).
Never fabricates output: if every model fails, raises LLMUnavailable."""
import os, json, base64, mimetypes, urllib.request, urllib.error, time, threading

class LLMUnavailable(RuntimeError): pass
class _Quota(Exception): pass

DEFAULT_CHAIN = ("gemini:gemini-3.8-flash,gemini:gemini-3.7-flash,gemini:gemini-3.6-flash,gemini:gemini-3.5-flash,"
                 "groq:openai/gpt-oss-120b,openrouter:openrouter/free,"
                 "gemini:gemini-3.5-flash-lite,gemini:gemini-3.1-flash-lite,groq:openai/gpt-oss-20b")
KEYS = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY", "openai": "OPENAI_API_KEY"}
_bench, _lock = {}, threading.Lock()

def _post(url, body, headers, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    for attempt in range(2):
        try:
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except urllib.error.HTTPError as e:
            if e.code == 429: raise _Quota(e.read()[:200])
            if e.code in (500, 502, 503) and attempt == 0: time.sleep(3); continue
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:200]!r}")

def _img(path):
    mt = mimetypes.guess_type(path)[0] or "image/png"
    return mt, base64.b64encode(open(path, "rb").read()).decode()

def _call(prov, model, system, user, image_path):
    key = os.environ[KEYS[prov]]
    if prov == "gemini":
        parts = [{"text": user}]
        if image_path:
            mt, b = _img(image_path); parts.append({"inline_data": {"mime_type": mt, "data": b}})
        d = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                  {"system_instruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": parts}],
                   "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}, {"x-goog-api-key": key})
        return json.loads(d["candidates"][0]["content"]["parts"][0]["text"])
    base = {"groq": "https://api.groq.com/openai/v1", "openrouter": "https://openrouter.ai/api/v1",
            "openai": os.environ.get("FIXIT_BASE_URL", "https://api.openai.com/v1")}[prov]
    content = user
    if image_path and prov != "groq":   # groq text models: screenshot is skipped
        mt, b = _img(image_path)
        content = [{"type": "text", "text": user}, {"type": "image_url", "image_url": {"url": f"data:{mt};base64,{b}"}}]
    d = _post(base + "/chat/completions", {"model": model, "temperature": 0.2, "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}]},
              {"Authorization": "Bearer " + key})
    txt = d["choices"][0]["message"]["content"].strip()
    if txt.startswith("```"): txt = txt.strip("`").removeprefix("json").strip()
    return json.loads(txt)

def available_chain():
    chain = [c.split(":", 1) for c in os.environ.get("FIXIT_CHAIN", DEFAULT_CHAIN).split(",") if ":" in c]
    return [(p, m) for p, m in chain if p in KEYS and os.environ.get(KEYS[p])]

def complete_json(system, user, image_path=None, model=None):
    """Returns (result_dict, "provider:model")."""
    chain = [("gemini" if not ":" in model else model.split(":")[0], model.split(":")[-1])] if model else available_chain()
    if not chain: raise LLMUnavailable("No LLM key set. Set any of: " + ", ".join(KEYS.values()))
    bench_s = int(os.environ.get("FIXIT_BENCH_SECONDS", "3600")); errs = []
    for prov, m in chain:
        tag = f"{prov}:{m}"
        with _lock:
            if _bench.get(tag, 0) > time.time(): continue
        try:
            return _call(prov, m, system, user, image_path), tag
        except _Quota:
            with _lock: _bench[tag] = time.time() + bench_s
            errs.append(f"{tag} quota")
        except Exception as e:
            errs.append(f"{tag} {str(e)[:80]}")
    raise LLMUnavailable("All models failed or out of quota: " + "; ".join(errs))
