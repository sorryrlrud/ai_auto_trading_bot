#!/bin/sh
set -eu

decision_base64="$(base64 | tr -d '\n')"
if [ -z "$decision_base64" ]; then
  echo "decision JSON is required on stdin" >&2
  exit 2
fi

ssh -o BatchMode=yes -o ConnectTimeout=10 sorryrlrud@136.119.201.220 \
  "cd /home/sorryrlrud/ai_auto_trading_bot &&
   docker exec --user 1001:1002 --env HOME=/tmp/bot-home \\
     quant-ai-manual-api python -u /app/scheduled_trader.py --json \\
       --decision-base64 '$decision_base64'"
