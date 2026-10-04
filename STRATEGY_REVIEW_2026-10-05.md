# Strategy Review — 2026-10-05

## Production verification

Direct SSH checks on the GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` confirmed normal operation. The container has run since October 1 06:10:59 KST with zero restarts and no OOM. The October 5 06:01:41 real cycle completed successfully; risk checks advanced through 06:06:21 with zero cycle failures, risk failures or pending orders. Since the scheduled previous run, October 4 06:01:08.559 KST, Docker logs contained 1,982 INFO records and no WARNING/ERROR/CRITICAL records. The September 7 error timestamp is historical.

Disk usage is 32%, available memory 476 MiB, and container memory 85.23 MiB. Docker init and Python were the only listed processes, with no zombies. VM Git was clean and bot-user GitHub SSH returned the published dashboard head. Trading source SHA-256 remains `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081`; generator SHA-256 remains `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`.

Public GitHub Pages returned HTTP 200 with the 06:01:41 heartbeat, three decisions, 87 realized exits and the corrected realized-trade-return label. No private entry context or order UUID was present in its data payload. No local Docker commands were used.

## Performance and exchange reconciliation

Since the previous run there have been **two buys and no sells**, so new realized PnL is **KRW 0**. Previously reported October 2–3 exits are not counted again. Lifetime explicit SELL history remains **87 exits, 27 wins, 60 losses, -KRW 6,245.34**, win rate 31.03%, profit factor 0.6397 and recorded fees KRW 1,385.58. Dashboard realized-trade return remains -0.4497%; its denominator is cumulative completed-trade purchase amounts plus buy fees, not initial account equity.

Upbit CLI v0.9.1 ran on the VM with credentials confined to child-process environments. Accounts, closed orders, individual order details, waiting/reserved orders and account flows were checked. These checks use the official [balance](https://docs.upbit.com/kr/reference/get-balance) and [individual order](https://docs.upbit.com/kr/reference/get-order) APIs. Both market buys have terminal `cancel` status with actual fills; the bot correctly retained their full quantities and fees.

| Entry | Quantity | Actual funds | Buy fee | Entry 15-minute RSI | Six-hour momentum |
| --- | ---: | ---: | ---: | ---: | ---: |
| SOL October 4 13:01:36 | 0.08924683 | KRW 14,645.404803 | KRW 7.3227024015 | 66.57 | +0.98% |
| XRP October 4 17:01:37 | 7.19664538 | KRW 14,652.36999368 | KRW 7.32618499684 | 66.88 | +0.64% |

Exchange quantities, funds, average prices, fees and UUIDs agree with VM state. Cash is **KRW 29,562.1658117**, with no locked balance or open waiting/reserved order. Previous cash KRW 58,874.58949578 minus both actual entry amounts and fees reconciles to current cash within KRW 0.000000002. The latest deposit is the already-recorded October 1 KRW 275; no new deposit or withdrawal occurred in this window. The CLI emits adjacent JSON objects for some list commands and empty output for empty lists; successful list output was decoded accordingly rather than treating it as one JSON array.

At the exchange ticker snapshot around October 5 06:04:01, XRP was KRW 2,040 and SOL KRW 164,300. Total marked equity is **KRW 58,906.58**, up **KRW 31.99 (+0.05433%)** from the prior all-cash baseline. This includes paid buy fees but excludes a future sell fee. Estimated liquidation PnL after a 0.05% sell fee is **+KRW 17.31**, before adverse execution movement. These are unrealized figures, not newly completed profit or time-weighted account returns.

## Algorithm review and decision

Reviewed source history and prior decisions cover confirmed order recovery, continuous hard stops, three-hour loss and twelve-hour streak/ticker pauses, the 25% position cap, Bollinger and 5% ATR ceilings, the 0.5% six-hour momentum floor, persistent 1.2% gross profit memory and the October 1 completed 15-minute RSI ceiling of 75. The October 2 change only corrected reporting terminology.

Both new entries satisfy the current filters and score threshold. Entry ATR is 3.58% for SOL and 4.84% for XRP. The latest cycle holds both because their completed-candle trends remain aligned. Their persisted observed peaks are SOL KRW 165,300 (+0.7313% gross) and XRP KRW 2,043 (+0.3438% gross), both below the 1.2% profit-memory arming threshold. No additional armed-profit loss or completed losing reentry has occurred. Hard-stop monitoring continues independently of entry filters.

The VM snapshot contains 1,919 observations from September 15 08:16:37 through October 5 06:01:41. Applying the prior RSI ceiling of 78 with all other current source filters and each recorded score threshold, then spacing the common opportunity sample six hours per ticker, yields 13 numeric opportunities since deployment. Four occur in the new interval: SOL October 4 13:00, XRP 17:00, BTC 20:00 and BTC October 5 06:00. The first two led to actual entries, each within the 25% position cap. BTC 20:00 produced a BUY plan with only KRW 3,036 available; execution correctly skipped it below the KRW 5,000 minimum. A BUY plan is not evidence of a completed transaction.

There are now two common-sample opportunities rejected solely by the RSI ceiling: the previously reviewed October 1 BTC signal and a new October 5 06:00 BTC signal with RSI 76.17. The new signal has no one-/three-/six-hour future observation yet. It cannot support tightening or relaxing the ceiling today. Signal diagnostics do not replay alternative portfolio transactions or capital reuse.

Current-version completed trades remain **three, two wins and one loss, +KRW 78.99** after fees; the two open positions are excluded. Repeating the prior fixed-entry comparison on 13 comparable completed entries passing current gates gives actual fills +KRW 1,486.43, trend memory +KRW 1,568.97 and the previously rejected half-peak price trail +KRW 926.75. The diagnostic includes estimated 0.05% sell fees and 0.1% adverse movement for hypothetical earlier exits. It still disfavors changing to price-only exits. It fixes entries, sizes and original exits and uses sparse cycle observations; it cannot reproduce 60-second sampling, replacement trades or an untouched holdout.

**Decision:** keep trading rules and configuration unchanged. No production defect or adequately supported incremental improvement was identified. Overall realized performance remains negative, and three completed current-version trades do not establish positive future expectancy. Record and synchronize this review without restarting the unchanged trading process.

## Validation and follow-up

All 105 local tests passed in a temporary source copy with socket connections blocked. No live verification order was submitted, no dependency or image changed, and production state/history were preserved. This report and the operations guide are the only source changes.

Next review should track closure of the two open positions, the new October 5 RSI-only BTC rejection once future observations exist, additional armed-profit losses and repeated losing reentries. Continue separating realized PnL, marked account changes and external cash flows.
