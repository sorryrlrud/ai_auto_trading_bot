# Strategy Review — 2026-10-06

## Production verification

Direct SSH checks on the GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` confirmed the trading process is healthy. The container has run since October 1 06:10:59 KST with zero restarts and no OOM. The October 6 06:01:35 real cycle completed; the 06:03:30 risk check had zero cycle failures, risk failures and pending orders. Since the scheduled previous run, October 5 06:02:19.617 KST, container logs through approximately 06:04 contained 1,946 INFO records and no WARNING/ERROR/CRITICAL records. The September 7 error timestamp is historical.

Disk usage is 32%, available memory 481 MiB and container memory 94.3 MiB. Docker init and Python remained the only processes after dashboard publishing completed, with no zombies. VM Git was clean; bot-user GitHub SSH returned `0f4806a`. Trading source SHA-256 remains `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081`; generator SHA-256 remains `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker commands were used.

## Public dashboard delay: external Actions outage

The VM dashboard and successfully pushed repository commit contain the 06:01:36 generation time and 06:01:35 successful cycle. Public GitHub Pages returned HTTP 200, three decisions, 90 realized exits and no private entry context or order UUID, but still showed **04:31:34** at 06:05 KST. A cache-busting URL with `Cache-Control: no-cache` returned the same older content. HTTP success therefore does not confirm a fresh heartbeat.

GitHub Actions run `37373345322` for `0f4806a` was queued with no assigned runner and no executed steps. Five preceding fifteen-minute builds were cancelled before any runner executed a step; the last successful run `37363969210` finished at 04:43:09 KST. The official [GitHub Actions incident](https://www.githubstatus.com/incidents/3q1yb5m7ltvb), opened October 6 04:11:58 KST, reports delays assigning hosted runners and starting workflows, with Actions marked as a major outage. This supports an external deployment-queue cause for the observed stale dashboard. Trading execution and repository pushes are healthy; public deployment freshness remains blocked by that outage. A retry alone cannot supply a runner. No hosting, publishing frequency or trading rule was changed to work around the platform incident.

## Performance and exchange reconciliation

Since the prior run there have been **one buy and three sells**, with **-KRW 438.57** newly realized PnL after fees. Previously reported entries and October 2–3 exits are not recounted as new transactions.

| Exit on October 5 | Entry | Net PnL | Net return | Persisted peak gross return | Exit |
| --- | --- | ---: | ---: | ---: | --- |
| XRP 12:01:45 | October 4 17:01:37 | +KRW 86.05 | +0.5870% | +1.4735% | Armed profit memory, 15-minute trend break |
| SOL 13:01:40 | October 4 13:01:36 | -KRW 148.45 | -1.0131% | +0.7313% | Both 15-minute and hourly trends damaged |
| ZKP 20:15:16 | October 5 19:01:37 | -KRW 376.17 | -2.5700% | +0.1374% | Continuous hard stop |

Lifetime explicit SELL history is **90 exits, 28 wins, 62 losses, -KRW 6,683.91**, win rate 31.11%, profit factor 0.6257 and recorded fees KRW 1,429.31. Dashboard realized-trade return is -0.4665%; its denominator is cumulative completed-trade purchase amounts plus buy fees, not account starting equity. Current October 1 strategy entries now have **six completed trades, three wins and three losses, -KRW 359.58**, profit factor 0.5440. This forward result is negative.

Upbit CLI v0.9.1 ran on the VM with credentials confined to child-process environments. Accounts, individual entry/exit orders, recent closed orders, waiting/reserved orders and account flows were verified using the official [balance](https://docs.upbit.com/kr/reference/get-balance) and [order-detail](https://docs.upbit.com/kr/reference/get-order) APIs. All three exit quantities exactly match their entry quantities and recorded history. Actual fills and paid fees reconcile to each history PnL within its cent rounding. Market buys have terminal `cancel` state with actual full fills, which the bot correctly retained.

Exact new net PnL is **-KRW 438.565087557572**. Prior all-cash KRW 58,874.58949578 plus that result yields KRW 58,436.024408222428; the independently queried balance is **KRW 58,436.02440822**, differing by only KRW 0.000000002428. There are no coin holdings, locked funds, open waiting/reserved orders or new deposits/withdrawals. The October 1 KRW 275 deposit is already included in the earlier baseline and is not profit.

Current all-cash equity is KRW 58,436.02. Compared with yesterday's 06:04:01 marked equity KRW 58,906.58, the snapshot change is **-KRW 470.55 (-0.79881%)**. This reverses yesterday's open-position marks as well as realizing today's results; it is distinct from today's -KRW 438.57 completed-trade PnL and is not a time-weighted return. Against the October 4 all-cash baseline, the complete position-cycle result is -0.74491%.

## Algorithm review and decision

Reviewed prior source changes and decisions cover confirmed order recovery, continuous hard stops, three-hour global loss pauses, twelve-hour streak/ticker pauses, the 25% position cap, Bollinger and 5% ATR ceilings, the 0.5% six-hour momentum floor, persistent 1.2% gross profit memory and the completed 15-minute RSI ceiling of 75. The October 2 change only corrected reporting terminology.

XRP's persisted peak was KRW 2,066 against entry KRW 2,036, so profit memory armed and its later short-trend break produced a positive exit. SOL never reached the 1.2% arming threshold; its loss is not an armed-profit failure. ZKP also never armed. Its entry ATR 4.53%, RSI 57.41, six-hour return +1.25% and score 14 against threshold 11 passed the existing gates, and its approximately KRW 14,636.80 cost including fee stayed within the 25% cap. Its entry followed SOL's loss by six hours, beyond the three-hour global pause. It was a new ticker entry rather than an immediate losing reentry.

ZKP's risk check at 20:14:13 retained the holding; at 20:15:14 the observed gross loss was -2.34% and the independent monitor sold it. The fill was another 0.140647% below the decision price, and fees brought net loss to -2.57%. The -2.2% rule is a sampled trigger, not a guaranteed fill return. The logs establish normal stop execution; they do not establish the price path between checks. No stop relaxation or higher sampling frequency is supported by this one event. The minimum-hour hold deferred ordinary exits at 19:16–20:01, while the hard stop remained active.

The private snapshot contains **2,015 observations**, September 15 08:16:37 through October 6 06:01:35. Repeating the same prior-RSI-78/current-other-gates/recorded-score-threshold diagnostic with common six-hour spacing per ticker yields **16 numeric opportunities** since October 1 deployment, three more than yesterday: XRP and ETH at October 5 08:00, ZKP at 19:00. XRP was already held. These are numeric signals, not automatically executable replacement transactions.

There remain two RSI-only blocked BTC opportunities. Using the nearest same-ticker observation within two minutes of each signal's observed time plus one/three/six hours reproduces the earlier October 1 values and now gives:

| BTC signal | RSI | 1-hour observed return | 3-hour | 6-hour |
| --- | ---: | ---: | ---: | ---: |
| October 1 15:00 | 76.66 | -0.3421% | -0.5149% | -0.1545% |
| October 5 06:00 | 76.17 | +0.1118% | +0.5091% | +0.4850% |

Offsets from target times are respectively +1/-2/-5 seconds and +1/-4/-10 seconds. The new signal rose, unlike the earlier one. Two mixed observations do not establish whether to relax the ceiling; gross signal returns exclude fees, execution, holding exits and alternative capital allocation. Keep the ceiling and continue tracking both outcomes.

The same fixed-entry diagnostic now covers **16 comparable completed entries passing current gates**: actual fills **+KRW 1,047.86**, trend memory **+KRW 1,130.40**, half-peak price trail **+KRW 488.18**. The newest three entries receive unchanged outcomes in both alternatives. A price-only trail improves the post-September-24 subgroup from -KRW 708.27 to -KRW 500.23 but worsens the full comparable sample substantially; that subgroup is not an untouched validation set. Hypothetical earlier fills include estimated 0.05% sell fees and 0.1% adverse execution movement. The diagnostic fixes entries, quantities and original exits, uses sparse cycle observations, and does not replay sixty-second sampling, replacement trades or cash reuse. It does not establish positive future expectancy.

**Decision:** keep trading source and settings unchanged. Forward PnL has deteriorated, but the identified exits comply with the rules and the specific alternatives lack adequate evidence. No new armed-profit loss or repeated immediate losing reentry was found. The actionable operational finding is stale public deployment during the documented GitHub outage, which must not be presented as a stopped VM. Record and synchronize the review without restarting the unchanged trading process.

## Validation and follow-up

All **105 local tests passed** in a temporary source copy with socket connections blocked. Runtime inputs came from the VM; private observations and secrets remain outside the repository. No verification order, dependency change, image build or container restart was used. Only this report and `HARNESS.md` change.

Next review should verify that Actions has recovered and public generation time catches up to VM publication, then track current-version completed trades, additional RSI-only rejection paths, armed-profit losses and stop execution gaps. Keep lifetime PnL, forward strategy PnL, marked account changes and external cash flows separate.
