import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import pandas as pd

import autotrade
import generate_dashboard
import publish_dashboard


def sample_market_row(ticker="KRW-ETH", **overrides):
    row = {
        "coin": ticker,
        "p": 1000,
        "volume_ratio": 1.8,
        "price_change_1d": 2.0,
        "price_change_3d": 4.0,
        "price_change_1h": 1.0,
        "price_change_6h": 3.0,
        "atr_pct": 5.0,
        "indicators": {
            "daily": {
                "rsi": 55,
                "macd_hist": 10,
                "ma5_over_20": True,
                "ma20_over_60": True,
                "price_over_ma20": True,
                "bb_position": 0.65,
            },
            "1h": {
                "rsi": 58,
                "macd_hist": 5,
                "ma5_over_long": True,
                "price_over_long": True,
                "volume_ratio": 1.4,
            },
            "15m": {
                "rsi": 58,
                "macd_hist": 2,
                "ma5_over_long": True,
                "price_over_long": True,
                "volume_ratio": 1.2,
            },
        },
    }
    for key, value in overrides.items():
        if key in row:
            row[key] = value
        elif key in row["indicators"]["daily"]:
            row["indicators"]["daily"][key] = value
        elif key.startswith("hour_"):
            row["indicators"]["1h"][key.replace("hour_", "")] = value
        elif key.startswith("minute_"):
            row["indicators"]["15m"][key.replace("minute_", "")] = value
    return row


class TestTradingLogic(unittest.TestCase):
    def test_dashboard_publisher_retries_pending_commit_before_new_commit(self):
        with mock.patch.object(publish_dashboard, "pending_commit_count", return_value=1), mock.patch.object(
            publish_dashboard, "has_dashboard_changes", return_value=True
        ), mock.patch.object(publish_dashboard, "run") as run:
            publish_dashboard.main()

        self.assertEqual(
            run.call_args_list,
            [
                mock.call("git", "push", "origin", "main"),
                mock.call("git", "add", publish_dashboard.DASHBOARD_PATH),
                mock.call("git", "commit", "-m", "Update trading dashboard"),
                mock.call("git", "push", "origin", "main"),
            ],
        )

    def test_dashboard_publisher_does_not_commit_when_pending_push_fails(self):
        error = publish_dashboard.subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "push", "origin", "main"],
        )
        with mock.patch.object(publish_dashboard, "pending_commit_count", return_value=1), mock.patch.object(
            publish_dashboard, "run", side_effect=error
        ) as run:
            with self.assertRaises(publish_dashboard.subprocess.CalledProcessError):
                publish_dashboard.main()

        self.assertEqual(run.call_args_list, [mock.call("git", "push", "origin", "main")])

    def test_upbit_error_payload_is_reported_cleanly(self):
        class ErrorUpbit:
            def get_balances(self):
                return {"error": {"name": "no_authorization_ip", "message": "This is not a verified IP."}}

        with self.assertRaisesRegex(RuntimeError, "no_authorization_ip"):
            autotrade.get_current_holdings(ErrorUpbit())

    def test_recent_losses_raise_cash_reserve(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as f:
            json.dump(
                [
                    {"side": "SELL", "ticker": "KRW-A", "profit": -2.0},
                    {"side": "SELL", "ticker": "KRW-B", "profit": -1.0},
                    {"side": "SELL", "ticker": "KRW-C", "profit": 0.5},
                    {"side": "SELL", "ticker": "KRW-D", "profit": -0.5},
                    {"side": "SELL", "ticker": "KRW-E", "profit": -1.2},
                ],
                f,
            )
            f.flush()
            perf = autotrade.load_recent_performance(path=f.name, limit=5)

        reserve = autotrade.cash_reserve_pct(
            {"risk_mode": "defensive", "market_volatility": "high"},
            perf,
        )
        self.assertGreaterEqual(reserve, 80)

    def test_recent_performance_uses_realized_sell_rows(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as f:
            json.dump(
                [
                    {"side": "BUY", "profit_pct": 99.0},
                    {"ticker": "KRW-LEGACY", "profit": 88.0},
                    {"side": "SELL", "profit_pct": 1.5},
                    {"side": "SELL", "profit_pct": -0.5},
                ],
                f,
            )
            f.flush()
            perf = autotrade.load_recent_performance(path=f.name, limit=10)

        self.assertEqual(perf["count"], 2)
        self.assertEqual(perf["avg_profit"], 0.5)
        self.assertEqual(perf["net_profit"], 1.0)

    def test_dashboard_ignores_ambiguous_legacy_trade_rows(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as f:
            json.dump(
                [
                    {"date": "04-13 22:02", "ticker": "KRW-0G", "profit": 0.57},
                    {
                        "executed_at": "2026-05-18T09:46:27+09:00",
                        "side": "SELL",
                        "ticker": "KRW-KAITO",
                        "profit_krw": -303.63,
                        "cost_basis_krw": 12736.0,
                        "profit_pct": -2.384,
                    },
                ],
                f,
            )
            f.flush()
            trades = generate_dashboard.load_realized_trades(path=generate_dashboard.Path(f.name))

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["ticker"], "KRW-KAITO")

    def test_sell_history_record_uses_order_detail(self):
        decision = {
            "ticker": "KRW-ETH",
            "balance": 2,
            "avg_buy_price": 1000,
            "current_price": 1100,
            "profit_pct": 10.0,
            "reason": "test",
        }
        order = {
            "paid_fee": "1.1",
            "trades": [
                {"volume": "1.0", "funds": "1100"},
                {"volume": "1.0", "funds": "1100"},
            ],
        }

        record = autotrade.build_sell_history_record(decision, order)

        self.assertEqual(record["gross_proceeds_krw"], 2200.0)
        self.assertEqual(record["fee_krw"], 1.1)
        self.assertEqual(record["profit_krw"], 198.9)
        self.assertEqual(record["profit_pct"], 9.945)
        self.assertEqual(record["source"], "order_detail")

    def test_sell_history_record_includes_prorated_buy_fee(self):
        decision = {
            "ticker": "KRW-ETH",
            "balance": 2,
            "avg_buy_price": 1000,
            "current_price": 1100,
            "profit_pct": 10.0,
            "reason": "test",
        }
        order = {
            "paid_fee": "1.1",
            "trades": [
                {"volume": "1.0", "funds": "1100"},
                {"volume": "1.0", "funds": "1100"},
            ],
        }
        entry_state = {"entry_volume": 4, "entry_fee_krw": 2}

        record = autotrade.build_sell_history_record(decision, order, entry_state=entry_state)

        self.assertEqual(record["buy_fee_krw"], 1.0)
        self.assertEqual(record["sell_fee_krw"], 1.1)
        self.assertEqual(record["fee_krw"], 2.1)
        self.assertEqual(record["profit_krw"], 197.9)
        self.assertEqual(record["profit_pct"], round(197.9 / 2001 * 100, 4))

    def test_buy_state_record_uses_order_detail(self):
        record = autotrade.build_buy_state_record(
            {
                "paid_fee": "1.5",
                "trades": [
                    {"volume": "1.0", "funds": "1000"},
                    {"volume": "2.0", "funds": "2000"},
                ],
            }
        )

        self.assertEqual(record["entry_volume"], 3.0)
        self.assertEqual(record["entry_funds_krw"], 3000.0)
        self.assertEqual(record["entry_fee_krw"], 1.5)

    def test_execute_buy_persists_entry_fee_details(self):
        class FakeUpbit:
            def get_balance(self, currency):
                self.requested_balance = currency
                return 10000

            def buy_market_order(self, ticker, amount):
                self.buy = (ticker, amount)
                return {"uuid": "buy-order"}

            def get_order(self, order_id):
                self.order_id = order_id
                return {
                    "paid_fee": "4.98",
                    "trades": [{"volume": "5", "funds": "9950"}],
                }

        upbit = FakeUpbit()
        state = {"trades": {}}
        plan = {
            "decisions": [{"ticker": "KRW-ETH", "decision": "BUY", "reason": "test"}],
            "buy_budget_krw": 10000,
            "cash_reserve_pct": 25,
        }

        with mock.patch.object(autotrade, "TRADE_ENABLED", True), mock.patch.object(
            autotrade, "save_bot_state"
        ), mock.patch.object(autotrade.time, "sleep"):
            autotrade.execute_rebalance_plan(upbit, plan, state)

        entry = state["trades"]["KRW-ETH"]
        self.assertEqual(upbit.order_id, "buy-order")
        self.assertEqual(entry["entry_volume"], 5.0)
        self.assertEqual(entry["entry_funds_krw"], 9950.0)
        self.assertEqual(entry["entry_fee_krw"], 4.98)

    def test_execute_sell_uses_and_clears_entry_fee_details(self):
        class FakeUpbit:
            def get_balance(self, currency):
                return 5 if currency == "ETH" else 10000

            def sell_market_order(self, ticker, balance):
                return {"uuid": "sell-order"}

            def get_order(self, order_id):
                return {
                    "paid_fee": "2.75",
                    "trades": [{"volume": "5", "funds": "5500"}],
                }

        state = {
            "trades": {
                "KRW-ETH": {
                    "last_buy_ts": 1,
                    "entry_volume": 5,
                    "entry_funds_krw": 5000,
                    "entry_fee_krw": 2.5,
                }
            }
        }
        plan = {
            "decisions": [
                {
                    "ticker": "KRW-ETH",
                    "decision": "SELL",
                    "balance": 5,
                    "avg_buy_price": 1000,
                    "current_price": 1100,
                    "profit_pct": 10,
                    "reason": "test",
                }
            ],
            "buy_budget_krw": 0,
            "cash_reserve_pct": 25,
        }

        with mock.patch.object(autotrade, "TRADE_ENABLED", True), mock.patch.object(
            autotrade.pyupbit, "get_current_price", return_value=1100
        ), mock.patch.object(autotrade, "save_bot_state"), mock.patch.object(
            autotrade, "append_trade_history"
        ) as append_history, mock.patch.object(autotrade.time, "sleep"):
            changed = autotrade.execute_rebalance_plan(FakeUpbit(), plan, state)

        record = append_history.call_args.args[0]
        self.assertTrue(changed)
        self.assertEqual(record["buy_fee_krw"], 2.5)
        self.assertEqual(record["fee_krw"], 5.25)
        self.assertNotIn("entry_fee_krw", state["trades"]["KRW-ETH"])
        self.assertIn("last_sell_ts", state["trades"]["KRW-ETH"])

    def test_dashboard_total_return_uses_buy_fee_in_invested_capital(self):
        summary = generate_dashboard.summarize(
            [
                {
                    "profit_krw": -101.0,
                    "profit_pct": -10.0899,
                    "cost_basis_krw": 1000.0,
                    "buy_fee_krw": 1.0,
                }
            ]
        )

        self.assertEqual(summary["total_return_pct"], round(-101 / 1001 * 100, 4))

    def test_decision_history_keeps_latest_entries(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as f:
            for index in range(3):
                autotrade.append_decision_history(
                    {
                        "risk_mode": "normal",
                        "cash_reserve_pct": 25,
                        "buy_threshold": 10,
                        "buy_budget_krw": 10000 + index,
                        "decisions": [{"ticker": f"KRW-{index}", "decision": "HOLD", "reason": "test"}],
                    },
                    path=f.name,
                    keep=2,
                )

            rows = autotrade.load_decision_history(path=f.name)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["buy_budget_krw"], 10001)
        self.assertEqual(rows[1]["decisions"][0]["ticker"], "KRW-2")

    def test_decision_history_skips_identical_snapshot(self):
        plan = {
            "risk_mode": "defensive",
            "cash_reserve_pct": 80,
            "buy_threshold": 12.5,
            "buy_budget_krw": 10000,
            "entry_block_reason": "BTC 방어장세에서는 신규 매수 차단",
            "decisions": [],
        }
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as f:
            self.assertTrue(autotrade.append_decision_history(plan, path=f.name))
            self.assertFalse(autotrade.append_decision_history(plan, path=f.name))
            rows = autotrade.load_decision_history(path=f.name)

        self.assertEqual(len(rows), 1)

    def test_dashboard_refresh_logs_subprocess_diagnostics(self):
        error = autotrade.subprocess.CalledProcessError(
            returncode=1,
            cmd=["python", "publish_dashboard.py"],
            output="publish stdout",
            stderr="publish stderr",
        )
        with mock.patch.object(autotrade.subprocess, "run", side_effect=error), self.assertLogs(
            autotrade.logger, level="ERROR"
        ) as logs:
            autotrade.refresh_dashboard()

        joined = "\n".join(logs.output)
        self.assertIn("publish_dashboard.py", joined)
        self.assertIn("publish stdout", joined)
        self.assertIn("publish stderr", joined)

    def test_runtime_status_tracks_cycle_success_and_failure(self):
        start = datetime(2026, 5, 18, 9, 0, tzinfo=timezone.utc)
        success = start + timedelta(minutes=1)
        failure = success + timedelta(minutes=15)
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as f:
            autotrade.mark_cycle_started(path=f.name, now=start)
            autotrade.mark_cycle_succeeded(
                next_expected_cycle_at="2026-05-18T09:15:20+00:00",
                path=f.name,
                now=success,
            )
            autotrade.mark_cycle_failed(RuntimeError("boom"), path=f.name, now=failure)
            status = autotrade.load_runtime_status(path=f.name)

        self.assertEqual(datetime.fromisoformat(status["last_cycle_started_at"]), start.astimezone())
        self.assertEqual(datetime.fromisoformat(status["last_success_at"]), success.astimezone())
        self.assertEqual(status["next_expected_cycle_at"], "2026-05-18T09:15:20+00:00")
        self.assertEqual(status["last_error_type"], "RuntimeError")
        self.assertEqual(status["consecutive_failures"], 1)

    def test_dashboard_heartbeat_refresh_waits_for_interval(self):
        refreshed_at = datetime(2026, 5, 18, 9, 0, tzinfo=timezone.utc)
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as f:
            autotrade.mark_dashboard_refreshed(path=f.name, now=refreshed_at)
            status = autotrade.load_runtime_status(path=f.name)

        self.assertFalse(
            autotrade.should_refresh_dashboard_for_heartbeat(
                status,
                now=refreshed_at + timedelta(minutes=59),
                interval_seconds=3600,
            )
        )
        self.assertTrue(
            autotrade.should_refresh_dashboard_for_heartbeat(
                status,
                now=refreshed_at + timedelta(hours=1),
                interval_seconds=3600,
            )
        )

    def test_default_http_timeout_is_added_to_wrapped_requests(self):
        calls = []

        def fake_request(*args, **kwargs):
            calls.append(kwargs)
            return "ok"

        wrapped = autotrade._with_default_timeout(fake_request, timeout_seconds=7)

        self.assertEqual(wrapped("https://example.test"), "ok")
        self.assertEqual(calls[-1]["timeout"], 7)

        wrapped("https://example.test", timeout=3)
        self.assertEqual(calls[-1]["timeout"], 3)

    def test_stop_loss_generates_sell_without_ai(self):
        holding = {
            "ticker": "KRW-ETH",
            "balance": 1,
            "avg_buy_price": 1000,
            "current_price": 960,
            "value": 960,
            "profit_pct": -4.0,
        }
        plan = autotrade.build_rebalance_plan(
            market_data=[sample_market_row()],
            market_context={"risk_mode": "normal", "market_volatility": "normal"},
            krw=100000,
            current_holdings=[holding],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
        )
        self.assertEqual(plan["decisions"][0]["decision"], "SELL")

    def test_weak_candidate_is_not_bought(self):
        weak = sample_market_row(
            ticker="KRW-WEAK",
            volume_ratio=8.0,
            price_change_1d=18.0,
            atr_pct=15.0,
            rsi=78,
            macd_hist=-5,
            ma5_over_20=False,
            ma20_over_60=False,
            price_over_ma20=False,
            hour_rsi=82,
            hour_macd_hist=-2,
            hour_ma5_over_long=False,
            hour_price_over_long=False,
            minute_rsi=82,
            minute_macd_hist=-2,
            minute_ma5_over_long=False,
            minute_price_over_long=False,
            price_change_1h=8.0,
        )
        plan = autotrade.build_rebalance_plan(
            market_data=[weak],
            market_context={"risk_mode": "normal", "market_volatility": "normal"},
            krw=100000,
            current_holdings=[],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
        )
        self.assertFalse([d for d in plan["decisions"] if d["decision"] == "BUY"])

    def test_strong_candidate_can_be_bought(self):
        plan = autotrade.build_rebalance_plan(
            market_data=[sample_market_row("KRW-STRONG")],
            market_context={"risk_mode": "normal", "market_volatility": "normal"},
            krw=100000,
            current_holdings=[],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
        )
        buys = [d for d in plan["decisions"] if d["decision"] == "BUY"]
        self.assertEqual(len(buys), 1)
        self.assertEqual(buys[0]["ticker"], "KRW-STRONG")
        self.assertEqual(plan["buy_budget_krw"], 25000)
        self.assertEqual(plan["max_single_position_pct"], 25.0)

    def test_multiple_candidates_each_respect_single_position_cap(self):
        plan = autotrade.build_rebalance_plan(
            market_data=[sample_market_row("KRW-A"), sample_market_row("KRW-B")],
            market_context={"risk_mode": "normal", "market_volatility": "normal"},
            krw=100000,
            current_holdings=[],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
        )

        buys = [decision for decision in plan["decisions"] if decision["decision"] == "BUY"]
        self.assertEqual(len(buys), 2)
        self.assertEqual(plan["buy_budget_krw"], 50000)

    def test_buy_budget_respects_total_portfolio_exposure(self):
        holding = {
            "ticker": "KRW-BTC",
            "balance": 1,
            "avg_buy_price": 100000,
            "current_price": 100000,
            "value": 75000,
            "profit_pct": 0.0,
        }
        plan = autotrade.build_rebalance_plan(
            market_data=[sample_market_row("KRW-STRONG"), sample_market_row("KRW-BTC")],
            market_context={"risk_mode": "normal", "market_volatility": "normal"},
            krw=25000,
            current_holdings=[holding],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
        )
        self.assertEqual(plan["cash_reserve_pct"], 25)
        self.assertEqual(plan["buy_budget_krw"], 0)

    def test_buy_cooldown_blocks_recently_traded_ticker(self):
        now_ts = 10_000
        state = {"trades": {"KRW-STRONG": {"last_sell_ts": now_ts - 60}}}
        plan = autotrade.build_rebalance_plan(
            market_data=[sample_market_row("KRW-STRONG")],
            market_context={"risk_mode": "normal", "market_volatility": "normal"},
            krw=100000,
            current_holdings=[],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
            state=state,
            now_ts=now_ts,
        )
        self.assertFalse([d for d in plan["decisions"] if d["decision"] == "BUY"])

    def test_excluded_entry_ticker_is_not_bought(self):
        plan = autotrade.build_rebalance_plan(
            market_data=[sample_market_row("KRW-USDT")],
            market_context={"risk_mode": "normal", "market_volatility": "normal"},
            krw=100000,
            current_holdings=[],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
        )
        self.assertFalse([d for d in plan["decisions"] if d["decision"] == "BUY"])
        self.assertEqual(plan["entry_rejections"][0]["reason"], "전략 제외 종목")

    def test_top_volume_targets_batches_all_markets_and_excludes_stables(self):
        markets = [f"KRW-{index}" for index in range(205)] + ["KRW-USDT", "KRW-USDC", "KRW-USD1"]

        class FakeResponse:
            def __init__(self, rows):
                self._rows = rows

            def raise_for_status(self):
                return None

            def json(self):
                return self._rows

        def fake_get(_url, params, timeout):
            chunk = params["markets"].split(",")
            rows = [{"market": ticker, "acc_trade_price_24h": index} for index, ticker in enumerate(chunk, start=1)]
            for row in rows:
                if row["market"] in {"KRW-USDT", "KRW-USDC", "KRW-USD1"}:
                    row["acc_trade_price_24h"] = 10_000
            return FakeResponse(rows)

        with mock.patch.object(autotrade.pyupbit, "get_tickers", return_value=markets), mock.patch.object(
            autotrade.requests, "get", side_effect=fake_get
        ) as requests_get, mock.patch.object(autotrade, "_sleep_api"):
            result = autotrade.get_top_volume_targets(limit=5)

        self.assertEqual(requests_get.call_count, 3)
        self.assertFalse({"KRW-USDT", "KRW-USDC", "KRW-USD1"} & set(result))
        self.assertEqual(len(result), 5)

    def test_defensive_mode_blocks_new_buys(self):
        plan = autotrade.build_rebalance_plan(
            market_data=[sample_market_row("KRW-STRONG")],
            market_context={"risk_mode": "defensive", "market_volatility": "normal"},
            krw=100000,
            current_holdings=[],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
        )
        self.assertFalse([d for d in plan["decisions"] if d["decision"] == "BUY"])
        self.assertEqual(plan["entry_block_reason"], "BTC 방어장세에서는 신규 매수 차단")

    def test_high_atr_candidate_is_hard_blocked(self):
        volatile = sample_market_row("KRW-VOLATILE", atr_pct=12.5)
        plan = autotrade.build_rebalance_plan(
            market_data=[volatile],
            market_context={"risk_mode": "normal", "market_volatility": "normal"},
            krw=100000,
            current_holdings=[],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
        )
        self.assertFalse([d for d in plan["decisions"] if d["decision"] == "BUY"])

    def test_small_loss_needs_hour_and_short_break_before_sell(self):
        holding = {
            "ticker": "KRW-ETH",
            "balance": 1,
            "avg_buy_price": 1000,
            "current_price": 990,
            "value": 990,
            "profit_pct": -1.0,
        }
        row = sample_market_row(
            minute_ma5_over_long=False,
            minute_price_over_long=False,
            minute_macd_hist=-1,
        )
        plan = autotrade.build_rebalance_plan(
            market_data=[row],
            market_context={"risk_mode": "normal", "market_volatility": "normal"},
            krw=100000,
            current_holdings=[holding],
            recent_performance={"count": 0, "avg_profit": 0, "loss_rate": 0, "net_profit": 0},
        )
        self.assertEqual(plan["decisions"][0]["decision"], "HOLD")

    def test_completed_candles_drop_latest_row(self):
        df = pd.DataFrame({"close": [1, 2, 3, 4]})
        completed = autotrade._completed_candles(df, min_rows=3)
        self.assertEqual(completed["close"].tolist(), [1, 2, 3])

    def test_next_cycle_aligns_to_boundary_with_buffer(self):
        self.assertEqual(
            autotrade.seconds_until_next_cycle(now_ts=901, interval_seconds=900, buffer_seconds=20),
            919,
        )

if __name__ == "__main__":
    unittest.main()
