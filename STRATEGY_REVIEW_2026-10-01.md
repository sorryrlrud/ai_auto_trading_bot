# Strategy Review — 2026-10-01

## Production status

- The GCP VM and `quant-ai-bot` container were inspected directly at 06:02–06:04 KST. The container had been up for about 23 hours with zero restarts and no OOM event.
- The 06:00 cycle completed at 06:01:32 KST and the 60-second risk check completed at 06:03:15 KST. Consecutive cycle failures, risk-check failures, and pending orders were all zero.
- Since the prior review, the container emitted 1,940 INFO records and no warning, error, or critical records.
- Upbit reported only KRW 58,520.60233029, with no locked balance, coin holding, or open order. The four new closed orders independently confirmed both buys and both completed market sells.

## Performance since the prior review

- SOL entered at 22:01 KST and hit the 60-second hard stop at 23:23 KST. Realized PnL was -KRW 344.13 (-2.3401%) after KRW 14.53 of buy and sell fees.
- ETH entered at 21:01 KST, reached an observed peak of KRW 3,705,000 from a KRW 3,649,000 average cost, then exited at 23:46 KST after the armed profit-memory rule saw a completed 15-minute trend break. Realized PnL was -KRW 74.90 (-0.5106%) after KRW 14.63 of fees.
- The two exits lost KRW 419.03 in total. Lifetime explicit SELL history is now 84 exits, 25 wins, 59 losses, -KRW 6,324.33, profit factor 0.6295, and KRW 1,341.54 of recorded fees.
- Cash fell by KRW 419.03 (-0.711%) from the prior review's KRW 58,939.62998577. The equality with realized PnL is consistent with an all-cash account and no intervening deposit or withdrawal, but the balance comparison is not a general substitute for realized-history accounting.

## Entry diagnostic and selected change

SOL's completed entry candle had 15-minute RSI 75.64, 15-minute volume ratio 5.02, one-hour volume ratio 5.20, and a one-hour move of +2.04%. The old hard overheat ceiling was 78 on the 15-minute timeframe, even though the one-hour ceiling was already 75.

The private observation journal was replayed with the current ATR, Bollinger, momentum, trend and score rules. Opportunities were spaced by the existing six-hour ticker cooldown and required observations near one, three and six hours later. This produced 37 comparable opportunities:

| Entry subset | Opportunities | 1h average | 3h average | 6h average | Positive at 6h |
| --- | ---: | ---: | ---: | ---: | ---: |
| All current-rule opportunities | 37 | +0.175% | +0.324% | +0.369% | 17 |
| 15m RSI above 75 | 3 | -0.839% | -0.749% | -1.743% | 0 |
| 15m RSI 72–75 | 2 | +0.086% | -0.228% | -0.202% | 1 |
| 15m RSI at or below 72 | 32 | +0.276% | +0.459% | +0.602% | 16 |

The three above-75 cases were two independently spaced SOL opportunities and one BTC opportunity. All three were negative after three and six hours. The realized-entry sample contains only one trade above 75—the latest SOL loss—so the opportunity result remains small and descriptive rather than an out-of-sample proof.

Strategy `2026-10-01-15m-rsi-overheat-gate` changes only the entry hard filter: a completed-candle 15-minute RSI above `MAX_ENTRY_15M_RSI` (default `75.0`) is rejected as overheated. The boundary itself remains eligible. This aligns the fast timeframe with the existing one-hour ceiling and would have blocked the latest SOL entry. Position sizing, cooldowns, loss controls, stop loss, profit protection, and all existing holding management are unchanged.

The offline realized-entry review now records the 15-minute RSI gate separately and includes it in the combined safeguard diagnostic. Entry context and private observations persist the configured limit for later attribution.

## Exit review and rejected change

The first live use of persistent profit memory exposed its deliberate tradeoff: ETH had crossed the 1.2% gross arming level but surrendered the gain before the completed 15-minute trend break. A price-only trail would have ended that observed path earlier and likely avoided this loss.

The broader evidence still does not justify replacing trend confirmation. Across 36 comparable paths, the half-peak price trail improved the broad historical diagnostic from -KRW 5,053.11 to -KRW 3,391.16. But among 11 realized entries passing today's numeric gates and recorded score threshold, it reduced fixed-entry net PnL from +KRW 1,063.31 to +KRW 503.63 by cutting several profitable recoveries. The current trend-memory diagnostic was +KRW 1,145.85 on that same subset. Therefore the price-only trail remains rejected; ETH is retained as forward evidence for the next review rather than used to reverse yesterday's deliberately selected exit behavior after one trade.

## Limits and verification

- Opportunity returns use observed cycle prices, not executable fills, and do not replay portfolio cash, replacement trades, or changed cooldown paths.
- The six-hour spacing reduces repeated signals but does not make the sample independent or untouched. All three above-75 cases were visible when selecting the threshold.
- Fixed-entry exit diagnostics use sparse 15-minute observations and cannot reproduce the live 60-second peak monitor or intraperiod gaps.
- Local and isolated VM suites each passed 105 tests. The VM suite ran from a temporary source copy, preserving live runtime files and avoiding synthetic test logs in production.

## Deployment

- Source revision: `2030511`; backup: `/home/sorryrlrud/bot-backup-20261001-dwYmDO`. No dependency or image rebuild was needed. Runtime state and history were preserved.
- The container started at 06:10:59 KST with zero restarts and no OOM event. Local, VM and container `autotrade.py` SHA-256 was `67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081`.
- Startup logged strategy `2026-10-01-15m-rsi-overheat-gate` and `max_entry_15m_rsi=75.0`. The first risk check had zero holdings, stops, and pending orders.
- The first live cycle completed at 06:12:17 KST with zero cycle/risk failures and zero pending orders. Its private observation recorded `max_15m_rsi=75.0`; the existing nine-loss streak correctly blocked new entries for twelve hours, so no verification order was submitted.
- Automatic dashboard commit `91afa8d` was pushed. The public GitHub Pages endpoint returned HTTP 200 with generation time 06:12:17 KST, the new strategy version, and the loss-streak entry-block reason. Bot-user GitHub access and a host-side fast-forward pull both succeeded.
