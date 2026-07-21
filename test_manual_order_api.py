import tempfile
import unittest
from pathlib import Path
from unittest import mock

import manual_order_api


class FakeUpbit:
    def __init__(self):
        self.buy_calls = []
        self.sell_calls = []

    def get_balance(self, currency):
        return 1_000_000 if currency == "KRW" else 2

    def buy_market_order(self, market, amount):
        self.buy_calls.append((market, amount))
        return {"uuid": "buy-uuid"}

    def sell_market_order(self, market, volume):
        self.sell_calls.append((market, volume))
        return {"uuid": "sell-uuid"}

    def get_order(self, order_uuid):
        if order_uuid == "buy-uuid":
            return {
                "uuid": order_uuid,
                "state": "done",
                "paid_fee": "5",
                "trades": [{"volume": "0.01", "funds": "10000"}],
            }
        return {
            "uuid": order_uuid,
            "state": "done",
            "paid_fee": "5",
            "trades": [{"volume": "1", "funds": "10000"}],
        }


class TestManualOrderApi(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.history_path = Path(self.temporary_directory.name) / "history.json"
        self.upbit = FakeUpbit()
        self.patches = [
            mock.patch.object(manual_order_api, "MANUAL_TRADE_ENABLED", True),
            mock.patch.object(manual_order_api, "ORDER_HISTORY_FILE", self.history_path),
            mock.patch.object(manual_order_api.autotrade, "load_bot_state", return_value={"trades": {}}),
            mock.patch.object(manual_order_api.autotrade, "save_bot_state"),
            mock.patch.object(manual_order_api.autotrade, "append_trade_history"),
            mock.patch.object(manual_order_api.autotrade, "trade_execution_lock", mock.MagicMock()),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_buy_requires_explicit_confirmation(self):
        with self.assertRaisesRegex(manual_order_api.ApiError, "confirm"):
            manual_order_api.execute_manual_order(
                "/v1/orders/buy",
                {"market": "KRW-BTC", "amount_krw": 10000, "idempotency_key": "request-001"},
                self.upbit,
            )
        self.assertEqual(self.upbit.buy_calls, [])

    def test_buy_is_idempotent(self):
        payload = {
            "market": "krw-btc",
            "amount_krw": 10000,
            "idempotency_key": "request-001",
            "confirm": "CONFIRM",
        }
        first, first_replayed = manual_order_api.execute_manual_order("/v1/orders/buy", payload, self.upbit)
        second, second_replayed = manual_order_api.execute_manual_order("/v1/orders/buy", payload, self.upbit)

        self.assertFalse(first_replayed)
        self.assertTrue(second_replayed)
        self.assertEqual(first, second)
        self.assertEqual(self.upbit.buy_calls, [("KRW-BTC", 10000.0)])

    def test_buy_limit_is_enforced(self):
        with self.assertRaisesRegex(manual_order_api.ApiError, "MANUAL_MAX_BUY_KRW"):
            manual_order_api.execute_manual_order(
                "/v1/orders/buy",
                {
                    "market": "KRW-BTC",
                    "amount_krw": manual_order_api.MANUAL_MAX_BUY_KRW + 1,
                    "idempotency_key": "request-002",
                    "confirm": "CONFIRM",
                },
                self.upbit,
            )

    def test_idempotency_key_cannot_be_reused_for_another_order(self):
        payload = {
            "market": "KRW-BTC",
            "amount_krw": 10000,
            "idempotency_key": "request-004",
            "confirm": "CONFIRM",
        }
        manual_order_api.execute_manual_order("/v1/orders/buy", payload, self.upbit)
        payload["amount_krw"] = 20000

        with self.assertRaisesRegex(manual_order_api.ApiError, "already used"):
            manual_order_api.execute_manual_order("/v1/orders/buy", payload, self.upbit)

        self.assertEqual(self.upbit.buy_calls, [("KRW-BTC", 10000.0)])

    def test_sell_percentage_uses_available_balance(self):
        payload = {
            "market": "KRW-BTC",
            "percentage": 25,
            "idempotency_key": "request-003",
            "confirm": "CONFIRM",
        }
        with mock.patch.object(manual_order_api.pyupbit, "get_current_price", return_value=10000):
            response, replayed = manual_order_api.execute_manual_order("/v1/orders/sell", payload, self.upbit)

        self.assertFalse(replayed)
        self.assertEqual(response["side"], "SELL")
        self.assertEqual(self.upbit.sell_calls, [("KRW-BTC", 0.5)])


if __name__ == "__main__":
    unittest.main()
