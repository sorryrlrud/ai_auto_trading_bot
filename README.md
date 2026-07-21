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
