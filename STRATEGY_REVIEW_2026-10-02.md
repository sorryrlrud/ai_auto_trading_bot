# Strategy Review — 2026-10-02

## Production verification

The GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` were inspected directly from 06:02 KST. The container remained running from October 1 06:10:59, with zero restarts and no OOM event. The 06:00 cycle completed at 06:01:42, and the risk monitor advanced to 06:05:03 with zero cycle failures, risk failures, or pending orders. The old September 7 error timestamp is historical, not an active failure.

The downloaded VM log contained 1,967 INFO records and no WARNING, ERROR, or CRITICAL records since the prior review at October 1 06:13:58. The VM disk was 32% used; available host memory was 462 MiB and container memory about 89 MiB. Docker init and Python were running with no zombie process shown. VM and container `autotrade.py` hashes matched the October 1 deployment (`67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081`).

Bot-user GitHub SSH access succeeded, and VM HEAD had no unpublished commits. Public GitHub Pages returned HTTP 200, a 06:01:42 generation time, three decision snapshots, and no private entry context.

## Performance and cash reconciliation

There were no new realized sells. Lifetime explicit SELL history remains 84 exits, 25 wins, 59 losses, net PnL **-KRW 6,324.33**, profit factor 0.6295, and recorded fees KRW 1,341.54. The current strategy has two open positions and no completed forward trade.

Upbit CLI queries were executed using the VM's production credentials on the VM. Accounts and closed orders independently confirmed:

- KRW cash: 29,523.92196437, with zero locked balance.
- ETH: 0.00397324, bought October 1 14:01:35 at average KRW 3,681,000; actual funds KRW 14,625.49644 and paid buy fee KRW 7.31274822.
- BTC: 0.00012782, bought October 1 15:31:38 at average KRW 114,470,000; actual funds KRW 14,631.5554 and paid buy fee KRW 7.3157777.
- Neither waiting nor reserved open orders were returned. Both market buys are terminal `cancel` records with confirmed fills; their quantities, funds, fees and UUIDs agree with bot state. The terminal state must not be interpreted as an unfilled buy. Order semantics are documented in [Upbit's order reference](https://docs.upbit.com/kr/reference/get-order).

The apparent increase in account value includes an accepted **KRW 275 deposit at October 1 11:46:30**. VM observations independently show cash moving from 58,520.60233029 to 58,795.60233029 before either buy. No recent KRW withdrawal was present. Subtracting both actual purchase amounts and fees from that adjusted cash exactly reproduces current cash.

At the VM's 06:04:30 quotes (BTC KRW 115,054,000; ETH KRW 3,670,000), marked account value was KRW 58,811.92. Its raw increase from the prior all-cash snapshot was KRW 291.31 (+0.498%). Excluding the KRW 275 deposit gives a simple flow-adjusted mark change of **KRW 16.31 (+0.0279%)** relative to the starting value. This is a snapshot comparison, not a time-weighted or money-weighted return.

Estimated liquidation PnL includes recorded buy fees and an assumed 0.05% sell fee:

| Position | Estimated net PnL | Estimated net return |
| --- | ---: | ---: |
| BTC | +KRW 59.98 | +0.4097% |
| ETH | -KRW 58.31 | -0.3985% |
| Total open positions | +KRW 1.67 | — |

These estimates are not realized fills and exclude any future slippage. At the latest completed cycle, BTC and ETH were both HOLD. Persisted peaks imply gross gains of 1.1558% and 0.3532%, respectively; neither had reached the 1.2% profit-protection arming threshold.

## Algorithm review and decision

The September reviews successively introduced confirmed-order recovery, continuous hard stops, loss and same-ticker cooldowns, loss-streak and Bollinger brakes, a 5% ATR ceiling, and a 0.5% six-hour momentum floor. The September 30 cycle review added persistent profit memory while deliberately retaining completed 15-minute trend confirmation. October 1 added the 75 RSI ceiling after a SOL stop and three negative above-75 opportunity paths. The prior review rejected a price-only trail because it cut profitable recoveries among historical entries passing current gates.

The current private observation rotation retains 1,631 snapshots from September 15 08:16:37 through October 2 06:01:42. Earlier snapshots used in past reviews have rotated out, so this window must not be treated as an unchanged all-history sample.

For forward entry review, observations after October 1 deployment were checked against the prior 78 RSI ceiling and otherwise-current numeric/trend rules and recorded score threshold. Opportunities were spaced six hours per ticker using the common prior-rule sample, then classified by the new RSI ceiling. Prices near one, three and six hours were matched within 20 minutes, with no future observations substituted before a horizon matured.

| Common-sample opportunity | 15m RSI | 1h observed return | 3h observed return | 6h observed return |
| --- | ---: | ---: | ---: | ---: |
| ETH, October 1 11:00 | 56.44 | -0.0546% | +0.5191% | -0.2459% |
| BTC, October 1 15:00, RSI-blocked | 76.66 | -0.3421% | -0.5149% | -0.1545% |
| BTC, October 1 23:30 | 63.73 | -0.0576% | +0.7412% | +0.5354% |

The RSI-only blocked BTC opportunity was negative at all three horizons. This is one additional forward observation, not proof of improved expectancy. The ETH opportunity occurred during the global loss-streak pause; the later BTC opportunity was already held. These are numeric signal paths, not executable replacement trades. Common-sample six-hour spacing also omits the actual later ETH/BTC entry times from the table. Cash, holdings, fees, alternate exits and altered cooldowns are not replayed.

There is no new armed-profit-loss exit and no completed current-version trade. Keep entry thresholds, position sizes, loss controls, hard stops, profit protection and cycle timing unchanged. Changing these on two open positions and one blocked opportunity would add unsupported tuning. The next review should separate completed October 1 strategy trades, follow RSI-blocked opportunities, and watch whether armed positions repeatedly surrender gains before trend confirmation.

## Selected reporting correction

The dashboard's `total_return_pct` is realized net PnL divided by the sum of completed trades' purchase amounts and buy fees. Reused capital appears repeatedly in this denominator; deposits and open positions are excluded. Its current -0.4703% is therefore not the account's cumulative investment return.

Rename the visible card from `누적 수익률` to `실현 거래 수익률`, and add the denominator and exclusions beside the statistics. Keep the existing data field and calculation for compatibility. This makes the metric interpretable without exposing private holdings or account flows. No trading strategy or dependency changes are required.

## Validation

The local suite passed all 105 tests. A dashboard generated from the private VM snapshot preserved 84 exits, -KRW 6,324.33, -0.4703%, and three recent decisions, while showing the corrected wording and excluding private entry context. The reporting-only change is deployed by updating the bind-mounted generator and publishing a freshly generated dashboard; the already-running bot does not need a restart.
