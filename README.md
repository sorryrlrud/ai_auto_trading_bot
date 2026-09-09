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

New entries also require the completed-candle one-hour return to be at least `MIN_ENTRY_CHANGE_1H_PCT` (default `-1.0%`). Previously this weakness only reduced the score and a high aggregate score could still buy it. This is an entry rule; it does not force an exit from an existing position. The September 9 review did not establish an incremental net-profit improvement over the corrected two-hour cooldown. See [the review](STRATEGY_REVIEW_2026-09-09.md) for the measured tradeoffs.

After any realized losing sell, the bot pauses all new entries for `LOSS_COOLDOWN_SECONDS` (default `7200`, or two hours). Existing holdings continue to be monitored and sold normally during this portfolio-wide cooling-off period. The existing `TRADE_COOLDOWN_SECONDS` remains a separate per-ticker re-entry guard.

The existing hard stop (`STOP_LOSS_PCT`, default `-2.2%` before fees) is checked every `RISK_CHECK_SECONDS` (default `60`) between rebalance cycles and during market scans. Entry and indicator-based exit decisions still follow the 15-minute cycle. Checks run in the same process, so API calls and dashboard publishing can delay them; a market stop does not guarantee the threshold price. Dashboard subprocesses have bounded timeouts. Holdings are refreshed after each market scan before the rebalance plan is built.

When a sell realizes a loss, the global entry cooldown is re-checked before any replacement buy from the same rebalance plan. This prevents an immediate cross-ticker rotation from bypassing `LOSS_COOLDOWN_SECONDS`.

Accepted orders are saved under `pending_orders` in `bot_state.json` and checked for terminal `done` or `cancel` status with matching execution details. Pending orders are reconciled after restart and prevent replacement buys. Realized PnL uses actual fills only, retains the remaining buy fee after a partial sell, and deduplicates history by order UUID. State and trade history writes are atomic. A submission that fails before returning an order UUID still requires checking the exchange; the pending-order recovery covers acknowledged orders.

Malformed realized history now stops entry planning/execution instead of resetting the loss controls to an empty history. A missing history file is still accepted for a new installation.

## Strategy review data

`strategy_observations.jsonl` records every completed cycle's private planning inputs: market context, the full scanned candidate set, completed-candle timestamps, holdings, KRW, recent performance and the plan. It rotates at 10 MiB with three backups (about 40 MiB maximum). A journal write failure is logged and does not prevent order reconciliation or exits. The file is ignored by Git and is not included in the public dashboard.

Confirmed entries retain their order UUID and signal context through pending-order recovery. Partial exits preserve this context for the remaining position; final exits attach it to the realized sell and clear it from active state. Sell records also distinguish the decision's observed price/profit from the actual fill. These records support subsequent strategy comparisons without reconstructing all input indicators from prose logs.

Use an SSH copy of the VM runtime files for an offline review:

```bash
./venv/bin/python review_strategy.py --history /tmp/vm-snapshot/trade_history.json \
  --log /tmp/vm-snapshot/trading.log --since 2026-08-29 --output /tmp/review.json
```

The report separates actual realized PnL from entry-selection diagnostics. Those diagnostics keep historical quantities and exits fixed, cannot simulate alternative opportunities or capital reuse, and are not account returns or a portfolio backtest. Test messages in the log are not counted as actual trades. Multiple partial exits matched to one entry disable the selection simulation.

## Local test

```bash
./venv/bin/python -m unittest test_logic.py test_execution.py test_strategy_review.py
```
