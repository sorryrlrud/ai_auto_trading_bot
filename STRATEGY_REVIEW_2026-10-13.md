# Strategy Review — 2026-10-13

## Production verification

Direct SSH checks of `/home/sorryrlrud/ai_auto_trading_bot` and the GCP VM's `quant-ai-bot` container confirmed normal operation. The container has run since October 1 06:10:59 KST with zero restarts and no OOM. The October 13 05:46:30 real cycle and 05:57:51 risk check succeeded. Cycle failures, risk failures and pending orders are zero; the September 7 error timestamp is historical.

Snapshot logs after the previous review's final October 12 06:05:30 risk check contain 1,903 INFO records and no WARNING/ERROR/CRITICAL or buy/sell/realized events. Disk usage is 32%, available memory 475 MiB and container memory 98.62 MiB. No zombie processes were found. VM Git is clean and GitHub SSH succeeds as the bot user. Trading/generator SHA-256 hashes match local, VM and container copies: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker commands were used.

[Pages run 38304791681](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/38304791681) completed build, report and deploy successfully for dashboard commit `a1c5691f`. Public HTTP 200 verification shows October 13 05:31:31 generation / 05:31:30 cycle time, 92 exits and three decisions. Private entry context, order UUIDs and pending-order objects are absent. The public publication snapshot is within the bounded hourly heartbeat cadence; live cycle health is checked directly on the VM.

## Performance and exchange reconciliation

**No new buy, sell or account flow occurred.** October 7's SOL loss is already included. Although the supplied last-run metadata is October 11, the latest completed memory entry is October 12; its verification boundary avoids duplicate accounting.

| Measure | Result |
| --- | ---: |
| Lifetime explicit SELL records | 92: 28 wins, 64 losses |
| Lifetime realized PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| Current October 1 strategy | 8 completed trades: 3 wins, 5 losses |
| Current-version PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-version fees | KRW 116.59 |
| Current-version SOL | 3 losses, -KRW 620.01 |
| Current all-cash balance | KRW 57,964.4659928 |
| Change since prior exchange snapshot | KRW 0 / 0% |
| Dashboard realized-trade return | -0.4895% |

Read-only Upbit CLI v0.9.1 checks completed on the VM at **05:58:44–49 KST**. Credentials stayed in VM memory and child-process environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) returned only KRW 57,964.4659928 with zero locked funds. Closed orders since October 12 06:05:30 are empty; waiting and reserved orders are empty. All 21 deposits and three withdrawals contain no new created/completed or pending flow. Exchange cash agrees with VM observations and yesterday's verified balance.

The CLI automatically streams paginated objects, including an empty output for zero open orders. Initial array-only parsing was corrected to decode the complete JSON stream, and the final read-only reconciliation succeeded. No exchange write or validation order was submitted.

The October 1 pre-entry cash baseline plus the previously verified KRW 275 deposit is KRW 58,795.60233029. Current cash is KRW 831.13633749 lower: **-1.41360%** simple change against that flow-adjusted baseline, not a time-weighted return. The dashboard uses completed-trade purchase costs including buy fees as its denominator; its realized-trade return remains separate.

## Algorithm and prior decisions

Source history and the October 1, October 7–8 and October 12 reviews were checked. Existing controls remain confirmed-fill reconciliation, minute-level hard stops independent of ordinary exit holding time, three-hour global and twelve-hour ticker/streak loss pauses, a 25% position cap, Bollinger/5% ATR ceilings, a +0.5% six-hour momentum floor, September 30 persistent profit memory armed at 1.2% gross, October 1's completed fifteen-minute RSI ceiling of 75, and October 2's return-label correction. Container configuration and latest recorded rules agree with these defaults; live trading and dashboard publishing are enabled.

All **95 new observations** after October 12 06:01:37 through the initial October 13 05:46:30 snapshot are defensive with no order plan or holding. The loss-streak pause expired October 7; current inactivity follows the market gate. Diagnostically bypassing defensive blocking at the latest snapshot still rejects all **21 signals**: 16 exceed ATR and five miss six-hour momentum. This snapshot is not evidence of executable alternative trades.

Journal rotation changed coverage to **1,585 observations**, September 26 18:46:42 through October 13 05:46:30. Compared with yesterday's 1,992 observations and today's 95 additions, 502 older observations rotated out. The current strategy's October 1 onward coverage remains present. Recomputing the previous RSI=78 source gate/scoring with the other current filters, recorded score thresholds and common six-hour ticker spacing still yields **21 opportunities**, zero new. The same two RSI-only BTC cases remain mixed evidence; the 75 ceiling stays in place.

Eighteen completed entries pass current numeric gates and recorded score thresholds. Chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain +KRW 576.30 / +KRW 818.70 / +KRW 589.34. Eighteen hours removes an ETH winner as well as the last SOL loss; twenty-four hours changes loss chronology and permits that SOL loss again. Fixed quantities/entries/exits cannot replay replacement trades or capital reuse. Maximizing this unchanged historical sample would fit known losses without independent evidence.

Seven entries now lack holding paths, versus four yesterday. On the same **eleven currently observable entries**, actual PnL is -KRW 1,388.98, trend-memory diagnostic PnL -KRW 1,306.44 and price-only half-peak-trail PnL -KRW 1,091.19. All eleven belong to the post-September-24 subgroup. Do not compare these totals directly with yesterday's fourteen-path totals: the difference reflects lost historical paths, with no new trade. All **eight current-version entries** remain -KRW 831.14 under both alternatives. Sparse fifteen-minute observations cannot reproduce minute-level monitoring; estimated earlier fills include fees and adverse slippage. These retrospective diagnostics do not establish future profitability.

## Decision and validation

**Keep trading source and configuration unchanged.** Forward results remain negative, but this review adds no completed trade, eligible opportunity or operational defect supporting a change. Preserve defensive blocking, stops, profit memory, RSI limits and cooldowns. Continue tracking same-ticker losses after permitted reentry, new RSI-only opportunities, armed-profit losses and stop trigger/fill gaps. Record journal coverage before comparing diagnostics so rotation cannot masquerade as performance improvement.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. Synthetic logs stayed outside production. Only this report and `HARNESS.md` require publishing and VM fast-forward synchronization; the unchanged trading process requires no image build or restart. Private snapshots and credentials are excluded from Git.
