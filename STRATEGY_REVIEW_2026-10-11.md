# Strategy Review — 2026-10-11

## Production verification

Direct SSH checks of the GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` confirmed normal operation. The container has run since October 1 06:10:59 KST with zero restarts and no OOM. The October 11 06:01:33 real cycle and 06:02:46 risk check succeeded; cycle failures, risk failures and pending orders are zero. The September 7 error timestamp is historical. Snapshot logs since the previous verified October 10 05:59:16 risk check contain 1,927 INFO records and no WARNING/ERROR/CRITICAL records or buy/sell/realized events.

Disk usage is 31%, available memory 462 MiB and container memory 104.3 MiB. No zombie processes were found. VM Git is clean and GitHub SSH works as the bot user. Trading and generator SHA-256 hashes match local, VM and container copies: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` and `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker commands were used.

[Pages run 38086033204](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/38086033204) completed build, report and deploy successfully for dashboard commit `37c19731`. Independent public HTTP 200 verification shows October 11 06:01:33 generation/cycle time, 92 exits and three decisions. Private entry context, order UUIDs and pending-order objects are absent. Public heartbeat timestamps are publication snapshots; direct VM checks establish current service health.

## Performance and exchange reconciliation

**No new buy, sell or account flow occurred.** The October 7 SOL exit is already included and is not counted again. Although this invocation's supplied last-run timestamp points to October 10 05:56:40 KST, the automation memory contains the completed October 10 review; the verified 05:59:16 boundary avoids duplicating that work.

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
| Change since previous account snapshot | KRW 0 / 0% |
| Dashboard realized-trade return | -0.4895% |

Read-only Upbit CLI v0.9.1 checks completed on the VM at 06:03:52 KST. Credentials were read into VM process memory from the container configuration and passed only in child-process environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) returned only KRW 57,964.4659928, with zero locked funds. Closed orders since October 10 05:59:16 KST returned none; waiting and reserved order lists are empty. All 21 listed deposits and three withdrawals contain no new created/completed or pending flow. Exchange cash matches the previous exchange snapshot and VM observations exactly.

The October 1 pre-entry cash baseline plus the previously verified KRW 275 deposit is KRW 58,795.60233029. Current cash is KRW 831.13633749 lower, a **-1.41360%** simple change against that flow-adjusted baseline, rather than a time-weighted return. Dashboard realized-trade return instead divides realized PnL by completed-trade purchase cost plus buy fees. The two denominators must remain distinct.

## Algorithm and historical decisions

Source history and earlier reviews were checked for confirmed-order reconciliation, independent minute-level hard stops, three-hour global and twelve-hour ticker/streak loss pauses, 25% position cap, Bollinger and 5% ATR ceilings, +0.5% six-hour momentum floor, September 30 persistent profit memory armed at 1.2% gross, October 1 completed fifteen-minute RSI ceiling of 75, and October 2 return-label correction. Current recorded entry/exit rules match those controls.

All **97 new observations** after the previous snapshot are defensive, explicitly block new entries, and contain no BUY/SELL plan or holding. This count includes the October 10 06:01 cycle following yesterday's 05:46 snapshot through today's 06:01 cycle. The loss-streak pause expired on October 7; current inactivity follows the market gate. At the latest snapshot, diagnostically bypassing defensive blocking still rejects every one of 22 signals: 17 exceed the 5% ATR ceiling, four miss the +0.5% six-hour momentum floor, and one exceeds the Bollinger position ceiling. This single-snapshot exercise does not replay alternative executions.

No new repeated SOL reentry, armed-profit loss or stop trigger/fill event exists. Earlier SOL losses and their valid reentry gaps, fees and stop execution were reconciled in the October 7 and October 8 reviews.

### Comparable diagnostics

The retained journal contains **1,896 observations**, September 21 13:31:38 through October 11 06:01:33. Coverage start is unchanged and no older holding path was lost. Applying the previous 78 RSI source gate/scoring with current other filters, recorded score thresholds and common six-hour ticker spacing still produces **21 numeric opportunities** since October 1 deployment, with zero new opportunities. The two already-known RSI-only BTC signals remain the entire mixed sample; no new signal supports changing the 75 ceiling.

The same eighteen completed entries pass current source gates and recorded score thresholds. Chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain +KRW 576.30 / +KRW 818.70 / +KRW 589.34. Eighteen hours removes an ETH winner as well as the final SOL loss; twenty-four hours changes the selected-loss chronology and allows that SOL loss again. Entries, quantities and exits are fixed, with no replacement purchases, replay of rejected historical trades or capital reuse. Choosing eighteen hours from these unchanged outcomes would fit known losses rather than add independent evidence.

Four entries lack paths following earlier journal rotation. On the same fourteen observable entries, actual PnL is -KRW 319.36, trend-memory diagnostic PnL -KRW 236.82 and price-only half-peak-trail PnL -KRW 487.22. The twelve-entry post-September-24 subgroup is actual -KRW 1,179.83 versus price trail -KRW 971.79. All eight current-version entries remain -KRW 831.14 under both alternatives. These fixed-entry retrospective results cannot establish future profitability; sparse fifteen-minute paths do not reconstruct minute-level monitoring, and estimated early fills include fees and adverse slippage.

## Decision and validation

**Keep trading source and configuration unchanged.** Forward performance remains negative, but this review adds no trade, eligible opportunity or operational defect. Preserve defensive blocking, hard stops, profit memory, RSI limits and cooldowns. Track repeated same-ticker losses after eligible reentries resume, new RSI-only signals, armed-profit losses and stop trigger/fill gaps.

All **105 local tests passed** from an isolated temporary source copy with socket connections blocked. Synthetic test logs stayed outside production. Private VM snapshots and credentials are not committed. Publish this review and `HARNESS.md`, then fast-forward the VM repository and verify hashes/runtime health. Since no trading code, dependency or configuration changed, no image rebuild or trading-container restart is required.
