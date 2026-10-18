# Strategy Review — 2026-10-19

## Production finding: exchange maintenance, recovery unverified

Direct SSH checks of GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` found a running process with **degraded trading/risk checks**. The container has run since October 1 06:10:59 KST with zero restarts/OOM. Disk use is 32%, available memory 472 MiB, container memory 84.11 MiB, and GitHub SSH/publishing works. Trading/generator hashes match local, VM and container: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` / `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker command was used.

The last successful cycle is **02:01:34 KST**, last successful risk check **02:02:07**. The 05:56 runtime snapshot has **33 consecutive cycle failures / 174 risk failures**, with `ConnectTimeout` on Upbit accounts. The first logged risk exception is 02:04:27. Since the previous final check, October 18 06:05:47, the private log snapshot contains 1,631 INFO and 174 ERROR records, no warnings/critical records or new buy/sell/realized events. Main-loop risk failures also contribute to the risk counter, so log counts must not be added to runtime counters.

[Upbit's official notice](https://support.upbit.com/hc/ko/articles/59610087642009-서버-점검-안내-10-19-02-00) schedules all-service maintenance for **October 19 02:00–08:00 KST**, subject to change. Failed public requests from the VM host/container and an independent endpoint probe are consistent with that maintenance; GitHub remains reachable. A read-only VM Upbit CLI v0.9.1 accounts request at **05:59:03** exceeded an 18-second deadline. Credentials stayed in VM memory/child environment; no order or exchange write was submitted. Current balances, open/closed orders and flows therefore remain **unverified**, rather than being assumed unchanged from yesterday. Maintenance completion and actual bot recovery have not been observed.

## Recorded performance

The completed October 18 review/memory is the comparison boundary; the supplied last-run metadata is older. No new trade appears in VM history. These are recorded totals, not fresh exchange reconciliation.

| Measure | Result |
| --- | ---: |
| Lifetime explicit SELL records | 92: 28 wins, 64 losses |
| Lifetime realized PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| Current October 1 strategy | 8 completed: 3 wins, 5 losses |
| Current-version PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-version fees | KRW 116.59 |
| Current-version SOL | 3 losses, -KRW 620.01 |
| Last successful cycle cash / holdings | KRW 57,964.4659928 / zero |
| Dashboard realized-trade return | -0.4895% |

The last independently reconciled account is October 18 06:04:16. The same cash appears in today's 02:01:34 successful observation. Relative to the previously verified flow-adjusted baseline KRW 58,795.60233029, it corresponds to -KRW 831.13633749 / **-1.41360%** simple change. Today's live account return cannot be confirmed while the API is unavailable. Dashboard return uses cumulative completed-trade purchase cost plus buy fees; these denominators remain separate.

## Algorithm and historical decisions

Revisited September 30 profit memory, October 1 RSI deployment, October 7–8 allowed SOL reentry/stop execution and October 18's decision to retain rules. Confirmed-fill reconciliation, minute-level hard stops, three-hour global and twelve-hour ticker/streak loss pauses, the 25% position cap, 5% ATR/Bollinger ceilings, +0.5% six-hour momentum floor, 1.2% gross profit-memory arming and completed fifteen-minute RSI ceiling 75 remain in source. The exception path fails before producing an executable plan when account retrieval fails; existing retries and failure reporting remain active.

The snapshot contains **1,639 observations**, October 2 00:31:40 through October 19 02:01:34. Since yesterday's final cycle there are **80 new successful observations**, all defensive, with zero decisions or holdings. Today's latest 23 candidates also fail numeric gates when defensive blocking alone is diagnostically bypassed: **19 exceed ATR / four miss six-hour momentum**. With actual market context and recorded score thresholds, none of the new observations passes current or prior RSI rules. Missing cycles during connectivity loss are failures, not successful no-trade observations.

Journal rotation removed **507 older records** (2,066 previous + 80 new - 1,639 retained). Prior-RSI-78 source gate/scoring with current other filters and common six-hour ticker spacing now yields **19 retained opportunities**, including one RSI-only BTC block on October 5. October 1's other RSI-only path has rotated out. The previous total of 21 and two RSI-only cases cannot be compared as though today's sample had identical coverage. No new opportunity supports relaxing the RSI ceiling.

Eighteen completed entries still pass today's numeric gates/recorded thresholds. Chronological selected-loss diagnostics for twelve/eighteen/twenty-four-hour ticker pauses remain **+KRW 576.30 / +KRW 818.70 / +KRW 589.34**, fixing actual entries, quantities and exits. As reviewed October 8, eighteen hours removes an ETH winner along with the final SOL loss, while twenty-four hours changes which earlier loss starts a later pause. These known-outcome comparisons do not justify optimizing the threshold.

Rotation increases missing holding paths from seven to **ten** of those eighteen entries. The remaining **eight paths are exactly the eight current-version trades**: actual, trend-memory and price-only half-peak-trail diagnostics all remain **-KRW 831.14**, with no earlier alternative exit. Yesterday's eleven-path actual/alternative totals are not comparable to this smaller sample. Sparse fifteen-minute observations cannot reconstruct minute-level peaks/stops, replacement purchases or cash reuse; hypothetical earlier fills include fees and adverse slippage.

## Decision and validation

**Keep trading source/configuration unchanged.** Current performance is negative, but no new trade, eligible signal or demonstrated application defect supports a strategy change. The actionable finding is Upbit maintenance and pending recovery verification. Do not suppress errors, reset failure counters or label a running container as healthy trading. Existing timeout/retry paths will continue; an unnecessary restart cannot restore the unavailable exchange.

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. [Pages run 39164226288](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/39164226288) completed successfully. Public HTTP 200 serves generation time **05:38:25**, last success 02:01:34 and subsequent `ConnectTimeout`, 92 exits and three decisions. Existing dashboard logic reports an error without a later success; private entry context, order UUIDs and pending-order objects are absent. Successful page hosting is not successful trading.

Publish this review and `HARNESS.md`, then fast-forward the VM. This documentation-only synchronization requires no trading image build/restart. Private snapshots, credentials and the user's untracked `AGENTS.md` are excluded.

**Pending after maintenance:** observe both a new VM cycle and risk success, zero failure counters, reconcile accounts/closed orders (`done` + `cancel`)/open orders (`wait` + `watch`)/deposits/withdrawals, confirm pending reconciliation and a recovered public heartbeat. The scheduled 08:00 endpoint is not proof of completion. Current exchange reconciliation and recovery remain blocked until the external service returns.
