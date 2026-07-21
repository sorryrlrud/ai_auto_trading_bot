import json
import logging
import os
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pyupbit

import autotrade


logger = logging.getLogger(__name__)

API_HOST = "0.0.0.0"
API_PORT = int(os.getenv("MANUAL_API_PORT", "8765"))
MANUAL_TRADE_ENABLED = os.getenv("MANUAL_TRADE_ENABLED", "false").lower() == "true"
MANUAL_MAX_BUY_KRW = float(os.getenv("MANUAL_MAX_BUY_KRW", "100000"))
ORDER_HISTORY_FILE = Path(os.getenv("MANUAL_ORDER_HISTORY_FILE", "manual_order_history.json"))
MAX_REQUEST_BYTES = 16_384
MARKET_PATTERN = re.compile(r"^KRW-[A-Z0-9]+$")


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _load_history():
    try:
        rows = json.loads(ORDER_HISTORY_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        rows = []
    return rows if isinstance(rows, list) else []


def _save_history(rows):
    temporary = ORDER_HISTORY_FILE.with_suffix(ORDER_HISTORY_FILE.suffix + ".tmp")
    temporary.write_text(json.dumps(rows[-1000:], ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(ORDER_HISTORY_FILE)


def _existing_record(rows, idempotency_key):
    for row in reversed(rows):
        if row.get("idempotency_key") == idempotency_key:
            return row
    return None


def _validate_common(payload):
    market = str(payload.get("market", "")).strip().upper()
    idempotency_key = str(payload.get("idempotency_key", "")).strip()
    if not MARKET_PATTERN.fullmatch(market):
        raise ApiError(400, "invalid_market", "market must use the KRW-BTC format")
    if not 8 <= len(idempotency_key) <= 128:
        raise ApiError(400, "invalid_idempotency_key", "idempotency_key must be 8-128 characters")
    return market, idempotency_key


def _order_detail(upbit, result):
    if not isinstance(result, dict):
        raise ApiError(502, "upbit_order_failed", f"unexpected Upbit response: {result!r}")
    error = autotrade._upbit_error_message(result)
    if error:
        raise ApiError(502, "upbit_order_failed", error)
    order_uuid = result.get("uuid")
    if not order_uuid:
        raise ApiError(502, "upbit_order_failed", f"order UUID missing: {result!r}")
    try:
        detail = upbit.get_order(order_uuid)
        return detail if isinstance(detail, dict) else result
    except Exception as exc:
        logger.warning("Could not retrieve order detail for %s: %s", order_uuid, exc)
        return result


def _public_order(detail, side, market, idempotency_key):
    return {
        "idempotency_key": idempotency_key,
        "uuid": detail.get("uuid"),
        "market": market,
        "side": side,
        "state": detail.get("state", "submitted"),
        "executed_volume": detail.get("executed_volume"),
        "paid_fee": detail.get("paid_fee"),
        "submitted_at": _now(),
    }


def _execute_buy(upbit, payload, market, idempotency_key, state):
    amount_krw = autotrade.safe_float(payload.get("amount_krw"), -1)
    if amount_krw < autotrade.MIN_ORDER_KRW:
        raise ApiError(400, "order_too_small", f"amount_krw must be at least {autotrade.MIN_ORDER_KRW}")
    if amount_krw > MANUAL_MAX_BUY_KRW:
        raise ApiError(400, "order_too_large", f"amount_krw exceeds MANUAL_MAX_BUY_KRW={MANUAL_MAX_BUY_KRW:g}")
    krw_balance = autotrade.safe_float(upbit.get_balance("KRW"))
    if amount_krw > krw_balance:
        raise ApiError(409, "insufficient_balance", "available KRW balance is lower than amount_krw")

    detail = _order_detail(upbit, upbit.buy_market_order(market, amount_krw))
    trade_state = state["trades"].setdefault(market, {})
    trade_state["last_buy_ts"] = datetime.now().timestamp()
    trade_state.update(autotrade.build_buy_state_record(detail))
    autotrade.save_bot_state(state)
    return _public_order(detail, "BUY", market, idempotency_key)


def _execute_sell(upbit, payload, market, idempotency_key, state):
    percentage = autotrade.safe_float(payload.get("percentage", 100), -1)
    if not 0 < percentage <= 100:
        raise ApiError(400, "invalid_percentage", "percentage must be greater than 0 and at most 100")
    currency = market.split("-", 1)[1]
    available_volume = autotrade.safe_float(upbit.get_balance(currency))
    volume = available_volume * percentage / 100
    current_price = autotrade.safe_float(pyupbit.get_current_price(market))
    if volume <= 0 or volume * current_price < autotrade.MIN_ORDER_KRW:
        raise ApiError(409, "insufficient_balance", "sell value is below the minimum order amount")

    detail = _order_detail(upbit, upbit.sell_market_order(market, volume))
    trade_state = state["trades"].setdefault(market, {})
    entry_state = dict(trade_state)
    executed_volume = autotrade._sum_trade_field(detail, "volume") or autotrade.safe_float(
        detail.get("executed_volume"), volume
    )
    entry_volume = autotrade.safe_float(entry_state.get("entry_volume"))
    entry_funds = autotrade.safe_float(entry_state.get("entry_funds_krw"))
    avg_buy_price = entry_funds / entry_volume if entry_volume else 0
    decision = {
        "ticker": market,
        "balance": executed_volume,
        "avg_buy_price": avg_buy_price,
        "current_price": current_price,
        "reason": "manual API order",
    }
    autotrade.append_trade_history(autotrade.build_sell_history_record(decision, detail, entry_state))
    trade_state["last_sell_ts"] = datetime.now().timestamp()
    remaining_ratio = max((entry_volume - executed_volume) / entry_volume, 0) if entry_volume else 0
    if remaining_ratio > 0.000001:
        for field in autotrade.ENTRY_STATE_FIELDS:
            trade_state[field] = autotrade.safe_float(entry_state.get(field)) * remaining_ratio
    else:
        for field in autotrade.ENTRY_STATE_FIELDS:
            trade_state.pop(field, None)
    autotrade.save_bot_state(state)
    return _public_order(detail, "SELL", market, idempotency_key)


def execute_manual_order(path, payload, upbit=None):
    if not MANUAL_TRADE_ENABLED:
        raise ApiError(503, "manual_trading_disabled", "MANUAL_TRADE_ENABLED is false")
    if payload.get("confirm") != "CONFIRM":
        raise ApiError(400, "confirmation_required", 'confirm must be exactly "CONFIRM"')
    market, idempotency_key = _validate_common(payload)
    upbit = upbit or autotrade.setup_api()
    if upbit is None:
        raise ApiError(503, "upbit_credentials_missing", "Upbit credentials are not configured")

    with autotrade.trade_execution_lock():
        history = _load_history()
        request_fingerprint = {
            "path": path,
            "market": market,
            "amount_krw": payload.get("amount_krw"),
            "percentage": payload.get("percentage", 100) if path == "/v1/orders/sell" else None,
        }
        existing = _existing_record(history, idempotency_key)
        if existing is not None:
            if existing.get("request") != request_fingerprint:
                raise ApiError(409, "idempotency_conflict", "idempotency_key was already used for another request")
            return existing.get("response"), True
        state = autotrade.load_bot_state()
        if path == "/v1/orders/buy":
            response = _execute_buy(upbit, payload, market, idempotency_key, state)
        elif path == "/v1/orders/sell":
            response = _execute_sell(upbit, payload, market, idempotency_key, state)
        else:
            raise ApiError(404, "not_found", "endpoint not found")
        history.append(
            {
                "recorded_at": _now(),
                "idempotency_key": idempotency_key,
                "request": request_fingerprint,
                "response": response,
            }
        )
        _save_history(history)
        return response, False


class ManualOrderHandler(BaseHTTPRequestHandler):
    server_version = "ManualOrderAPI/1.0"

    def _json_response(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path == "/health":
            self._json_response(200, {"status": "ok", "manual_trading_enabled": MANUAL_TRADE_ENABLED})
        else:
            self._json_response(404, {"error": {"code": "not_found", "message": "endpoint not found"}})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ApiError(400, "invalid_body", "request body is empty or too large")
            try:
                payload = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ApiError(400, "invalid_json", "request body must be valid JSON")
            if not isinstance(payload, dict):
                raise ApiError(400, "invalid_json", "request body must be a JSON object")
            response, replayed = execute_manual_order(path, payload)
            response = dict(response)
            response["idempotent_replay"] = replayed
            self._json_response(200, response)
        except ApiError as exc:
            self._json_response(exc.status, {"error": {"code": exc.code, "message": exc.message}})
        except Exception:
            logger.exception("Unhandled manual order API error")
            self._json_response(500, {"error": {"code": "internal_error", "message": "internal server error"}})

    def log_message(self, format_string, *args):
        logger.info("manual-api %s - %s", self.client_address[0], format_string % args)


def main():
    if not MANUAL_TRADE_ENABLED:
        logger.warning("Manual trading API started with MANUAL_TRADE_ENABLED=false")
    server = ThreadingHTTPServer((API_HOST, API_PORT), ManualOrderHandler)
    logger.info("Manual order API listening on %s:%s", API_HOST, API_PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
