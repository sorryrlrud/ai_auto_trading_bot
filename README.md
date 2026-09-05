# AI Auto Trading Bot

Rule-based Upbit trading bot with a static realized-performance dashboard.

## Dashboard

`generate_dashboard.py` reads `trade_history.json` and `decision_history.json`, then writes a single static page to `docs/index.html`.

```bash
python3 generate_dashboard.py
```

The dashboard shows only explicit completed sell-side trades (`side="SELL"`) plus the latest three rebalance decision snapshots. Ambiguous legacy rows that merely have a date/ticker/profit field are ignored so stale local history cannot inflate the public totals. Open positions, balances, and secrets are not published.

To expose the page through GitHub Pages:

1. Open the repository settings in GitHub.
2. Go to `Pages`.
3. Set the source to `Deploy from a branch`.
4. Select branch `main` and folder `/docs`.

The bot regenerates `docs/index.html` after decision/trade changes and also emits an operational heartbeat at most once per hour by default so the public page can show whether the bot was recently seen alive without exposing a VM port. Publishing updates to GitHub Pages still requires pushing the changed `docs/index.html` file to the repository.

For automatic publishing from the VM:

1. Add a repository-scoped deploy key with write access in GitHub.
2. Change the VM remote to the SSH form: `git@github.com:sorryrlrud/ai_auto_trading_bot.git`.
3. Set `DASHBOARD_AUTO_PUBLISH=true` in the VM `.env`.

When enabled, the bot regenerates the dashboard, commits only `docs/index.html`, and pushes it after each decision/trade change plus the hourly heartbeat refresh controlled by `DASHBOARD_HEARTBEAT_PUBLISH_SECONDS` (default `3600`).

The container timezone defaults to `Asia/Seoul` through `TZ`, so log timestamps and dashboard generation timestamps use KST by default.
Automatic publishing expects the host SSH configuration to be available at `${HOME}/.ssh`; the Compose service mounts it read-only at `/host-ssh`, and the entrypoint copies the deploy key/config into the bot user's home with SSH-safe permissions before starting the bot.
Upbit HTTP calls use `UPBIT_HTTP_TIMEOUT_SECONDS` (default `10`) so a stalled API response cannot block rebalance cycles and dashboard heartbeat publishing indefinitely.
The entrypoint prepares SSH as root, creates a lightweight bot user for `BOT_UID:BOT_GID` (default `1001:1002` on the GCP VM), then drops privileges before starting Python so Git objects and runtime files created through the bind mount remain host-user writable.

The rule engine keeps at least the market- and performance-dependent cash reserve and caps each new position at `MAX_SINGLE_POSITION_PCT` of total portfolio value (default `25%`). This prevents a single eligible candidate from consuming the entire investable balance when `MAX_POSITIONS` is greater than one.

The existing hard stop (`STOP_LOSS_PCT`, default `-2.2%` before fees) is checked every `RISK_CHECK_SECONDS` (default `60`) between rebalance cycles and during market scans. Entry and indicator-based exit decisions still follow the 15-minute cycle. Checks run in the same process, so API calls and dashboard publishing can delay them; a market stop does not guarantee the threshold price. Dashboard subprocesses have bounded timeouts. Holdings are refreshed after each market scan before the rebalance plan is built.

Accepted orders are saved under `pending_orders` in `bot_state.json` and checked for terminal `done` or `cancel` status with matching execution details. Pending orders are reconciled after restart and prevent replacement buys. Realized PnL uses actual fills only, retains the remaining buy fee after a partial sell, and deduplicates history by order UUID. State and trade history writes are atomic. A submission that fails before returning an order UUID still requires checking the exchange; the pending-order recovery covers acknowledged orders.

## Local test

```bash
./venv/bin/python -m unittest test_logic.py test_execution.py
```
