#!/bin/sh
PYTHONPATH="$(dirname "$(readlink -f "$0")")" exec python3 -m fixit.cli "$@"
