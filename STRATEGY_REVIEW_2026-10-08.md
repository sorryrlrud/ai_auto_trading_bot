# Strategy Review — 2026-10-08

## Production verification

Direct SSH checks of the GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` confirmed a healthy process. The container has run since October 1 06:10:59 KST, with zero restarts and no OOM. The October 8 05:46:33 real cycle and 05:58:01 risk check succeeded; cycle failures, risk failures and pending orders are zero. The September 7 error timestamp is historical. Logs from the previous scheduled run, October 7 06:00:13.128 KST, through the initial 05:56 snapshot contained 1,911 INFO records and no WARNING/ERROR/CRITICAL records. Disk usage was 31%, available memory 284 MiB and container memory 89.2 MiB, with no zombie processes. Bot-user GitHub SSH succeeded and the VM Git working tree was clean.

Trading source and generator hashes match the VM/container and unchanged local source: `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081` and `b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`. No local Docker commands were used.

[Pages run 37682661752](https://github.com/sorryrlrud/ai_auto_trading_bot/actions/runs/37682661752) succeeded for automatic dashboard commit `ae3141a2`. Independent public HTTP 200 verification showed October 8 **05:31:33** generation/cycle time, 92 exits and three decisions, without private entry context or order UUIDs. The later 05:46 cycle made no decision changes and correctly skipped publishing until the bounded hourly heartbeat. The earlier Actions outage remains recovered.

## Performance and exchange reconciliation

Since the previous run, **one SOL buy and one full sell** newly realized **-KRW 350.46 (-2.4147%)**, including both fees. Entry was October 7 07:01:34 at KRW 164,000; exit was 11:03:59 at KRW 160,200; quantity was 0.08845185 SOL. Earlier trades are not counted again.

| Measure | Result |
| --- | ---: |
| Lifetime explicit SELL records | 92: 28 wins, 64 losses |
| Lifetime realized PnL / profit factor | -KRW 7,155.47 / 0.6096 |
| Lifetime recorded fees | KRW 1,458.13 |
| Current October 1 version | 8 completed trades: 3 wins, 5 losses |
| Current-version realized PnL / profit factor | -KRW 831.14 / 0.3404 |
| Current-version SOL results | 3 losses, -KRW 620.01 |
| Current all-cash account value | KRW 57,964.4659928 |
| Change since prior all-cash snapshot | -KRW 350.455074885 (-0.60097%) |
| Dashboard realized-trade return | -0.4895% |

The dashboard return uses cumulative completed-trade purchase cost plus buy fees, not account capital. Since the October 1 pre-entry all-cash baseline, adjusted for its already-documented KRW 275 deposit, cash changed from KRW 58,795.60233029 to KRW 57,964.4659928: -KRW 831.13633749, or **-1.41360%**. This is a simple cash change against a flow-adjusted baseline, not a time-weighted return. The current strategy's forward performance is negative.

Upbit CLI v0.9.1 ran on the VM with credentials confined to child-process environments. Accounts, recent closed orders, individual entry/exit orders, both waiting/reserved order states and deposits/withdrawals were independently checked using the official [balance](https://docs.upbit.com/kr/reference/get-balance) and [order-detail](https://docs.upbit.com/kr/reference/get-order) APIs. The market buy ended in terminal `cancel` with actual full fills. Both UUIDs and quantities match the VM history. Exact entry funds/fee were KRW 14,506.1034 / 7.2530517; exit funds/fee were KRW 14,169.98637 / 7.084993185. Exact net PnL is **-KRW 350.455074885**; the prior cash KRW 58,314.92106768 plus that result equals current cash to within KRW 0.000000005 of exchange decimal precision. There are no holdings, locked balances, open orders or new flows. The existing deposit is not counted as profit.

## Algorithm review

Reviewed source history and previous decisions cover confirmed order reconciliation and independent hard stops; three-hour global and twelve-hour ticker/streak loss pauses; the 25% position cap; Bollinger and 5% ATR ceilings; the +0.5% six-hour momentum floor; September 30 persistent profit memory at 1.2% gross; October 1 completed 15-minute RSI ceiling of 75; and October 2 reporting correction.

The new SOL entry passed the existing gates: ATR 3.14%, six-hour return +0.68%, hourly return -0.06%, completed 15-minute RSI 55.79, score 14 against threshold 11, and aligned daily/hourly/15-minute trends. Entry cost including buy fee was KRW 14,513.36, below the KRW 14,578.73 position cap. The previous SOL exit was approximately sixteen hours fifteen minutes earlier, beyond both twelve-hour loss pauses. This was an allowed reentry, not a cooldown violation.

Its persisted peak was KRW 164,300, only **+0.1829% gross**, so profit memory never armed. By 11:01 the cycle observed -2.13%, still above the -2.2% hard-stop threshold, and the joint-trend predicates did not yet require an exit. The 11:02:56 risk check did not trigger; the next check at 11:03:58 observed **-2.26%** and executed the stop. The fill moved another -0.062383% from the observed decision price; this and both fees explain the -2.4147% net result. There was no missing stop, pending order or armed-profit loss. Raising the profit floor would not affect this trade because it never armed.

Four consecutive losses now trigger the twelve-hour global pause until October 7 23:03:59. Subsequent defensive BTC conditions also block entries. The latest empty buy list reflects intentional risk controls, not a stalled process.

### Repeated losses and longer ticker pauses

SOL has now lost on all three current-version trades. To investigate the repeated reentry, chronological fixed-entry selection was repeated on eighteen completed entries with recorded signals passing current numeric gates. With the existing three-hour global and twelve-hour streak pauses, the twelve-hour ticker pause retains all eighteen and nets +KRW 576.30. An eighteen-hour ticker pause retains sixteen and nets +KRW 818.70: it removes today's -KRW 350.46 SOL loss but also the October 1 ETH trade that later earned +KRW 108.06. A twenty-four-hour pause instead nets +KRW 589.34: it removes the earlier -KRW 121.10 SOL trade and that same ETH winner, but then permits today's -KRW 350.46 SOL loss because the skipped earlier loss no longer starts a pause.

These are selected-loss chronological diagnostics, not portfolio simulations: original quantities/exits are fixed, rejected historical entries and alternative purchases are not replayed, and capital reuse is excluded. The threshold results change which later loss starts the next pause. Choosing eighteen hours solely because it maximizes this observed sample would tune to today's known loss. The modest twenty-four-hour result and lost ETH winner do not establish a reliable improvement. Keep the twelve-hour ticker pause; track whether repeated same-ticker losses persist after valid reentries.

### Forward signals and exit alternatives

The retained journal contains **1,607 observations**, September 21 13:31:38 through October 8 05:46:33. Coverage start is unchanged from yesterday; there is no additional historical-path loss in this snapshot. Reapplying the prior 78 RSI source gate/scoring, current other filters, recorded cycle thresholds and a common six-hour spacing per ticker yields **21 numeric opportunities** since October 1 deployment, versus yesterday's 20. The only new spaced signal is the actual SOL entry. Its one/three/six-hour observed price changes were -0.2439%/-0.4268%/-2.1341%, excluding fees, execution and capital constraints. No further spaced opportunity was found during the new loss pause. These signals are not automatically executable alternative trades.

The two common-sample RSI-only blocked BTC signals remain unchanged: October 1 had negative one/three/six-hour paths (-0.3421%/-0.5149%/-0.1545%); October 5 had positive paths (+0.1118%/+0.5091%/+0.4850%). Each horizon uses the nearest same-ticker observation within 120 seconds of the signal's observed time plus the horizon. This mixed evidence does not support changing the 75 ceiling.

Of the eighteen completed current-gate entries, four still lack holding paths after earlier rotation. On the **same fourteen observable entries**, fixed-entry actual PnL is **-KRW 319.36**, trend-memory PnL **-KRW 236.82**, and price-only half-peak-trail PnL **-KRW 487.22**. The post-September-24 twelve-entry subgroup is actual -KRW 1,179.83 versus price trail -KRW 971.79; all eight current-version trades remain -KRW 831.14 under either alternative. Compared with yesterday's thirteen-path sample, the only added path is today's SOL loss. Sparse fifteen-minute observations cannot reproduce minute-level peaks/stops; estimated earlier fills include fees and adverse slippage. These remain retrospective diagnostics, not independent validation or evidence of future profitability.

## Decision and validation

**Keep trading source and configuration unchanged.** Forward losses have worsened and SOL repeat losses warrant continued attention, but entry/cooldown/stop execution matches intended behavior. The checked alternatives do not provide sufficient evidence for another threshold. Preserve hard stops, profit memory and the RSI gate.

All **105 local tests passed** from an isolated temporary source copy with socket connections blocked. Private VM snapshots and credentials are not committed. Only this review and `HARNESS.md` change; publish and fast-forward them on the VM. The unchanged trading process needs no restart or image rebuild.

Next review should prioritize additional repeated ticker losses, new current-version completed trades, RSI-only opportunities, armed-profit losses and stop trigger/fill differences. Preserve the cash baseline above, record observation coverage, and separate account flows, unrealized marks and realized trade returns.
