#!/bin/sh
set -eu

ssh -o BatchMode=yes -o ConnectTimeout=10 sorryrlrud@136.119.201.220 \
  'cd /home/sorryrlrud/ai_auto_trading_bot &&
   docker exec --user 1001:1002 --env HOME=/tmp/bot-home \
     quant-ai-manual-api python -u /app/scheduled_trader.py --json'
