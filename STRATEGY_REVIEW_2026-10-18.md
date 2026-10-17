# Strategy Review — 2026-10-18

## Production verification

Direct SSH checks of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirmed healthy operation. The container has run since October 1 06:10:59 KST with zero restarts and no OOM. Today's **06:01:28** cycle and **06:02:47** risk check succeeded; cycle failures, risk failures and pending orders are zero. September 7's error timestamp is historical.

The private snapshot's logs after the previous final risk check, October 17 06:01:37, contain **1,920 INFO records**, no warnings/errors/critical records and no buy/sell/realized events. Disk usage is 32%, available memory 479 MiB and container memory 83.41 MiB; no zombies were found. VM Git is clean and bot-user GitHub SSH succeeds. Local, VM and container trading/generator hashes match the prior review: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` and `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. Trading and dashboard publishing are enabled; single-run mode is disabled. No local Docker command was used.

[Pages run 39069175215](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/39069175215) completed build, report and deploy successfully for dashboard commit `bc0fa858`. Independent public HTTP 200 showed October 18 **06:01:28** generation/cycle, 92 exits and three decisions. Private entry context, order UUIDs and pending-order objects are absent.

## Performance and exchange reconciliation

The completed October 17 review/memory is the comparison boundary; supplied last-run metadata is older. No new trade or account flow occurred. October 7's SOL loss remains included once.

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
| Change since prior all-cash balance | KRW 0 / 0% |
| Dashboard realized-trade return | -0.4895% |

Read-only Upbit CLI v0.9.1 checks completed on the VM at **06:04:16 KST**, with credentials confined to VM memory and child environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) returned only KRW cash with zero locked funds. Closed orders since October 17 06:01:30, queried with both `done` and `cancel`, are empty; waiting and reserved orders are empty. All 21 deposits and three withdrawals contain no new created/completed or pending flow. No exchange write or test order was submitted.

October 1 pre-entry cash plus the previously verified KRW 275 deposit gives the **KRW 58,795.60233029** baseline. Current cash is KRW 831.13633749 lower: **-1.41360%** simple change against that flow-adjusted baseline, not a time-weighted return. The dashboard uses a separate cumulative completed-trade purchase-cost denominator.

## Algorithm and prior decisions

Reviewed source history and the October 1, October 7–8 and October 17 decisions. Confirmed-fill reconciliation, minute-level hard stops, three-hour global and twelve-hour ticker/streak loss pauses, the 25% position cap, 5% ATR and Bollinger ceilings, +0.5% six-hour momentum floor, September 30's 1.2% gross profit memory and October 1's completed fifteen-minute RSI ceiling of 75 remain active.

The snapshot contains **2,066 observations**, September 26 18:46:42 through October 18 06:01:28: 97 additions against yesterday's initial 1,969, with unchanged coverage start and no rotation. All **96 observations after yesterday's final 06:01:30 cycle** are defensive, with zero order plans or holdings. The old loss-streak pause has expired; current inactivity follows the market gate. Diagnostically bypassing defensive blocking still rejects all latest **20 candidates**: **16 exceed ATR** and **four miss six-hour momentum**. These are first rejection reasons, not executable alternative trades.

Replaying source gate/scoring with the prior RSI ceiling of 78, current other filters, recorded cycle thresholds and common six-hour ticker spacing from October 1 deployment still yields **21 opportunities**. None of today's new observations passes the numeric gates/score under either the current or prior RSI ceiling with the actual market context. The same two RSI-only BTC signals remain on October 1 at 15:00:36 and October 5 at 06:00:45; their previously reviewed forward paths are mixed. There is no new evidence for relaxing the ceiling of 75.

Eighteen completed entries pass current numeric gates and recorded score thresholds. Recalculated chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. As documented October 8, eighteen hours excludes an ETH winner as well as the final SOL loss, while twenty-four hours changes which earlier loss starts a later pause. Selecting the best observed threshold would fit known outcomes. Original entries, quantities and exits are fixed; replacement trades and cash reuse are absent.

Seven eligible entries still lack holding paths. On the same eleven observable entries, recalculated actual PnL is **-KRW 1,388.98**, trend-memory diagnostic PnL **-KRW 1,306.44**, and price-only half-peak-trail PnL **-KRW 1,091.19**. All eight current-version trades remain **-KRW 831.14** under either alternative. Earlier rotation reduced coverage; older larger-sample totals are not comparable. Sparse fifteen-minute prices cannot reconstruct minute-level peaks/stops; hypothetical earlier fills include fees and adverse slippage. These retrospective diagnostics do not establish future profitability.

## Decision and validation

**Keep trading source and configuration unchanged.** Performance remains negative, but there is no new completed trade, eligible opportunity or runtime defect supporting a threshold change. Preserve the existing risk controls. Continue tracking allowed same-ticker repeat losses, new RSI-only opportunities, armed-profit losses and stop trigger/fill gaps, with explicit coverage and cash-flow boundaries.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. Publish this review and `HARNESS.md`, then synchronize the VM by fast-forward. This documentation-only update requires no trading image build or container restart. Private snapshots, credentials and the user's untracked `AGENTS.md` are excluded from Git.
