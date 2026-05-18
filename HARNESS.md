# Operations Harness

Last verified: 2026-05-18 KST

This file is a handoff guide for future sessions working on the live trading bot. Read this before assuming that the local Docker environment is production.

## Production target

| Item | Value |
| --- | --- |
| Cloud VM | GCP Compute Engine |
| VM hostname | `instance-20260517-085519` |
| Public IP | `136.119.201.220` |
| SSH user | `sorryrlrud` |
| SSH command | `ssh sorryrlrud@136.119.201.220` |
| Repo path on VM | `/home/sorryrlrud/ai_auto_trading_bot` |
| Main container | `quant-ai-bot` |
| Docker image tag | `ai_auto_trading_bot-coin-bot:latest` |
| Git branch | `main` |

Important: the local workspace and local Docker daemon are not the production environment. If the task concerns live behavior, inspect the GCP VM first.

## SSH and Git publishing setup

The VM repository remote is SSH-based:

```text
git@github.com-ai-auto-trading-bot:sorryrlrud/ai_auto_trading_bot.git
```

The VM SSH config defines:

```text
Host github.com-ai-auto-trading-bot
  HostName github.com
  User git
  IdentityFile ~/.ssh/ai_auto_trading_bot_deploy
  IdentitiesOnly yes
```

Do not commit `.env`, deploy keys, or private SSH material. The Compose service mounts the host SSH directory read-only at `/host-ssh`, and `/app/docker-entrypoint.sh` copies only the needed files into the bot user's home with SSH-safe permissions before the bot starts.

## Runtime layout

- Source code is bind-mounted from the VM repository into the container at `/app`.
- The bot runs from `docker-compose.yml` as service `coin-bot`.
- The entrypoint starts as root only long enough to prepare SSH and create a lightweight bot user, then runs the Python bot as `BOT_UID:BOT_GID`, currently `1001:1002` on the GCP VM, to match the host repository owner.
- The container timezone is intended to be KST through `TZ=Asia/Seoul`.
- The VM host itself may still report UTC; check the container if the task concerns bot timestamps:

```bash
docker exec quant-ai-bot date
```

- Important runtime files:
  - `trade_history.json`
  - `decision_history.json`
  - `bot_state.json`
  - `trading.log`
  - `docs/index.html`

`decision_history.json`, `trade_history.json`, `bot_state.json`, and `trading.log` are runtime data files and should not be committed.

## Current dashboard behavior

- `generate_dashboard.py` reads:
  - realized sell history from `trade_history.json`
  - recent rebalance decisions from `decision_history.json`
- The dashboard now shows:
  - realized PnL summary
  - realized sell history
  - the latest three decision snapshots
- Decision snapshots include `entry_block_reason` when new buys are intentionally blocked, so an empty buy list in defensive mode is explainable from the dashboard payload.
- `autotrade.py` now refreshes the dashboard after every rebalance cycle, not only after sells.
- With `DASHBOARD_AUTO_PUBLISH=true`, the bot commits only `docs/index.html` and pushes it to `main`.

Because dashboard publishing creates commits automatically, local `main` can fall behind remote `main` during active bot operation. Before pushing source changes, use:

```bash
git fetch origin main
git rebase origin/main
git push origin main
```

## Known-good verification commands

Run these on the VM when checking production:

```bash
ssh sorryrlrud@136.119.201.220
cd /home/sorryrlrud/ai_auto_trading_bot

docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker logs --tail 120 quant-ai-bot
docker exec quant-ai-bot date
docker exec quant-ai-bot sh -lc 'cd /app && git ls-remote origin HEAD | head -1'
git status --short
git log --oneline -5
```

To verify the generated dashboard payload:

```bash
python3 - <<'PY'
import json, re
from pathlib import Path

html = Path("docs/index.html").read_text(encoding="utf-8")
payload = re.search(
    r'<script id="dashboard-data" type="application/json">(.*?)</script>',
    html,
).group(1)
data = json.loads(payload)
print("recent_decisions", len(data.get("recent_decisions", [])))
for item in data.get("recent_decisions", []):
    print(item["recorded_at"], [d.get("decision") for d in item.get("decisions", [])])
PY
```

## What happened on 2026-05-18

### Initial mistakes and findings

1. Work initially inspected local Docker by mistake. Production was actually the GCP VM above.
2. The live dashboard appeared stale because:
   - it was only regenerated after completed sells
   - automatic publishing was enabled but broken
3. Live container logs showed:
   - `FileNotFoundError: [Errno 2] No such file or directory: 'git'`
   - later, after adding Git, SSH failed with `Bad owner or permissions on /root/.ssh/config`
4. The live container and VM originally reported UTC timestamps. The container is now configured for KST.
5. After automatic dashboard commits began working, host-side `git pull` later failed with `insufficient permission for adding an object to repository database .git/objects` because container-created Git objects were root-owned.

### Fixes applied

- Added recent decision history tracking.
- Added the latest three decision cards to the dashboard.
- Switched dashboard refresh cadence from sell-only to every rebalance cycle.
- Added KST container configuration.
- Added Git and SSH support to the Dockerfile.
- Added `docker-entrypoint.sh` so SSH credentials are copied into bot-user-owned files with safe permissions.
- Backfilled three recent decision snapshots from existing logs once so the dashboard did not start empty.
- Verified automatic dashboard publishing end-to-end from inside the container.

### Verified success signals

Examples observed after the fix:

- Container time:
  - `Mon May 18 00:42:14 KST 2026`
- Automatic publish log:
  - `Dashboard published.`
- Auto-published dashboard commits:
  - `d10c005`
  - `4f655da`
- Dashboard payload contained three decision snapshots after backfill.

## Environment limitations and deployment caveats

### 1. Docker image rebuilds stalled on the VM

On 2026-05-18, both of these paths hung for an unusually long time near the image export/commit phase:

```bash
docker compose up -d --build
DOCKER_BUILDKIT=0 docker build -t ai_auto_trading_bot-coin-bot:latest .
```

The source code itself was still deployable because `/app` is bind-mounted from the repository, but package additions such as `git` and `openssh-client` required extra care.

Operational workaround used:

1. Recreate the container from Compose so the new source and mounts are active.
2. Install `git`, `openssh-client`, and `tzdata` into the running container.
3. Remove `/root/.ssh` from the container.
4. Commit the container into `ai_auto_trading_bot-coin-bot:latest`.
5. Recreate the service again from that sanitized image.

This preserved installed packages without baking deploy keys into the image.

Follow-up recommended: investigate why image export stalls on this VM before relying on routine rebuilds.

### 2. Historical root-owned runtime files on the host

Before the bot was switched to `BOT_UID:BOT_GID`, runtime files created by the container appeared as root-owned in the bind-mounted repo. For example, `decision_history.json` was root-owned after first creation, so a host-side backfill script hit `PermissionError`.

If a historical root-owned runtime file remains, repair it once on the host:

```bash
sudo chown sorryrlrud:sorryrlrud trade_history.json decision_history.json bot_state.json trading.log
```

### 3. SSH files mounted directly into `/root/.ssh` are rejected

Mounting `${HOME}/.ssh` directly into `/root/.ssh` caused OpenSSH to reject the config because the files were owned by the host user, not root. Keep using the current pattern:

```yaml
- ${HOME}/.ssh:/host-ssh:ro
```

Then let `docker-entrypoint.sh` copy and chmod the needed files into the bot user's home.

### 4. Dashboard automation advances `main`

The bot auto-commits dashboard updates. This means:

- the remote branch may advance while you are editing locally
- a push can fail with `fetch first`
- a source commit should usually be rebased onto the latest `origin/main` before push

Do not force-push over dashboard commits unless there is a deliberate reason.

## Current strategy guardrails

- Entry indicators are calculated from completed candles only; the latest in-progress daily, 1-hour, and 15-minute candles are excluded before RSI/MACD/MA calculations.
- With the current default `ALLOW_DEFENSIVE_BUYS=false`, `risk_mode=defensive` blocks all new entries while still managing existing holdings.
- Candidate entries are hard-blocked when the long-term trend is not aligned, the 1-hour or 15-minute trend is not aligned, the market is overheated, the move is too extended, or `atr_pct` exceeds `MAX_ENTRY_ATR_PCT` (default `12.0`).
- Small losing positions are no longer sold on a 15-minute break alone; early loss exits require both 15-minute and 1-hour trend damage unless a harder stop-loss or other broader exit rule is hit.
- The rebalance loop now aligns to `LOOP_SLEEP_SECONDS` boundaries with a `CANDLE_CLOSE_BUFFER_SECONDS` delay (default `20`) instead of sleeping a flat interval after each cycle. With the default 900-second loop this targets the first moments after each 15-minute candle close.

### 5. Historical container-side Git commits left root-owned `.git` objects

Before the bot was switched to `BOT_UID:BOT_GID`, `publish_dashboard.py` committed from inside the bind-mounted repository as root, so new files under `.git/objects` could be created as `root:root`. Later, a host-side pull as `sorryrlrud` failed with:

```text
error: insufficient permission for adding an object to repository database .git/objects
fatal: failed to write object
```

Immediate recovery used on 2026-05-18:

```bash
cd /home/sorryrlrud/ai_auto_trading_bot
sudo chown -R sorryrlrud:sorryrlrud .git
git pull --ff-only origin main
```

The entrypoint now drops the Python process to the host-compatible UID/GID, so new Git objects should be user-owned. Keep the recovery command above in mind for older root-owned objects that may still exist.

## Safe operating sequence for future changes

1. Confirm whether the task is about local development or the GCP live bot.
2. If live, SSH into the VM first and inspect `docker logs`.
3. Pull the latest remote branch before changing code.
4. Make source changes locally and run tests with the project venv:

```bash
./venv/bin/python -m unittest test_logic.py
```

5. Rebase onto `origin/main` before pushing because dashboard commits may have landed.
6. On the VM, pull the source change and recreate the container carefully.
7. Verify:
   - container time is KST
   - `git ls-remote origin HEAD` works inside the container
   - dashboard auto-publish succeeds on a real rebalance cycle
   - `recent_decisions` remains populated
   - host-side `git pull --ff-only origin main` still succeeds after an automatic dashboard commit

## Security notes

- Do not place secrets, API keys, private key contents, or `.env` values in this file.
- The public IP, SSH alias, repo path, and operational commands are intentionally documented because they are needed for future maintenance.
- If the VM is recreated or the public IP changes, update this file at the same time as the deployment change.
