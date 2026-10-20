# Operations Harness

Last verified: 2026-10-21 KST (live health, exchange reconciliation and strategy review verified)

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
- Compose enables `init: true`, so Docker's init process is PID 1 and reaps detached Git maintenance children.
- The entrypoint starts as root only long enough to prepare SSH and create a lightweight bot user, then runs the Python bot as `BOT_UID:BOT_GID`, currently `1001:1002` on the GCP VM, to match the host repository owner.
- The container timezone is intended to be KST through `TZ=Asia/Seoul`.
- The VM host itself may still report UTC; check the container if the task concerns bot timestamps:

```bash
docker exec quant-ai-bot date
```

- Important runtime files:
  - `trade_history.json`
  - `decision_history.json`
  - `runtime_status.json`
  - `bot_state.json`
  - `trading.log`
  - `strategy_observations.jsonl` and up to three rotated backups
  - `docs/index.html`

`decision_history.json`, `trade_history.json`, `runtime_status.json`, `bot_state.json`, and `trading.log` are runtime data files and should not be committed.
`strategy_observations.jsonl*` also contains private runtime data (including account snapshots), is ignored by Git, and must not be published. It rotates at 10 MiB per file with three backups. Use a VM copy for offline diagnostics with `review_strategy.py`; never substitute local runtime files for production performance.

## Current dashboard behavior

- `generate_dashboard.py` reads:
  - realized sell history from `trade_history.json`
  - recent rebalance decisions from `decision_history.json`
- The dashboard now shows:
  - realized PnL summary
  - public operational status based on the latest published heartbeat
  - realized sell history
  - the latest three decision snapshots
- Realized-performance aggregation only accepts rows with explicit `side="SELL"` so legacy local rows without order-side evidence are ignored.
- New entries store their exact paid buy fee in `bot_state.json`; realized PnL and the dashboard subtract both buy and sell fees.
- Decision snapshots include `entry_block_reason` when new buys are intentionally blocked, so an empty buy list in defensive mode is explainable from the dashboard payload.
- When non-defensive entries are rejected by hard filters, the latest top rejected candidates are stored as `entry_rejections` for later tuning.
- `autotrade.py` refreshes the dashboard after decision/trade changes plus a bounded hourly heartbeat, not only after completed sells.
- When there are no decision/trade changes, `autotrade.py` refreshes the dashboard heartbeat at most once per hour by default (`DASHBOARD_HEARTBEAT_PUBLISH_SECONDS=3600`) so GitHub Pages can show the latest known-alive status without opening an inbound VM port.
- With `DASHBOARD_AUTO_PUBLISH=true`, the bot commits only `docs/index.html` and pushes it to `main`.
- If a dashboard push fails after a commit, the next attempt pushes that pending commit before creating another one. This bounds commit growth during a publishing outage.

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
docker exec --user 1001:1002 --env HOME=/tmp/bot-home quant-ai-bot \
  sh -lc 'cd /app && git ls-remote origin HEAD | head -1'
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

Run unit tests from an isolated temporary copy inside the container. Importing
`autotrade.py` configures a file logger in the current directory, so running the
suite from `/app` would append synthetic test messages to the production
`trading.log`:

```bash
docker exec --user 1001:1002 --env HOME=/tmp/bot-home quant-ai-bot sh -lc '
  test_dir=$(mktemp -d /tmp/bot-tests.XXXXXX)
  trap '\''rm -rf -- "$test_dir"'\'' EXIT
  cp /app/*.py "$test_dir"/
  cd "$test_dir"
  python -m unittest test_logic.py
'
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

- The hard stop is also checked between cycles with `RISK_CHECK_SECONDS=60` by default. No entries are generated by this monitor. It runs during the 15-minute waiting period, between target scans, and during rebalance-error backoff. Blocking API calls can extend the interval.
- The monitor also records each active position's observed `peak_price` and `peak_avg_buy_price` in private state. Reaching the existing gross `PROFIT_PROTECT_PCT=1.2` arms profit protection persistently; a later completed 15-minute trend break exits even below that current-profit threshold. This is a candle-cycle exit, not a price-only trailing stop. Peaks survive restart/partial sells and clear on full exits/new entries. Never transplant peak fields between different entries. The September 30 cycle review documents both the selected rule and the rejected price-only alternative.
- `runtime_status.json` includes `last_risk_check_at`, `risk_check_interval_seconds`, `risk_check_failures`, and `pending_order_count`. The normal cycle heartbeat remains separate.
- Holdings and state are reloaded after market scanning, so exit decisions use a fresh holding price and recognize any stop executed during the scan.
- Acknowledged orders are persisted as `pending_orders` before polling their terminal status. Do not delete pending orders or roll back to code that ignores them while any remain unresolved. Terminal canceled orders may contain fills; realized PnL requires actual fill quantities, funds and fees. Partial sells preserve the remaining entry fee. Trade history uses `order_uuid` to avoid duplicate PnL after restart.
- Runtime state, status and realized history use atomic writes. Corrupt trading state/history fails closed instead of being silently overwritten. Dashboard generation/publishing subprocesses each time out after 30 seconds.
- Entry indicators are calculated from completed candles only; the latest in-progress daily, 1-hour, and 15-minute candles are excluded before RSI/MACD/MA calculations.
- With the current default `ALLOW_DEFENSIVE_BUYS=false`, `risk_mode=defensive` blocks all new entries while still managing existing holdings.
- Candidate entries are hard-blocked when the long-term trend is not aligned, the 1-hour or 15-minute trend is not aligned, the daily Bollinger position exceeds `MAX_ENTRY_BB_POSITION` (default `1.05`), the market is overheated, the move is too extended, or `atr_pct` exceeds `MAX_ENTRY_ATR_PCT` (default `5.0`).
- Candidates with completed-candle one-hour returns below `MIN_ENTRY_CHANGE_1H_PCT` (default `-1.0%`) are now blocked even if their total score passes. This only affects entries. The September 9 historical selection diagnostic did not establish an incremental net-profit gain over the fixed two-hour cooldown; see `STRATEGY_REVIEW_2026-09-09.md` before claiming a performance improvement.
- Candidates with completed-candle six-hour returns below `MIN_ENTRY_CHANGE_6H_PCT` (default `0.5%`) are blocked even if their total score passes. This entry-only rule was added from the September 28 realized and opportunity diagnostics; it does not change holding management or exits.
- Candidates with completed-candle 15-minute RSI above `MAX_ENTRY_15M_RSI` (default `75.0`) are blocked as overheated. This October 1 entry-only change aligns the fast-timeframe ceiling with the existing one-hour ceiling and does not affect holding management or exits.
- Entry order UUIDs and their indicator context persist through pending-order recovery and partial exits, and are attached to realized history. They are cleared from active state after a full exit. Malformed trade-history JSON now blocks new entries instead of silently clearing loss controls.
- Full scan inputs and plans are captured privately after each completed cycle, including observed times and completed-candle start times. A diagnostic write failure does not block trade handling. The public decision payload includes the strategy version but excludes entry context.
- A realized losing sell pauses all new entries across tickers for `LOSS_COOLDOWN_SECONDS` (default 3 hours), while existing holding management and exits continue. This complements the per-ticker 6-hour trade cooldown and reduces cross-ticker churn after a stop-out.
- When a ticker's latest realized sell was a loss, that ticker remains ineligible for `LOSS_TICKER_COOLDOWN_SECONDS` (default 12 hours). Profitable exits still use the ordinary 6-hour per-ticker cooldown. The latest realized result is derived from explicit SELL history, so the rule also survives restarts and applies to pre-deployment losses.
- At `LOSS_STREAK_COUNT` consecutive realized losses (default 3), that new-entry pause extends to `LOSS_STREAK_COOLDOWN_SECONDS` (default 12 hours) after the latest loss. A non-losing realized sell resets the streak; holding management and exits remain active.
- The loss cooldown is checked again after sells complete, before replacement buys execute, so a newly realized loss also blocks a buy that was already present in the same rebalance plan.
- A new position is capped at `MAX_SINGLE_POSITION_PCT` of total portfolio value (default `25%`), even when only one candidate passes and more portfolio slots are available.
- Stablecoin-like entry candidates are excluded by default through `EXCLUDED_ENTRY_TICKERS=KRW-USDT,KRW-USDC,KRW-USD1`.
- The top-volume target scan batches the full KRW market list instead of checking only an initial slice of tickers.
- Small losing positions are no longer sold on a 15-minute break alone; early loss exits require both 15-minute and 1-hour trend damage unless a harder stop-loss or other broader exit rule is hit.
- The rebalance loop now aligns to `LOOP_SLEEP_SECONDS` boundaries with a `CANDLE_CLOSE_BUFFER_SECONDS` delay (default `20`) instead of sleeping a flat interval after each cycle. With the default 900-second loop this targets the first moments after each 15-minute candle close.
- Consecutive identical decision snapshots are deduplicated, so repeated no-op defensive cycles do not keep creating dashboard commits.
- Dashboard refresh subprocess failures now log command, return code, stdout, and stderr so future publish regressions are diagnosable from `trading.log`.

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

## What happened on 2026-07-15

- The trading loop was healthy and the container had run for five weeks without a restart, but dashboard publishing had stopped on 2026-07-08.
- Detached Git maintenance processes were inherited by the Python process running as PID 1 and were never reaped. The container accumulated 677 `git`/`ssh` zombies and reached its cgroup task limit of 680.
- Once the task limit was exhausted, dashboard pushes failed with `cannot fork() for maintenance` and `cannot fork() for ssh`. Because each failed attempt had already committed the new heartbeat, the VM branch grew to 660 unpublished dashboard commits.
- Compose now enables Docker's init process, the entrypoint disables detached Git maintenance, and the dashboard publisher retries pending commits before creating another commit.
- During recovery, preserve the incident history on an archive branch before realigning the VM `main` branch with `origin/main`; runtime JSON/log files are ignored and must remain in place.

## Safe operating sequence for future changes

1. Confirm whether the task is about local development or the GCP live bot.
2. If live, SSH into the VM first and inspect `docker logs`.
3. Pull the latest remote branch before changing code.
4. Make source changes locally and run tests with the project venv:

```bash
./venv/bin/python -m unittest test_logic.py test_execution.py test_strategy_review.py test_profit_protection.py
```

5. Rebase onto `origin/main` before pushing because dashboard commits may have landed.
6. On the VM, pull the source change and recreate the container carefully.
7. Verify:
   - container time is KST
   - `git ls-remote origin HEAD` works as the bot user with `HOME=/tmp/bot-home` inside the container
   - dashboard auto-publish succeeds on a real rebalance cycle
   - `recent_decisions` remains populated
   - host-side `git pull --ff-only origin main` still succeeds after an automatic dashboard commit

## Deployment verified on 2026-09-05

- Source revision: `3dd3cbe` (hard-stop monitoring and confirmed order reconciliation).
- Both local Python and the VM container's Python passed 54 tests. VM tests used isolated temporary source copies with no live API calls or runtime-file changes.
- Existing source/runtime files were backed up to `/home/sorryrlrud/bot-backup-20260905-pDzQkZ` before the production container was stopped, fast-forwarded and started. No image rebuild or dependency change was needed.
- Container started at 12:48:53 KST with Docker init enabled. Source SHA-256 was `b950929bbeaf7252dae32c56438e80b1fc21f79d7a131f929eb9f27e416c6602` on both local workspace and VM.
- The first real rebalance completed at 12:50:08 KST. Risk checks completed at 12:48:56, 12:49:56 and 12:50:56 with no failures or pending orders.
- Bot-user SSH access to GitHub succeeded. Automatic dashboard commit `2182f32` was generated at 12:50:08 KST, and the public GitHub Pages payload showed that update with three decision snapshots.
- Verification observed monitoring and a HOLD cycle. No new live order was needed to test execution; delayed/partial order handling was verified with mocked exchange responses.

## Deployment verified on 2026-09-09

- Source revision: `24c297b` (`2026-09-09-momentum-audit`). Local and isolated VM tests each passed 74 tests; VM tests blocked socket connections and used temporary source/runtime directories.
- Backup: `/home/sorryrlrud/bot-backup-20260909-dk9c47hc`. No dependency or image rebuild was needed. Existing runtime history was preserved.
- Container started at 11:58:28 KST. Local/VM `autotrade.py` SHA-256: `a0d5850446756e6fed3be56bcbfd14d521c240501b66ea08b6e96040dde5c5ad`.
- First cycle completed at 11:59:49 KST. Risk checks at 11:58:32, 11:59:33 and 12:00:35 had zero failures and zero pending orders.
- The first private observation included 24 valid candidate inputs, completed-candle timestamps and the new strategy version. The journal was confirmed Git-ignored.
- Automatic dashboard commit `b9f06f5` and public HTTP 200 payload both showed the 11:59:49 update, three recent decisions and the new version. Entry context was absent from the public payload. Bot-user GitHub SSH access worked.
- The bot was defensive with no order decisions during verification. No verification trade was submitted. Profit improvement from the new entry filter remains unproven; see `STRATEGY_REVIEW_2026-09-09.md` for actual PnL, rejected alternatives and the counterfactual selection limits.

## Deployment verified on 2026-09-21

- Source revision: `d7e5430` (`2026-09-21-overextension-streak-brakes`). Local and isolated VM tests each passed 77 tests. The VM backup is `/home/sorryrlrud/bot-backup-20260921-ZVg2jt`; no dependency or image rebuild was needed.
- Container started at 06:11:53 KST with restart count 0 and OOM false. Local/VM `autotrade.py` SHA-256: `c6c562b84ba6ca136b2671a27a10736f9332479c7ba9309dffcdc6b29ede4ec0`.
- Startup logged `max_entry_bb_position=1.05` and the `3/43200s` loss-streak brake. Risk checks succeeded with one BTC holding and zero pending orders.
- The first real cycle completed at 06:13:18 KST. It detected seven consecutive realized losses, kept BTC on HOLD, and blocked new entries for 12 hours after the latest loss. Consecutive failures and risk-check failures remained zero.
- Automatic dashboard commit `f00ac45` was generated and pushed. The public GitHub Pages payload showed the 06:13:18 decision and the new strategy version; bot-user GitHub SSH access returned the same commit.
- No verification order was submitted. The new safeguards only restrict entries; their forward performance remains unproven. See `STRATEGY_REVIEW_2026-09-21.md` for the fixed-exit diagnostics and limitations.

## Deployment verified on 2026-09-24

- Source revision: `463d659` (`2026-09-24-atr-volatility-gate`). Local and isolated VM tests each passed 82 tests. The VM backup is `/home/sorryrlrud/bot-backup-20260924-2AZHTZ`; no dependency or image rebuild was needed.
- Container started at 06:15:48 KST with restart count 0 and OOM false. Local/VM `autotrade.py` SHA-256: `164906be52c422aa12e1cf5b547db80b3f1b5fcbf8f533818ef7906fd515ceb5`.
- The first real cycle completed at 06:17:19 KST. Its private observation recorded strategy version `2026-09-24-atr-volatility-gate` and `max_atr_pct=6.0`; consecutive failures, risk-check failures and pending orders remained zero.
- Automatic dashboard commit `a9d2a95` was generated and pushed. The public GitHub Pages payload showed the 06:17:19 decision and new strategy version, and bot-user GitHub SSH access returned the same commit.
- No verification order was submitted. The bot held only KRW and the existing 12-hour loss-streak pause remained active; the tighter ATR gate only restricts future entries. See `STRATEGY_REVIEW_2026-09-24.md` for the realized-trade and observation diagnostics.

## Deployment verified on 2026-09-27

- Source revision: `9ef347d` (`2026-09-27-atr-five-percent-gate`). Local and isolated VM tests each passed 82 tests. The VM backup is `/home/sorryrlrud/bot-backup-20260927-rIDRnb`; no dependency or image rebuild was needed.
- Container started at 06:07:51 KST with restart count 0 and OOM false. Local/VM `autotrade.py` SHA-256: `735bda5fb90769489d742dafe3e8c27d04a29ea3590dbb4a9534bb54e8522012`.
- The first real cycle completed at 06:09:10 KST. Its private observation recorded strategy version `2026-09-27-atr-five-percent-gate` and `max_atr_pct=5.0`; consecutive failures, risk-check failures and pending orders remained zero.
- The latest three realized results were losses, so the existing twelve-hour loss-streak pause correctly blocked new entries. The account held KRW only and no verification order was submitted.
- Automatic dashboard commit `9c9f03e` was generated and pushed. Local, VM and remote source history all contain the deployment commit. See `STRATEGY_REVIEW_2026-09-27.md` for the realized-trade and observation evidence behind the 5% ceiling.

## Deployment verified on 2026-09-28

- Source revision: `3bc300d` (`2026-09-28-six-hour-momentum-gate`). Local and isolated VM tests each passed 83 tests. The VM backup is `/home/sorryrlrud/bot-backup-20260928-OMKWvP`; no dependency or image rebuild was needed.
- Container started at 06:11:36 KST with restart count 0 and OOM false. Startup logged `min_entry_change_6h_pct=0.5`, `max_entry_atr_pct=5.0`, and the existing loss/cooldown settings.
- The first real cycle completed at 06:13:03 KST. Its private observation recorded strategy version `2026-09-28-six-hour-momentum-gate` and `min_change_6h_pct=0.5`; consecutive failures, risk-check failures, and pending orders remained zero.
- The account retained its existing BTC position, which remained on HOLD. The latest four realized results were losses, so the existing twelve-hour loss-streak pause continued to block new entries; no verification order was submitted.
- Automatic dashboard commit `2dfdb4b` was generated and pushed. The dashboard payload showed the 06:13:03 successful cycle, three recent decisions, and the new strategy version. Bot-user GitHub SSH access returned the same remote revision.
- See `STRATEGY_REVIEW_2026-09-28.md` for the realized-trade and deduplicated opportunity evidence behind the six-hour momentum floor.

## Deployment verified on 2026-09-30

- Source revision: `9583eb6` (`2026-09-30-profit-protection-memory`). Local and isolated VM suites each passed 103 tests with socket connections blocked. The VM backup is `/home/sorryrlrud/bot-backup-20260930-0G3DdA`; source and runtime history were preserved. No image rebuild or dependency change was needed.
- Container started at 07:05:33 KST with zero restarts and no OOM. Local/VM `autotrade.py` SHA-256: `cc192079f7fc8346321360155ec85efcd9cc588d919e1ce1aee406968bb54538`. Startup confirmed the 1.2% gross profit-memory threshold, required 15-minute trend break, and 60-second peak sampling.
- The first real cycle completed at 07:07:01 KST and dashboard refresh completed at 07:07:04. Consecutive failures, risk failures and pending orders remained zero. The bot held no coin position; no candidate passed the unchanged entry filters and no verification order was submitted.
- Automatic dashboard commit `642f3a8` followed the first cycle. See `STRATEGY_REVIEW_2026-09-30_CYCLE.md` for the retrospective diagnostic, rejected price-only trail, and performance limitations.

## Deployment verified on 2026-10-01

- Source revision: `2030511` (`2026-10-01-15m-rsi-overheat-gate`). Local and isolated VM suites each passed 105 tests. The VM backup is `/home/sorryrlrud/bot-backup-20261001-dwYmDO`; no dependency or image rebuild was needed.
- The container started at 06:10:59 KST with zero restarts and no OOM event. Local, VM and container `autotrade.py` SHA-256 was `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081`.
- Startup logged `max_entry_15m_rsi=75.0`. The first risk check had no holdings, stops, or pending orders, and the first real cycle completed at 06:12:17 KST with zero failures.
- The first private observation recorded the new strategy version and RSI ceiling. The existing twelve-hour loss-streak pause blocked entries, so no verification order was submitted.
- Automatic dashboard commit `91afa8d` was pushed. The public GitHub Pages payload returned HTTP 200 with the 06:12:17 generation time, new strategy version, and entry-block reason. Bot-user GitHub access and a host-side fast-forward pull both succeeded.

## Reporting deployment verified on 2026-10-02

- Source/report revision: `94ba2a3`; VM backup: `/home/sorryrlrud/bot-backup-20261002-ztjp6tzd`.
- Corrected the dashboard label to `실현 거래 수익률` and explained its completed-trade purchase-amount plus buy-fee denominator. Account flows and open-position marks are excluded; the calculation and data field are unchanged.
- The VM fast-forwarded source and regenerated/published the dashboard from the existing container as the bot user (`0ccd963`). Because only the separately invoked generator changed, no trading-process restart or image rebuild was needed.
- Local/VM/container generator SHA-256: `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. Trading source remains the October 1 strategy.
- Public HTTP 200 and browser inspection confirmed the 06:08:56 dashboard and corrected wording. GitHub Pages run `36926685891` succeeded. The original container remained running with zero restarts/OOM, and the 06:09:03 risk check had zero failures/pending orders.
- See `STRATEGY_REVIEW_2026-10-02.md` for the independently verified KRW 275 deposit, open BTC/ETH marks, forward RSI opportunity and reasons for keeping trading rules unchanged.

## Daily review verified on 2026-10-04

- VM/container remained healthy with zero restarts, OOM, cycle/risk failures or pending orders; the 06:01:32 cycle and subsequent risk checks succeeded. Trading source remains the October 1 strategy, and the dashboard generator remains the October 2 reporting correction.
- Upbit CLI on the VM independently verified KRW 58,874.58949578, no holdings/locked balances/open orders, and the three sells since the last documented October 2 review. Those sells netted +KRW 78.99; no new trade occurred after the scheduled prior run at October 3 12:12 KST. The October 1 KRW 275 deposit was excluded from profit.
- Lifetime realized PnL remains negative at -KRW 6,245.34. Current-version forward evidence is only three completed trades. Rechecking the relevant fixed-entry subset still disfavors a price-only trail on net PnL, so trading rules remain unchanged.
- Local 105-test suite passed in an isolated temporary copy with socket connections blocked. Public HTTP 200 showed the current heartbeat, three decisions and no private entry context. Only this operations guide and `STRATEGY_REVIEW_2026-10-04.md` are synchronized; no trading-process restart or image rebuild is required.

## Daily review verified on 2026-10-05

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The 06:01:41 cycle and 06:06:21 risk check succeeded; public HTTP 200 showed the current heartbeat and three decisions without private entry context.
- Upbit CLI independently verified two new filled market buys (SOL and XRP), no sells, no new flows or open orders, and cash KRW 29,562.1658117. Actual entry quantities, funds and fees reconcile with VM state and prior cash. At the 06:04:01 price snapshot, equity was KRW 58,906.58 (+0.05433% since the prior all-cash baseline); estimated open-position liquidation PnL was +KRW 17.31 before adverse execution movement.
- Lifetime realized PnL remains -KRW 6,245.34 and current-version completed trades remain three. A new RSI-only blocked BTC signal has no forward price path yet; exit diagnostics still disfavour price-only trailing exits. Trading rules and configuration remain unchanged.
- All 105 local tests passed in an isolated temporary copy with socket connections blocked. Only this guide and `STRATEGY_REVIEW_2026-10-05.md` require synchronization; no trading-process restart or image rebuild is needed.

## Daily review verified on 2026-10-06

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The 06:01:35 cycle and 06:03:30 risk check succeeded. Trading source and generator hashes remain unchanged.
- Upbit CLI independently verified one new buy and three full exits, no new flows, no holdings/locked funds/open orders, and cash KRW 58,436.02440822. Exact new net PnL -KRW 438.565087557572 reconciles with the October 4 all-cash baseline. Lifetime PnL is -KRW 6,683.91; current-version six completed trades net -KRW 359.58.
- XRP exited profitably after profit memory armed; SOL and ZKP never armed. ZKP's independent hard stop executed normally, with observed trigger/fill movement and fees explaining its -2.57% net loss. Six current-version trades and mixed RSI-only forward signals do not support another rule change.
- Public HTTP 200 still showed 04:31:34 at 06:05 despite the VM and pushed repository showing 06:01:36. GitHub run 37373345322 was queued without a runner, with prior builds cancelled before executing steps. Official Actions incident 3q1yb5m7ltvb reports hosted-runner assignment delays and a major outage. Public deployment freshness is blocked externally; successful repository push alone is not proof of public deployment success.
- All 105 isolated local tests passed with socket connections blocked. Only this guide and `STRATEGY_REVIEW_2026-10-06.md` are synchronized; the unchanged trading process requires no restart or image rebuild. Next review must check Actions recovery and public heartbeat freshness.

## Daily review verified on 2026-10-07

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The 06:01:33 cycle and 06:03:17 risk check succeeded; trading and generator hashes remain unchanged.
- Upbit CLI independently verified one new SOL buy/full exit, exact net PnL -KRW 121.103340540 and cash KRW 58,314.92106768. Quantities, funds and fees reconcile exactly with the previous all-cash balance; there are no holdings, locked funds, open orders or new flows. Lifetime realized PnL is -KRW 6,805.01; current-version seven completed trades net -KRW 480.68.
- SOL's allowed reentry and joint-trend loss exit complied with existing controls; its +0.2445% peak never armed profit protection. Three consecutive losses correctly triggered the twelve-hour pause. Additional paused signals and unchanged mixed RSI-only evidence do not support a rule change.
- Actions recovered from incident 3q1yb5m7ltvb. Pages run 37530866831 succeeded for dashboard commit 049c27a, and public HTTP 200 independently showed the 06:01:34 generation time, 06:01:33 cycle, three decisions and no private entry context/order UUID.
- Journal rotation reduced coverage to September 21 onward: 1,512 observations and thirteen comparable fixed-entry paths. Do not compare this total directly with yesterday's sixteen-path result. All 105 isolated local tests passed; only this guide and STRATEGY_REVIEW_2026-10-07.md require synchronization, with no trading restart or image rebuild.

## Daily review verified on 2026-10-08

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The 05:46:33 cycle and 05:58:01 risk check succeeded; source/generator hashes remain unchanged. Public HTTP 200 showed the 05:31:33 bounded heartbeat, three decisions and no private entry context/UUID; Pages run 37682661752 succeeded.
- Upbit CLI independently verified one new SOL buy/full exit, exact net PnL -KRW 350.455074885, and cash KRW 57,964.4659928. Quantity, funds and fees reconcile with prior cash within exchange decimal precision; there are no holdings, locked funds, open orders or new flows. Lifetime PnL is -KRW 7,155.47; current-version eight completed trades net -KRW 831.14.
- SOL's third current-version loss followed a valid sixteen-hour reentry gap. Its peak never armed profit memory; the next minute-level risk check after threshold crossing executed the hard stop, with fill movement and fees explaining the -2.4147% net loss. The twelve-hour global pause and subsequent defensive market gate behaved as intended.
- Longer ticker-pause diagnostics also remove an ETH winner and change which later loss triggers a pause; eighteen-hour sample maximization would tune to today's loss. No new RSI-only evidence or exit alternative supports changing rules. Trading configuration remains unchanged.
- Journal coverage is September 21 onward, 1,607 observations and fourteen comparable holding paths, with one new SOL loss since the previous review. All 105 isolated local tests passed. Only this guide and STRATEGY_REVIEW_2026-10-08.md require synchronization; no trading restart or image rebuild is required.

## Daily review verified on 2026-10-09

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The 05:46:32 cycle and 05:58:58 risk check succeeded; source/generator hashes remain unchanged. Logs since the previous run contained 1,920 INFO records and no warnings/errors.
- Read-only VM Upbit CLI independently verified unchanged all-cash KRW 57,964.4659928, no locked balances, waiting/reserved orders, new completed orders or new flows. Lifetime realized PnL remains -KRW 7,155.47; the current eight-trade strategy remains -KRW 831.14 (-1.41360% against the flow-adjusted cash baseline).
- All 96 newly observed cycles were defensive and intentionally blocked entries. The existing loss-streak pause had expired. No new trade, numeric opportunity, RSI-only signal or holding path changes the previous diagnostics; trading rules and configuration remain unchanged.
- Journal coverage is September 21 onward, 1,703 observations and the same fourteen comparable holding paths. All 105 isolated local tests passed with sockets blocked. Pages run 37834484417 succeeded; public HTTP 200 showed the 04:46:37 heartbeat, three decisions and no private context/UUID. Unchanged heartbeat refreshes occur on the first cycle after the hourly minimum spacing, allowing approximately 75 minutes before refresh plus external deployment latency.
- The next real cycle completed at 06:01:32, stayed defensive, and generated the due heartbeat commit `ad40c5e`; its 06:01:00 risk check also succeeded. Only this guide and STRATEGY_REVIEW_2026-10-09.md require synchronization; no trading restart or image rebuild is required.

## Daily review verified on 2026-10-10

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The initial 05:46:32 cycle and 05:57:17 risk check succeeded; source/generator hashes remain unchanged. Initial logs since the prior run contain 1,918 INFO records and no warnings/errors; disk usage is 31% and no zombies were found.
- Read-only VM Upbit CLI independently verified unchanged all-cash KRW 57,964.4659928, zero locked funds/open orders and no new completed orders or flows. Lifetime realized PnL remains -KRW 7,155.47; the current eight-trade strategy remains -KRW 831.14 (-1.41360% against the flow-adjusted cash baseline).
- All 96 new observed cycles were defensive and submitted no order. No new numeric opportunity, RSI-only signal or holding path changes the prior cooldown/exit diagnostics. Trading rules and configuration remain unchanged.
- Journal coverage remains September 21 onward with 1,799 observations and fourteen comparable holding paths. All 105 isolated local tests passed with sockets blocked. Pages run 37985879495 succeeded; public HTTP 200 showed the 05:16:32 heartbeat, three decisions and no private context/UUID.
- Only this guide and STRATEGY_REVIEW_2026-10-10.md require publishing and VM synchronization; the unchanged trading process needs no restart or image rebuild.

## Daily review verified on 2026-10-11

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The 06:01:33 cycle and 06:02:46 risk check succeeded; source/generator hashes remain unchanged. Snapshot logs since the previous verified run contain 1,927 INFO records and no warnings/errors; disk usage is 31% and no zombies were found.
- Read-only VM Upbit CLI independently verified unchanged all-cash KRW 57,964.4659928, zero locked funds/open orders and no new completed orders or flows. Lifetime realized PnL remains -KRW 7,155.47; the current eight-trade strategy remains -KRW 831.14 (-1.41360% against the flow-adjusted cash baseline).
- All 97 new observations since yesterday's 05:46 snapshot are defensive and submit no order. No new numeric opportunity, RSI-only signal or holding path changes the prior cooldown/exit diagnostics. Trading source and configuration remain unchanged.
- Journal coverage remains September 21 onward with 1,896 observations and fourteen comparable holding paths. All 105 isolated local tests passed with sockets blocked. Pages run 38086033204 completed build/report/deploy successfully; public HTTP 200 showed the 06:01:33 heartbeat, three decisions and no private context/UUID.
- Only this guide and STRATEGY_REVIEW_2026-10-11.md require publishing and VM fast-forward synchronization; the unchanged trading process needs no restart or image rebuild.

## Daily review verified on 2026-10-12

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The 06:01:37 cycle and 06:04:30 risk check succeeded; trading/generator hashes remain unchanged. Snapshot logs since the previous final verification contain 1,914 INFO records and no warnings/errors. Disk usage is 32% and no zombies were found.
- Read-only VM Upbit CLI independently verified unchanged all-cash KRW 57,964.4659928, zero locked funds/open orders and no new completed orders or flows. Lifetime realized PnL remains -KRW 7,155.47; the current eight-trade strategy remains -KRW 831.14 (-1.41360% against the flow-adjusted cash baseline).
- All 96 new cycle observations are defensive and submit no order. No new eligible opportunity, RSI-only signal or holding path changes the prior diagnostics. Trading source/configuration remain unchanged; the latest 24 signals also fail numeric filters when defensive blocking is diagnostically bypassed.
- Journal coverage remains September 21 onward with 1,992 observations and the same fourteen comparable holding paths. All 105 isolated local tests passed with sockets blocked. Pages run 38173624111 completed successfully; public HTTP 200 showed the 05:46:37 heartbeat, three decisions and no private entry context/UUID.
- Only this guide and STRATEGY_REVIEW_2026-10-12.md require publishing and VM fast-forward synchronization; the unchanged trading process requires no image build or restart.

## Daily review verified on 2026-10-13

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The 05:46:30 cycle and 05:57:51 risk check succeeded; trading/generator hashes match local, VM and container. Snapshot logs since the prior final verification contain 1,903 INFO records and no warnings/errors. Disk usage is 32% and no zombies were found.
- Read-only VM Upbit CLI independently verified unchanged all-cash KRW 57,964.4659928, zero locked funds/open orders and no new completed orders or flows. Lifetime PnL remains -KRW 7,155.47; current eight-trade strategy remains -KRW 831.14 (-1.41360% against the flow-adjusted cash baseline).
- All 95 new observations are defensive with no order plan or holding. The latest 21 candidates also fail numeric filters when defensive blocking is diagnostically bypassed. No new eligible opportunity or RSI-only signal supports changing trading rules/configuration.
- Journal rotation moved coverage to September 26 onward: 1,585 observations, 502 older observations removed, and eleven comparable holding paths versus fourteen yesterday. Recalculated exit totals reflect this sample change, not new performance. All eight current-version paths remain present and unchanged under both exit alternatives.
- All 105 isolated local tests passed with sockets blocked. Pages run 38304791681 succeeded; public HTTP 200 showed the 05:31:31 generation / 05:31:30 cycle heartbeat, 92 exits, three decisions and no private context/UUID.
- Only this guide and STRATEGY_REVIEW_2026-10-13.md require publishing and VM fast-forward synchronization; unchanged trading code requires no image build or restart.

## Daily review verified on 2026-10-14

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The initial 05:46:27 cycle and 05:58:06 risk check succeeded; the next real cycle completed at 06:01:26 and remained defensive. Trading/generator hashes match local, VM and container. Initial logs since prior final verification contain 1,909 INFO records and no warnings/errors. Disk usage is 32% and no zombies were found.
- Read-only VM Upbit CLI independently verified unchanged all-cash KRW 57,964.4659928, zero locked funds/open orders and no new completed orders or flows. Lifetime PnL remains -KRW 7,155.47; current eight-trade strategy remains -KRW 831.14 (-1.41360% against the flow-adjusted baseline).
- All 95 new observations after yesterday's final cycle are defensive, with no order plan or holding. The latest initial 20 candidates also fail numeric filters if defensive blocking is diagnostically bypassed. No new eligible opportunity or RSI-only signal supports a rule/configuration change.
- Journal coverage remains September 26 onward: 1,681 observations, 96 additions relative to yesterday's initial snapshot and no rotation. The same eleven holding paths and all eight current-version paths retain unchanged exit diagnostics. All 105 isolated local tests passed with sockets blocked.
- Pages run 38459501962 succeeded; public HTTP 200 showed the 05:01:26 bounded heartbeat, 92 exits, three decisions and no private context/UUID. Only this guide and STRATEGY_REVIEW_2026-10-14.md require publishing and VM fast-forward synchronization; unchanged trading code requires no image build or restart.

## Daily review verified on 2026-10-15

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The initially running cycle completed at 06:01:30; the 06:01:40 risk check succeeded. Source/generator hashes match local, VM and container. Initial logs since the prior final verification contain 1,911 INFO records and no warnings/errors. Disk usage is 33%, available memory 444 MiB, and no zombies were found.
- Read-only VM Upbit CLI verified unchanged all-cash KRW 57,964.4659928, zero locked funds/open orders and no new completed orders or flows. Lifetime realized PnL remains -KRW 7,155.47; the current eight-trade strategy remains -KRW 831.14 (-1.41360% against the flow-adjusted cash baseline).
- All 95 new initial observations and the following 06:01:30 cycle are defensive without order plans or holdings. The latest initial 21 candidates also fail numeric filters if defensive blocking is diagnostically bypassed. No new eligible opportunity supports changing trading rules/configuration.
- Journal coverage remains September 26 onward: 1,777 initial observations, 96 additions relative to yesterday's initial snapshot and no rotation. The same eleven comparable holding paths and all eight current-version paths retain unchanged diagnostics. All 105 isolated local tests passed with sockets blocked.
- Pages run 38632819661 completed build/report/deploy successfully; public HTTP 200 showed 05:31:31 generation / 05:31:30 cycle, 92 exits, three decisions and no private context/UUID. Only this guide and STRATEGY_REVIEW_2026-10-15.md require publishing and VM fast-forward synchronization; unchanged trading code requires no image build or restart.

## Daily review verified on 2026-10-16

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. Initial cycle completed at 05:46:30 and the 05:59:08 risk check succeeded. Trading/generator hashes match local, VM and container. Initial logs since October 15 06:03:40 contain 1,907 INFO records and no warnings/errors; disk usage is 33%, available memory 471 MiB, and there are no zombies. Bot-user GitHub SSH succeeds.
- Read-only VM Upbit CLI checks at 05:59:02 independently verified unchanged all-cash KRW 57,964.4659928, zero locked funds/open orders and no new completed orders or flows. Lifetime realized PnL remains -KRW 7,155.47; the current eight-trade strategy remains -KRW 831.14 (-1.41360% against the flow-adjusted cash baseline).
- All 95 initial observations after yesterday's final cycle are defensive, without order plans or holdings. All latest 21 candidates fail numeric filters when defensive blocking is diagnostically bypassed: ATR 15, daily MA20 four, and hourly momentum two. No new eligible opportunity supports a trading-rule/configuration change.
- Journal coverage remains September 26 onward: 1,873 observations, 96 additions relative to yesterday's initial snapshot and no rotation. The same eleven comparable paths and all eight current-version paths retain unchanged exit diagnostics. All 105 isolated local tests passed with socket connections blocked.
- Pages run 38800607594 completed build/report/deploy successfully; public HTTP 200 showed 05:16:30 generation/cycle, 92 exits, three decisions and no private context/UUID. Publish this guide and STRATEGY_REVIEW_2026-10-16.md and fast-forward the VM. Unchanged trading code requires no image build or restart.

## Daily review verified on 2026-10-17

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The initial 05:46:32 cycle and 05:58:34 risk check succeeded; the next cycle started at 06:00:20 and a follow-up VM check confirmed successful completion at 06:01:30, still defensive with no decisions or holdings. Trading/generator hashes match local, VM and container. Initial logs after October 16 06:01:30 contain 1,910 INFO records and no warnings/errors. Disk usage is 32%, available memory 473 MiB and no zombies were found; bot-user GitHub SSH succeeds.
- Read-only VM Upbit CLI checks completed at 05:59:59: unchanged all-cash KRW 57,964.4659928, no locked funds, open orders, new completed orders or flows. Lifetime realized PnL remains -KRW 7,155.47; current eight-trade strategy remains -KRW 831.14 (-1.41360% against its flow-adjusted baseline).
- All 95 initial observations after yesterday's final cycle are defensive, with no plans or holdings. Diagnostically bypassing defensive blocking still rejects all 22 latest candidates: 18 exceed ATR and four miss six-hour momentum. No new eligible opportunity supports a trading-rule/configuration change.
- Journal coverage remains September 26 onward: 1,969 observations, 96 additions against yesterday's initial snapshot and no rotation. Eleven comparable exit paths and all eight current-version paths retain unchanged diagnostics. All 105 isolated local tests passed with socket connections blocked.
- Pages run 38961057159 completed build/report/deploy successfully; public HTTP 200 showed 05:16:32 generation/cycle, 92 exits, three decisions and no private context/UUID. Publish this guide and STRATEGY_REVIEW_2026-10-17.md and fast-forward the VM. Unchanged trading code requires no image build or restart.

## Daily review verified on 2026-10-18

- Direct VM/container checks confirmed zero restarts, OOM, cycle/risk failures and pending orders. The 06:01:28 cycle and 06:02:47 risk check succeeded. Trading/generator hashes match local, VM and container. Snapshot logs after October 17 06:01:37 contain 1,920 INFO records and no warnings/errors; disk usage is 32%, available memory 479 MiB and no zombies were found. Bot-user GitHub SSH succeeds.
- Read-only VM Upbit CLI checks at 06:04:16 independently verified unchanged all-cash KRW 57,964.4659928, no locked funds, open orders, new completed orders or flows. Lifetime realized PnL remains -KRW 7,155.47; current eight-trade strategy remains -KRW 831.14 (-1.41360% against its flow-adjusted baseline).
- All 96 observations after yesterday's final cycle are defensive, with no plans or holdings. Diagnostically bypassing defensive blocking rejects all 20 latest candidates: 16 exceed ATR and four miss six-hour momentum. No new numeric opportunity under current/prior RSI rules supports changing trading rules/configuration.
- Journal coverage remains September 26 onward: 2,066 observations, 97 additions against yesterday's initial snapshot and no rotation. Recalculated eleven-path exit and eighteen-entry ticker-pause diagnostics are unchanged; all eight current-version trades retain their observed results under both exit alternatives. All 105 isolated local tests passed with socket connections blocked.
- Pages run 39069175215 completed build/report/deploy successfully; public HTTP 200 showed 06:01:28 generation/cycle, 92 exits, three decisions and no private context/UUID. Publish this guide and STRATEGY_REVIEW_2026-10-18.md and fast-forward the VM. Unchanged trading code requires no image build or restart.

## Daily review verified on 2026-10-19

- The VM/container process is running, but **trading/risk service health is degraded**. Last successful cycle is 02:01:34 KST and last successful risk check 02:02:07. The 05:56 snapshot has 33 consecutive cycle failures and 174 risk failures, all during Upbit connectivity loss; zero pending orders is the last local state, not a fresh exchange verification. Container has zero restarts/OOM, disk use 32%, available memory 472 MiB and matching trading/generator hashes. GitHub publishing remains accessible.
- [Official Upbit notice](https://support.upbit.com/hc/ko/articles/59610087642009-서버-점검-안내-10-19-02-00) schedules full-service maintenance for October 19 02:00–08:00 KST, subject to change. VM host/container and independent public endpoint probes fail for Upbit while GitHub succeeds. A read-only VM Upbit CLI accounts request at 05:59 exceeded an 18-second deadline. Fresh balance, fills, open orders and flows cannot be reconciled until service returns. Do not infer a VM firewall/DNS defect from this exchange-specific failure or mark the bot healthy merely because its process runs.
- Recorded performance remains 92 exits / -KRW 7,155.47 lifetime and eight current-version trades / -KRW 831.14. The last successful 02:01:34 cycle records KRW 57,964.4659928 and zero holdings; October 18's last independently reconciled account remains the exchange comparison boundary. The -1.41360% flow-adjusted baseline comparison is carried forward, not a newly verified account return.
- Eighty new successful observations are defensive with no decisions/holdings. Journal rotation moved coverage to October 2 00:31:40: 1,639 observations versus 2,066 previously, implying 507 older records removed after 80 additions. Current/prior RSI gates yield no new eligible signal. Only eight of eighteen eligible completed entries retain holding paths; all eight current-version paths remain available and unchanged. Compare coverage explicitly before comparing older diagnostics.
- All 105 isolated, socket-blocked local tests passed. Pages run 39164226288 succeeded; public HTTP 200 publishes the 05:38:25 failure snapshot, 92 exits and three decisions, with no private entry context/UUID. No trading-source/configuration change is justified. Synchronize this guide and STRATEGY_REVIEW_2026-10-19.md on the VM; no trading restart or image rebuild is required.
- **Recovery verification remains pending:** after official maintenance completes, inspect VM runtime status and require both cycle and risk success timestamps newer than the outage, failure counters reset to zero, then reconcile CLI accounts, both closed-order states, wait/watch open orders and deposits/withdrawals since the previous verified boundary. Check pending-order reconciliation and dashboard publication. Existing code retries automatically and records failures; do not reset runtime status manually, bypass risk checks or create a verification order.

## Daily review verified on 2026-10-20

- Direct VM/container checks verified automatic recovery without a restart: October 20 06:01:35 cycle and 06:03:17 risk success, both failure counters and pending orders zero. The process remains running since October 1 with zero restarts/OOM; source/generator hashes match local, VM and container. Disk use is 32%, available memory 480 MiB and no zombies were found. Historical October 19 error timestamps precede subsequent successes and must not be treated as current failures.
- The official exchange notice now reports maintenance completion and sequential trading resumption from October 19 06:55. VM risk/account retrieval recovered at 06:30:18 and the first cycle observation is 06:31:57; these earlier successful API checks are not proof that trading had resumed. No trade was submitted during the interval. Snapshot logs after yesterday's 06:01:01 contain 22 remaining outage errors, none after 06:30. One later KRW-ICX ticker HTTP-404 warning was handled by the existing skip path and its cycle completed.
- Read-only VM Upbit CLI checks beginning 06:04:52 independently confirm KRW 57,964.4659928, zero holdings/locked funds/open orders, and no closed orders or flows since the last October 18 06:04:16 reconciliation. Both done/cancel and wait/watch states were queried. Yesterday's pending recovery checklist is satisfied. Lifetime PnL remains -KRW 7,155.47 and eight current-version trades remain -KRW 831.14, or -1.41360% against the existing flow-adjusted baseline.
- All 95 new observations are defensive with no decisions or holdings. Latest 22 candidates also fail numeric gates with defensive blocking diagnostically bypassed: 18 exceed ATR and four miss six-hour momentum. Journal coverage is October 2 onward, 1,734 records, no new rotation. Retained prior-RSI opportunities remain 19; eighteen-entry pause and eight-path exit comparisons remain unchanged. No evidence supports changing trading rules or configuration.
- All 105 isolated local tests passed with socket connections blocked. Pages run 39322132705 succeeded; public HTTP 200 shows 05:46:32 generation, recovered cycle/risk and zero failure counters, 92 exits/three decisions, with no private entry context/UUID. Publish this guide and STRATEGY_REVIEW_2026-10-20.md and fast-forward the VM; unchanged trading code requires no image build or restart.

## Daily review verified on 2026-10-21

- Direct VM/container checks confirmed the 06:01:25 cycle and 06:03:41 risk success, zero cycle/risk failures and pending orders, zero restarts/OOM, and matching local/VM/container trading/generator hashes. Disk use is 32%, available memory 444 MiB, container memory 104 MiB and no zombies were found. VM Git is clean and bot-user GitHub SSH succeeds. October 19 error timestamps are historical and precede subsequent successes.
- Read-only VM Upbit CLI reconciliation at 06:05:25 confirms unchanged all-cash KRW 57,964.4659928, no holdings/locked funds/open orders, and no closed orders or flows since October 20 06:04:52. Both done/cancel and wait/watch states were queried. Lifetime PnL remains -KRW 7,155.47 and eight current-version trades remain -KRW 831.14, or -1.41360% against the existing flow-adjusted baseline.
- All 96 new observations are defensive with no plans/holdings. Latest 20 candidates also fail numeric gates when defensive blocking alone is diagnostically bypassed: 14 ATR, four six-hour momentum, one Bollinger and one fifteen-minute trend. Retained journal coverage remains October 2 onward, 1,830 records and no new rotation. Prior-rule opportunities remain 19; eighteen-entry ticker-pause and eight-path exit comparisons are unchanged. No new evidence supports changing trading rules/configuration.
- Snapshot logs after October 20 06:06:17 contain 1,916 INFO records with no warnings/errors/critical records or trading events. All 105 isolated, socket-blocked local tests passed. Pages run 39490565655 succeeded; public HTTP 200 shows 05:16:25 generation/cycle, risk 05:15:35, zero failure counters, 92 exits/three decisions, without private context/UUIDs. Publish this guide and STRATEGY_REVIEW_2026-10-21.md and fast-forward the VM; unchanged trading source requires no image build or restart.

## Security notes

- Do not place secrets, API keys, private key contents, or `.env` values in this file.
- The public IP, SSH alias, repo path, and operational commands are intentionally documented because they are needed for future maintenance.
- If the VM is recreated or the public IP changes, update this file at the same time as the deployment change.
