import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import scheduled_trader


class FakeUpbit:
    def __init__(self, krw=100_000, coin_balance=0, coin_price=10_000, avg_buy_price=10_000):
        self.krw = krw
        self.coin_balance = coin_balance
        self.coin_price = coin_price
        self.avg_buy_price = avg_buy_price

    def get_balances(self):
        rows = [{"currency": "KRW", "balance": str(self.krw), "locked": "0"}]
        if self.coin_balance:
            rows.append(
                {
                    "currency": "ETH",
                    "balance": str(self.coin_balance),
                    "locked": "0",
                    "avg_buy_price": str(self.avg_buy_price),
                }
            )
        return rows


class TestScheduledTrader(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.state_path = Path(self.temporary_directory.name) / "state.json"
        self.context_path = Path(self.temporary_directory.name) / "context.json"
        self.patches = [
            mock.patch.object(scheduled_trader, "ACTIVATE_AT", ""),
            mock.patch.object(scheduled_trader, "DEACTIVATE_AT", ""),
            mock.patch.object(scheduled_trader, "TRADE_ENABLED", True),
            mock.patch.object(scheduled_trader, "TAKE_PROFIT_PCT", 0.5),
            mock.patch.object(scheduled_trader, "MAX_LOSS_PCT", 0.4),
            mock.patch.object(scheduled_trader, "SIGNAL_INTERVAL_MINUTES", 10),
            mock.patch.object(scheduled_trader.pyupbit, "get_current_price", return_value=10_000),
            mock.patch.object(scheduled_trader.autotrade, "_sleep_api"),
            mock.patch.object(scheduled_trader.autotrade, "trade_execution_lock", mock.MagicMock()),
            mock.patch.object(
                scheduled_trader.autotrade,
                "get_market_context",
                return_value={"risk_mode": "normal", "market_volatility": "normal"},
            ),
            mock.patch.object(scheduled_trader.autotrade, "get_top_volume_targets", return_value=[]),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_trading_day_rolls_over_at_two_am(self):
        before = datetime(2026, 7, 22, 1, 59, tzinfo=scheduled_trader.KST)
        after = datetime(2026, 7, 22, 2, 0, tzinfo=scheduled_trader.KST)
        self.assertEqual(str(scheduled_trader.trading_day(before)), "2026-07-21")
        self.assertEqual(str(scheduled_trader.trading_day(after)), "2026-07-22")

    def test_first_tick_sets_baseline_and_runs_one_signal_slot(self):
        now = datetime(2026, 7, 22, 2, 1, tzinfo=scheduled_trader.KST)
        result = scheduled_trader.run_tick(
            FakeUpbit(), now=now, state_path=self.state_path, context_path=self.context_path
        )
        state = scheduled_trader.load_state(self.state_path)
        self.assertEqual(result["status"], "needs_decision")
        self.assertTrue(result["decision_token"])
        self.assertEqual(state["session_date"], "2026-07-22")
        self.assertEqual(state["phase"], 1)
        self.assertEqual(state["phase_start_equity_krw"], 100_000)
        self.assertEqual(state["session_start_equity_krw"], 100_000)
        self.assertEqual(result["decision_interval_minutes"], 10)
        self.assertEqual(result["daily_target_pct"], 0.5)

    def test_same_signal_slot_only_runs_heartbeat(self):
        first = datetime(2026, 7, 22, 2, 1, tzinfo=scheduled_trader.KST)
        second = datetime(2026, 7, 22, 2, 9, tzinfo=scheduled_trader.KST)
        context = scheduled_trader.run_tick(
            FakeUpbit(), now=first, state_path=self.state_path, context_path=self.context_path
        )
        with mock.patch.object(scheduled_trader.autotrade, "append_decision_history", return_value=False), mock.patch.object(
            scheduled_trader.autotrade, "execute_rebalance_plan", return_value=False
        ):
            scheduled_trader.execute_llm_decision(
                {"decision_token": context["decision_token"], "decisions": []},
                upbit=FakeUpbit(),
                now=first,
                state_path=self.state_path,
                context_path=self.context_path,
            )
        result = scheduled_trader.run_tick(
            FakeUpbit(), now=second, state_path=self.state_path, context_path=self.context_path
        )
        self.assertEqual(result["action"], "heartbeat_only")

    def test_existing_state_migrates_original_daily_baseline(self):
        now = datetime(2026, 7, 21, 20, 5, tzinfo=scheduled_trader.KST)
        scheduled_trader.save_state(
            {
                "session_date": "2026-07-21",
                "status": "active",
                "phase": 1,
                "phase_start_equity_krw": 100_000,
                "last_signal_slot": scheduled_trader.signal_slot(now),
            },
            self.state_path,
        )
        result = scheduled_trader.run_tick(
            FakeUpbit(), now=now, state_path=self.state_path, context_path=self.context_path
        )
        state = scheduled_trader.load_state(self.state_path)
        self.assertEqual(result["action"], "heartbeat_only")
        self.assertEqual(state["session_start_equity_krw"], 100_000)
        self.assertEqual(state["daily_return_pct"], 0.0)

    def test_profit_target_liquidates_and_completes_day(self):
        now = datetime(2026, 7, 22, 9, 0, tzinfo=scheduled_trader.KST)
        scheduled_trader.save_state(
            {
                "session_date": "2026-07-22",
                "status": "active",
                "phase": 1,
                "phase_start_equity_krw": 100_000,
                "session_start_equity_krw": 99_500,
            },
            self.state_path,
        )
        with mock.patch.object(scheduled_trader, "liquidate_all", return_value=True) as liquidate, mock.patch.object(
            scheduled_trader.autotrade, "refresh_dashboard"
        ):
            result = scheduled_trader.run_tick(
                FakeUpbit(), now=now, state_path=self.state_path, context_path=self.context_path
            )
        self.assertEqual(result["status"], "completed_target")
        liquidate.assert_called_once()

    def test_morning_stop_waits_until_noon_then_starts_phase_two(self):
        morning = datetime(2026, 7, 22, 10, 0, tzinfo=scheduled_trader.KST)
        scheduled_trader.save_state(
            {
                "session_date": "2026-07-22",
                "status": "active",
                "phase": 1,
                "phase_start_equity_krw": 100_500,
                "session_start_equity_krw": 100_500,
            },
            self.state_path,
        )
        with mock.patch.object(scheduled_trader, "liquidate_all", return_value=True), mock.patch.object(
            scheduled_trader.autotrade, "refresh_dashboard"
        ):
            stopped = scheduled_trader.run_tick(
                FakeUpbit(), now=morning, state_path=self.state_path, context_path=self.context_path
            )
        self.assertEqual(stopped["status"], "waiting_noon")

        noon = datetime(2026, 7, 22, 12, 0, tzinfo=scheduled_trader.KST)
        restarted = scheduled_trader.run_tick(
            FakeUpbit(), now=noon, state_path=self.state_path, context_path=self.context_path
        )
        state = scheduled_trader.load_state(self.state_path)
        self.assertEqual(restarted["status"], "needs_decision")
        self.assertEqual(state["phase"], 2)
        self.assertEqual(state["phase_start_equity_krw"], 100_000)
        self.assertEqual(state["session_start_equity_krw"], 100_500)
        self.assertLess(restarted["daily_return_pct"], -0.4)

    def test_phase_two_gain_does_not_complete_before_daily_target(self):
        now = datetime(2026, 7, 22, 12, 10, tzinfo=scheduled_trader.KST)
        scheduled_trader.save_state(
            {
                "session_date": "2026-07-22",
                "status": "active",
                "phase": 2,
                "phase_start_equity_krw": 99_600,
                "session_start_equity_krw": 100_000,
            },
            self.state_path,
        )
        result = scheduled_trader.run_tick(
            FakeUpbit(), now=now, state_path=self.state_path, context_path=self.context_path
        )
        self.assertEqual(result["status"], "needs_decision")
        self.assertGreater(result["phase_return_pct"], 0.4)
        self.assertEqual(result["daily_return_pct"], 0.0)

    def test_phase_two_closes_after_reaching_daily_target(self):
        now = datetime(2026, 7, 22, 12, 20, tzinfo=scheduled_trader.KST)
        scheduled_trader.save_state(
            {
                "session_date": "2026-07-22",
                "status": "active",
                "phase": 2,
                "phase_start_equity_krw": 99_600,
                "session_start_equity_krw": 100_000,
            },
            self.state_path,
        )
        with mock.patch.object(scheduled_trader.autotrade, "refresh_dashboard"):
            result = scheduled_trader.run_tick(
                FakeUpbit(krw=100_501),
                now=now,
                state_path=self.state_path,
                context_path=self.context_path,
            )
        self.assertEqual(result["status"], "completed_target")
        self.assertGreaterEqual(result["daily_return_pct"], 0.5)

    def test_afternoon_stop_completes_day(self):
        now = datetime(2026, 7, 22, 12, 1, tzinfo=scheduled_trader.KST)
        scheduled_trader.save_state(
            {
                "session_date": "2026-07-22",
                "status": "active",
                "phase": 2,
                "phase_start_equity_krw": 100_500,
                "session_start_equity_krw": 100_000,
            },
            self.state_path,
        )
        with mock.patch.object(scheduled_trader, "liquidate_all", return_value=True), mock.patch.object(
            scheduled_trader.autotrade, "refresh_dashboard"
        ):
            result = scheduled_trader.run_tick(
                FakeUpbit(), now=now, state_path=self.state_path, context_path=self.context_path
            )
        self.assertEqual(result["status"], "completed_stop")
        self.assertEqual(result["action"], "liquidated_until_next_session")

    def test_activation_time_prevents_early_api_access(self):
        now = datetime(2026, 7, 21, 23, 0, tzinfo=scheduled_trader.KST)
        with mock.patch.object(scheduled_trader, "ACTIVATE_AT", "2026-07-22T02:00:00+09:00"):
            result = scheduled_trader.run_tick(
                upbit=None, now=now, state_path=self.state_path, context_path=self.context_path
            )
        self.assertEqual(result["status"], "waiting_activation")

    def test_deactivation_time_closes_test_window(self):
        now = datetime(2026, 7, 21, 23, 50, tzinfo=scheduled_trader.KST)
        scheduled_trader.save_state(
            {
                "session_date": "2026-07-21",
                "status": "active",
                "phase": 1,
                "phase_start_equity_krw": 100_000,
                "session_start_equity_krw": 100_000,
            },
            self.state_path,
        )
        with mock.patch.object(
            scheduled_trader, "DEACTIVATE_AT", "2026-07-21T23:50:00+09:00"
        ), mock.patch.object(scheduled_trader.autotrade, "refresh_dashboard"):
            result = scheduled_trader.run_tick(
                FakeUpbit(), now=now, state_path=self.state_path, context_path=self.context_path
            )
        self.assertEqual(result["status"], "completed_test_window")
        self.assertEqual(result["action"], "test_window_closed")

    def test_llm_decision_is_rejected_after_deactivation(self):
        now = datetime(2026, 7, 21, 23, 50, tzinfo=scheduled_trader.KST)
        with mock.patch.object(
            scheduled_trader, "DEACTIVATE_AT", "2026-07-21T23:50:00+09:00"
        ):
            with self.assertRaisesRegex(RuntimeError, "window has ended"):
                scheduled_trader.execute_llm_decision(
                    {}, now=now, state_path=self.state_path, context_path=self.context_path
                )

    def test_failed_liquidation_is_retried_on_next_heartbeat(self):
        now = datetime(2026, 7, 22, 13, 0, tzinfo=scheduled_trader.KST)
        upbit = FakeUpbit(krw=90_000, coin_balance=1, coin_price=10_000)
        scheduled_trader.save_state(
            {
                "session_date": "2026-07-22",
                "status": "active",
                "phase": 2,
                "phase_start_equity_krw": 100_500,
                "session_start_equity_krw": 100_000,
            },
            self.state_path,
        )
        with mock.patch.object(scheduled_trader, "liquidate_all", return_value=False), mock.patch.object(
            scheduled_trader.autotrade, "refresh_dashboard"
        ):
            result = scheduled_trader.run_tick(
                upbit, now=now, state_path=self.state_path, context_path=self.context_path
            )
        self.assertEqual(result["status"], "liquidation_pending")
        self.assertEqual(result["remaining"], ["KRW-ETH"])

    def test_llm_buy_is_limited_to_context_candidates(self):
        snapshot = scheduled_trader.account_snapshot(FakeUpbit())
        context = {
            "decision_token": "token-123",
            "candidates": [{"coin": "KRW-ETH"}],
            "market_context": {"risk_mode": "normal"},
        }
        plan = scheduled_trader._validated_llm_plan(
            {
                "decision_token": "token-123",
                "decisions": [{"ticker": "KRW-ETH", "decision": "BUY", "reason": "상승 추세"}],
            },
            context,
            snapshot,
        )
        self.assertEqual(plan["cash_reserve_pct"], 0)
        self.assertEqual(plan["decision_source"], "gpt-5.6-sol/medium")
        self.assertEqual(plan["decisions"][0]["decision"], "BUY")

        with self.assertRaisesRegex(ValueError, "BUY is not allowed"):
            scheduled_trader._validated_llm_plan(
                {
                    "decision_token": "token-123",
                    "decisions": [{"ticker": "KRW-XRP", "decision": "BUY", "reason": "임의 종목"}],
                },
                context,
                snapshot,
            )


if __name__ == "__main__":
    unittest.main()
