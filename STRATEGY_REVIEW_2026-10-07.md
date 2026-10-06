# Strategy Review — 2026-10-07

## Production and dashboard verification

Direct SSH checks of `/home/sorryrlrud/ai_auto_trading_bot` on the GCP VM and `quant-ai-bot` confirmed a healthy process. The container has run since October 1 06:10:59 KST, with zero restarts and no OOM. The October 7 06:01:33 real cycle and 06:03:17 risk check succeeded; cycle failures, risk failures and pending orders are zero. Since the scheduled previous run, October 6 06:00:55.313 KST, logs through approximately 06:02 contained 1,923 INFO records and no WARNING/ERROR/CRITICAL records. The September 7 error timestamp remains historical. Disk usage is 31%, available memory 488 MiB and container memory approximately 91 MiB; no zombie processes were found. Bot-user GitHub SSH works.

Trading source and generator SHA-256 match on the VM and inside the container, respectively `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` and `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker commands were used.

The previous external deployment delay has recovered. The official [GitHub Actions incident](https://www.githubstatus.com/incidents/3q1yb5m7ltvb) was resolved October 6 07:49:42 KST. The latest real-cycle dashboard commit `049c27a` completed Pages run `37530866831` successfully. Public HTTP 200 now contains generation time **October 7 06:01:34**, successful cycle **06:01:33**, 91 exits and three recent decisions, with no private entry context or order UUID. Repository push and public deployment freshness were both checked independently.

## Performance and exchange reconciliation

Since the prior run there was **one filled SOL buy and one full sell**, newly realizing **-KRW 121.10 (-0.8327%)** including both fees. Entry was October 6 08:01:36 at KRW 163,600; exit was 14:46:41 at KRW 162,400; quantity was 0.08885058 SOL. Previous trades are not counted again.

| Measure | Result |
| --- | ---: |
| Lifetime explicit SELL records | 91: 28 wins, 63 losses |
| Lifetime realized PnL / profit factor | -KRW 6,805.01 / 0.6215 |
| Lifetime recorded fees | KRW 1,443.79 |
| Current October 1 version | 7 completed trades: 3 wins, 4 losses |
| Current-version PnL / profit factor | -KRW 480.68 / 0.4716 |
| Current all-cash account value | KRW 58,314.92106768 |
| Change since prior all-cash snapshot | -KRW 121.10334054 (-0.20724%) |

The dashboard's realized-trade return is **-0.4702%**, using cumulative completed-trade purchase cost plus buy fees as its denominator. It is not the account return. The current-version forward result remains negative and does not establish an improvement in profitability.

Upbit CLI v0.9.1 ran on the VM, with credentials only in child-process environments. Accounts, individual entry/exit orders, closed orders, waiting/reserved orders and recent flows were checked against the official [balance](https://docs.upbit.com/kr/reference/get-balance) and [order-detail](https://docs.upbit.com/kr/reference/get-order) APIs. The market buy ended in terminal `cancel` with actual full fills; the bot correctly retained those fills. Both order UUIDs and executed quantities match history. Exact entry funds/fee were KRW 14,535.954888 / 7.267977444; exit funds/fee were KRW 14,429.334192 / 7.214667096, giving **-KRW 121.103340540**. Prior cash KRW 58,436.02440822 plus that result equals the independently queried current balance exactly at its reported precision.

There are no coin holdings, locked funds, waiting/reserved orders or new deposits/withdrawals. The October 1 KRW 275 deposit was already included in the baseline and is not counted as profit.

## Algorithm review and decision

Reviewed source history and prior decisions include confirmed order reconciliation, continuous hard stops, the three-hour global loss pause, twelve-hour ticker/streak pauses, the 25% position cap, Bollinger and 5% ATR ceilings, the six-hour momentum floor of 0.5%, persistent profit memory at 1.2% gross, the completed 15-minute RSI ceiling of 75 and the October 2 reporting correction.

SOL's new entry passed the current gates: ATR 3.46%, six-hour return +0.74%, completed 15-minute RSI 59.96 and score 14.75 against threshold 11. Its cost including buy fee was KRW 14,543.22, below the KRW 14,609.01 position cap. The previous SOL loss was approximately nineteen hours earlier, beyond the twelve-hour ticker pause; the previous ZKP loss was approximately eleven hours forty-six minutes earlier, beyond the three-hour global pause. There were two consecutive losses before entry, so the twelve-hour streak pause had not yet activated. This was an eligible later reentry, not a cooldown violation.

Its persisted peak was KRW 164,000, only **+0.2445% gross** above entry, so profit protection never armed. At exit both hourly and 15-minute MA alignment/price conditions were broken and MACD histograms were negative. The observed gross loss of -0.73% met the existing joint-trend loss rule; the actual fill matched the decision price and fees explain the -0.8327% net result. No new armed-profit loss or stop-monitor failure occurred.

The exit created three consecutive losses and correctly activated the twelve-hour global pause, ending October 7 02:46:41 KST. Three independently spaced numeric opportunities during that pause were BTC/XRP at October 6 21:00 and SOL at October 7 00:01. Their gross six-hour observed returns were respectively -0.4831%, -0.3914% and -0.1827% (mean -0.3524%); shorter horizons were mixed. These signals exclude fees, execution and replacement capital allocation and do not justify shortening the pause. After expiry the latest cycle has no eligible entry: SOL/BTC lack six-hour momentum and other high-scoring candidates exceed the ATR ceiling.

The retained journal now has **1,512 observations**, September 21 13:31:38 through October 7 06:01:33. Rotation removed earlier September paths; this smaller window must not be compared as though yesterday's full sample were unchanged. Since October 1 deployment, the same prior-RSI-78/current-other-gates/recorded-threshold diagnostic with common six-hour ticker spacing yields **20 numeric opportunities**, four more than yesterday. Three were paused opportunities above; the fourth was the actual SOL entry. The two RSI-only blocked BTC signals remain unchanged and mixed: October 1 had negative one/three/six-hour paths, while October 5 had positive paths. No additional RSI-only sample supports adjusting the ceiling.

Seventeen completed entries pass current numeric gates, but four lack holding paths after rotation. On the **same thirteen observable entries**, fixed-entry results are actual **+KRW 31.10**, trend memory **+KRW 113.64**, and price-only half-peak trail **-KRW 136.76**. The post-September-24 eleven-entry subgroup is actual -KRW 829.37 versus price trail -KRW 621.33, while all seven current-version trades remain -KRW 480.68 under either alternative. Sparse cycle observations, fixed original entries/sizes, estimated earlier fills and excluded replacement transactions make these diagnostics retrospective comparisons, not portfolio backtests or independent validation. Today's lower full-sample total also reflects missing historical paths, not just the new loss.

**Decision:** keep trading rules and configuration unchanged. The new loss worsens forward results, but entry, cooldown and exit behavior match the intended safeguards, and the reviewed alternatives lack sufficient support. Do not loosen the exit, shorten the pause or add a new threshold from this single trade. Synchronize the review and operations guide without restarting the unchanged trading process.

## Validation and next review

All **105 local tests passed** in an isolated temporary source copy with socket connections blocked. Production inputs came from the VM; private snapshots and credentials are not committed. Only this report and `HARNESS.md` change, so deployment consists of a VM fast-forward synchronization; no image build, trading restart or verification order is needed.

Next review should track new current-version completed trades, repeated same-ticker losses after allowed reentry, further RSI-only signals, armed-profit losses and stop trigger/fill differences. Record observation coverage explicitly when rotation changes the comparable exit sample. Keep realized PnL, marked account changes and external flows separate.
