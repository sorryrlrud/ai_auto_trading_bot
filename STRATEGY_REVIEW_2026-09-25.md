# Strategy Review — 2026-09-25

## Production status

- The GCP VM and `quant-ai-bot` container were inspected directly at 06:01–06:05 KST.
- The container was running with zero restarts, no OOM kill, zero consecutive cycle failures, zero risk-check failures, and zero pending orders.
- The 06:00 cycle completed successfully at 06:01:34 KST. The next cycle was scheduled for 06:15:20 KST.
- The Upbit account held only KRW 59,975.8957856, with no locked balance or open orders.
- No error, warning, or critical log records occurred after the prior review. Dashboard heartbeat commits continued to advance `main`, so the earlier one-off SSH publishing failure did not recur.

## Performance since the prior review

- Two new positions were opened under strategy version `2026-09-24-atr-volatility-gate` and both closed at a loss:
  - SOL: -262.04 KRW (-1.7428%), exited after simultaneous 15-minute and 1-hour trend damage.
  - ETH: -173.90 KRW (-1.1570%), exited for the same condition.
- Period total: 0 wins, 2 losses, -435.94 KRW, including 29.84 KRW of buy and sell fees.
- Lifetime realized total: 74 sells, 24 wins, 50 losses, -4,869.04 KRW, profit factor 0.6839.
- The latest realized sequence is seven consecutive losses. The existing three-loss circuit breaker is therefore applying a 12-hour portfolio-wide entry pause after the ETH exit, until approximately 08:01 KST on 2026-09-25. Holding management and risk checks remain active.

## ATR gate review

- Both new losses had entry ATR below the new 6% ceiling (SOL 4.30%, ETH 3.65%). They are evidence that the gate cannot eliminate ordinary signal failure, but two post-change exits are too small a sample for another threshold change.
- In the fixed historical sample since September 9, entries with ATR at or below 6% still produced +419.20 KRW across 15 exits (8 wins, 7 losses). This is a selection diagnostic, not a portfolio backtest.
- Since the prior review, 6-hour-per-ticker deduplication produced 15 ATR-rejected opportunities with observable 3-hour and 6-hour forward prices. Their average forward returns were -1.045% and -1.056%, respectively; 11 of 15 were negative at both horizons.
- The journal recorded 93 ATR rejections across 95 completed cycles. The gate is active and is filtering the intended high-volatility population.

## Decision

- Keep the live trading rules unchanged. Adding a BTC-RSI or 6-hour-momentum gate from only the two new losses would be overfitting, and the current loss-streak pause is already preventing immediate re-entry.
- Reassess after more ATR-compliant completed trades accumulate. Compare post-gate realized results separately and continue tracking the forward returns of rejected opportunities.
- Isolate the buy-execution unit test from production `trade_history.json`. The test previously inherited the live loss cooldown and failed on the VM even though it uses a fake Upbit client; mocking recent performance makes the test deterministic without changing runtime behavior.
