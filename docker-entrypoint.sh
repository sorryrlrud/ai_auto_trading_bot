#!/bin/sh
set -eu

: "${HOME:=/tmp/bot-home}"
: "${BOT_UID:=1001}"
: "${BOT_GID:=1002}"
: "${BOT_USER:=bot}"
export HOME

if ! getent group "$BOT_GID" >/dev/null 2>&1; then
  echo "$BOT_USER:x:$BOT_GID:" >> /etc/group
fi

if ! getent passwd "$BOT_UID" >/dev/null 2>&1; then
  echo "$BOT_USER:x:$BOT_UID:$BOT_GID:Bot user:$HOME:/bin/sh" >> /etc/passwd
fi

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

chown -R "$BOT_UID:$BOT_GID" "$HOME"

setpriv --reuid="$BOT_UID" --regid="$BOT_GID" --clear-groups \
  env HOME="$HOME" git config --global --add safe.directory /app
setpriv --reuid="$BOT_UID" --regid="$BOT_GID" --clear-groups \
  env HOME="$HOME" git config --global maintenance.autoDetach false
setpriv --reuid="$BOT_UID" --regid="$BOT_GID" --clear-groups \
  env HOME="$HOME" git config --global gc.autoDetach false

if [ "$#" -eq 0 ]; then
  set -- python -u autotrade.py
fi

exec setpriv --reuid="$BOT_UID" --regid="$BOT_GID" --clear-groups \
  env HOME="$HOME" "$@"
