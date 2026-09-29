# Strategy Review — 2026-09-30

## Production status

- The GCP VM and `quant-ai-bot` container were inspected directly at 06:01–06:05 KST.
- The container had remained up since 2026-09-28 06:11:36 KST with zero restarts and no OOM kill. The 06:00 cycle completed successfully at 06:01:36 KST; consecutive cycle failures, risk-check failures, and pending orders were all zero.
- Timestamp-aware parsing found 1,914 INFO records and no warning, error, or critical records since the prior review. The VM checkout, GitHub `main`, and the container's Git remote all resolved to dashboard revision `26d7692`.
- The Upbit account held only KRW 58,939.62998577, with no locked balance, coin holdings, or open orders. The exchange's closed-order record independently confirmed the latest ETH market sell as fully filled.

## Performance since the prior review

- ETH closed at 13:01 KST for -KRW 144.49 (-0.9770%), including KRW 14.72 of buy and sell fees. It entered under `2026-09-28-six-hour-momentum-gate` and exited after simultaneous 15-minute and one-hour trend damage.
- Lifetime realized performance is now 82 sells, 25 wins, 57 losses, -KRW 5,905.30, profit factor 0.6453, and KRW 1,312.38 of recorded fees.
- The account value fell by about KRW 169.54 (-0.287%) from the prior review's marked KRW 59,109.17 to the current cash balance, assuming no deposits or withdrawals. This marked-account comparison is not the same as realized PnL.
- The latest seven realized sells are losses. The twelve-hour three-loss circuit breaker blocked new entries through 01:01 KST and the bot currently has no position.

## Current-strategy evidence

- The deployed six-hour-momentum version now has two completed trades: LINK and ETH. Both lost, for -KRW 482.94 combined and KRW 29.33 of fees. Two trades are insufficient to identify a stable new threshold.
- Applying the current numeric entry gates to comparable historical executed entries yields nine completed trades: six wins, three losses, +KRW 1,482.34, and profit factor 3.885. This is a small, partly in-sample diagnostic rather than proof of future returns, but it does not support tightening the entry rules from the two newest losses alone.
- Since the prior review, three current-rule opportunities appeared while the loss-streak cooldown was active: ETH, BTC, and SOL. All three were positive after three hours, with a +0.416% mean and +0.397% median. After six hours, two were negative; the mean was -0.178% and the median was -0.163%.
- Two otherwise qualified opportunities were rejected only by the 0.5% six-hour-momentum floor. Both were negative after three and six hours; their mean returns were -0.978% and -0.676%, respectively. This small forward sample remains directionally consistent with keeping the floor.
- LINK and ETH both recovered after their realized exits. LINK was +5.30%/+5.91% from entry at three/six hours, and ETH was approximately +1.04% from entry six hours after its exit. The prior broader hard-stop diagnostic still showed negative three- and six-hour outcomes for most stopped positions, so these two rebounds do not justify weakening the hard stop or trend exit.

## Decision

- Keep the live 0.5% six-hour momentum floor, 5% ATR ceiling, score threshold, position sizing, cooldowns, and exit rules unchanged.
- Do not add an upper six-hour-momentum bound, shorten the loss-streak cooldown, or add a fixed holding-time exit from the current sample.
- The local unit suite passed all 83 tests. Because no runtime source or configuration changed, deployment only synchronizes this review and the harness verification date; the running container does not need a rebuild or restart.
- The next review should continue separating completed trades under `2026-09-28-six-hour-momentum-gate`, compare opportunities during cooldowns with executed trades, and revisit exit timing only after additional forward samples accumulate.
