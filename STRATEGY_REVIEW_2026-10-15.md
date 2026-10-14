# Strategy Review — 2026-10-15

## Production verification

Direct SSH checks of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirmed healthy operation. The container has run since October 1 06:10:59 KST, with zero restarts and no OOM. The initial snapshot caught the 06:00 cycle still running; a subsequent VM check confirmed completion at **06:01:30** and a successful 06:01:40 risk check. Cycle failures, risk failures and pending orders are zero. September 7's error timestamp is historical.

Initial snapshot logs after October 14 06:03:07 contain **1,911 INFO records**, no WARNING/ERROR/CRITICAL and no buy/sell/realized events. Disk usage is 33%, available memory 444 MiB and container memory 101.1 MiB. No zombie process was found. VM Git is clean and bot-user GitHub SSH succeeds. Local, VM and container source/generator SHA-256 values remain `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` and `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker command was used.

[Pages run 38632819661](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/38632819661) completed build, report and deploy successfully for dashboard commit `0db99ef9`. Independent public HTTP 200 showed October 15 **05:31:31** generation / **05:31:30** cycle, 92 exits and three decisions. Private entry context, order UUIDs and pending-order objects are absent. Publication is within the bounded hourly heartbeat cadence; live cycle health is separately verified on the VM.

## Performance and exchange reconciliation

The latest completed October 14 memory entry is the comparison boundary; the supplied last-run metadata is older. No new trade or account flow occurred. October 7's SOL loss remains included once.

| Measure | Result |
| --- | ---: |
| Lifetime explicit SELL records | 92: 28 wins, 64 losses |
| Lifetime realized PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| October 1 strategy completed trades | 8: 3 wins, 5 losses |
| Current-version PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-version fees | KRW 116.59 |
| Current-version SOL | 3 losses, -KRW 620.01 |
| Exchange cash | KRW 57,964.4659928 |
| Change since prior balance | KRW 0 / 0% |
| Dashboard realized-trade return | -0.4895% |

Read-only Upbit CLI v0.9.1 checks completed on the VM at **06:01:57 KST**. Credentials stayed in VM process memory and child environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) returned only KRW cash with zero locked funds. Closed orders since October 14 06:03:07, queried with both `done` and `cancel`, are empty; waiting and reserved orders are empty. All 21 deposits and three withdrawals contain no new created/completed or pending flow. No exchange write or test order was submitted.

October 1 pre-entry cash plus the previously verified KRW 275 deposit gives a **KRW 58,795.60233029** baseline. Current cash is KRW 831.13633749 lower: **-1.41360%** simple change against that flow-adjusted baseline, not a time-weighted return. The dashboard's completed-trade purchase-cost denominator is separate.

## Algorithm and prior decisions

Reviewed source history and prior October 1, October 7–8 and October 14 decisions. Confirmed-fill reconciliation, minute-level hard stops, three-hour global and twelve-hour ticker/streak loss pauses, 25% position cap, 5% ATR and Bollinger ceilings, +0.5% six-hour momentum floor, September 30's 1.2% gross profit memory and October 1's completed fifteen-minute RSI ceiling of 75 remain active. Safe container settings confirm trading and dashboard publishing enabled; private observations agree with source defaults.

The initial snapshot contains **1,777 observations**, September 26 18:46:42 through October 15 05:46:30: 96 additions relative to yesterday's initial 1,681 and no rotation. All **95 observations after yesterday's final 06:01:26 cycle** are defensive, with zero order plans or holdings. The subsequent 06:01:30 cycle also remained defensive, giving 96 new cycles through that check. The October 7 loss pause has expired; current inactivity follows the market gate. Diagnostically bypassing defensive blocking at the initial latest snapshot still rejects all **21 candidates**: 17 exceed ATR and four miss six-hour momentum. These input diagnostics do not represent executable alternative trades.

Replaying the prior RSI=78 source gate/scoring, current other filters, recorded cycle thresholds and common six-hour ticker spacing from October 1 deployment yields **21 opportunities**, zero new. The same RSI-only BTC signals occurred October 1 15:01:38 and October 5 06:01:41. Their previously verified paths were mixed; no additional forward evidence supports relaxing the 75 ceiling.

Eighteen completed entries pass current numeric gates and recorded score thresholds. Chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. Eighteen hours removes a winner as well as the final SOL loss; twenty-four hours changes which earlier loss starts the next pause and permits the final loss again. Fixed original entries, quantities and exits exclude replacement trades and cash reuse. Selecting the best historical pause still risks fitting known results.

Seven eligible entries lack holding paths, unchanged. For the same eleven observable entries, actual PnL is **-KRW 1,388.98**, trend-memory diagnostic PnL **-KRW 1,306.44**, and price-only half-peak-trail PnL **-KRW 1,091.19**. All eight current-version trades remain **-KRW 831.14** under either alternative. Earlier rotation reduced coverage; comparisons with older, larger samples are invalid. Sparse fifteen-minute prices cannot reconstruct minute-level peaks/stops; hypothetical earlier fills include fees and adverse slippage. These diagnostics do not establish future profitability.

## Decision and validation

**Keep trading source and configuration unchanged.** Forward performance remains negative, but today's review supplies no new completed trade, eligible opportunity or runtime defect to justify changing thresholds. Track allowed same-ticker repeat losses, new RSI-only opportunities, armed-profit losses and stop trigger/fill gaps; preserve coverage and cash-flow boundaries.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. Synthetic logs stayed outside production. Publish this report and `HARNESS.md`, then synchronize the VM with a fast-forward pull. Unchanged trading code requires no image build or container restart. Private snapshots and credentials are excluded from Git.
