# Strategy Review — 2026-09-26

## Production status

- The GCP VM and `quant-ai-bot` container were inspected directly at 06:02–06:04 KST.
- The container has run continuously since 2026-09-24 06:15:48 KST with zero restarts and no OOM kill. The 06:00 cycle completed successfully at 06:01:38 KST, consecutive cycle failures and risk-check failures were zero, and there were no pending orders.
- Since the prior review, 96 observation cycles completed. The Docker log contained no errors and one expected warning when a realized loss activated the cross-ticker cooldown. Dashboard publishing had no recorded failure.
- The Upbit account held KRW 45,112.99529562 and 112.33026315 DOGE, with no locked balance or open orders. DOGE was bought at an average price of KRW 133 and was also quoted at KRW 133 during the review, so the open position was approximately flat before fees.

## Performance since the prior review

- Two positions closed after the prior review:
  - SOL: +209.15 KRW (+1.4014%), exited by the 1.5% profit-protection rule after the 15-minute trend weakened.
  - ETH: -124.65 KRW (-0.8351%), exited after simultaneous 15-minute and 1-hour trend damage.
- Period realized total: 1 win, 1 loss, +84.50 KRW, including 29.89 KRW of buy and sell fees.
- Lifetime realized total: 76 sells, 25 wins, 51 losses, -4,784.54 KRW, profit factor 0.6919, and 1,223.76 KRW of recorded fees.
- The prior seven-loss streak pause expired as designed. New entries resumed at 08:46 and 09:01 KST, more than twelve hours after the prior 20:01 loss; those two completed positions produced the positive period total above. The later ETH loss activated the ordinary three-hour cooldown, and the next entry was DOGE at 05:01 KST.

## ATR gate review

- Four positions opened under strategy version `2026-09-24-atr-volatility-gate` have closed: one win, three losses, -351.44 KRW, profit factor 0.3731. This remains too small an out-of-sample set for another threshold change.
- Across actual entries since September 9, ATR at or below 6% produced 17 exits, 9 wins, 8 losses, +503.70 KRW, and profit factor 1.2509. ATR above 6% produced 11 losses from 11 exits and -4,017.02 KRW.
- The 5–6% ATR band produced -498.41 KRW across six historical exits, but all six came from earlier strategy versions. Tightening the live ceiling to 5% from this small reused sample would be overfitting. The current open DOGE entry has ATR 5.91%, so changing the threshold now would also be a reaction to an unresolved position rather than a completed outcome.
- Since the prior review, the journal contained 218 ATR-rejection rows. Six-hour-per-ticker deduplication produced 28 opportunities; 24 had a three-hour observation and 22 had a six-hour observation. The three-hour average return was -0.047% with a -0.337% median and 14 negative observations. The six-hour average was +0.598%, but its median was -0.613% and 12 observations were negative; the average was skewed by a few large rebounds, led by ARK (+11.72%) and SUI (+10.94%). This does not establish that relaxing the gate would improve executable PnL.

## Decision

- Keep the live trading rules unchanged. The twelve-hour streak cooldown resumed trading correctly and the first two completed trades after it were net profitable. The current ATR gate still has strong realized-loss evidence above 6%, while the new-strategy sample is too small to justify tightening or relaxing it.
- Continue collecting post-gate outcomes. The next review should evaluate the open DOGE result, compare the completed 5–6% ATR entries with lower-ATR entries, and keep reporting both mean and median forward returns for rejected candidates so outliers do not dominate the conclusion.
- No runtime source, dependency, or environment setting changed in this review, so a container restart is neither required nor desirable. The review document may be synchronized to the VM without interrupting the live process.
