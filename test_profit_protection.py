import json
import os
import tempfile
import unittest
from unittest import mock

import autotrade as bot
from review_exit_paths import compare_exits
from test_logic import sample_market_row


def holding(price, basis=1000):
    return {"ticker": "KRW-ETH", "balance": 10, "avg_buy_price": basis,
            "current_price": price, "value": price * 10,
            "profit_pct": (price / basis - 1) * 100}


class TestProfitProtection(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(os.chdir, self.old_cwd)
        self.state = {"trades": {"KRW-ETH": {"entry_volume": 10, "entry_fee_krw": 5,
                        "entry_funds_krw": 10000, "last_buy_ts": 9999}}}
        for name, value in (("PROFIT_PROTECT_PCT", 1.2), ("ESTIMATED_FEE_RATE", 0.0005),
                            ("STOP_LOSS_PCT", -2.2)):
            patch = mock.patch.object(bot, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def decision(self, price, broken=True, state=None):
        signal = sample_market_row("KRW-ETH")
        if broken:
            signal["indicators"]["15m"].update(price_over_long=False, ma5_over_long=False, macd_hist=-1)
        return bot.should_sell_holding(holding(price), {"KRW-ETH": signal}, {"risk_mode": "normal"},
                                       self.state if state is None else state, 10000)

    def test_fee_estimate_uses_actual_buy_fee_and_legacy_fallback(self):
        trade = self.state["trades"]["KRW-ETH"]
        expected = (1010 * 0.9995 / 1000.5 - 1) * 100
        self.assertAlmostEqual(bot.estimated_net_profit_pct(1010, 1000, trade), expected)
        self.assertAlmostEqual(bot.estimated_net_profit_pct(1010, 1000, {}), expected)
        trade["entry_fee_krw"] = 0  # Known zero fee must not become an estimated fee.
        self.assertAlmostEqual(bot.estimated_net_profit_pct(1010, 1000, trade), 0.9495)

    def test_unarmed_position_does_not_exit_on_small_retracement(self):
        bot.update_profit_peaks([holding(1011.9)], self.state)
        self.assertFalse(self.decision(1001)[0])

    def test_uptrend_has_no_fixed_profit_cap(self):
        for price in (1012, 1032, 1060, 1080):
            bot.update_profit_peaks([holding(price)], self.state)
            self.assertFalse(self.decision(price, broken=False)[0])

    def test_armed_trend_break_exits_before_minimum_hold(self):
        bot.update_profit_peaks([holding(1012)], self.state)
        sell, reason = self.decision(1005)
        self.assertTrue(sell)
        self.assertIn("고점 수익 보호", reason)

    def test_armed_retracement_requires_confirmed_trend_damage(self):
        bot.update_profit_peaks([holding(1030)], self.state)
        self.assertFalse(self.decision(1005, broken=False)[0])
        self.assertFalse(bot.should_sell_holding(holding(1005), {}, {}, self.state, 10000)[0])

    def test_armed_gap_below_breakeven_still_exits(self):
        bot.update_profit_peaks([holding(1020)], self.state)
        self.assertIn("고점 수익 보호", self.decision(995)[1])
        self.assertIn("손절", self.decision(970)[1])

    def test_peak_persists_across_restart_and_never_decreases(self):
        bot.update_profit_peaks([holding(1040)], self.state)
        bot.save_bot_state(self.state)
        restored = bot.load_bot_state()
        self.assertFalse(bot.update_profit_peaks([holding(1030)], restored))
        self.assertEqual(restored["trades"]["KRW-ETH"]["peak_price"], 1040)
        self.assertIn("고점 수익 보호", self.decision(1005, state=restored)[1])

    def test_changed_cost_basis_does_not_inherit_old_peak(self):
        bot.update_profit_peaks([holding(1100)], self.state)
        self.assertFalse(bot.profit_protection_armed(holding(900, 900), self.state))
        bot.update_profit_peaks([holding(900, 900)], self.state)
        self.assertEqual(self.state["trades"]["KRW-ETH"]["peak_price"], 900)
        self.assertFalse(bot.profit_protection_armed(holding(900, 900), self.state))

    def test_invalid_prices_cannot_arm_protection(self):
        for price in (0, -1, float("nan"), float("inf")):
            self.assertFalse(bot.update_profit_peaks([holding(price)], self.state))
        self.assertNotIn("peak_price", self.state["trades"]["KRW-ETH"])

    def test_monitor_records_peak_across_restart_then_candle_cycle_handles_exit(self):
        bot.save_bot_state(self.state)
        upbit = mock.Mock()
        with mock.patch.object(bot, "TRADE_ENABLED", True), \
                mock.patch.object(bot, "get_current_holdings", side_effect=[[holding(1020)], [holding(1005)]]), \
                mock.patch.object(bot, "execute_rebalance_plan", return_value=False) as execute, \
                mock.patch.object(bot, "get_market_data") as scan:
            bot.RiskMonitor(upbit).check()
            bot.RiskMonitor(upbit).check()  # Simulate process restart between quotes.
        scan.assert_not_called()
        execute.assert_not_called()
        self.assertEqual(bot.load_bot_state()["trades"]["KRW-ETH"]["peak_price"], 1020)
        self.assertIn("고점 수익 보호", self.decision(1005, state=bot.load_bot_state())[1])
        self.assertEqual(bot.load_runtime_status()["risk_check_failures"], 0)

    def test_dry_run_does_not_persist_synthetic_peak(self):
        bot.save_bot_state(self.state)
        with mock.patch.object(bot, "TRADE_ENABLED", False), \
                mock.patch.object(bot, "get_current_holdings", return_value=[holding(1100)]):
            bot.RiskMonitor(mock.Mock()).check()
        self.assertNotIn("peak_price", bot.load_bot_state()["trades"]["KRW-ETH"])

    def test_pending_partial_sell_preserves_peak_and_fee_per_unit_then_full_exit_clears(self):
        bot.update_profit_peaks([holding(1040)], self.state)
        for order_id, volume in (("partial", 4), ("remaining", 6)):
            before = dict(self.state["trades"]["KRW-ETH"])
            self.state["pending_orders"] = {order_id: {
                "entry_state": before, "submitted_at": 10000,
                "decision": dict(holding(1010), decision="SELL", reason="profit protection")}}
            detail = {"uuid": order_id, "paid_fee": volume * 1010 * 0.0005,
                      "trades": [{"volume": volume, "funds": volume * 1010}]}
            with mock.patch.object(bot, "confirmed_order_detail", return_value=detail):
                bot.reconcile_pending_orders(mock.Mock(), self.state)
            trade = self.state["trades"]["KRW-ETH"]
            if volume == 4:
                self.assertEqual(trade["peak_price"], 1040)
                self.assertEqual(trade["entry_fee_krw"], 3)
                self.assertEqual(trade["entry_volume"], 6)
            else:
                self.assertNotIn("peak_price", trade)
                self.assertNotIn("peak_avg_buy_price", trade)
        with open(bot.TRADE_HISTORY_FILE) as stream:
            history = json.load(stream)
        self.assertEqual(history[0]["peak_price"], 1040)
        self.assertAlmostEqual(sum(r["profit_krw"] for r in history), 89.95)

    def test_new_confirmed_buy_clears_previous_peak(self):
        bot.update_profit_peaks([holding(1100)], self.state)
        self.state["pending_orders"] = {"new": {"entry_state": dict(self.state["trades"]["KRW-ETH"]),
            "submitted_at": 10000, "decision": {"ticker": "KRW-ETH", "decision": "BUY"}}}
        order = {"paid_fee": 5, "trades": [{"volume": 10, "funds": 10000}]}
        with mock.patch.object(bot, "confirmed_order_detail", return_value=order):
            bot.reconcile_pending_orders(mock.Mock(), self.state)
        self.assertNotIn("peak_price", self.state["trades"]["KRW-ETH"])


class TestExitDiagnostic(unittest.TestCase):
    def row(self):
        return {"side": "SELL", "ticker": "KRW-ETH", "entry_order_uuid": "buy",
                "entry_submitted_at": "2026-09-25T00:00:00+09:00",
                "executed_at": "2026-09-25T01:00:00+09:00", "profit_krw": -100,
                "avg_buy_price": 1000, "quantity": 10, "buy_fee_krw": 5}

    def obs(self, minute, price, exits=False, broken=True):
        signal = sample_market_row("KRW-ETH")
        if broken:
            signal["indicators"]["15m"].update(price_over_long=False, ma5_over_long=False, macd_hist=-1)
        return {"recorded_at": f"2026-09-25T00:{minute:02d}:00+09:00", "holdings": [holding(price)],
                "market_data": [signal],
                "plan": {"decisions": [{"ticker": "KRW-ETH", "decision": "SELL"}] if exits else []}}

    def test_observed_fill_after_gap_is_used_not_theoretical_profit_floor(self):
        report = compare_exits([self.row()], [self.obs(15, 1020, broken=False), self.obs(30, 990)])
        result = report["trades"][0]["candidate_profit_krw"]
        self.assertAlmostEqual(result, round(990 * 0.999 * 10 * 0.9995 - 10005, 2))
        self.assertLess(result, -100)

    def test_original_exit_same_snapshot_keeps_actual_fill(self):
        report = compare_exits([self.row()], [self.obs(15, 1020, broken=False), self.obs(30, 990, exits=True)])
        self.assertEqual(report["all"]["earlier_exits"], 0)
        self.assertEqual(report["trades"][0]["candidate_profit_krw"], -100)

    def test_future_observations_cannot_arm_an_earlier_exit(self):
        report = compare_exits([self.row()], [self.obs(15, 1005), self.obs(30, 1020, broken=False)])
        self.assertEqual(report["all"]["earlier_exits"], 0)

    def test_partial_exits_are_excluded_instead_of_counted_as_two_entries(self):
        report = compare_exits([self.row(), self.row()], [self.obs(15, 1020)])
        self.assertEqual(report["all"]["count"], 0)
        self.assertEqual(report["skipped"]["partial_or_ambiguous_entry"], 2)

    def test_missing_paths_are_not_reported_as_success(self):
        report = compare_exits([self.row()], [])
        self.assertEqual(report["all"]["count"], 0)
        self.assertEqual(report["skipped"]["missing_holding_path"], 1)

    def test_missing_trend_signal_does_not_trigger_exit(self):
        observations = [self.obs(15, 1020), self.obs(30, 990)]
        for observation in observations:
            del observation["market_data"]
        self.assertEqual(compare_exits([self.row()], observations)["all"]["earlier_exits"], 0)

    def test_rejected_price_only_trail_is_available_for_comparison(self):
        observations = [self.obs(15, 1020, broken=False), self.obs(30, 1005, broken=False)]
        self.assertEqual(compare_exits([self.row()], observations)["all"]["earlier_exits"], 0)
        self.assertEqual(compare_exits([self.row()], observations, mode="price_trail")["all"]["earlier_exits"], 1)


if __name__ == "__main__":
    unittest.main()
