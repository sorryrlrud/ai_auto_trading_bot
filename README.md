# AI Auto Trading Bot

Rule-based Upbit trading bot with a static realized-performance dashboard.

## Dashboard

`generate_dashboard.py` reads `trade_history.json` and `decision_history.json`, then writes a single static page to `docs/index.html`.

```bash
python3 generate_dashboard.py
```

The dashboard shows completed sell-side trades plus the latest three rebalance decision snapshots. Open positions, balances, and secrets are not published.

To expose the page through GitHub Pages:

1. Open the repository settings in GitHub.
2. Go to `Pages`.
3. Set the source to `Deploy from a branch`.
4. Select branch `main` and folder `/docs`.

The bot regenerates `docs/index.html` after every rebalance cycle so the recent-decision section stays current. Publishing updates to GitHub Pages still requires pushing the changed `docs/index.html` file to the repository.

For automatic publishing from the VM:

1. Add a repository-scoped deploy key with write access in GitHub.
2. Change the VM remote to the SSH form: `git@github.com:sorryrlrud/ai_auto_trading_bot.git`.
3. Set `DASHBOARD_AUTO_PUBLISH=true` in the VM `.env`.

When enabled, the bot regenerates the dashboard, commits only `docs/index.html`, and pushes it after each rebalance cycle that changes the page.

The container timezone defaults to `Asia/Seoul` through `TZ`, so log timestamps and dashboard generation timestamps use KST by default.
Automatic publishing expects the host SSH configuration to be available at `${HOME}/.ssh`; the Compose service mounts it read-only at `/host-ssh`, and the entrypoint copies the deploy key/config into the bot user's home with SSH-safe permissions before starting the bot.
The entrypoint prepares SSH as root, creates a lightweight bot user for `BOT_UID:BOT_GID` (default `1001:1002` on the GCP VM), then drops privileges before starting Python so Git objects and runtime files created through the bind mount remain host-user writable.

## Local test

```bash
docker compose run --rm coin-bot python -m unittest test_logic.py
```
