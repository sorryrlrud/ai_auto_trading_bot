#!/bin/sh
set -eu

: "${HOME:=/tmp/bot-home}"
export HOME

if [ -d /host-ssh ]; then
  mkdir -p "$HOME/.ssh"
  chmod 700 "$HOME/.ssh"

  for file in config known_hosts ai_auto_trading_bot_deploy; do
    if [ -f "/host-ssh/$file" ]; then
      cp "/host-ssh/$file" "$HOME/.ssh/$file"
    fi
  done

  [ -f "$HOME/.ssh/config" ] && chmod 600 "$HOME/.ssh/config"
  [ -f "$HOME/.ssh/ai_auto_trading_bot_deploy" ] && chmod 600 "$HOME/.ssh/ai_auto_trading_bot_deploy"
  [ -f "$HOME/.ssh/known_hosts" ] && chmod 644 "$HOME/.ssh/known_hosts"
fi

git config --global --add safe.directory /app

exec python -u autotrade.py
