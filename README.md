# AI Auto Trading Bot

Rule-based Upbit trading bot with a static realized-performance dashboard.

## Dashboard

`generate_dashboard.py` reads `trade_history.json` and `decision_history.json`, then writes a single static page to `docs/index.html`.

```bash
python3 generate_dashboard.py
```

The dashboard shows only explicit completed sell-side trades (`side="SELL"`) plus up to 50 recent decision snapshots. Scheduled decision cards include their KST date/time, session metadata, and the overall BUY/SELL/HOLD or no-trade rationale. Ambiguous legacy rows that merely have a date/ticker/profit field are ignored so stale local history cannot inflate the public totals. Open positions, balances, and secrets are not published.

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

## Scheduled trading heartbeat

The always-running `coin-bot` service is now a disabled legacy profile. Scheduled
trading runs one deterministic tick at a time inside `quant-ai-manual-api`:

```bash
./run_scheduled_tick.sh
```

The session day rolls over at 02:00 KST. Every tick checks estimated account
liquidation value. The daily target closes all marketable holdings when return
from the 02:00 session baseline reaches +0.5%. A phase-level -0.4% stop before
12:00 KST waits until noon and starts phase 2 with a new stop-loss baseline while
preserving the original daily baseline; a stop at or after noon ends the session.
Entry and rebalance signals are evaluated at most once per completed 10-minute
slot, matching the ten-minute scheduled task cadence. The tick
returns a bounded market/account context. A local Codex scheduled run using
`gpt-5.6-sol` with `medium` reasoning chooses BUY, SELL, or HOLD and submits a
token-bound JSON decision plus an overall decision summary through
`execute_llm_trade_decision.sh`. Every scheduled signal slot is retained in the
dashboard history, including no-trade decisions.

The LLM context identifies the 10-minute decision cadence and includes current
daily return, remaining return to the +0.5% target, and completed daily, 1-hour,
and 10-minute indicators. Legacy scores and block reasons are advisory; the LLM
makes the final signal decision within the hard execution and risk constraints.
For a no-trade decision with no current holdings, the model returns an empty
`decisions` array. `HOLD` and `SELL` are valid only for tickers in the current
holdings, while `BUY` is valid only for unheld context candidates.

Scheduled mode passes `cash_reserve_pct_override=0`, so it does not retain a
strategy cash reserve. `SCHEDULED_ORDER_BUFFER=0.999` keeps only a 0.1% execution
buffer for fees and rounding. Runtime state is stored in
`scheduled_trading_state.json`; the signal slot is persisted before order
execution to make retries at-most-once. The pending model context is stored in
`scheduled_llm_context.json` and expires after 10 minutes. The server rejects
unknown buy candidates, sells of unowned assets, duplicate tickers, stale or
reused decision tokens, and decisions above `MAX_POSITIONS`. Failed or partial
liquidation remains in `liquidation_pending` and is retried by the next tick.

Live scheduled orders require `SCHEDULED_TRADE_ENABLED=true`. An optional
`SCHEDULED_ACTIVATE_AT` can delay first activation. The local launchers use the
production bot UID/GID to avoid creating root-owned runtime files in the
bind-mounted repository.

The ten-minute Codex trading automation pauses itself after a completed daily
target or final stop, preventing completed sessions from consuming more model
tokens. A separate no-trade control automation reactivates it every day at
02:00 KST; the next tick initializes the new daily session.

An optional `SCHEDULED_DEACTIVATE_AT` ends a bounded trading window. At or after
that KST timestamp, no new LLM decision can execute; the next scheduled tick
liquidates marketable holdings and records `completed_test_window`.

## Manual order API over SSH

The manual market-order API is published only on the VM loopback interface. It is
not reachable from the public network. Start an SSH tunnel from the authorized Mac:

```bash
ssh -N \
  -o ExitOnForwardFailure=yes \
  -L 8765:127.0.0.1:8765 \
  sorryrlrud@136.119.201.220
```

While the tunnel is open, check the API from another local terminal:

```bash
curl http://127.0.0.1:8765/health
```

Submit a market buy by KRW amount:

```bash
curl -X POST http://127.0.0.1:8765/v1/orders/buy \
  -H 'Content-Type: application/json' \
  -d '{
    "market": "KRW-BTC",
    "amount_krw": 10000,
    "idempotency_key": "replace-with-a-new-unique-value",
    "confirm": "CONFIRM"
  }'
```

Submit a market sell by percentage of the available asset balance:

```bash
curl -X POST http://127.0.0.1:8765/v1/orders/sell \
  -H 'Content-Type: application/json' \
  -d '{
    "market": "KRW-BTC",
    "percentage": 100,
    "idempotency_key": "replace-with-another-new-unique-value",
    "confirm": "CONFIRM"
  }'
```

`idempotency_key` prevents a retried request from placing the same order twice.
Reusing it with different order parameters is rejected. Each request also requires
the literal `"confirm": "CONFIRM"`. Manual ordering is disabled unless
`MANUAL_TRADE_ENABLED=true`; market buys are capped by `MANUAL_MAX_BUY_KRW`
(default `100000`). The automatic bot and manual API share a process-level file
lock so they cannot submit orders at the same time.

## Local test

```bash
docker compose run --rm coin-bot python -m unittest test_logic.py
```
