# Strategy cycle review — 2026-09-30

## Production evidence

The GCP VM was inspected directly from 06:51 KST. The bot used a 900-second candle cycle with a 20-second close buffer and a 60-second hard-stop monitor. The container had zero restarts, no OOM event, zero cycle/risk failures, and zero pending orders. The latest observation contained no coin holdings. VM checkout was `06ce166` at the initial inspection.

The private VM snapshot contains 2,002 cycle observations from September 9 11:59 to September 30 06:46 KST. Explicit SELL history has 82 exits, 25 wins, 57 losses, and net realized PnL of **-KRW 5,905.30**. The latest seven exits lost money. Current entry rules have only two completed forward trades, LINK and ETH; this is insufficient evidence to optimize more entry thresholds.

## Finding and selected change

The old profit-protection rule required both current gross profit of at least 1.2% and a complete 15-minute trend break at the same cycle. It forgot that the position had previously crossed 1.2%. If profit dropped below that level before all three trend conditions broke, it reverted to the broader loss exits. ADA, DOGE and ETH from September 26–29 illustrate this mismatch.

Strategy `2026-09-30-profit-protection-memory` persists the highest actually observed price at the existing 60-second risk checks and at the post-scan holding refresh. Once gross return has reached the existing 1.2% threshold, a completed 15-minute trend break can exit even after profit drops below the threshold. Trend damage still requires price below MA20, MA5 below MA20, and negative MACD histogram together. The existing minimum-hold exception for profit protection is retained. Strong trends are not exited merely for retracing a price threshold.

No new entry threshold, position size, cooldown, stop-loss level, or cycle duration was optimized. Peaks survive restarts and partial sells, reset if average cost changes, and clear on a new buy or full exit. They are attached to private realized records for later review. Estimated net return in exit reasons includes recorded buy fees and an estimated 0.05% sell fee; realized PnL remains based on confirmed fills and actual fees.

## Fixed-entry exit diagnostic

`review_exit_paths.py` compares original exits with earlier exits at observed holding prices. It includes known buy fees, an estimated 0.05% sell fee, and an adverse 0.1% execution-price allowance. Original fills are retained when the old strategy exits on the same snapshot. Forty-eight older exits lack explicit entry timestamps and are excluded; the remaining 34 have observed paths, with a maximum observation gap of 911 seconds. There are no duplicated partial entries in this sample.

| Sample | Exits | Original net PnL | Selected rule diagnostic | Wins, original → candidate |
| --- | ---: | ---: | ---: | ---: |
| All comparable paths | 34 | -KRW 4,634.08 | -KRW 3,442.79 | 9 → 9 |
| Entries before September 24 | 24 | -KRW 3,161.88 | -KRW 2,290.56 | 8 → 8 |
| Entries from September 24 | 10 | -KRW 1,472.20 | -KRW 1,152.23 | 1 → 1 |
| Historical entries passing current numeric gates and recorded score threshold | 9 | +KRW 1,482.34 | +KRW 1,564.88 | 6 → 6 |

The selected rule changes seven historical exits, all losses, and leaves the nine winners' observed exits unchanged. It reduces losses in this diagnostic; **it does not establish an improved win rate, positive overall expectancy, or maximum profit**. Of the nine current-gate historical entries, only ETH's exit changes. That incremental evidence is particularly small.

The current-gate subset was obtained by applying `entry_block_reason` to each trade's recorded entry signal/market context and requiring the recorded score to meet its recorded buy threshold. It does not replay portfolio cooldowns or alternate capital allocation.

## Rejected alternative

A price-only trail, armed at the same 1.2% gross gain and exiting at half the highest estimated net return (minimum 0.2%), improved the broad 34-trade diagnostic to -KRW 3,061.85 and 15 wins. However, among the nine entries passing current gates it reduced net PnL from +KRW 1,482.34 to +KRW 832.94, cutting several recoveries. That rule was rejected despite its attractive all-history win rate. Its diagnostic remains available as `--mode price_trail`; it is not used by the live strategy.

## Limits and verification

This is a retrospective fixed-entry diagnostic, not a portfolio backtest or an untouched holdout. Changed exit times alter cooldowns, replacement entries and cash reuse in live operation. Fifteen-minute snapshots cannot reproduce the new monitor's 60-second observed peaks, intraperiod price gaps or actual execution. The chronological split is descriptive; both periods were available during review. All-history loss reductions do not prove incremental performance for the current entry filters.

The local suite passed 103 tests covering both earlier safeguards and profit-memory behavior, trend confirmation, gap losses, restarts, partial fills, new entries, actual fee accounting, dry-run isolation and diagnostic lookahead exclusions. Deployment verification is recorded below after the VM rollout.
