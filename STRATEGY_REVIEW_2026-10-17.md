# Strategy Review — 2026-10-17

## Production verification

Direct SSH checks of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirmed healthy operation. The container has run since October 1 06:10:59 KST, with zero restarts and no OOM. The initial completed cycle was **05:46:32** and the **05:58:34** risk check succeeded. Cycle failures, risk failures and pending orders are zero. September 7's error timestamp is historical. The next scheduled cycle started normally at 06:00:20 and a follow-up VM check confirmed its successful completion at **06:01:30**, still defensive with no decisions or holdings.

Initial snapshot logs after October 16 06:01:30 contain **1,910 INFO records**, no WARNING/ERROR/CRITICAL and no buy/sell/realized events. Disk usage is 32%, available memory 473 MiB and container memory 86.51 MiB; no zombies were found. VM Git is clean and bot-user GitHub SSH succeeds. Trading source and generator SHA-256 values match local, VM and container: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` and `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. Trading/dashboard publishing are enabled, single-run mode is disabled, and absent entry overrides use source defaults confirmed by private observations. No local Docker command was used.

[Pages run 38961057159](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/38961057159) completed build, report and deploy successfully for dashboard commit `578461b7`. Independent public HTTP 200 showed October 17 **05:16:32** generation/cycle, 92 exits and three decisions. Private entry context, order UUIDs and pending-order objects are absent. Dashboard freshness is within its bounded hourly publishing cadence; production health was checked directly on the VM.

## Performance and exchange reconciliation

The completed October 16 review/memory is the comparison boundary; supplied last-run metadata is older. No new trade or account flow occurred. October 7's SOL loss remains included once.

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

Read-only Upbit CLI v0.9.1 checks completed on the VM at **05:59:59 KST**, with credentials confined to VM memory and child environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) returned only KRW cash with zero locked funds. Closed orders since October 16 06:01:30, queried with both `done` and `cancel`, are empty; waiting and reserved orders are empty. All 21 deposits and three withdrawals contain no new created/completed or pending flow. No exchange write or test order was submitted.

October 1 pre-entry cash plus the previously verified KRW 275 deposit gives the **KRW 58,795.60233029** baseline. Current cash is KRW 831.13633749 lower: **-1.41360%** simple change against that flow-adjusted baseline, not a time-weighted return. The dashboard's cumulative completed-trade purchase-cost denominator is separate.

## Algorithm and prior decisions

Reviewed source history and the October 1, October 7–8 and October 16 decisions. Confirmed-fill reconciliation, minute-level hard stops, three-hour global and twelve-hour ticker/streak loss pauses, the 25% position cap, 5% ATR and Bollinger ceilings, +0.5% six-hour momentum floor, September 30's 1.2% gross profit memory and October 1's completed fifteen-minute RSI ceiling of 75 remain active.

The initial snapshot contains **1,969 observations**, September 26 18:46:42 through October 17 05:46:32: 96 additions relative to yesterday's initial 1,873 and no rotation. All **95 observations after yesterday's final 06:01:30 cycle** are defensive with zero order plans or holdings. The October 7 loss pause has expired; current inactivity follows the market gate. Diagnostically bypassing defensive blocking still rejects all latest **22 candidates**: **18 exceed ATR** and **four miss six-hour momentum**. These are first rejection reasons, not a simulation of executable alternative trades.

Replaying the source gate/scoring with the prior RSI ceiling of 78, current other filters, recorded cycle thresholds and common six-hour ticker spacing from October 1 deployment yields **21 opportunities**, zero new. The same two RSI-only BTC observations remain on October 1 at 15:00:36 and October 5 at 06:00:45 (signal-observation times; corresponding cycle records are 15:01:38 and 06:01:41). Their previously reviewed forward paths were mixed; there is no new evidence for relaxing the ceiling of 75.

Eighteen completed entries pass current numeric gates and recorded score thresholds. Chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. As documented October 8, eighteen hours excludes an ETH winner as well as the final SOL loss, while twenty-four hours changes which earlier loss starts a later pause. Selecting the maximum would fit known outcomes. Original entries, quantities and exits are fixed; replacement trades and cash reuse are absent.

Seven eligible entries still lack holding paths. On the same eleven observable entries, actual PnL is **-KRW 1,388.98**, trend-memory diagnostic PnL **-KRW 1,306.44**, and price-only half-peak-trail PnL **-KRW 1,091.19**. All eight current-version trades remain **-KRW 831.14** under either alternative. Earlier rotation reduced coverage; older larger-sample totals are not comparable. Sparse fifteen-minute prices cannot reconstruct minute-level peaks/stops; hypothetical earlier fills include fees and adverse slippage. These retrospective diagnostics do not establish future profitability.

## Decision and validation

**Keep trading source and configuration unchanged.** Results remain negative, but there is no new completed trade, eligible opportunity or runtime defect supporting a threshold change. Continue tracking allowed same-ticker repeat losses, new RSI-only opportunities, armed-profit losses and stop trigger/fill gaps; preserve coverage and cash-flow boundaries.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. Publish this report and `HARNESS.md`, then synchronize the VM by fast-forward. Unchanged trading code requires no image build or container restart. Private snapshots, credentials and the user's untracked `AGENTS.md` are excluded from Git.

The review was published as `ef39603e` and fast-forward synchronized to the VM. Document hashes match local/VM, the VM working tree is clean, and the container remains running without restart or OOM. The follow-up 06:01:30 real cycle adds one further defensive observation after the initial snapshot.
