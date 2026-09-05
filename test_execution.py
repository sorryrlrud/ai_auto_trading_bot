import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import autotrade as bot


def fill(volume=5, funds=5500, state="done", fee=2.75):
    return {"state": state, "executed_volume": str(volume), "paid_fee": str(fee),
            "trades": [{"volume": str(volume), "funds": str(funds)}] if volume else []}


def sell_decision():
    return {"ticker": "KRW-ETH", "decision": "SELL", "balance": 5,
            "avg_buy_price": 1000, "current_price": 1100, "profit_pct": 10, "reason": "test"}


class TestExecution(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(os.chdir, self.old_cwd)
        self.state = {"trades": {"KRW-ETH": {"last_buy_ts": 1, "entry_volume": 5,
                       "entry_funds_krw": 5000, "entry_fee_krw": 2.5}}}
        self.upbit = mock.Mock()
        self.upbit.get_balance.side_effect = lambda currency: 5 if currency == "ETH" else 10000
        self.upbit.get_order.return_value = fill()
        self.upbit.sell_market_order.return_value = {"uuid": "sell-1"}
        self.upbit.buy_market_order.return_value = {"uuid": "buy-1"}
        for patch in [mock.patch.object(bot, "TRADE_ENABLED", True),
                      mock.patch.object(bot.time, "sleep"),
                      mock.patch.object(bot.pyupbit, "get_current_price", return_value=1100),
                      mock.patch.object(bot, "refresh_dashboard", return_value=True)]:
            patch.start()
            self.addCleanup(patch.stop)

    def pending(self, decision=None):
        self.state["pending_orders"] = {"sell-1": {"decision": decision or sell_decision(),
                    "entry_state": dict(self.state["trades"]["KRW-ETH"]), "submitted_at": 123}}
        bot.save_bot_state(self.state)

    def plan(self, with_buy=False):
        decisions = [sell_decision()]
        if with_buy:
            decisions.append({"ticker": "KRW-BTC", "decision": "BUY", "reason": "replacement"})
        return {"decisions": decisions, "cash_reserve_pct": 25, "buy_budget_krw": 10000}

    def test_waiting_order_is_polled_until_terminal(self):
        self.upbit.get_order.side_effect = [fill(1, 1100, state="wait"), fill()]
        self.assertEqual(bot.confirmed_order_detail(self.upbit, "sell-1")["uuid"], "sell-1")
        self.assertEqual(self.upbit.get_order.call_count, 2)

    def test_canceled_market_buy_with_fills_is_confirmed(self):
        self.upbit.get_order.return_value = fill(state="cancel")
        self.assertIsNotNone(bot.confirmed_order_detail(self.upbit, "buy-1"))

    def test_terminal_order_with_incomplete_trade_details_remains_pending(self):
        order = fill()
        order["executed_volume"] = "6"
        self.upbit.get_order.return_value = order
        self.assertIsNone(bot.confirmed_order_detail(self.upbit, "sell-1"))

    def test_missing_fee_is_not_reported_as_zero(self):
        order = fill()
        del order["paid_fee"]
        self.upbit.get_order.return_value = order
        self.assertIsNone(bot.confirmed_order_detail(self.upbit, "sell-1"))

    def test_missing_fill_never_becomes_snapshot_profit(self):
        with self.assertRaisesRegex(ValueError, "confirmed fills"):
            bot.build_sell_history_record(sell_decision(), {"state": "wait"})

    def test_timeout_preserves_entry_and_pending_order_across_restart(self):
        self.upbit.get_order.side_effect = TimeoutError("read timeout")
        bot.execute_rebalance_plan(self.upbit, self.plan(), self.state)
        reloaded = bot.load_bot_state()
        self.assertEqual(reloaded["trades"]["KRW-ETH"]["entry_fee_krw"], 2.5)
        self.assertIn("sell-1", reloaded["pending_orders"])
        self.assertFalse(os.path.exists(bot.TRADE_HISTORY_FILE))
        self.upbit.get_order.side_effect = None
        self.upbit.get_order.return_value = fill()
        self.assertTrue(bot.reconcile_pending_orders(self.upbit, reloaded))
        self.assertFalse(reloaded["pending_orders"])
        self.upbit.sell_market_order.assert_called_once()
        self.assertEqual(json.loads(Path(bot.TRADE_HISTORY_FILE).read_text())[0]["profit_krw"], 494.75)

    def test_pending_sell_is_not_resubmitted(self):
        self.pending()
        self.upbit.get_order.return_value = fill(state="wait")
        bot.execute_rebalance_plan(self.upbit, self.plan(with_buy=True), self.state)
        self.upbit.sell_market_order.assert_not_called()
        self.upbit.buy_market_order.assert_not_called()

    def test_resolved_pending_sell_does_not_execute_stale_replacement_plan(self):
        self.pending()
        bot.execute_rebalance_plan(self.upbit, self.plan(with_buy=True), self.state)
        self.upbit.sell_market_order.assert_not_called()
        self.upbit.buy_market_order.assert_not_called()

    def test_canceled_unfilled_order_does_not_change_entry_or_history(self):
        self.pending()
        self.upbit.get_order.return_value = fill(0, 0, state="cancel", fee=0)
        self.assertFalse(bot.reconcile_pending_orders(self.upbit, self.state))
        self.assertEqual(self.state["trades"]["KRW-ETH"]["entry_fee_krw"], 2.5)
        self.assertNotIn("last_sell_ts", self.state["trades"]["KRW-ETH"])
        self.assertFalse(os.path.exists(bot.TRADE_HISTORY_FILE))

    def test_partial_sell_preserves_remaining_cost_and_fee(self):
        self.pending()
        self.upbit.get_order.return_value = fill(2, 2200, state="cancel", fee=1.1)
        bot.reconcile_pending_orders(self.upbit, self.state)
        entry = self.state["trades"]["KRW-ETH"]
        self.assertEqual(entry["entry_volume"], 3)
        self.assertEqual(entry["entry_funds_krw"], 3000)
        self.assertEqual(entry["entry_fee_krw"], 1.5)
        record = json.loads(Path(bot.TRADE_HISTORY_FILE).read_text())[0]
        self.assertEqual(record["quantity"], 2)
        self.assertEqual(record["buy_fee_krw"], 1)

    def test_recovery_after_history_write_does_not_duplicate_pnl(self):
        self.pending()
        original = bot.load_bot_state()
        bot.reconcile_pending_orders(self.upbit, self.state)
        bot.reconcile_pending_orders(self.upbit, original)
        self.assertEqual(len(json.loads(Path(bot.TRADE_HISTORY_FILE).read_text())), 1)
        self.assertNotIn("entry_fee_krw", original["trades"]["KRW-ETH"])

    def test_failed_sell_blocks_replacement_buy(self):
        self.upbit.sell_market_order.return_value = {"error": {"name": "rejected"}}
        bot.execute_rebalance_plan(self.upbit, self.plan(with_buy=True), self.state)
        self.upbit.buy_market_order.assert_not_called()

    def test_partial_sell_blocks_replacement_buy(self):
        self.upbit.get_order.return_value = fill(2, 2200, state="cancel", fee=1.1)
        bot.execute_rebalance_plan(self.upbit, self.plan(with_buy=True), self.state)
        self.upbit.buy_market_order.assert_not_called()

    def test_full_exit_can_fund_replacement(self):
        self.upbit.get_balance.side_effect = [5, 0, 10000]
        self.upbit.get_order.side_effect = [fill(), fill(0.1, 9950, state="cancel", fee=4.975)]
        bot.execute_rebalance_plan(self.upbit, self.plan(with_buy=True), self.state)
        self.upbit.buy_market_order.assert_called_once_with("KRW-BTC", 9950)

    def test_no_fill_buy_does_not_start_holding_timer(self):
        self.state = {"trades": {}}
        self.upbit.get_order.return_value = fill(0, 0, state="cancel", fee=0)
        bot.execute_rebalance_plan(self.upbit, {"decisions": [{"ticker": "KRW-BTC", "decision": "BUY",
                                  "reason": "test"}], "buy_budget_krw": 10000, "cash_reserve_pct": 25}, self.state)
        self.assertNotIn("KRW-BTC", self.state["trades"])

    def test_corrupt_state_and_history_are_not_silently_erased(self):
        for path in [bot.BOT_STATE_FILE, bot.TRADE_HISTORY_FILE]:
            with open(path, "w") as f:
                f.write('{"truncated":')
        with self.assertRaises(json.JSONDecodeError):
            bot.load_bot_state()
        with self.assertRaises(json.JSONDecodeError):
            bot.append_trade_history({"order_uuid": "sell-1"})

    def test_atomic_write_keeps_previous_state_when_replace_fails(self):
        bot.save_bot_state(self.state)
        with mock.patch.object(bot.os, "replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                bot.save_bot_state({"trades": {}})
        self.assertEqual(bot.load_bot_state(), self.state)

    def test_risk_monitor_checks_stop_without_candle_scan_or_minimum_hold(self):
        bot.save_bot_state(self.state)
        holding = dict(sell_decision(), profit_pct=-3, current_price=970, value=5820, balance=6)
        with mock.patch.object(bot, "get_current_holdings", return_value=[holding]), \
                mock.patch.object(bot, "execute_rebalance_plan", return_value=True) as execute, \
                mock.patch.object(bot, "get_market_data") as scan:
            bot.RiskMonitor(self.upbit).check()
        plan = execute.call_args.args[1]
        self.assertEqual(plan["buy_budget_krw"], 0)
        self.assertEqual(plan["decisions"][0]["decision"], "SELL")
        scan.assert_not_called()
        self.assertIn("last_risk_check_at", bot.load_runtime_status())

    def test_risk_monitor_does_not_exit_above_existing_stop(self):
        with mock.patch.object(bot, "get_current_holdings", return_value=[dict(sell_decision(), profit_pct=-2.1)]), \
                mock.patch.object(bot, "execute_rebalance_plan") as execute:
            bot.RiskMonitor(self.upbit).check()
        execute.assert_not_called()

    def test_risk_monitor_interval_and_error_reporting(self):
        with mock.patch.object(bot.time, "monotonic", return_value=100), \
                mock.patch.object(bot, "get_current_holdings", side_effect=RuntimeError("balances failed")) as holdings:
            monitor = bot.RiskMonitor(self.upbit)
            with self.assertRaises(RuntimeError):
                monitor.check()
            monitor.check()
        self.assertEqual(holdings.call_count, 1)
        self.assertEqual(bot.load_runtime_status()["risk_check_failures"], 1)

    def test_dry_run_does_not_submit_or_reconcile_orders(self):
        self.pending()
        with mock.patch.object(bot, "TRADE_ENABLED", False):
            bot.execute_rebalance_plan(self.upbit, self.plan(with_buy=True), self.state)
        self.upbit.get_order.assert_not_called()
        self.upbit.sell_market_order.assert_not_called()
        self.upbit.buy_market_order.assert_not_called()

    def test_main_refreshes_holdings_after_scan_before_sell_decision(self):
        old = dict(sell_decision(), profit_pct=0, current_price=1000, value=10000)
        fresh = dict(old, profit_pct=-3, current_price=970, value=9700)
        with mock.patch.object(bot, "RUN_ONCE", True), \
                mock.patch.object(bot.subprocess, "Popen"), \
                mock.patch.object(bot, "setup_api", return_value=self.upbit), \
                mock.patch.object(bot, "RiskMonitor"), \
                mock.patch.object(bot, "get_current_holdings", side_effect=[[old], [fresh]]), \
                mock.patch.object(bot, "get_market_context", return_value={"risk_mode": "normal"}), \
                mock.patch.object(bot, "get_top_volume_targets", return_value=[]), \
                mock.patch.object(bot, "get_market_data", return_value=None), \
                mock.patch.object(bot, "execute_rebalance_plan", return_value=False) as execute:
            bot.main()
        decision = execute.call_args.args[1]["decisions"][0]
        self.assertEqual(decision["decision"], "SELL")
        self.assertEqual(decision["current_price"], 970)

    def test_wait_checks_risk_throughout_fifteen_minute_gap(self):
        now = [0.0]
        def advance(seconds):
            self.assertLessEqual(seconds, 60)
            now[0] += seconds
        with mock.patch.object(bot.time, "monotonic", side_effect=lambda: now[0]), \
                mock.patch.object(bot.time, "sleep", side_effect=advance), \
                mock.patch.object(bot, "get_current_holdings", return_value=[]) as holdings:
            bot.RiskMonitor(self.upbit).wait(900)
        self.assertEqual(holdings.call_count, 15)
        self.assertEqual(now[0], 900)


if __name__ == "__main__":
    unittest.main()
