# Strategy Review — 2026-10-30

## Production and exchange verification

Direct SSH checks of `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` confirm running since October 1 06:10:59 KST, zero restarts/OOM, successful October 30 06:01:27 cycle and 06:05:53 risk check, zero cycle/risk failures and pending orders. October 19 timeout fields are historical, followed by successful checks. Disk use is 34% with 19 GiB free, available RAM 479 MiB, container RAM 94.6 MiB. VM Git is clean and bot-user GitHub SSH succeeds. Local, VM and container trading/generator SHA256 match the previously verified hashes (`67d5f857…` / `b9202da8…`). No local Docker was used.

Merged VM dotenv/container environment confirms trading and dashboard publication enabled, RUN_ONCE disabled, loop/heartbeat 900/3600 seconds, HTTP timeout ten seconds and existing explicit position cap 25%. No overrides occur among the inspected stop, profit protection, risk-check, ATR, fast RSI, six-hour momentum, defensive-buy and ticker-loss settings. Logs after October 29 06:07:45 contain 1,915 INFO records and zero warning/error/critical or BUY/SELL events.

Read-only VM-host Upbit CLI reconciliation at **06:05:49–06:05:54 KST** confirms KRW **57,964.4659928**, no coin holdings or locked balance, zero done/cancel closed orders since October 29 06:06:10, and zero wait/watch open orders. All 21 deposits and three withdrawals contain no new or pending flows. Credentials stayed in VM memory/child environments; JSON streams and empty CLI results were decoded explicitly. No order or test order was submitted. The official [accounts reference](https://docs.upbit.com/kr/reference/get-balance) documents the read-only balance query.

| Measure | Result |
| --- | ---: |
| New completed trades / daily account change | 0 / KRW 0 (0%) |
| Lifetime realized exits | 92: 28 wins, 64 losses |
| Lifetime net PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| October 1 strategy completed trades | 8: 3 wins, 5 losses |
| Current-strategy net PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-strategy recorded fees | KRW 116.59 |
| Cash versus existing flow-adjusted baseline | -1.41360% |
| Dashboard lifetime completed-trade return | -0.4895% |

The flow-adjusted baseline remains KRW 58,795.60233029, including the previously verified KRW 275 deposit. That deposit and the October 7 SOL loss are not new activity. Dashboard return divides lifetime realized PnL by cumulative completed-trade purchase cost plus buy fees; it differs from account return. Current-strategy performance remains negative.

## Algorithm, prior decisions and coverage

Revisited source history and September 30 / October 1 / October 8 decisions: confirmed-fill reconciliation and independent hard stops; persistent 1.2% gross profit memory with completed fifteen-minute trend confirmation; six-hour momentum floor; ATR/Bollinger/RSI gates; three-hour global and twelve-hour ticker/streak pauses; and the 25% position cap. The October 7 SOL loss was a permitted reentry and never armed profit memory. Historical ETH showed that trend confirmation can surrender an armed gain; the broader current-gate sample previously rejected a price-only trail because it cut profitable recoveries. No new completed trade or execution defect changes that tradeoff.

All four retained journal files contain **1,675 observations**, October 12 15:16:32 through October 30 06:01:27. Relative to yesterday: **2,100 + 96 new - 521 rotated = 1,675**. New observations are all defensive without holdings or planned decisions. Latest BTC is bearish, RSI 45.08, below daily MA20/MA60. With only defensive blocking bypassed, all latest **22 candidates** still fail numeric gates: **16 ATR / six hourly momentum** first rejections.

Pure entry/scoring functions extracted from source AST, recorded market context, configured numeric gates and recorded cycle score thresholds yield **zero new eligible signals** at current RSI 75 and prior RSI 78. Bypassing only defensive blocking while preserving defensive scoring/thresholds also yields zero new signals. Current/prior retained opportunities at six-hour ticker spacing are now both zero. The previously retained one prior-rule opportunity and last October 7 holding path rotated out; this is reduced coverage, not a change in historical performance or proof that exit alternatives no longer matter. The October 25 MTL defensive-only candidate remains previously reviewed evidence, not a new observation or realized avoided loss.

Persisted entry contexts still provide eighteen completed entries passing current gates and recorded score thresholds. Recomputed chronological fixed-entry twelve/eighteen/twenty-four-hour ticker-loss-pause PnL is unchanged at **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. Quantities/exits are fixed, replacement entries and cash reuse absent; choosing eighteen hours on this selected sample would tune to known outcomes.

No completed entry retains a holding path today: all 44 timestamped entries, including the eighteen eligible entries, lack paths; 48 older exits lack entry times. Both exit diagnostics therefore have **zero comparable paths**, and no actual-versus-alternative PnL comparison is available. Do not report an empty diagnostic's zero sum as improved performance or compare it with yesterday's one-path -KRW 350.46. Full trade history still establishes current-strategy -KRW 831.14. No new armed-profit loss, repeated ticker loss after valid reentry, or stop-trigger/fill gap occurred. Sparse fifteen-minute snapshots cannot reproduce minute-level stops or intraperiod peaks.

## Decision and validation

**Keep trading source/configuration unchanged.** Negative performance remains unresolved, but there is no independent new evidence for another threshold or execution fix. Preserve defensive blocking, profit memory, hard stops, entry gates and loss pauses. Prioritize new completed trades, defensive-only/RSI-only opportunities, repeated ticker losses, armed-profit losses and stop-trigger/fill gaps; report coverage loss separately.

All **105 tests passed** from an isolated local source copy with socket connections blocked. [Pages run 40952016947](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/40952016947) succeeded. Independent public HTTP 200 verification shows October 30 **05:46:27 generation/cycle**, risk 05:45:50, zero failures, 92 exits and three decisions, without private contexts, order UUIDs or pending-order objects. This confirms a newer heartbeat than yesterday's pending publication, within heartbeat plus cycle bounds.

Publish this review and HARNESS.md, synchronize the VM and verify final health/document hashes. Documentation changes require no trading restart or image build. Preserve runtime files and the user's untracked AGENTS.md; remove private temporary snapshots.
