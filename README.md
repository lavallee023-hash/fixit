# FixIt v1 - diagnosis agent for broken AI-built apps
Usage:
  ./fixit.sh --tool lovable --error "new row violates row-level security policy..." [--screenshot shot.png] [--repo https://github.com/u/r] [--context "..."] [--json]
  echo "<error>" | ./fixit.sh --tool bolt
Python:  from fixit import diagnose, Intake; diagnose(Intake("cursor", err, screenshot_path=None, repo_url=None))
Returns: root_cause, explanation, fix_steps, tool_prompt, confidence, escalate (conf < FIXIT_ESCALATE_BELOW, default 0.6), missing_info, secret_warning.
LLM: FIXIT_PROVIDER=gemini (GEMINI_API_KEY, FIXIT_MODEL default gemini-3.5-flash) or FIXIT_PROVIDER=openai (OPENAI_API_KEY, FIXIT_BASE_URL, FIXIT_MODEL). No key -> clear error, no fake output.
Secrets: pasted keys are regex-redacted before the LLM call, never stored; user gets a rotate-now warning. Repo access: unauthenticated public GitHub reads only (tree + key config files, redacted; .env files never read).
Eval: tests/cases.py (30 cases + source URLs + known fixes), tests/run_agent.py -> tests/outputs.json, manual grades in tests/grades.json.
