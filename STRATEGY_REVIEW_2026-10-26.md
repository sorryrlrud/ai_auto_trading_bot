# Strategy Review — 2026-10-26

## Production verification

Direct SSH inspection of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirmed running since October 1 06:10:59 KST, zero restarts/OOM, successful October 26 06:01:31 cycle and 06:01:58 risk check, zero cycle/risk failures and pending orders. October 19 timeout fields precede subsequent successes and remain historical. Disk use is 33%, available memory 475 MiB, container memory 89.21 MiB, and the process list contains Docker init/Python without zombies. VM Git is clean and bot-user GitHub SSH succeeds. Trading/publication are enabled, RUN_ONCE is disabled, loop/heartbeat intervals are 900/3600 seconds and HTTP timeout is ten seconds. The explicit position cap remains 25%; no other inspected strategy overrides are present. No local Docker was used.

Local/VM/container trading and generator SHA256 match: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. Snapshot logs after October 25 06:04:14 contain 1,915 INFO records, no warnings/errors/critical records and no BUY/SELL events.

## Exchange reconciliation and performance

Read-only VM-host Upbit CLI checks at **06:02:29–06:02:36 KST** independently confirm **KRW 57,964.4659928**, zero coins/locked balances/open orders. Both done/cancel closed states since October 25 06:03:23 and both wait/watch open states were queried. All returned deposits (21) and withdrawals (3) contain no new or pending flows. Credentials stayed in VM memory/child-process environments. JSON object streams and empty output were decoded explicitly. No order or test order was submitted. The official [asset balance reference](https://docs.upbit.com/kr/reference/get-balance) documents the read-only account endpoint.

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

Against the previously reconciled flow-adjusted October 1 baseline KRW 58,795.60233029, current cash is lower by KRW 831.13633749 (**-1.41360%**). The baseline already includes the previously verified KRW 275 deposit. That deposit and the October 7 SOL loss are not new activity. Dashboard return instead divides realized PnL by cumulative completed-trade purchase cost plus buy fees. Neither cumulative figure represents today's return. Current-strategy performance remains negative.

## Algorithm and historical decisions

Revisited source history and the September 30 / October 1 / October 8 reviews: confirmed fills/pending-order recovery, independent hard stops, persistent 1.2% gross profit memory with confirmed fifteen-minute trend exits, six-hour momentum floor, ATR/Bollinger/RSI ceilings, three-hour global / twelve-hour ticker and streak loss pauses, and the 25% position cap. The October 7 SOL loss followed a valid reentry and never armed profit memory. Extending the ticker pause to eighteen hours removes both that known loser and an ETH winner in the recorded sample. No new execution defect or independent evidence supports changing those decisions today.

All four retained journal files contain **1,812 observations**, October 7 05:01:32 through October 26 06:01:31. There are **96 additions and no rotation** since yesterday (1,716 + 96 = 1,812). New observations are all defensive, with no holdings or planned decisions. Latest BTC is bearish, RSI 40.05, below daily MA20/MA60. Bypassing only defensive blocking for diagnosis, all latest **21 candidates** still fail numeric gates: **14 ATR, four six-hour momentum, one Bollinger, one daily MA20/MA60 alignment and one price-below-daily-MA20**. These are first rejection reasons.

Source AST-extracted entry/scoring functions, actual context and recorded cycle thresholds produce **zero new allowed numeric signals** at both current RSI 75 and prior RSI 78. The retained prior-rule sample with common six-hour ticker spacing remains one opportunity, with zero retained RSI-only opportunities. Both earlier October 1/5 RSI-only cases remain outside retained raw coverage; their historical reports are not reversed by rotation.

### Newly observed defensive-only rejection

Unlike yesterday, bypassing defensive blocking alone while preserving defensive scoring/thresholds yields **one new numeric candidate**: **KRW-MTL, October 25 19:16:19**, recorded at 19:16:30. Price was KRW 401, score 13 against threshold 12.5, ATR 4.51%, six-hour momentum +3.18%, and completed fifteen-minute RSI 60.02. Its daily/hourly/fifteen-minute alignment predicates passed. The actual plan correctly contained no buy because BTC remained defensive.

Nearest same-ticker journal prices to observed signal time plus one/three/six hours, each within 120 seconds, give **-6.73317% / -8.47880% / -9.22693%** (absolute time offsets 8/9/11 seconds). These are observed price changes, before fees and execution. They are not hypothetical realized losses: a live position would be managed by the minute risk monitor, hard stop and subsequent cycles. This single adverse path supports retaining the defensive block today; it does not establish its long-run incremental return or justify another threshold.

Eighteen completed entries with persisted entry contexts still pass current numeric gates and recorded thresholds. Recomputed chronological fixed-entry selection with twelve/eighteen/twenty-four-hour ticker loss pauses remains **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. These trade records persist independently of rotated observation paths. No new completed entry provides forward validation for a different pause.

Only **one of the eighteen entries** still has a retained holding path; seventeen lack paths. On that same October 7 SOL entry, actual / trend-memory / price-only half-peak-trail results all equal **-KRW 350.46**, with zero earlier alternative exits, unchanged from yesterday. Full current-version realized PnL remains -KRW 831.14 because trade history is intact. No new armed-profit loss, allowed repeated ticker loss or stop-trigger/fill gap occurred.

These remain sparse retrospective fixed-entry diagnostics with original sizes/exits, no replacement entries/capital reuse, and estimated fees/adverse slippage for hypothetical earlier exits. Older historical paths cannot currently be reproduced from the retained journal. Do not tune parameters against the same selected known losses.

## Decision and validation

**Keep trading source/configuration unchanged.** Negative performance remains unresolved, but the new defensive-only candidate's adverse path and absence of execution defects support preserving the current controls. Continue tracking new current-version completed trades, defensive-only/RSI-only opportunities, allowed repeated ticker losses, armed-profit losses and stop-trigger/fill gaps. State retained coverage separately.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. [Pages run 40232350003](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/40232350003) completed build/report/deploy successfully. Independent public HTTP 200 verification serves October 26 **05:46:31 generation**, cycle 05:46:30 / risk 05:45:56, zero failures, 92 exits and three decisions, with private entry contexts, UUIDs and pending-order objects excluded. This is within the configured heartbeat plus cycle interval. The previous review's unobserved next publication is now confirmed by a newer public heartbeat.

Publish this review and HARNESS.md, fast-forward the VM and verify final health/document hashes. Documentation changes require no trading restart or image build. Preserve runtime files and the user's untracked AGENTS.md; remove private temporary snapshots.
