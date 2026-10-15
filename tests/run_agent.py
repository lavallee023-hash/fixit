"""Run the agent on all cases; saves raw outputs (grading is separate: tests/grades.json)."""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixit import diagnose, Intake
from cases import C
models = os.environ.get("FIXIT_EVAL_MODELS", "gemini-3.5-flash,gemini-3.7-flash,gemini-3.6-flash").split(",")
out = json.load(open("tests/outputs.json")) if os.path.exists("tests/outputs.json") else {}
for i, (tool, err, url, known) in enumerate(C, 1):
    if str(i) in out and "output" in out[str(i)]: continue
    while models:
        try:
            r = diagnose(Intake(tool, err), model=models[0]); out[str(i)] = {"model": models[0], "tool": tool, "error": err, "source": url, "known_fix": known, "output": r}; break
        except Exception as e:
            if "429" in str(e): print("quota hit on", models.pop(0)); continue
            out[str(i)] = {"error_run": str(e)[:200]}; break
    print(i, out.get(str(i), {}).get("model"), out.get(str(i), {}).get("output", {}).get("confidence"), flush=True)
    json.dump(out, open("tests/outputs.json", "w"), indent=2)
