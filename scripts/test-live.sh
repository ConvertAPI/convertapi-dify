#!/bin/zsh
# Runs all tests, live ones against production, with the token masked in any output.
set -o pipefail
cd "${0:A:h}/.."
TOKEN_FILE="${CONVERTAPI_TOKEN_FILE:-$HOME/.config/convertapi/convertapi-production-api-token}"
[[ -s "$TOKEN_FILE" ]] || { echo "token file missing: $TOKEN_FILE"; exit 2; }
CONVERTAPI_TOKEN_FILE="$TOKEN_FILE" .venv/bin/python -m pytest "$@" 2>&1 \
  | TOKEN_FILE="$TOKEN_FILE" python3 -c '
import os, sys
t = open(os.environ["TOKEN_FILE"]).read().strip()
for line in sys.stdin:
    sys.stdout.write(line.replace(t, "***MASKED***") if t else line)
'
