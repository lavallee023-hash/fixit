# PythonAnywhere WSGI file. Paste this into the WSGI config file linked on the Web tab
# (e.g. /var/www/<username>_pythonanywhere_com_wsgi.py). Replace <username>.
import os, sys
HOME = os.path.expanduser("~")
APP = os.path.join(HOME, "fixit")
# Secrets live in ~/fixit.env (KEY=value lines), never in the repo.
envf = os.path.join(HOME, "fixit.env")
if os.path.exists(envf):
    for line in open(envf):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
# Free accounts reach the internet only via this proxy (urllib honours these vars).
os.environ.setdefault("HTTPS_PROXY", "http://proxy.server:3128")
os.environ.setdefault("HTTP_PROXY", "http://proxy.server:3128")
os.environ.setdefault("FIXIT_DATA_DIR", os.path.join(HOME, "fixit-data"))   # persistent disk: usage + escalation queue
sys.path.insert(0, APP); sys.path.insert(0, os.path.join(APP, "web"))
from app import app as application
