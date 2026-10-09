# Strategy Review — 2026-10-10

## Production verification

Direct SSH inspection of the GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` confirmed normal operation. The container has run since October 1 06:10:59 KST, with zero restarts and no OOM. The initial snapshot shows the October 10 05:46:32 successful real cycle and 05:57:17 risk check; cycle failures, risk failures and pending orders are zero. The September 7 error timestamp is historical. Logs since the previous scheduled run, October 9 05:57:05.252 KST, contain 1,918 INFO records and no WARNING/ERROR/CRITICAL records through the initial snapshot.

Disk usage is 31%, available memory 481 MiB and container memory 84.75 MiB. No zombie processes were found. VM Git is clean and GitHub SSH works as the bot user. Trading and generator SHA-256 hashes match local, VM and container copies: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` and `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker commands were used.

[Pages run 37985879495](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/37985879495) succeeded for dashboard commit `7586abe2`. Independent public HTTP 200 verification shows October 10 05:16:32 generation/cycle time, 92 exits and three decisions. Private entry context, pending-order objects and order UUIDs are absent. Subsequent unchanged cycles correctly skipped publication. The 3,600-second minimum spacing followed by the next fifteen-minute cycle can produce approximately 75 minutes between unchanged heartbeats, plus Pages latency; the direct VM cycle confirms current operation.

## Performance and exchange reconciliation

**No new buy, sell or account flow occurred since the prior scheduled run.** The October 7 SOL loss is already included in previous reviews and is not counted again.

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

Read-only Upbit CLI v0.9.1 checks completed on the VM at 05:58:18 KST. Credentials remained in VM process memory and child-process environments. The [official balance endpoint](https://docs.upbit.com/kr/reference/get-balance) independently returned only KRW 57,964.4659928, with zero locked funds. Closed orders since October 9 05:57:05.252 KST returned none; waiting and reserved order lists are empty. The latest 21 deposits and three withdrawals contain no new created/completed or pending flow. Exchange cash exactly matches the preceding exchange snapshot and VM observations; no new individual order requires reconciliation.

The October 1 pre-entry cash baseline plus the previously verified KRW 275 deposit is KRW 58,795.60233029. Current cash is KRW 831.13633749 lower, a **-1.41360%** simple change against that flow-adjusted baseline. This is not a time-weighted return. Dashboard realized-trade return instead uses completed-trade purchase cost plus buy fees as its denominator; it excludes deposits and open-position marks. Both measures remain unchanged, and current-strategy forward performance remains negative.

## Algorithm and historical decisions

Source history and prior reviews were checked for confirmed-order reconciliation, independent minute-level hard stops, three-hour global and twelve-hour ticker/streak loss pauses, 25% position cap, Bollinger and 5% ATR ceilings, +0.5% six-hour momentum floor, September 30 persistent profit memory armed at 1.2% gross, October 1 completed fifteen-minute RSI ceiling of 75 and October 2 return-label correction.

All **96 new observed cycles** are defensive, record the explicit defensive entry block, and contain no BUY/SELL plans or holdings. The last loss-streak pause expired on October 7; current inactivity follows the market gate. At the latest snapshot, diagnostically removing defensive blocking still rejects all 22 signals: 18 exceed the 5% ATR ceiling and four miss the +0.5% six-hour momentum floor. This is a snapshot diagnosis, not a replay of alternative execution or a claim that the market gate never matters.

No new repeated SOL reentry, armed-profit loss or stop trigger/fill event exists. The earlier SOL hard stop, allowed reentry interval, fees and trigger/fill movement were reconciled in the October 8 review. No new live evidence supports changing those controls today.

### Comparable diagnostics

The retained journal contains **1,799 observations**, September 21 13:31:38 through October 10 05:46:32. Coverage start is unchanged; 96 observations were added and no older holding path was lost in this snapshot. The previous 78 RSI source gate/scoring, current other filters, recorded cycle thresholds and common six-hour ticker spacing still yield **21 numeric opportunities** since October 1 deployment, with **zero new opportunities**.

The two RSI-only blocked BTC signals remain mixed. October 1 one/three/six-hour observed returns are -0.3421%/-0.5149%/-0.1545%; October 5 returns are +0.1118%/+0.5091%/+0.4850%. Horizons use the nearest same-ticker observation within 120 seconds of the signal's observation time plus the horizon and exclude fees, execution and capital constraints. Two already-known signals do not support adjusting the 75 ceiling.

The same eighteen completed entries pass current source gates and recorded score thresholds. Chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain +KRW 576.30 / +KRW 818.70 / +KRW 589.34. The eighteen-hour choice removes an ETH winner as well as the last SOL loss; twenty-four hours changes the loss chronology and permits that SOL loss again. Entries, sizes and exits are fixed, with no replacement purchases, rejected historical-trade replay or capital reuse. Selecting eighteen hours now would still optimize to known outcomes.

Four entries lack paths after earlier journal rotation. On the same fourteen observable entries, actual PnL is -KRW 319.36, trend-memory diagnostic PnL -KRW 236.82 and price-only half-peak-trail PnL -KRW 487.22. The twelve-entry post-September-24 subgroup is actual -KRW 1,179.83 versus price trail -KRW 971.79. All eight current-version entries remain -KRW 831.14 under both alternatives. Sparse fifteen-minute observations cannot reproduce minute-level monitoring; estimated earlier fills include fees and adverse slippage. These retrospective results do not establish future profitability.

## Decision and validation

**Keep trading source and configuration unchanged.** The eight-trade forward sample remains loss-making, but today adds no trade, eligible opportunity or operational failure. Preserve defensive blocking, hard stops, profit memory, RSI limit and existing cooldowns. Prioritize repeated same-ticker losses when eligible reentries resume rather than changing thresholds to fit unchanged historical outcomes.

All **105 local tests passed** from an isolated temporary source copy with socket connections blocked. Private VM snapshots and credentials are not committed. Only this review and `HARNESS.md` need publishing and VM fast-forward synchronization; the unchanged trading process needs no restart or image rebuild.

Next review should check fresh current-version trades, repeated losses after valid reentry intervals, new RSI-only signals, armed-profit losses and stop trigger/fill differences. Preserve the flow-adjusted cash baseline, journal coverage and distinction between realized returns, account flows and open-position marks.
