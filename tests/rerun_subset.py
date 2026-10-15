import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixit import diagnose, Intake
from cases import C
ids = [int(x) for x in sys.argv[1:]]; out = {}
for i in ids:
    t, e, u, k = C[i-1]
    try: r = diagnose(Intake(t, e)); out[i] = r; print(i, r["model_used"], r["confidence"], r["escalate"], r["escalate_reasons"], "|", r["root_cause"][:230], flush=True)
    except Exception as ex: print(i, "ERR", str(ex)[:200])
json.dump(out, open("tests/outputs_v2_subset.json", "w"), indent=1)
