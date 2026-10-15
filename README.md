# FixIt v1 - diagnosis agent for broken AI-built apps
Usage:
  ./fixit.sh --tool lovable --error "new row violates row-level security policy..." [--screenshot shot.png] [--repo https://github.com/u/r] [--context "..."] [--json]
  echo "<error>" | ./fixit.sh --tool bolt
Python:  from fixit import diagnose, Intake; diagnose(Intake("cursor", err, screenshot_path=None, repo_url=None))
Returns: root_cause, explanation, fix_steps, tool_prompt, confidence, escalate (conf < FIXIT_ESCALATE_BELOW, default 0.6), missing_info, secret_warning.
LLM: FIXIT_PROVIDER=gemini (GEMINI_API_KEY, FIXIT_MODEL default gemini-3.5-flash) or FIXIT_PROVIDER=openai (OPENAI_API_KEY, FIXIT_BASE_URL, FIXIT_MODEL). No key -> clear error, no fake output.
Secrets: pasted keys are regex-redacted before the LLM call, never stored; user gets a rotate-now warning. Repo access: unauthenticated public GitHub reads only (tree + key config files, redacted; .env files never read).
Eval: tests/cases.py (30 cases + source URLs + known fixes), tests/run_agent.py -> tests/outputs.json, manual grades in tests/grades.json.

## Deploy (free, no credit card): PythonAnywhere
1. Sign up (email) at https://www.pythonanywhere.com/registration/register/beginner/
2. Open a Bash console and run: bash <(curl -s https://raw.githubusercontent.com/lavallee023-hash/fixit/master/deploy/pythonanywhere/setup.sh)
3. Edit ~/fixit.env and add GEMINI_API_KEY.
4. Web tab -> Add a new web app -> Manual configuration -> Python 3.12. Open the WSGI file link, replace its contents with deploy/pythonanywhere/wsgi.py, and Save -> Reload.
5. Live at https://<username>.pythonanywhere.com . Optional auto-deploy: move deploy/pythonanywhere/github-action-deploy.yml into .github/workflows/ and add secrets PA_USERNAME + PA_API_TOKEN. Otherwise update by running `cd ~/fixit && git pull` then Reload.
Escalation queue: ~/fixit-data/escalations.jsonl (persistent). Free web apps must be extended once every 3 months (button on Web tab).
