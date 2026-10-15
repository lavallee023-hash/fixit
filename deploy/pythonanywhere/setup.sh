#!/bin/bash
# Run ONCE in a PythonAnywhere Bash console (free account): bash <(curl -s https://raw.githubusercontent.com/lavallee023-hash/fixit/master/deploy/pythonanywhere/setup.sh)
set -e
cd ~
[ -d fixit ] && (cd fixit && git pull) || git clone https://github.com/lavallee023-hash/fixit.git
pip3.12 install --user -q -r fixit/requirements.txt
mkdir -p ~/fixit-data
[ -f ~/fixit.env ] || cp fixit/deploy/pythonanywhere/fixit.env.example ~/fixit.env
echo "Done. Now: edit ~/fixit.env (add GEMINI_API_KEY), then Web tab -> Add new web app -> Manual configuration -> Python 3.12,"
echo "open the WSGI file link and replace its contents with ~/fixit/deploy/pythonanywhere/wsgi.py, then click Reload."
