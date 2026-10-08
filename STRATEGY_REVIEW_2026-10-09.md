# Strategy Review — 2026-10-09

## Production verification

Direct SSH checks of the GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` confirmed normal operation. The container has run since October 1 06:10:59 KST with zero restarts and no OOM. The October 9 05:46:32 real cycle and 05:58:58 risk check succeeded; cycle failures, risk failures and pending orders are zero. The September 7 error timestamp is historical. Logs since the previous scheduled run, October 8 05:55:24.946 KST, through the initial snapshot contain 1,920 INFO records and no WARNING/ERROR/CRITICAL records. There are no new BUY plans or completed trades.

Disk usage is 31%, available memory 448 MiB and container memory 109.3 MiB. No zombie processes were found. The VM Git working tree is clean, and GitHub SSH works as the container bot user. Trading and dashboard-generator SHA-256 hashes match local, VM and container copies: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` and `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker commands were used.

[Pages run 37834484417](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/37834484417) succeeded for dashboard commit `ea128062`. Initial independent public HTTP 200 verification showed October 9 04:46:37 generation time, the 04:46:36 cycle, 92 exits and three decisions. Private entry context and order UUIDs are absent. Later unchanged cycles correctly skipped publication: the 3,600-second minimum publication spacing plus the next 15-minute cycle means an unchanged heartbeat can approach 75 minutes before the next refresh, followed by Pages latency. The public timestamp alone must not be substituted for the directly verified VM cycle.

## Performance and exchange reconciliation

**No new buy, sell or account flow occurred since the previous scheduled run.** The October 7 SOL loss already documented yesterday is not counted again.

| Measure | Result |
| --- | ---: |
| Lifetime explicit SELL records | 92: 28 wins, 64 losses |
| Lifetime realized PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| Current October 1 version | 8 completed trades: 3 wins, 5 losses |
| Current-version realized PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-version fees | KRW 116.59 |
| Current-version SOL results | 3 losses, -KRW 620.01 |
| Current all-cash account value | KRW 57,964.4659928 |
| Change since the preceding all-cash snapshot | KRW 0 / 0% |
| Dashboard realized-trade return | -0.4895% |

Upbit CLI v0.9.1 ran read-only on the VM at 05:58:55 KST, with credentials confined to child-process environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) independently returned only KRW 57,964.4659928, with zero locked funds. Closed orders since October 8 05:55:24 returned none; both waiting and reserved order queries returned none. The latest 21 deposits and three withdrawals were checked and have no new created/completed item since the previous run. The exchange balance exactly matches both yesterday's exchange balance and the VM observation cash. No individual new order exists to reconcile today.

The October 1 pre-entry all-cash baseline plus its previously verified KRW 275 deposit is KRW 58,795.60233029. Current cash remains KRW 831.13633749 lower, a **-1.41360%** simple change against that flow-adjusted baseline. It is not a time-weighted return. Dashboard realized-trade return instead divides completed-trade net PnL by cumulative purchase cost plus buy fees, excluding deposits and open-position marks. Neither result changed today; the current strategy's forward performance remains negative.

## Algorithm and prior decisions

Source history and the previous reviews were checked: confirmed order reconciliation and independent minute-level hard stops; the three-hour global and twelve-hour ticker/streak loss pauses; the 25% position cap; Bollinger and 5% ATR ceilings; the +0.5% six-hour momentum floor; September 30 persistent profit memory at 1.2% gross; October 1 completed 15-minute RSI ceiling of 75; and October 2 return-label correction.

All **96 observed cycles** since the previous scheduled run are defensive, explicitly recording `BTC 방어장세에서는 신규 매수 차단`. Their cash is unchanged and there are no holdings or pending orders. The earlier twelve-hour loss-streak pause has already expired; the current absence of trades is caused by the market filter. Removing that filter diagnostically from the latest snapshot still leaves all 22 scanned signals rejected: 17 exceed the 5% ATR ceiling and five fail the +0.5% six-hour floor. This is a snapshot check, not evidence that relaxing the market filter would always have no effect.

There is no new repeated SOL reentry, armed-profit loss or stop trigger/fill event. The last SOL hard stop and its fees/execution movement were fully reconciled in the October 8 review. Today's unchanged exchange balance and empty order queries confirm no subsequent execution anomaly.

### Common-sample diagnostics

The journal now retains **1,703 observations**, September 21 13:31:38 through October 9 05:46:32. The coverage start is unchanged, with 96 additional observations and no loss of an older holding path. Applying the prior 78 RSI source gate/scoring, current other filters, recorded cycle thresholds and common six-hour ticker spacing still finds **21 numeric opportunities** since October 1 deployment, with **zero new opportunities** today. They are diagnostic signals, not automatically executable replacement trades.

The two RSI-only blocked BTC signals remain mixed and unchanged. October 1 one/three/six-hour price changes were -0.3421%/-0.5149%/-0.1545%; October 5 changes were +0.1118%/+0.5091%/+0.4850%. Horizons use the nearest same-ticker observation within 120 seconds of the signal's observed time plus the horizon. They exclude fees, execution and capital constraints. There is no new evidence to change the 75 RSI ceiling.

The same eighteen completed entries pass current source gates and recorded entry thresholds. Chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain +KRW 576.30 / +KRW 818.70 / +KRW 589.34. Eighteen hours removes yesterday's SOL loss but also an ETH winner; twenty-four hours changes which later loss starts a pause and permits that SOL loss again. These fix original entries, quantities and exits, omit replacement purchases and capital reuse, and do not replay rejected historical trades. With no new independent trade, choosing eighteen hours would still optimize to the already-known loss.

Four of those eighteen entries lack holding paths after earlier journal rotation. On the **same fourteen observable entries**, actual PnL remains -KRW 319.36, trend-memory diagnostic PnL -KRW 236.82 and price-only half-peak-trail PnL -KRW 487.22. The post-September-24 twelve-entry subgroup is actual -KRW 1,179.83 versus price trail -KRW 971.79. All eight current-version entries remain -KRW 831.14 under either exit alternative. Sparse 15-minute observations cannot reproduce minute-level peaks/stops; estimated earlier fills include fees and adverse slippage. These retrospective results do not establish future profitability.

## Decision and validation

**Keep trading source and configuration unchanged.** The current eight-trade strategy has lost money, but today adds no trade or new eligible signal, and operational controls match their intended behavior. Preserve defensive entry blocking, hard stops, persistent profit memory, RSI ceiling and existing cooldowns. Repeated SOL losses remain a priority when eligible reentries resume; an unchanged historical optimum does not justify another threshold adjustment.

All **105 local tests passed** from an isolated temporary source copy with socket connections blocked. Private snapshots and credentials are not committed. Only this review and `HARNESS.md` require publishing and VM fast-forward synchronization; the unchanged trading process requires no restart or image rebuild.

The next real cycle completed at **06:01:32 KST**, remained defensive and submitted no order. Its risk check at 06:01:00 also succeeded with zero holdings/stops/pending orders. It correctly triggered the due hourly dashboard heartbeat and generated dashboard commit `ad40c5e`.

Next review should check fresh current-version trades, repeated same-ticker losses after valid reentry intervals, new RSI-only opportunities, armed-profit losses and stop trigger/fill differences. Preserve the cash baseline above, record journal coverage changes and distinguish account flows, realized returns and open-position marks.
