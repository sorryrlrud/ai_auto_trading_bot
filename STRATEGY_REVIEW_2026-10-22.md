# Strategy Review — 2026-10-22

## Production verification

Direct SSH inspection of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirmed healthy operation at 05:56 KST. The latest cycle completed at **05:46:28**, risk check at **05:55:53**, with zero cycle failures, risk failures and pending orders. The container remains running since October 1 06:10:59, with zero restarts/OOM. Historical October 19 error timestamps precede later successful checks.

The log snapshot after October 21 06:06:41 contains **1,902 INFO** records and no warnings, errors or critical records. No new trading event is present. Disk use is 33%, available memory 469 MiB, container memory 90.44 MiB, with no zombies. VM Git is clean and bot-user GitHub access succeeds. Trading/dashboard publishing are enabled and single-run mode is disabled. No local Docker was used.

Trading/generator SHA256 match local, VM and container: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`.

## Exchange reconciliation and performance

Read-only **VM Upbit CLI v0.9.1** checks ran at **05:57:13–05:57:20 KST**, with credentials confined to VM memory and child environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) returned only **KRW 57,964.4659928**, with no locked funds or coin balances. Both closed-order states (`done`, `cancel`) since October 21 06:05:19 are empty; both open-order states (`wait`, `watch`) are empty. All returned deposits (21) and withdrawals (3) were checked, with no newly created/completed or pending flows. No exchange write or verification order was submitted.

| Measure | Result |
| --- | ---: |
| New completed trades / account change | 0 / KRW 0 (0%) |
| Lifetime explicit SELL records | 92: 28 wins, 64 losses |
| Lifetime realized PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| October 1 strategy | 8 completed: 3 wins, 5 losses |
| Current-version PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-version recorded fees | KRW 116.59 |
| Current-version SOL | 3 losses, -KRW 620.01 |
| Current all-cash account value | KRW 57,964.4659928 |
| Dashboard realized-trade return | -0.4895% |

Against the existing October 1 cash baseline plus the previously verified KRW 275 deposit, **KRW 58,795.60233029**, cash is **KRW 831.13633749 lower / -1.41360%**. This is a simple flow-adjusted baseline comparison, not a time-weighted return. The dashboard's separate denominator is cumulative completed-trade purchase cost plus buy fees. Neither the old loss nor the old deposit is today's activity. Current forward strategy performance remains negative.

## Algorithm and historical decisions

Reviewed source history and previous decisions: confirmed-fill reconciliation and independent hard stops; three-hour global and twelve-hour ticker/streak loss pauses; 25% position cap; ATR/Bollinger ceilings; September 28 six-hour momentum floor; September 30 persistent profit memory; October 1 completed fifteen-minute RSI ceiling; October 7–8 allowed SOL reentries/stop execution; and October 19–20 exchange outage/recovery. The current inactivity follows intended entry controls, with no newly observed application defect.

The retained private journal has **1,925 observations**, October 2 00:31:40 through October 22 05:46:28. There are **95 additions** relative to yesterday's 1,830, with unchanged coverage start and no rotation. All 95 are defensive, with zero order plans and holdings. Latest BTC context is bearish, RSI **44.94**, below daily MA20 and above MA60. Diagnostically bypassing only defensive blocking still rejects all latest **20 candidates: 15 ATR, two six-hour momentum, one Bollinger, one daily MA20/MA60 alignment and one price below daily MA20**. These are first rejection reasons, not executable alternative trades.

Re-extracted the current and prior RSI-78 gate/scoring functions from source, retaining actual market context, other current filters and recorded score thresholds. Both yield **zero new numeric signals**. Common six-hour ticker spacing yields **19 retained prior-rule opportunities**, including the same one retained RSI-only BTC signal, October 5 06:00:45. The October 1 case remains outside rotated coverage. Numeric opportunities omit execution budgets and portfolio constraints and are not trade counts.

Eighteen completed entries pass current numeric gates and their recorded thresholds. Recomputed fixed-entry chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. As discussed October 8, the best observed threshold removes both a known SOL loser and an ETH winner, and longer pauses change which selected losses start later pauses. No new completed trade provides independent evidence for choosing another threshold.

Ten of eighteen entries lack retained holding paths. The remaining **eight are all eight current-version trades**. Actual, trend-memory and price-only half-peak-trail diagnostics each remain **-KRW 831.14**, with zero earlier alternative exits. No new armed-profit loss, allowed repeat ticker loss or stop trigger/fill gap is present. Original entries, quantities and exits remain fixed; replacement entries/cash reuse are omitted, and hypothetical earlier exits include fees/adverse slippage. Sparse fifteen-minute observations cannot reproduce minute-level monitoring. These retrospective comparisons do not establish future profitability.

## Decision, validation and synchronization

**Keep trading source and configuration unchanged.** There is no new defect or independent strategy evidence supporting a parameter change. Negative historical performance alone does not justify optimizing another threshold against the same known outcomes.

All **105 local unit tests passed** from an isolated temporary source copy with socket connections blocked. [Pages run 39664554752](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/39664554752) completed build/report/deploy successfully. Independent public HTTP 200 serves generation/cycle **04:46:28**, risk **04:45:50**, zero failure counters, 92 exits and three decisions. Private entry context, order UUIDs and pending-order objects are absent. The VM's last dashboard refresh is 04:46:30; its 05:46:28 cycle precedes the one-hour refresh boundary by two seconds, so a new heartbeat is expected on a later cycle. The newer VM cycle is independently verified.

Publish this review and `HARNESS.md`, fast-forward the VM, then verify document hashes and current health. Documentation-only synchronization requires no trading image rebuild or process restart. Preserve runtime data and the user's untracked `AGENTS.md`; remove private temporary snapshots after review.

Next review should track new current-version completed trades, repeated allowed ticker losses, new RSI-only opportunities, armed-profit losses and stop trigger/fill differences. Preserve cash-flow boundaries, return denominators and observation coverage.
