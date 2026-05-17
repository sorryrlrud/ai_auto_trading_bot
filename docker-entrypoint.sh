#!/bin/sh
set -eu

if [ -d /host-ssh ]; then
  mkdir -p /root/.ssh
  chmod 700 /root/.ssh

  for file in config known_hosts ai_auto_trading_bot_deploy; do
    if [ -f "/host-ssh/$file" ]; then
      cp "/host-ssh/$file" "/root/.ssh/$file"
    fi
  done

  [ -f /root/.ssh/config ] && chmod 600 /root/.ssh/config
  [ -f /root/.ssh/ai_auto_trading_bot_deploy ] && chmod 600 /root/.ssh/ai_auto_trading_bot_deploy
  [ -f /root/.ssh/known_hosts ] && chmod 644 /root/.ssh/known_hosts
fi

exec python -u autotrade.py
