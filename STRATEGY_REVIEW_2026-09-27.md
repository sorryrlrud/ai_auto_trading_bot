# Strategy Review — 2026-09-27

## Production status

- The GCP VM and `quant-ai-bot` container were inspected directly at 06:02–06:04 KST.
- The container has run continuously since 2026-09-24 06:15:48 KST with zero restarts and no OOM kill. The 06:00 cycle completed successfully at 06:01:33 KST, consecutive cycle failures and risk-check failures were zero, and there were no pending orders.
- Since the prior review, 96 observation cycles completed. Timestamp-aware log parsing found no errors or warnings. Dashboard publishing is current at remote revision `ca430b6`.
- The Upbit account held KRW 59,677.98877792 only, with no locked balance or open orders.

## Performance since the prior review

- Two positions closed after the prior review:
  - ADA: -142.91 KRW (-0.9562%), entered with ATR 5.41% and exited after simultaneous 15-minute and 1-hour trend damage.
  - DOGE: -239.49 KRW (-1.6022%), entered with ATR 5.91% and exited after simultaneous 15-minute and 1-hour trend damage.
- Period realized total: 0 wins, 2 losses, -382.40 KRW, including 29.70 KRW of buy and sell fees.
- Lifetime realized total: 78 sells, 25 wins, 53 losses, -5,166.94 KRW, profit factor 0.6753, and 1,253.46 KRW of recorded fees.
- The current `2026-09-24-atr-volatility-gate` version completed six positions: one win, five losses, -733.84 KRW, and profit factor 0.2218.

## ATR gate review

- Across actual entries since September 9, ATR at or below 5% produced 11 exits, 6 wins, 5 losses, +1,002.11 KRW, and profit factor 2.0082.
- The 5–6% ATR band produced 8 exits, 3 wins, 5 losses, -880.81 KRW, and profit factor 0.3691. Both entries in that band under the current strategy version lost: ADA at 5.41% and DOGE at 5.91%.
- ATR above 6% remained the clearest loss region: 11 losses from 11 exits and -4,017.02 KRW.
- Since the prior review, the journal contained 212 ATR-rejection rows above 6%. Six-hour-per-ticker deduplication produced 22 opportunities. Nineteen had a three-hour observation with a -0.117% mean and -0.337% median; thirteen had a six-hour observation with a +1.310% mean and 0.000% median. The divergent mean and median do not support relaxing the existing gate.
- Entry-qualified 5–6% candidates under the current strategy produced ten six-hour-deduplicated opportunities. Their observed three-hour mean/median was -0.006%/-0.144% across eight observations, and their six-hour mean/median was +0.028%/-0.288% across nine observations. This is near-flat opportunity performance with a negative median, while the completed executable trades in the same band lost money after fees.

## Decision

- Lower `MAX_ENTRY_ATR_PCT` from 6.0% to 5.0% and publish strategy version `2026-09-27-atr-five-percent-gate`. The change is entry-only and leaves all holding management, exit rules, risk checks, cooldowns, and position sizing unchanged.
- The change is supported by both the completed realized sample and the absence of a positive median in the entry-qualified observation sample. It also avoids adding a ticker-specific exception for the small profitable 5.5–6% subsample.
- Do not change exit rules from these two new losses. Both exited under the intended confirmation rule at modest pre-fee losses, and the current-strategy sample is still too small to distinguish exit timing from entry quality.
- The next review should compare completed entries at or below 5% under the new strategy version against the blocked 5–6% candidates, continuing to report both mean and median forward returns.
