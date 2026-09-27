# Strategy Review — 2026-09-28

## Production status

- The GCP VM and `quant-ai-bot` container were inspected directly at 06:01–06:04 KST.
- The container had run continuously since 2026-09-27 06:07:51 KST with zero restarts and no OOM kill. The 06:00 cycle completed successfully at 06:01:38 KST; consecutive cycle failures, risk-check failures, and pending orders were all zero.
- Timestamp-aware parsing found 1,966 INFO records and no warning or error records since the prior review. Dashboard publishing and bot-user GitHub SSH access were healthy at revision `93c051b`.
- The Upbit account held KRW 44,687.13119369 and 0.0001289 BTC, with no locked balance or open orders. At the 06:02 BTC quote of KRW 114,691,000, the account's marked value was about KRW 59,470.80. The BTC position's estimated liquidation PnL, including its paid buy fee and an assumed 0.05% sell fee, was about -82.88 KRW (-0.558%).

## Performance since the prior review

- ETH closed at 01:46 KST for -131.70 KRW (-0.8868%), including 14.79 KRW of buy and sell fees. It entered with ATR 3.25% and completed-candle six-hour momentum of 0.38%, then exited after simultaneous 15-minute and one-hour trend damage.
- Lifetime realized performance is 79 sells, 25 wins, 54 losses, -5,298.64 KRW, profit factor 0.6697, and 1,268.25 KRW of recorded fees.
- The `2026-09-27-atr-five-percent-gate` version has one completed loss and one open BTC position. This is too small to retune the ATR ceiling or exit rules by itself.
- The latest four realized results are losses. The existing three-loss circuit breaker correctly renewed a twelve-hour entry pause after the ETH loss, while the BTC holding continues to be monitored and managed normally.

## ATR gate follow-up

- Across actual entries since September 9, ATR at or below 5% now has 12 completed exits: 6 wins, 6 losses, +870.41 KRW, and profit factor 1.7732. The new ETH loss reduced but did not reverse the lower-ATR sample's positive result.
- Since the prior review, 28 recorded 5–6% ATR rejection rows produced six opportunities after six-hour-per-ticker deduplication. All six had a three-hour observation, with a -0.774% mean and -0.376% median. Four had a six-hour observation; all four were negative, with a -1.284% mean and -1.413% median.
- ATR is evaluated before later hard filters, so most of those six rejected observations would also have failed Bollinger or intraday-trend checks. Only the first DOGE observation passed the other hard filters, and all portfolio slots were occupied then. These returns are directional evidence, not saved executable PnL. They do not support relaxing the 5% ATR ceiling.

## Six-hour momentum diagnostic

- Within the 12 actual ATR-at-or-below-5% exits, the four entries whose completed-candle six-hour return was below 0.5% all lost, totaling -692.29 KRW. The eight entries at or above 0.5% produced 6 wins, 2 losses, +1,562.70 KRW, and profit factor 4.6058.
- As a separate opportunity check, actual plan BUY signals with ATR at or below 5% were deduplicated by ticker over six hours. All 18 opportunities had both three-hour and six-hour follow-up observations.
- At the three-hour horizon, the ten signals with entry momentum at or above 0.5% averaged +0.076% with a +0.042% median; the eight lower-momentum signals averaged -0.130% with a -0.126% median.
- At the six-hour horizon, the higher-momentum group averaged +0.865% with a +0.675% median and only 2 of 10 observations negative. The lower-momentum group averaged -0.470% with a -0.164% median and 7 of 8 observations negative.
- The opportunity sample is not a portfolio backtest: it does not reconstruct replacement entries, slippage, capital reuse, or alternative exits. The realized and observation samples are both small and partly reuse the same market period, so the filter's forward improvement remains unproven.

## Decision

- Add an entry-only `MIN_ENTRY_CHANGE_6H_PCT` hard gate with a default of `0.5%` and publish strategy version `2026-09-28-six-hour-momentum-gate`.
- Keep the 5% ATR ceiling, position sizing, cooldowns, hard stop, and all holding/exit rules unchanged. The open BTC position is not force-sold by the new rule.
- Record the new threshold in private observations and confirmed-entry context so its future outcomes can be audited directly.
- The next review should compare completed trades under the new version with rejected sub-0.5% candidates and should not tighten the threshold again until additional forward samples accumulate.
