import argparse, json, sys
from .agent import diagnose, Intake, TOOLS
from .llm import LLMUnavailable
def fmt(r):
    o = [f"ROOT CAUSE: {r['root_cause']}", "", r.get("explanation", ""), "", "FIX STEPS:"]
    o += [f"  {i}. {s}" for i, s in enumerate(r.get("fix_steps", []), 1)]
    o += ["", f"PASTE THIS INTO {r['tool'].upper()}:", "-"*60, r.get("tool_prompt", ""), "-"*60,
          f"Confidence: {r['confidence']:.2f}   Escalate to human: {'YES' if r['escalate'] else 'no'}"]
    if r.get("missing_info"): o.append("Would help to know: " + "; ".join(r["missing_info"]))
    if r.get("secret_warning"): o.insert(0, "!! " + r["secret_warning"] + "\n")
    return "\n".join(o)
def main():
    p = argparse.ArgumentParser(prog="fixit", description="Diagnose a broken AI-built app.")
    p.add_argument("--tool", required=True, choices=TOOLS)
    p.add_argument("--error", help="error text (or '-' to read stdin)")
    p.add_argument("--screenshot"); p.add_argument("--repo"); p.add_argument("--context")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    err = sys.stdin.read() if a.error in (None, "-") else a.error
    try: r = diagnose(Intake(a.tool, err, a.screenshot, a.repo, a.context))
    except LLMUnavailable as e: sys.exit(f"No LLM available: {e}")
    print(json.dumps(r, indent=2) if a.json else fmt(r))
if __name__ == "__main__": main()
