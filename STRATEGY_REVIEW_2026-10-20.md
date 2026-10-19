# Strategy Review — 2026-10-20

## Production recovery verified

Direct SSH checks of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` confirm successful automatic recovery after yesterday's exchange outage. The container has run since October 1 06:10:59 KST, with zero restarts/OOM. Today's cycle completed at **06:01:35 KST**, risk check succeeded at **06:03:17**, and cycle failures, risk failures and pending orders are all **zero**. Historical error timestamps remain visible and precede the newer successes; they do not indicate an ongoing outage. No runtime counters were manually reset.

Disk use is 32%, available memory 480 MiB and container memory 96.68 MiB. Only the init and Python processes appeared in the process snapshot, with no zombies. The VM working tree is clean and bot-user GitHub SSH succeeds. Trading/generator SHA256 match local, VM and container: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. Trading and dashboard publishing remain enabled; run-once is false and API timeout is ten seconds. No local Docker was used.

[Upbit's official completion notice](https://support.upbit.com/hc/ko/articles/59610087642009-서버-점검-안내-완료) was updated October 19 06:48 and announced sequential trading resumption from **06:55**. Independently, VM logs record the first successful risk check after the final 06:29:13 timeout at **06:30:18**, and the first successful cycle observation at **06:31:57**. These are API/account and scan recovery signals, not proof that exchange trading had already resumed at those earlier times. The bot held cash and submitted no trade during this interval.

The private log snapshot after October 19 06:01:01 contains 1,892 INFO, 22 ERROR and one WARNING record. All errors are confined to the continuing outage, with no ERROR/CRITICAL after 06:30. The one warning at 15:00:33 reports an unavailable `KRW-ICX` ticker. The existing HTTP-404 subdivision/skip path handled it; that cycle completed at 15:01:44, with zero holdings and no decisions. There is no evidence that this handled ticker warning requires a code change. Main-loop and risk failure counters overlap with logs and must not be summed as independent failures.

## Exchange reconciliation and performance

Read-only **VM Upbit CLI v0.9.1** reconciliation began at **06:04:52 KST**. Credentials stayed in VM memory and child environments. Accounts show **KRW 57,964.4659928**, zero locked funds and no coin balances. Closed orders queried in both `done` and `cancel` states since the last independent October 18 06:04:16 reconciliation return zero orders. Open `wait` and `watch` states also return zero. All returned deposits (21) and withdrawals (3) were checked; none is new since that boundary. The outage did not conceal a newly recorded order, flow or balance change. No exchange write or verification order was submitted.

| Measure | Result |
| --- | ---: |
| New completed trades / account change | 0 / KRW 0 (0%) |
| Lifetime explicit SELL records | 92: 28 wins, 64 losses |
| Lifetime realized PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| Current October 1 strategy | 8 completed: 3 wins, 5 losses |
| Current-version PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-version recorded fees | KRW 116.59 |
| Current-version SOL | 3 losses, -KRW 620.01 |
| Current all-cash account value | KRW 57,964.4659928 |
| Dashboard realized-trade return | -0.4895% |

Relative to the previously verified October 1 baseline adjusted for the existing KRW 275 deposit, KRW 58,795.60233029, the independently verified cash change remains **-KRW 831.13633749 / -1.41360%**. This is a simple flow-adjusted baseline comparison, not a time-weighted return. Dashboard return uses cumulative completed-trade purchase cost plus buy fees. The prior loss and deposit are not counted again as today's activity.

## Algorithm and earlier decisions

Revisited September 30 persistent profit memory, October 1 RSI deployment, October 7–8 repeated SOL losses and stop execution, and October 19's decision to preserve the automatic retry path. Confirmed-fill reconciliation, independent minute-level hard stops, three-hour global and twelve-hour ticker/streak loss pauses, 25% position cap, 5% ATR ceiling, Bollinger ceiling, +0.5% six-hour momentum floor, 1.2% gross profit-memory arming and completed fifteen-minute RSI ceiling 75 remain intact. Automatic recovery without a restart supports retaining the existing timeout/retry behavior.

The journal contains **1,734 observations**, October 2 00:31:40 through October 20 06:01:35. There are **95 additions** versus yesterday's 1,639, with no further rotation. All new observations are defensive, with zero planned decisions and zero holdings. Latest BTC context is bearish, RSI 45.13 and below daily MA20. Diagnostically bypassing only defensive blocking still rejects all **22 latest candidates: 18 exceed ATR and four miss six-hour momentum**. Actual-context source gates/scoring and recorded thresholds produce zero new numeric opportunities under either the current RSI 75 or prior RSI 78 rules. An absent buy plan is explained by the entry controls, not a stopped bot.

Re-extracted the prior source's gate/scoring functions and applied current other filters, recorded thresholds and common six-hour ticker spacing. The same retained sample yields **19 prior-rule numeric opportunities**, including the single retained RSI-only BTC rejection on October 5. The other October 1 RSI-only case remains outside rotated coverage. Do not compare these retained counts with older 21-opportunity/two-rejection reports as though coverage were identical. These diagnostic opportunities also omit execution budgets and portfolio constraints.

Eighteen completed entries pass current source numeric gates/scoring and recorded thresholds. Recomputed chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**. As documented October 8, the apparently best eighteen-hour setting removes a known SOL loss along with a profitable ETH entry; changing the pause also changes which losses start subsequent pauses. No new trade or independent evidence justifies selecting that threshold now.

Ten of those eighteen entries still lack holding paths. The remaining **eight are the eight current-version trades**. Actual, trend-memory and price-only half-peak-trail results each remain **-KRW 831.14**, with no earlier alternative exit. No new armed-profit loss, stop execution gap or repeated allowed ticker loss has appeared. These fixed-entry diagnostics preserve historical quantities/exits and omit replacement entries/cash reuse. Sparse fifteen-minute observations cannot reproduce minute-level monitoring. Negative forward performance remains unresolved; unchanged historical alternatives are not evidence of future profitability.

## Decision, validation and deployment

**Keep trading source/configuration unchanged.** The previously pending exchange and service recovery checks now pass. The observed no-trade period is consistent with the intended defensive and numeric entry controls. There is no demonstrated application defect or additional strategy evidence supporting a change.

All **105 local unit tests passed** in an isolated temporary source copy with socket connections blocked. [Pages run 39322132705](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/39322132705) completed build/report/deploy successfully. Public HTTP 200 serves generation **05:46:32**, successful cycle **05:46:31**, risk **05:46:16**, both failure counters zero, 92 exits and three decisions. Private entry context, order UUIDs and pending-order objects are absent. This is consistent with bounded hourly heartbeat publishing; the later 06:01 VM cycle is separately verified.

Publish this review and `HARNESS.md`, then fast-forward the production VM and recheck health and deployed document hashes. Documentation-only synchronization requires no trading image build or process restart. Private VM snapshots, credentials and the user's untracked `AGENTS.md` are excluded.

Next review should continue tracking new current-version completed trades, repeated same-ticker losses after valid reentries, RSI-only signals, armed-profit losses and stop trigger/fill differences. Preserve the independently verified account boundary above and the distinction between account change, flows and realized-trade returns.
