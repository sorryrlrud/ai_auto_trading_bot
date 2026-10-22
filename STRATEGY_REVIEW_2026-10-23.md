# Strategy Review — 2026-10-23

## Production verification

Direct SSH inspection of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` at 05:58 KST confirmed running since October 1 06:10:59, zero restarts/OOM, successful cycle 05:46:29 and risk check 05:57:35, zero cycle/risk failures and pending orders. October 19 error timestamps are historical and precede subsequent successes. Disk use is 33%, available memory 440 MiB, container memory 102 MiB and no zombie processes. VM Git is clean; bot-user GitHub SSH succeeds. Trading/dashboard publication are enabled, single-run mode disabled and HTTP timeout is ten seconds. The only inspected strategy environment override is the existing 900-second loop interval. No local Docker was used.

Trading/generator SHA256 match local, VM and container: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`.

Snapshot logs after October 22 05:58:53 contain 1,917 INFO records, no warnings/errors/critical records and no trading events.

## Exchange reconciliation and returns

Read-only VM Upbit CLI v0.9.1 account/closed-order checks began at 05:58:52 KST; open-order and flow reconciliation completed at 05:59:54. Credentials remained in VM memory and child environments. Account: **KRW 57,964.4659928**, no coins or locked funds. Closed orders, both done/cancel, since October 22 05:57:13 are empty. Open orders, both wait/watch, are empty. All returned deposits (21) and withdrawals (3) have no new or pending flow. CLI JSON output can be a sequence of JSON objects (and empty stdout for empty streamed collections); the reconciliation decoder handles these forms. No order or test order was submitted.

| Measure | Result |
| --- | ---: |
| New completed trades / daily account change | 0 / KRW 0 (0%) |
| Lifetime SELL records | 92: 28 wins, 64 losses |
| Lifetime realized PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| October 1 strategy | 8 completed: 3 wins, 5 losses |
| Current-version realized PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-version recorded fees | KRW 116.59 |
| Dashboard realized-trade return | -0.4895% |

The existing flow-adjusted October 1 baseline is KRW 58,795.60233029, including the previously verified KRW 275 deposit. Current cash is KRW 831.13633749 lower, **-1.41360%**. This is a simple baseline comparison, not a time-weighted return. The dashboard divides realized PnL by cumulative completed-trade purchase cost plus buy fees. The old deposit and October 7 SOL loss are not new activity. The current strategy remains loss-making.

## Historical decisions and algorithm review

Revisited source history and September 30 / October 1 / October 8 reviews: confirmed-fill and pending-order reconciliation, independent hard stops, persistent profit protection requiring a completed fifteen-minute trend break, six-hour momentum floor, ATR/Bollinger/RSI ceilings, three-hour global and twelve-hour ticker/streak loss pauses and 25% position cap. Also checked October 19–20 external outage and recovery. No new runtime defect is evident.

All four retained journal files contain **2,021 observations**, October 2 00:31:40 through October 23 05:46:29. This is **96 additions** against yesterday's 1,925, unchanged start and no rotation. All new observations are defensive with zero plans/holdings. Latest BTC context: bearish, RSI 51.41, below daily MA20 and MA60. Diagnostically bypassing defensive blocking alone rejects all latest **21 candidates: 15 ATR, five six-hour momentum and one Bollinger**. These are first rejection reasons, not executable alternative trades.

Re-extracted source entry/scoring functions and applied actual market context and recorded `buy_threshold` values. Current RSI-75 and prior RSI-78 rules both yield **zero new numeric signals**. The prior-rule sample retains 19 opportunities with six-hour per-ticker spacing and the same RSI-only BTC observation on October 5 (signal 06:00:45, cycle recorded 06:01:41). October 1 remains outside rotated coverage. Numeric diagnostics omit portfolio budgets and execution constraints.

Eighteen completed entries pass current numeric gates and recorded score thresholds. Fixed-entry chronological selected-loss diagnostics remain **+KRW 576.30 / +KRW 818.70 / +KRW 589.34** for twelve/eighteen/twenty-four-hour ticker pauses. As previously reviewed, the eighteen-hour alternative excludes both a known SOL loser and an ETH winner. No new completed trade supplies independent evidence for selecting another threshold.

Ten of eighteen entries lack retained holding paths. The remaining eight are all current-version trades: actual, trend-memory and price-only half-peak-trail results each remain **-KRW 831.14**, with zero earlier alternative exits. No new armed-profit loss, repeated allowed ticker loss or stop trigger/fill gap exists. These sparse fifteen-minute, fixed-entry comparisons preserve original quantities/exits, omit replacement entries/cash reuse and include fees/adverse slippage for hypothetical earlier exits; they do not establish future profitability.

## Decision and validation

**Keep trading source/configuration unchanged.** Performance is negative, but this run adds no independent evidence that warrants a new rule or parameter. Continue tracking current-version completed trades, allowed repeat ticker losses, RSI-only signals, armed-profit losses and stop trigger/fill gaps while preserving flow and observation-coverage boundaries.

All **105 local unit tests passed** from an isolated temporary source copy with socket connections blocked. [Pages run 39849606637](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/39849606637) succeeded. Public HTTP 200 serves generation/cycle 05:31:30, risk 05:30:32, zero failures, 92 exits and three decisions; private entry context, order UUIDs and pending-order objects are absent. Its heartbeat is within the configured hourly publication interval.

Publish this review and `HARNESS.md`, fast-forward the VM and verify final health and document hashes. Documentation-only changes require no trading restart or image build. Preserve runtime data and the user's untracked `AGENTS.md`; remove private temporary snapshots.
