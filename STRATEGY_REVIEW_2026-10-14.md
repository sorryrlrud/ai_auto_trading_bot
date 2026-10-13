# Strategy Review — 2026-10-14

## Production verification

Direct SSH inspection of the GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and container `quant-ai-bot` confirmed normal operation. The container has run since October 1 06:10:59 KST, with zero restarts and no OOM. The initial October 14 05:46:27 cycle and 05:58:06 risk check succeeded. The next real cycle completed at 06:01:26, remained defensive, and submitted no order. Cycle failures, risk failures and pending orders are zero; September 7's error timestamp is historical.

Initial snapshot logs since the previous final October 13 06:01:51 verification contain 1,909 INFO records and no WARNING/ERROR/CRITICAL or buy/sell/realized events. Disk usage is 32%, available memory 457 MiB and container memory 105.1 MiB. No zombie processes were found. VM Git is clean, and GitHub SSH works as the bot user. Local, VM and container trading/generator SHA-256 values remain `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` and `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker commands were used.

[Pages run 38459501962](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/38459501962) completed build, report and deploy successfully for dashboard commit `4e366420`. Public HTTP 200 showed October 14 05:01:26 generation/cycle time, 92 exits and three decisions, with no private entry context, order UUID or pending-order objects. The publication is within the bounded hourly cadence: a due refresh runs on the first fifteen-minute cycle after the 3,600-second minimum, allowing roughly 75 minutes plus external deployment latency. Live health is verified independently on the VM.

## Performance and exchange reconciliation

No new trade or account flow occurred. Use the latest completed October 13 memory entry as the comparison boundary, despite the supplied last-run metadata naming October 12. October 7's SOL loss is already included.

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

Read-only Upbit CLI v0.9.1 checks completed on the VM at **05:59:46 KST**. Credentials remained in VM process memory and child-process environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) returned only KRW 57,964.4659928 with zero locked funds. Closed orders since October 13 06:01:51 and waiting/reserved orders are empty. All 21 deposits and three withdrawals contain no new created/completed or pending flow. Exchange cash reconciles with VM observations and the previous verified balance. No exchange write or validation order was submitted.

The October 1 pre-entry cash plus the already verified KRW 275 deposit gives a KRW 58,795.60233029 baseline. Current cash is KRW 831.13633749 lower: **-1.41360%** simple change against that flow-adjusted baseline, not a time-weighted return. Dashboard realized-trade return uses completed purchase costs including buy fees and remains a separate measure.

## Algorithm and prior decisions

Source history and October 1, October 7–8 and October 13 reviews were checked. Existing confirmed-fill reconciliation, minute-level hard stops, three-hour global and twelve-hour ticker/streak loss pauses, 25% position cap, 5% ATR and Bollinger ceilings, +0.5% six-hour momentum floor, September 30's 1.2% gross profit memory and October 1's completed fifteen-minute RSI ceiling of 75 remain active. Trading and automatic dashboard publishing are enabled. Safe configuration fields and observation rules agree with source defaults.

The initial private snapshot contains **1,681 observations**, September 26 18:46:42 through October 14 05:46:27. All **95 observations after yesterday's final 06:01:30 cycle** are defensive, with no order plan or holding. Relative to yesterday's initial 1,585 observations, 96 were added and none rotated out. The subsequent 06:01:26 cycle also remained defensive. The loss-streak pause expired October 7; current inactivity follows the market gate. Diagnostically bypassing defensive blocking at the initial latest snapshot still rejects all **20 candidates**: 15 exceed ATR, two miss six-hour momentum and three are below daily MA20. These are input diagnostics, not executable alternative trades.

Replaying the previous RSI=78 source gate and scoring, other current filters, recorded score thresholds and common six-hour ticker spacing **from October 1 deployment** yields the same **21 opportunities**, zero new. The two RSI-only BTC cases remain mixed: October 1's one/three/six-hour observed returns are -0.3421%/-0.5149%/-0.1545%, and October 5's are +0.1118%/+0.5091%/+0.4850%. Earlier pre-deployment observations are excluded from this forward comparison. These returns exclude fees and execution and do not replay available cash or cooldowns.

The same 18 completed entries pass current numeric gates and recorded score thresholds. Chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain +KRW 576.30 / +KRW 818.70 / +KRW 589.34. Eighteen hours removes an ETH winner as well as the final SOL loss; twenty-four hours changes loss chronology and permits that loss again. Fixed entries, quantities and exits cannot model replacement trades or capital reuse. Choosing the best historical pause without new evidence would fit known results.

Seven entries lack holding paths, unchanged from yesterday. On the same eleven observable entries, actual PnL is -KRW 1,388.98, trend-memory diagnostic PnL -KRW 1,306.44 and price-only half-peak-trail PnL -KRW 1,091.19. All eight current-version entries remain -KRW 831.14 under both alternatives. Rotation previously reduced path coverage; these totals must not be compared with older, larger samples. Sparse fifteen-minute prices cannot reproduce minute-level monitoring; hypothetical earlier fills include fees and adverse slippage. The retrospective results do not establish future profitability.

## Decision and validation

**Keep trading source and configuration unchanged.** Returns remain negative, but today's review supplies no new completed trade, eligible opportunity or operational defect that supports a rule change. Track allowed same-ticker reentry losses, new RSI-only opportunities, armed-profit losses and stop trigger/fill gaps. Continue recording coverage before comparing exit diagnostics.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. Synthetic logs stayed outside production. Only this report and `HARNESS.md` require publishing and VM fast-forward synchronization; unchanged trading code requires no image build or restart. Private snapshots and credentials are excluded from Git.
