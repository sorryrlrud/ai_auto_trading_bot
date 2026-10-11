# Strategy Review — 2026-10-12

## Production verification

Direct SSH checks of `/home/sorryrlrud/ai_auto_trading_bot` on the GCP VM and its `quant-ai-bot` container confirmed normal operation. The container has run since October 1 06:10:59 KST with zero restarts and no OOM. The October 12 06:01:37 real cycle and 06:04:30 risk check succeeded. Cycle failures, risk failures and pending orders are zero; the September 7 error timestamp is historical.

Snapshot logs after the previous review's final October 11 06:05:46 risk check contain 1,914 INFO records and no WARNING/ERROR/CRITICAL or buy/sell/realized events. Disk usage is 32%, available memory 471 MiB and container memory 83.21 MiB. No zombie processes were found. VM Git is clean and GitHub SSH succeeds as the bot user. Trading/generator SHA-256 hashes match local, VM and container copies: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker commands were used.

[Pages run 38173624111](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/38173624111) completed build, report and deploy successfully for dashboard commit `cc213ccc`. Public HTTP 200 verification shows October 12 05:46:37 generation/cycle time, 92 exits and three decisions. Private entry context, order UUIDs and pending-order objects are absent. This publication snapshot predates the directly verified 06:01 cycle by fifteen minutes and is within the bounded hourly heartbeat cadence.

## Performance and exchange reconciliation

**No new buy, sell or account flow occurred.** The October 7 SOL loss is already included. The supplied last-run timestamp is earlier than the completed October 11 memory entry, so the verified October 11 boundary is used to avoid duplicate accounting.

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

Read-only Upbit CLI v0.9.1 checks completed on the VM at **06:04:11 KST**. Credentials were read into VM process memory and passed only in child-process environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) returned only KRW 57,964.4659928, with zero locked funds. Closed orders since October 11 06:05:46 returned none; waiting/reserved orders are empty. All 21 deposits and three withdrawals contain no new created/completed or pending flow. Exchange cash matches the prior verified balance and VM observations.

The pre-entry October 1 cash baseline plus the previously verified KRW 275 deposit is KRW 58,795.60233029. Current cash is KRW 831.13633749 lower: **-1.41360%** simple change against that flow-adjusted baseline, rather than a time-weighted return. The dashboard instead divides realized trade PnL by completed-trade purchase costs including buy fees. These denominators remain separate.

## Algorithm and earlier decisions

Source history and the October 1, October 7–8 and October 11 reviews were checked. Existing controls remain confirmed-fill reconciliation, minute-level hard stops independent of ordinary exit holding time, three-hour global and twelve-hour ticker/streak loss pauses, a 25% position cap, Bollinger/5% ATR ceilings, a +0.5% six-hour momentum floor, September 30 persistent profit memory armed at 1.2% gross, October 1's completed fifteen-minute RSI ceiling of 75, and October 2's return-label correction. Container configuration and latest recorded rules match these defaults; live trading and dashboard publishing are enabled.

All **96 new observations** after October 11 06:01:33 are defensive and contain no BUY/SELL plan or holding. The loss-streak pause expired on October 7; current inactivity follows the market gate. At the latest snapshot, diagnostically bypassing defensive blocking still rejects every one of **24 signals**: 17 exceed the ATR ceiling, two miss six-hour momentum, four are below daily MA20 and one exceeds the Bollinger ceiling. This is a single-snapshot numeric check, not alternative execution evidence.

The retained journal contains **1,992 observations**, September 21 13:31:38 through October 12 06:01:37. Coverage start is unchanged. Recomputing the previous RSI=78 source gate/scoring with current other filters, recorded score thresholds and common six-hour ticker spacing still yields **21 opportunities** since October 1 deployment, with zero new opportunities. The two known RSI-only BTC cases remain a mixed sample and do not justify changing the 75 ceiling.

Eighteen recorded completed entries pass current numeric gates and score thresholds. Chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain +KRW 576.30 / +KRW 818.70 / +KRW 589.34. Eighteen hours removes an ETH winner as well as the last SOL loss; twenty-four hours changes loss chronology and permits that SOL loss again. Quantities, entries and exits are fixed; replacement entries and capital reuse are not replayed. Maximizing this unchanged historical sample would fit known losses without independent evidence.

Four entries lack holding paths due to earlier rotation. On the same fourteen observable entries, actual PnL is -KRW 319.36, trend-memory diagnostic PnL -KRW 236.82 and price-only half-peak-trail PnL -KRW 487.22. The twelve-entry post-September-24 subgroup is actual -KRW 1,179.83 versus price trail -KRW 971.79. All eight current-version entries remain -KRW 831.14 under both alternatives. Sparse fifteen-minute observations cannot reproduce minute-level monitoring, and estimated early fills include fees and adverse slippage. These retrospective results do not establish future profitability.

## Decision and validation

**Keep trading source and configuration unchanged.** Forward results remain negative, but today's review adds no completed trade, eligible opportunity or operational defect supporting a change. Preserve defensive blocking, hard stops, profit memory, RSI limits and cooldowns. Continue checking same-ticker losses after permitted reentry, new RSI-only opportunities, armed-profit losses and stop trigger/fill gaps.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. Synthetic logs stayed outside production. Only this review and `HARNESS.md` require publishing and VM fast-forward synchronization; the unchanged trading process requires no image build or restart. Private snapshots and credentials are excluded from Git.
