# Strategy Review — 2026-10-04

## Production verification

The GCP VM `/home/sorryrlrud/ai_auto_trading_bot` and `quant-ai-bot` were checked directly from 06:01 KST. The container remains running from October 1 06:10:59 KST, with zero restarts and no OOM. The real cycle completed at 06:01:32; risk checks advanced to 06:05:41 with zero cycle failures, risk failures, or pending orders. The September 7 error timestamp is historical.

The VM disk is 32% used, available memory 456 MiB, and container memory 104 MiB. Docker init and Python are the only listed processes; no zombies were shown. VM and container hashes agree with the October 1 trading source (`67d5f857a082d30ee7f91d95d5767f4792c2fec54edf4ed8d6e2099721b29081`) and October 2 dashboard generator (`b9202da8e72f4c22656477ec007551000e46a2b9f883108d019d9a9e9617d855`). Bot-user GitHub SSH access succeeded, VM Git was clean, and no unpublished commits were observed.

Public GitHub Pages returned HTTP 200 with generation time 06:01:35, three decisions, the corrected realized-trade-return label, 87 exits, and no private entry context. Its cycle heartbeat agrees with the VM. No local Docker commands were used.

## Review windows and performance

Automation metadata says the previous run was October 3 12:12:01.508 KST, but persisted memory and source review reports end on October 2. These windows are reported separately rather than silently treating already-completed trades as new since the scheduled run.

- Since the scheduled previous run: **no new completed sell or buy**, realized PnL KRW 0. The VM snapshot has 1,428 INFO records and no WARNING/ERROR/CRITICAL records in this window.
- Since the last documented review at October 2 06:11:07: three completed sells, two wins and one loss, **+KRW 78.99** after KRW 44.04 recorded fees; 3,868 INFO records and no WARNING/ERROR/CRITICAL records.
- Lifetime explicit SELL history: **87 exits, 27 wins, 60 losses, -KRW 6,245.34**, 31.03% win rate, profit factor 0.6397, recorded fees KRW 1,385.58. Overall realized performance remains negative.

All three newer exits entered under `2026-10-01-15m-rsi-overheat-gate`:

| Entry / exit | Net realized PnL | Net trade return | Persisted peak gross return | Exit |
| --- | ---: | ---: | ---: | --- |
| BTC October 1 15:31 / October 2 16:01 | +KRW 234.88 | +1.6045% | +2.7745% | Current profit and completed 15-minute trend break |
| ETH October 1 14:01 / October 2 21:46 | +KRW 108.06 | +0.7385% | +1.6300% | Armed profit memory and completed 15-minute trend break |
| BTC October 2 22:16 / October 3 03:01 | -KRW 263.95 | -1.7935% | +0.3255% | Loss and combined 15-minute / one-hour trend damage |

The profitable BTC exit and later losing BTC entry are different positions. The second entry occurred more than six hours after the prior sell, satisfying the existing ticker cooldown. Its peak never armed profit memory. State contains no active entry/peak fields or pending orders after these full exits.

## Independent exchange reconciliation

Upbit CLI v0.9.1 ran on the VM with credentials loaded only into child-process environment variables. Accounts show **KRW 58,874.58949578**, zero locked balance, and no coin holding. Waiting and reserved order queries returned no open orders. Closed-order and individual-order queries confirmed all three full sells, the intervening BTC buy, quantities, fees, and order UUIDs. The latest market buy has terminal `cancel` state with a real fill; its fill was correctly preserved. Individual order verification follows [Upbit's official order API](https://docs.upbit.com/kr/reference/get-order); account verification follows [the official balance API](https://docs.upbit.com/kr/reference/get-balance).

The exchange's only deposit since October 1 is the already-documented accepted KRW 275 at October 1 11:46:30; there is no new deposit or withdrawal in the reviewed interval. Summing actual sell funds minus sell fees, entry amounts and entry fees gives precise net PnL **KRW 78.987165495**. Each recorded trade agrees within KRW 0.004 after display rounding. This reconciles October 1 cash KRW 58,520.60233029 + KRW 275 deposit + precise PnL to current cash within KRW 0.000000005.

Relative to the deposit-adjusted pre-entry all-cash value KRW 58,795.60233029, the simple account change is **+0.13434%**. It is not the return since the scheduled October 3 run or a time-weighted return. Relative to the October 2 marked snapshot KRW 58,811.92, current value increased about KRW 62.67 (+0.1066%); that comparison includes realization of positions already open in the earlier snapshot. Dashboard realized-trade return is -0.4497%, using repeatedly invested completed-trade purchase amounts and buy fees as its denominator, rather than initial account equity.

## Algorithm review and decision

Previous changes introduced confirmed order recovery and continuous hard stops; loss, ticker and loss-streak cooldowns; the Bollinger and 5% ATR ceilings; the 0.5% six-hour momentum floor; September 30 persistent profit memory; and October 1's 75 ceiling for completed 15-minute RSI. October 2 corrected reporting terminology. The current snapshot contains 1,823 private cycle observations from September 15 08:16:37 through October 4 06:01:32. Older data rotated out, so historical sample counts cannot be compared directly with earlier reviews.

The latest normal-mode cycle holds cash because candidates fail ATR or six-hour momentum gates, rather than an active global loss pause. For example, ETH six-hour momentum is +0.14%, below +0.5%, while ONDO ATR is 10.17%, above 5%. This matches the source's filters and current recorded inputs. There has been no executable BUY plan since the latest BTC loss.

Using the prior 78 RSI ceiling with the other current numeric/trend filters and the source score threshold, then spacing common-sample opportunities six hours per ticker, yields nine forward numeric opportunities since deployment. Only the previously reported October 1 15:00 BTC signal is rejected solely by the new RSI ceiling (RSI 76.66); its one-/three-/six-hour observed paths remain -0.3421%/-0.5149%/-0.1545%. No additional above-75 opportunity supports further adjustment. Many accepted numeric signals occur while held or in cooldown, and SOL's October 2 signal occurs with most investable capital already held. These are signal diagnostics, not replacement transactions or a portfolio backtest.

The second BTC position's preceding October 2 22:00 numeric signal loses 1.4799% at three hours and 1.8543% at six hours. Its actual entry RSI values (one-hour 71.93, 15-minute 60.60) pass existing rules. One losing reentry does not establish a new RSI ceiling or longer profitable-exit cooldown. The original six-hour cooldown was honored.

Profit memory exited ETH positively below the gross 1.2% arming level, unlike the September 30 armed-loss example. No new armed position ended at a loss. ETH's observed prices three/six hours after its actual exit were another 1.5328%/2.2332% lower. BTC's first exit was followed by +0.2457%/+0.7018%, while the losing BTC exit was followed by +0.0350%/-0.0154%. These sparse paths do not establish an optimal exit, but give no compelling reason to weaken exit controls.

Re-running the existing fixed-entry exit diagnostic on 13 comparable recorded entries passing current gates and their recorded score thresholds, including all three current-version trades, gives:

| Fixed-entry diagnostic | Net PnL | Wins | Earlier exits |
| --- | ---: | ---: | ---: |
| Actual fills | +KRW 1,486.43 | 8 / 13 | — |
| Trend memory | +KRW 1,568.97 | 8 / 13 | 1 |
| Half-peak price trail, 0.2% minimum net floor | +KRW 926.75 | 9 / 13 | 6 |

Candidate earlier exits assume 0.05% sell fees and 0.1% adverse price movement. All three current-version exits remain unchanged in this sparse diagnostic. Thus the previously rejected price-only trail still raises historical win rate while reducing net PnL for the relevant subset. Keep the existing trend confirmation. Observations have gaps up to about 15 minutes and cannot reproduce live 60-second peak sampling; quantities, actual entries, original exits and capital reuse are fixed. This is neither an untouched holdout nor proof of positive future expectancy.

**Decision:** retain entry thresholds, sizing, cooldowns, hard stops, profit memory and cycle timing. No live defect or sufficiently supported incremental strategy improvement was found. Three completed current-version trades are too few to justify another parameter change. Record this review and synchronize operations documentation to production without restarting the unchanged trading process.

## Validation and follow-up

All 105 local tests passed from a temporary source copy with socket connections blocked. Live runtime files and logs were preserved. No trading code, dependency or image changed, and no verification order was submitted.

Next review: continue separating current-version completed trades from historical diagnostics; watch for additional RSI-only blocked paths, repeated losing reentries after profitable exits, and any armed-profit loss. Reconcile flows before interpreting account returns. The latest scheduled-run window should remain the baseline rather than recounting today's backfilled October 2 trades as new.
