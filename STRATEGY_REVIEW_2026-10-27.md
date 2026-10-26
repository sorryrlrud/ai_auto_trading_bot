# Strategy Review — 2026-10-27

## Production verification

Direct SSH checks of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirmed running since October 1 06:10:59 KST, zero restarts/OOM, successful October 27 06:01:35 cycle and 06:02:31 risk check, and zero cycle/risk failures or pending orders. October 19 timeout fields precede subsequent successes and remain historical. Disk use is 33%, available memory 469 MiB and container memory 95.89 MiB. Docker init/Python are running without zombies; VM Git is clean and bot-user GitHub SSH succeeds. No local Docker was used.

Trading/dashboard publication are enabled and RUN_ONCE is disabled. Loop/heartbeat intervals are 900/3600 seconds and HTTP timeout is ten seconds. Merging the container environment with its dotenv file confirms the existing explicit 25% position cap and no other inspected strategy overrides. Local/VM/container trading and generator SHA256 match: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`.

Timestamp-parsed snapshot logs after October 26 06:04:58 contain 1,915 INFO records, no warnings/errors/critical records and no BUY/SELL events.

## Exchange reconciliation and performance

Read-only VM-host Upbit CLI reconciliation at **06:02:05–06:02:11 KST** confirms **KRW 57,964.4659928**, zero coin holdings or locked balances. Both done/cancel closed-order states since October 26 06:02:29 and both wait/watch open-order states return zero. All returned deposits (21) and withdrawals (3) contain no new or pending flows. Credentials remained in VM memory/child-process environments; JSON object streams and empty CLI output were decoded explicitly. No order or test order was submitted. The official [balance endpoint reference](https://docs.upbit.com/kr/reference/get-balance) documents the read-only account query.

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

Against the existing flow-adjusted October 1 baseline KRW 58,795.60233029, cash remains lower by KRW 831.13633749 (**-1.41360%**). The baseline already includes the previously verified KRW 275 deposit. That deposit and the October 7 SOL loss are not new activity. Dashboard return divides lifetime realized PnL by cumulative completed-trade purchase costs plus buy fees; its denominator differs from the account baseline. Neither cumulative measure is today's return. Current-strategy performance remains negative.

## Algorithm and historical decisions

Revisited source history and the September 30 / October 1 / October 8 reviews, including confirmed fills/pending-order recovery, independent hard stops, persistent 1.2% gross profit memory with confirmed fifteen-minute trend exits, six-hour momentum floor, ATR/Bollinger/RSI gates, three-hour global / twelve-hour ticker and loss-streak pauses, and the 25% position cap. The October 7 SOL loss followed a permitted reentry and never armed profit memory. An eighteen-hour ticker pause removes that known loser together with an ETH winner from the recorded sample. There is no new execution defect or completed trade to validate changing those decisions.

All four retained journal files contain **1,908 observations**, October 7 05:01:32 through October 27 06:01:35: **96 additions and no rotation** (1,812 + 96 = 1,908). All new observations are defensive, without holdings or planned decisions. Latest BTC is bearish, RSI 36.31, below daily MA20/MA60. Diagnostically bypassing only defensive blocking, all latest **23 candidates** still fail numeric entry gates: **18 ATR and five six-hour momentum** first rejections.

Source AST-extracted entry/scoring functions, actual recorded market context and recorded cycle score thresholds yield **zero new allowed numeric signals** at either current RSI 75 or prior RSI 78. Bypassing defensive blocking alone, with its scoring penalty and thresholds preserved, also yields **zero new candidates**. The retained prior-rule sample with common six-hour ticker spacing remains one opportunity. Earlier RSI-only cases remain outside retained raw coverage; historical conclusions are not reversed by missing paths.

The October 25 MTL defensive-only rejection and its adverse one/three/six-hour price path were already reviewed yesterday. They are not a new signal or a realized avoided loss today. No independent new candidate supports relaxing the defensive block.

Recomputed eighteen completed entries with persisted contexts still pass current numeric gates and recorded score thresholds. Chronological fixed-entry selection with twelve/eighteen/twenty-four-hour ticker loss pauses remains **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. This selected historical diagnostic fixes actual sizes/exits and does not replay replacement entries or capital reuse; its apparent optimum is not forward validation.

Only **one of those eighteen entries** retains a holding path; seventeen are missing after earlier journal rotation. On that same October 7 SOL entry, actual / trend-memory / price-only half-peak-trail results remain **-KRW 350.46**, with zero earlier alternative exits. Full current-version trade history still records -KRW 831.14 across eight completed trades. No new armed-profit loss, permitted repeated ticker loss or stop-trigger/fill gap occurred. Sparse fifteen-minute paths cannot reproduce minute-level stops or intraperiod peaks; hypothetical earlier exits use estimated fees and adverse slippage.

## Decision and validation

**Keep trading source/configuration unchanged.** Negative performance is unresolved, but no new execution defect or independent forward evidence justifies a rule change. Preserve the defensive block, hard stops, profit memory, entry gates and loss pauses. Continue tracking new current-version completed trades, defensive-only/RSI-only opportunities, repeated ticker losses after valid reentry, armed-profit losses and stop-trigger/fill gaps. Compare retained coverage explicitly.

All **105 local tests passed** from an isolated temporary source copy with socket connections blocked. [Pages run 40398642249](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/40398642249) completed successfully. Independent public HTTP 200 verification shows October 27 **05:46:35 generation/cycle**, risk 05:46:28, zero failure counters, 92 exits and three decisions. Private entry contexts, UUIDs and pending-order objects are excluded. This heartbeat is within the configured heartbeat plus cycle interval; live VM timestamps are newer.

Publish this review and HARNESS.md, fast-forward the VM and verify final health/document hashes. Documentation-only deployment requires no trading restart or image build. Preserve runtime files and the user's untracked AGENTS.md; remove private temporary snapshots after verification.
