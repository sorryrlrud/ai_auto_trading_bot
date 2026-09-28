# Strategy Review — 2026-09-29

## Production status

- The GCP VM and `quant-ai-bot` container were inspected directly at 06:01–06:07 KST.
- The container started at 2026-09-28 06:11:36 KST and remained running with zero restarts and no OOM kill. The 06:00 cycle completed successfully at 06:01:36 KST; consecutive cycle failures, risk-check failures, and pending orders were all zero.
- Timestamp-aware parsing found 2,679 INFO records and no warning or error records since the prior review. The VM checkout and GitHub `main` both pointed to dashboard revision `3c35bff`.
- The Upbit account had KRW 44,295.01253748 and 0.00405534 ETH, with no locked balance or open orders. At the 06:02 ETH quote of KRW 3,653,000, the marked account value was about KRW 59,109.17.
- The ETH position's estimated liquidation PnL, including its recorded KRW 7.39 buy fee and an assumed 0.05% sell fee, was about +KRW 17.64 (+0.119%).

## Performance since the prior review

- BTC closed at 07:46 KST for -KRW 123.72 (-0.8326%). Its entry used the prior strategy and had completed-candle six-hour momentum of 0.17%, so the current 0.5% floor would have blocked it.
- LINK closed at 00:17 KST for -KRW 338.45 (-2.2905%) after the always-on hard stop. It was the first completed trade entered under `2026-09-28-six-hour-momentum-gate`.
- The review period therefore had two sells, zero wins, -KRW 462.17 net realized PnL, and KRW 29.41 of fees.
- Lifetime realized performance is 81 sells, 25 wins, 56 losses, -KRW 5,760.81, profit factor 0.6510, and KRW 1,297.66 of recorded fees.
- The marked account value was about KRW 361.63 (-0.608%) below the prior review's KRW 59,470.80, assuming there were no deposits or withdrawals. This comparison includes the open ETH position and is not the same as realized PnL.
- The latest six realized sells are losses. The existing three-loss circuit breaker correctly blocks new entries for twelve hours after the LINK exit while the open ETH position continues to be managed.

## Six-hour momentum follow-up

- LINK entered with six-hour momentum of +7.42%, ATR of 4.99%, and daily Bollinger position of 1.04. It passed the current floor and the existing ATR, Bollinger, trend, RSI, and short-term chase checks.
- Replaying the current hard filters and score threshold over the private observation journal produced 20 opportunities after six-hour-per-ticker deduplication. LINK was the only opportunity with six-hour momentum at or above 4%.
- Although LINK was stopped after about one hour, its observed price was +5.30% from entry after three hours and +5.91% after six hours. A new maximum six-hour-momentum gate would therefore be based on one contradictory case and could remove a subsequently profitable move.
- Older realized trades with six-hour momentum above 4% were all losses, but all except LINK fail at least one current hard filter. They are not comparable forward evidence for the deployed rule set.

## Hard-stop follow-up

- Since September 9, the 15 always-on hard-stop exits realized -KRW 5,554.95 in total.
- Using later private observations without replaying fees, slippage, or intra-period risk, holding those positions until three hours after the actual exit would have left the entry-price return at a -2.228% mean and -1.701% median; only 3 of 15 were positive.
- At six hours, 14 positions had observations. The entry-price return averaged -3.081%, had a -2.788% median, and only 3 were positive.
- LINK was an unusually sharp rebound, but the broader sample still supports retaining the hard stop. Loosening it from one rebound would materially increase downside exposure without consistent evidence of better outcomes.

## Decision

- Keep the live entry filters, 5% ATR ceiling, 0.5% six-hour momentum floor, position sizing, cooldowns, and all exit rules unchanged.
- Do not add an upper six-hour-momentum bound and do not loosen the hard stop from the single completed forward trade under the new strategy.
- The local unit suite passed all 83 tests. Because no runtime source or configuration changed, no container rebuild or restart was performed.
- The next review should separate completed entries under `2026-09-28-six-hour-momentum-gate` from prior-rule positions and continue tracking high-six-hour-momentum candidates and post-stop paths before changing either guardrail.
