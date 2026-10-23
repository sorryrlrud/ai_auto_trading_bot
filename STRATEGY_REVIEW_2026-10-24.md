# Strategy Review — 2026-10-24

## Production verification

Direct SSH inspection of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirmed running since October 1 06:10:59 KST, zero restarts/OOM, successful October 24 06:01:30 cycle / 06:01:51 risk check, zero cycle/risk failures and pending orders. October 19 timeout timestamps precede subsequent successes and are historical. Disk use is 33%, available memory 456 MiB, container memory 89.23 MiB and no zombie processes. VM Git is clean and bot-user GitHub SSH succeeds. Trading/publication remain enabled, RUN_ONCE disabled and HTTP timeout ten seconds. Inspected environment overrides are the expected heartbeat 3600, loop 900 and position cap 25%, plus those operational flags. No local Docker was used.

Local/VM/container trading and generator SHA256 match: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. Snapshot logs after October 23 06:01:35 contain 1,919 INFO records, zero warnings/errors/critical records and no BUY/SELL events.

## Exchange reconciliation and performance

Read-only VM-host Upbit CLI checks at 06:04:03–06:04:10 KST independently confirm **KRW 57,964.4659928**, zero coins/locked balances/open orders. Both done/cancel closed states since October 23 05:58:52 and both wait/watch open states were queried. All returned deposits (21) and withdrawals (3) contain no new or pending flows. Credentials stayed in VM memory/child-process environments. CLI object streams and empty collections were decoded explicitly. Initial CLI invocation inside the container failed because its binary is installed only on the VM host; the successful reconciliation above ran on the host. No order/test order was submitted.

| Measure | Result |
| --- | ---: |
| New completed trades / daily account change | 0 / KRW 0 (0%) |
| Lifetime realized SELL records | 92: 28 wins, 64 losses |
| Lifetime realized PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| October 1 strategy | 8 completed: 3 wins, 5 losses |
| Current-version realized PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-version recorded fees | KRW 116.59 |
| Dashboard realized-trade return | -0.4895% |

Against the previously reconciled flow-adjusted October 1 baseline KRW 58,795.60233029, current cash is lower by KRW 831.13633749 (**-1.41360%**). This simple baseline comparison includes the previously verified KRW 275 deposit, which is not new income. Dashboard return instead divides realized PnL by cumulative completed-trade purchase cost plus buy fees. Neither figure represents today's gain. The current strategy remains loss-making; old SOL losses are not counted again.

## Algorithm and prior decisions

Revisited the source revision history and September 30 / October 1 / October 8 reviews: independent hard stops, persistent 1.2% gross profit memory with confirmed fifteen-minute trend exit, six-hour momentum floor, ATR/Bollinger/RSI ceilings, three-hour global / twelve-hour ticker and streak loss pauses, 25% position cap and confirmed-fill/pending-order handling. The October 19 external maintenance outage remains recovered. No new runtime defect was found.

All four retained journal files contain **2,118 observations**, October 2 00:31:40 through October 24 06:01:30: **97 additions**, same starting coverage, no rotation. All 97 new observations are defensive with no plans or holdings. Latest BTC is bearish, RSI 41.13, below daily MA20 and MA60. Bypassing only defensive blocking for diagnosis, all latest **21 candidates** are rejected: **16 ATR, four six-hour momentum, one Bollinger**. These are first rejection reasons, not executable alternative trades.

Source AST-extracted entry/scoring functions with actual context and recorded cycle score thresholds yield zero new signals under both current RSI-75 and prior RSI-78 rules. Allowing defensive buys diagnostically while preserving defensive scoring also yields zero new numeric signals. Thus no new RSI-only opportunity or trade outcome changes the prior decision. Rotated October 1 observations cannot be recovered from this snapshot.

Eighteen completed entries pass the current numeric gates and their recorded score thresholds. Recomputed chronological fixed-entry selection with twelve/eighteen/twenty-four-hour ticker loss pauses remains **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. As reviewed on October 8, the eighteen-hour alternative removes a known SOL loser and an ETH winner; it has no new independent validation here. Ten of these eighteen entries lack retained holding paths. On the remaining eight, actual / trend-memory / price-only half-peak-trail results all remain **-KRW 831.14**, zero earlier alternative exits. No new armed-profit loss, repeated allowed ticker loss or stop-trigger/fill gap exists.

These are sparse retrospective fixed-entry diagnostics, with original sizes/exits, no replacement entries/capital reuse, and estimated fees/adverse slippage for hypothetical earlier exits. They do not establish future profitability. Changing thresholds to maximize the same known sample would not address the lack of new validation.

## Decision and validation

**Keep trading source/configuration unchanged.** Negative performance warrants continued review, but today's observations provide no new execution defect or independent evidence supporting another parameter change. Track additional current-version completed trades, repeated allowed ticker losses, RSI-only opportunities, armed-profit losses and stop-trigger/fill gaps.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. [Pages run 40019892028](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/40019892028) succeeded. Public HTTP 200 serves October 24 05:31:31 generation/cycle, risk 05:30:48, zero failure counters, 92 exits and three decisions without private entry context, UUIDs or pending-order objects. Its heartbeat is within the configured hourly interval.

Publish this review and HARNESS.md, fast-forward the VM and verify final health/document hashes. Documentation-only changes require no trading restart or image build. Preserve runtime files and the user's untracked AGENTS.md; remove private temporary snapshots.
