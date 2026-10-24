# Strategy Review — 2026-10-25

## Production verification

Direct SSH inspection of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirmed running since October 1 06:10:59 KST, zero restarts/OOM, successful October 25 06:01:32 cycle / 06:02:14 risk check, zero cycle/risk failures and pending orders. October 19 timeout fields precede subsequent successes and are historical. Disk use is 33%, available memory 472 MiB, container memory 108.9 MiB and no zombie processes were found. VM Git is clean and bot-user GitHub SSH succeeds. Inspected operational overrides remain trading/publication enabled, RUN_ONCE disabled, loop 900 seconds, heartbeat 3600 seconds and HTTP timeout ten seconds; inspected strategy overrides are absent. No local Docker was used.

Local/VM/container trading and generator SHA256 match: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. Snapshot logs after October 24 06:04:51 contain 1,915 INFO records, no warnings/errors/critical records and no BUY/SELL events.

## Exchange reconciliation and performance

Read-only VM-host Upbit CLI checks at **06:03:23–06:03:31 KST** independently confirm **KRW 57,964.4659928**, zero coins/locked balances/open orders. Both done/cancel closed states since October 24 06:04:03 and both wait/watch open states were queried. All returned deposits (21) and withdrawals (3) contain no new or pending flows. Credentials stayed in VM memory/child-process environments. CLI object streams and empty collections were decoded explicitly. No order or test order was submitted. The official [account API reference](https://docs.upbit.com/kr/reference/get-balance) confirms the read-only asset/balance endpoint.

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

Against the previously reconciled flow-adjusted October 1 baseline KRW 58,795.60233029, current cash is lower by KRW 831.13633749 (**-1.41360%**). The baseline already includes the previously verified KRW 275 deposit; that deposit and old losses are not new activity. Dashboard return instead divides realized PnL by cumulative completed-trade purchase cost plus buy fees. Neither figure represents today's gain. Current-strategy performance remains negative.

## Algorithm and historical decisions

Revisited source history and September 30 / October 1 / October 8 reviews: independent hard stops, confirmed fills and pending-order recovery; persistent 1.2% gross profit memory with confirmed fifteen-minute trend exit; six-hour momentum floor, ATR/Bollinger/RSI ceilings; three-hour global / twelve-hour ticker and streak loss pauses; and 25% position cap. The October 7 SOL loss was an allowed reentry after the existing pause and never armed profit memory. Eighteen hours would remove both that loser and an ETH winner in the known sample. No new execution defect or independent evidence supports changing those decisions today.

All four retained journal files contain **1,716 observations**, October 7 05:01:32 through October 25 06:01:32. There are **96 new observations** and **498 older observations have rotated out** since yesterday (2,118 + 96 - 498 = 1,716). Each new observation is defensive with no holdings or planned decisions. Latest BTC is bearish, RSI 41.14, below daily MA20 and MA60. Bypassing only defensive blocking for diagnosis, all latest **21 candidates** fail numeric gates: **17 ATR, two six-hour momentum, one Bollinger and one daily MA20/MA60 alignment**. These are first rejection reasons, not executable alternative trades.

Source AST-extracted entry/scoring functions, actual context and recorded cycle score thresholds produce **zero new numeric signals** at both current RSI 75 and prior RSI 78. Allowing defensive buys diagnostically while preserving defensive scoring also produces zero new signals. Retained prior-RSI opportunities with common six-hour ticker spacing now number **one**, with zero retained RSI-only opportunities. Yesterday's nineteen/one figures covered an earlier starting date: their decline reflects rotation, not a reversal of historical evidence. Both previously discussed October 1 and October 5 RSI-only cases now lack raw observations in this snapshot; their earlier reports remain historical evidence.

Eighteen completed entries with persisted trade entry contexts still pass current numeric gates and recorded score thresholds. Recomputed chronological fixed-entry selection with twelve/eighteen/twenty-four-hour ticker loss pauses remains **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. These trade records are independent of the rotated observation paths. The eighteen-hour result still depends on removing the known SOL loser and ETH winner; no new forward validation was added.

Only **one of those eighteen entries** now has a retained holding path; seventeen lack paths. On this same one-entry sample (October 7 SOL), actual / trend-memory / price-only half-peak-trail results all equal **-KRW 350.46**, with zero earlier alternative exits. Yesterday's eight-path total of -KRW 831.14 cannot be compared as an equal-coverage result. The full current-version realized PnL still remains -KRW 831.14 because trade history was not lost. No new armed-profit loss, allowed repeated ticker loss or stop-trigger/fill gap occurred.

These remain sparse retrospective fixed-entry diagnostics with original sizes/exits, no replacement entries/capital reuse, and estimated fees/adverse slippage for hypothetical earlier exits. Reduced retained coverage limits fresh reproducibility; it does not establish better performance. Do not optimize parameters against the same selected known losses.

## Decision and validation

**Keep trading source/configuration unchanged.** Negative performance remains unresolved, but new observations provide no defect or independent evidence supporting another parameter change. Continue tracking new current-version completed trades, repeated allowed ticker losses, RSI-only opportunities, armed-profit losses and stop-trigger/fill gaps; always report the retained coverage separately.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. [Pages run 40127934806](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/40127934806) completed build/report/deploy successfully. Public HTTP 200 serves October 25 05:01:33 generation, cycle 05:01:31 / risk 05:01:08, zero failures, 92 exits and three decisions without private entry contexts, UUIDs or pending-order objects. The 06:01:32 cycle was four seconds before the next heartbeat boundary measured from VM refresh 05:01:36, so it skipped publishing normally. The public heartbeat is within the configured hourly interval plus one fifteen-minute cycle; the next refresh has not yet been observed.

Publish this review and HARNESS.md, fast-forward the VM and verify final health/document hashes. Documentation changes require no trading restart or image build. Preserve runtime files and the user's untracked AGENTS.md; remove private temporary snapshots.
