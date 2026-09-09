import unittest

import review_strategy as review


class TestStrategyReview(unittest.TestCase):
    def test_only_explicit_realized_sells_enter_summary_and_test_logs_are_ignored(self):
        history = [{"profit_krw": 10000}, {"side": "BUY", "profit_krw": 20000},
                   {"side": "SELL", "ticker": "KRW-A", "executed_at": "2026-09-01T12:00:00+09:00",
                    "profit_krw": -10, "fee_krw": 2, "reason": "손절"}]
        log = ("2026-09-01 09:00:00,000 - INFO - [BUY] KRW-A 5000 KRW | score 13: 1h weak\n"
               "2026-09-01 11:00:00,000 - INFO - [BUY] KRW-A 9950 KRW | test\n"
               "2026-09-01 11:10:00,000 - INFO - [REALIZED] KRW-A profit=9000 KRW (90%)")
        result = review.make_review(history, log, "2026-09-01")
        self.assertEqual(result["all_realized"]["net_profit_krw"], -10)
        self.assertEqual(result["negative_hour_momentum_entries"]["sell_count"], 1)
        self.assertEqual(result["entry_filter_diagnostic"]["with_negative_momentum_gate"]["sell_count"], 0)

    def test_cooldown_uses_only_preceding_accepted_realized_losses(self):
        rows = [dict(entry_ts=1, exit_ts=5, profit_krw=-10, negative_hour_momentum=True),
                dict(entry_ts=6, exit_ts=9, profit_krw=20, negative_hour_momentum=False),
                dict(entry_ts=15, exit_ts=20, profit_krw=-10, negative_hour_momentum=False)]
        baseline, _ = review.filter_recorded_entries(rows, cooldown_seconds=10)
        candidate, _ = review.filter_recorded_entries(rows, True, cooldown_seconds=10)
        self.assertEqual([row["entry_ts"] for row in baseline], [1, 15])
        self.assertEqual([row["entry_ts"] for row in candidate], [6, 15])

    def test_partial_exits_are_not_treated_as_independent_entries(self):
        history = [dict(side="SELL", ticker="KRW-A", profit_krw=-10, fee_krw=1,
                        executed_at=f"2026-09-01T{hour}:00:00+09:00") for hour in ("12", "13")]
        log = "2026-09-01 09:00:00,000 - INFO - [BUY] KRW-A 5000 KRW | score 13: trend"
        result = review.make_review(history, log, "2026-09-01")
        self.assertEqual(result["period_realized"]["sell_count"], 2)
        self.assertIn("filter_diagnostic_unavailable", result)
        self.assertNotIn("entry_filter_diagnostic", result)

    def test_unknown_fees_and_unmatched_entries_are_reported(self):
        history = [dict(side="SELL", ticker="KRW-A", profit_krw=10,
                        executed_at="2026-09-01T12:00:00+09:00")]
        result = review.make_review(history, "", "2026-09-01")
        self.assertEqual(result["unmatched_sells"], 1)
        self.assertIsNone(result["period_realized"]["fees_krw"])
        self.assertIsNone(result["period_realized"]["profit_factor"])


if __name__ == "__main__":
    unittest.main()
