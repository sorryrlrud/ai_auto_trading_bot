# Strategy Review — 2026-10-21

## Production verification

Direct SSH checks of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirm healthy operation. The cycle completed at **06:01:25 KST** and the initial risk check succeeded at **06:03:41**. Cycle failures, risk failures and pending orders are **zero**. The container has run since October 1 06:10:59 KST with zero restarts/OOM. October 19 error timestamps precede successful checks and are historical, not a current outage.

The private log snapshot after yesterday's final risk check, October 20 06:06:17, contains **1,916 INFO** records, no warnings/errors/critical records, and no buy/sell/realized events. Disk usage is 32%, available memory 444 MiB and container memory 104 MiB. The process snapshot shows init and Python, without zombies. The VM working tree is clean and bot-user GitHub SSH succeeds. Trading and dashboard publishing are enabled; single-run mode is disabled. No local Docker was used.

Trading/generator SHA256 match local, VM and container: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`.

## Exchange reconciliation and performance

Read-only **VM Upbit CLI v0.9.1** reconciliation completed at **06:05:25 KST**, with credentials confined to VM memory and child environments. The [official accounts endpoint](https://docs.upbit.com/kr/reference/get-balance) returned only **KRW 57,964.4659928**, with zero locked funds and no coin balances. Closed orders since yesterday's independent October 20 06:04:52 boundary are empty in both `done` and `cancel` states. Open `wait` and `watch` states are empty. All returned deposits (21) and withdrawals (3) were checked: no newly created/completed or pending flows. No exchange write or verification order was submitted.

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

Against the existing October 1 cash baseline plus the previously verified KRW 275 deposit, **KRW 58,795.60233029**, current cash is **KRW 831.13633749 lower / -1.41360%**. This is a simple flow-adjusted baseline comparison, not a time-weighted return. The dashboard uses cumulative completed-trade purchase cost plus buy fees as its separate denominator. Neither the old loss nor the old deposit is today's activity.

## Algorithm and historical decisions

Revisited September 30 persistent profit memory, October 1 RSI deployment, October 7–8 allowed SOL reentries and stop execution, and October 19–20 automatic exchange recovery. Confirmed-fill reconciliation, independent minute-level hard stops, three-hour global and twelve-hour ticker/streak loss pauses, the 25% position cap, ATR/Bollinger ceilings, +0.5% six-hour momentum floor, 1.2% gross profit-memory arming and completed fifteen-minute RSI ceiling 75 remain intact.

The retained private journal has **1,830 observations**, October 2 00:31:40 through October 21 06:01:25. There are **96 additions** versus yesterday's 1,734, with no further rotation. All 96 are defensive, with zero order plans and zero holdings. Latest BTC context is bearish, RSI 43.92, below daily MA20 and MA60. Diagnostically bypassing only defensive blocking still rejects all latest **20 candidates: 14 ATR, four six-hour momentum, one Bollinger and one fifteen-minute trend**. These are first rejection reasons, not executable alternative trades.

Re-extracted current and prior RSI-78 gate/scoring functions from source, retaining actual market context, other current filters and recorded score thresholds. Both produce **zero new numeric signals**. Applying common six-hour ticker spacing to the retained prior-rule sample still yields **19 numeric opportunities**, including the same single retained RSI-only BTC rejection on October 5. October 1's other RSI-only case remains outside rotated coverage. These opportunity counts omit execution budgets and portfolio constraints; they are not trade counts or a portfolio replay.

Eighteen completed entries pass current numeric gates and recorded thresholds. Recomputed chronological fixed-entry selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. As reviewed October 8, eighteen hours removes a known SOL loss and an ETH winner; twenty-four hours changes which earlier selected loss starts a later pause. No new trade supports choosing a threshold from those known outcomes.

Ten of those eighteen entries lack retained holding paths. The remaining **eight are all eight current-version trades**. Actual, trend-memory and price-only half-peak-trail diagnostics each remain **-KRW 831.14**, with zero earlier alternative exits. No new armed-profit loss, repeat allowed ticker loss or stop trigger/fill gap has appeared. These diagnostics fix original entries, quantities and exits, omit replacement entries/cash reuse, and include fees/adverse slippage for hypothetical earlier exits. Sparse fifteen-minute observations cannot reproduce minute-level monitoring. Negative forward performance remains unresolved; unchanged historical alternatives do not establish future profitability.

## Decision, validation and deployment

**Keep trading source and configuration unchanged.** Live service checks pass and current inactivity follows intended entry controls. There is no newly demonstrated application defect or independent strategy evidence supporting an adjustment.

All **105 local unit tests passed** in an isolated temporary source copy with socket connections blocked. [Pages run 39490565655](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/39490565655) completed build/report/deploy successfully. Independent public HTTP 200 serves generation/cycle **05:16:25**, risk **05:15:35**, both failure counters zero, 92 exits and three decisions. Private entry context, order UUIDs and pending-order objects are absent. This is consistent with bounded hourly publishing; the newer 06:01 VM cycle is independently verified.

Publish this review and `HARNESS.md`, fast-forward the production VM, and verify document hashes and current risk health. Documentation-only synchronization requires no trading image build or process restart. Preserve runtime data and the user's untracked `AGENTS.md`; exclude private snapshots and credentials.

Next review should track new current-version completed trades, repeated allowed ticker losses, new RSI-only opportunities, armed-profit losses and stop trigger/fill differences. Keep cash-flow boundaries, return denominators and observation coverage explicit.
