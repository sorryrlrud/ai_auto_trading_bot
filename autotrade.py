import json
import logging
import math
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from functools import wraps

import pandas as pd
import pandas_ta as ta  # registers the df.ta accessor
import pyupbit
import requests
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("trading.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

load_dotenv()

MIN_ORDER_KRW = 5_000
ORDER_BUFFER = 0.995
LOOP_SLEEP_SECONDS = int(os.getenv("LOOP_SLEEP_SECONDS", "900"))
RISK_CHECK_SECONDS = max(5, int(os.getenv("RISK_CHECK_SECONDS", "60")))
ORDER_CONFIRM_ATTEMPTS = 3
ORDER_CONFIRM_SLEEP_SECONDS = 0.5
API_CALL_SLEEP_SECONDS = float(os.getenv("API_CALL_SLEEP_SECONDS", "0.12"))
UPBIT_HTTP_TIMEOUT_SECONDS = float(os.getenv("UPBIT_HTTP_TIMEOUT_SECONDS", "10"))
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "3"))
MAX_SINGLE_POSITION_PCT = float(os.getenv("MAX_SINGLE_POSITION_PCT", "25.0"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-2.2"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "3.2"))
PROFIT_PROTECT_PCT = float(os.getenv("PROFIT_PROTECT_PCT", "1.2"))
BASE_BUY_SCORE = float(os.getenv("BASE_BUY_SCORE", "10.0"))
MIN_HOLD_SECONDS = int(os.getenv("MIN_HOLD_SECONDS", "3600"))
TRADE_COOLDOWN_SECONDS = int(os.getenv("TRADE_COOLDOWN_SECONDS", "21600"))
CANDLE_CLOSE_BUFFER_SECONDS = int(os.getenv("CANDLE_CLOSE_BUFFER_SECONDS", "20"))
MAX_ENTRY_ATR_PCT = float(os.getenv("MAX_ENTRY_ATR_PCT", "12.0"))
ALLOW_DEFENSIVE_BUYS = os.getenv("ALLOW_DEFENSIVE_BUYS", "false").lower() == "true"
EXCLUDED_ENTRY_TICKERS = {
    ticker.strip()
    for ticker in os.getenv("EXCLUDED_ENTRY_TICKERS", "KRW-USDT,KRW-USDC,KRW-USD1").split(",")
    if ticker.strip()
}
MAX_RECORDED_ENTRY_REJECTIONS = int(os.getenv("MAX_RECORDED_ENTRY_REJECTIONS", "5"))
TRADE_ENABLED = os.getenv("TRADE_ENABLED", "false").lower() == "true"
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"
DASHBOARD_AUTO_PUBLISH = os.getenv("DASHBOARD_AUTO_PUBLISH", "false").lower() == "true"
DASHBOARD_HEARTBEAT_PUBLISH_SECONDS = int(os.getenv("DASHBOARD_HEARTBEAT_PUBLISH_SECONDS", "3600"))
TRADE_HISTORY_FILE = "trade_history.json"
DECISION_HISTORY_FILE = "decision_history.json"
BOT_STATE_FILE = "bot_state.json"
RUNTIME_STATUS_FILE = "runtime_status.json"
ENTRY_STATE_FIELDS = ("entry_volume", "entry_funds_krw", "entry_fee_krw")

_ORIGINAL_REQUESTS_METHODS = {name: getattr(requests, name) for name in ("get", "post", "delete")}


def _with_default_timeout(method, timeout_seconds):
    @wraps(method)
    def wrapper(*args, **kwargs):
        kwargs.setdefault("timeout", timeout_seconds)
        return method(*args, **kwargs)

    return wrapper


def configure_http_timeouts(timeout_seconds=UPBIT_HTTP_TIMEOUT_SECONDS):
    if timeout_seconds <= 0:
        for name, method in _ORIGINAL_REQUESTS_METHODS.items():
            setattr(requests, name, method)
        return

    for name, method in _ORIGINAL_REQUESTS_METHODS.items():
        setattr(requests, name, _with_default_timeout(method, timeout_seconds))


configure_http_timeouts()


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def finite_float(value, default=0.0):
    value = safe_float(value, default)
    if not math.isfinite(value):
        return default
    return value


def save_json_atomic(value, path):
    """Never leave a truncated runtime file after interruption."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, temporary = tempfile.mkstemp(prefix=".bot-json-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_bot_state(path=BOT_STATE_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {}
    state.setdefault("trades", {})
    return state


def save_bot_state(state, path=BOT_STATE_FILE):
    save_json_atomic(state, path)


def _sleep_api():
    if API_CALL_SLEEP_SECONDS > 0:
        time.sleep(API_CALL_SLEEP_SECONDS)


def _upbit_error_message(payload):
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    name = error.get("name", "unknown_error")
    message = error.get("message", "unknown Upbit error")
    return f"{name}: {message}"


def setup_api():
    access = os.getenv("UPBIT_ACCESS_KEY")
    secret = os.getenv("UPBIT_SECRET_KEY")

    if not access or not secret:
        logger.error("UPBIT_ACCESS_KEY/UPBIT_SECRET_KEY is missing.")
        return None

    upbit = pyupbit.Upbit(access, secret)
    logger.info("Running rule-based mode. No LLM or Google API is used.")
    return upbit


def load_recent_performance(path=TRADE_HISTORY_FILE, limit=20):
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        rows = []

    # Ignore ambiguous legacy rows that predate explicit order-side tracking.
    # Without an explicit SELL marker, a row is not safe to use as realized
    # performance input for the live strategy.
    realized_rows = [row for row in rows if row.get("side") == "SELL"]
    recent = realized_rows[-limit:]
    profits = [safe_float(row.get("profit_pct", row.get("profit"))) for row in recent]
    losses = [p for p in profits if p < 0]

    return {
        "count": len(profits),
        "avg_profit": round(sum(profits) / len(profits), 3) if profits else 0.0,
        "loss_rate": round(len(losses) / len(profits), 3) if profits else 0.0,
        "net_profit": round(sum(profits), 3),
    }


def append_trade_history(record, path=TRADE_HISTORY_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = json.load(f)
    except FileNotFoundError:
        rows = []

    if record.get("order_uuid") and any(row.get("order_uuid") == record["order_uuid"] for row in rows):
        return False
    rows.append(record)
    save_json_atomic(rows, path)
    return True


def load_decision_history(path=DECISION_HISTORY_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        rows = []
    return rows if isinstance(rows, list) else []


def _iso_now(now=None):
    now = now or datetime.now().astimezone()
    return now.astimezone().isoformat(timespec="seconds")


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def load_runtime_status(path=RUNTIME_STATUS_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            status = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        status = {}
    return status if isinstance(status, dict) else {}


def save_runtime_status(status, path=RUNTIME_STATUS_FILE):
    save_json_atomic(status, path)


def mark_cycle_started(path=RUNTIME_STATUS_FILE, now=None):
    status = load_runtime_status(path)
    status.update(
        {
            "loop_interval_seconds": LOOP_SLEEP_SECONDS,
            "heartbeat_publish_interval_seconds": DASHBOARD_HEARTBEAT_PUBLISH_SECONDS,
            "last_cycle_started_at": _iso_now(now),
        }
    )
    save_runtime_status(status, path)
    return status


def mark_cycle_succeeded(next_expected_cycle_at=None, path=RUNTIME_STATUS_FILE, now=None):
    status = load_runtime_status(path)
    now_iso = _iso_now(now)
    status.update(
        {
            "loop_interval_seconds": LOOP_SLEEP_SECONDS,
            "heartbeat_publish_interval_seconds": DASHBOARD_HEARTBEAT_PUBLISH_SECONDS,
            "last_cycle_completed_at": now_iso,
            "last_success_at": now_iso,
            "next_expected_cycle_at": next_expected_cycle_at,
            "consecutive_failures": 0,
        }
    )
    save_runtime_status(status, path)
    return status


def mark_cycle_failed(error, path=RUNTIME_STATUS_FILE, now=None):
    status = load_runtime_status(path)
    status.update(
        {
            "loop_interval_seconds": LOOP_SLEEP_SECONDS,
            "heartbeat_publish_interval_seconds": DASHBOARD_HEARTBEAT_PUBLISH_SECONDS,
            "last_error_at": _iso_now(now),
            "last_error_type": type(error).__name__,
            "consecutive_failures": int(status.get("consecutive_failures", 0)) + 1,
        }
    )
    save_runtime_status(status, path)
    return status


def should_refresh_dashboard_for_heartbeat(
    status=None,
    *,
    now=None,
    interval_seconds=DASHBOARD_HEARTBEAT_PUBLISH_SECONDS,
):
    if interval_seconds <= 0:
        return False

    status = status or load_runtime_status()
    last_refresh = _parse_iso_datetime(status.get("last_dashboard_refresh_at"))
    if last_refresh is None:
        return True

    now_dt = now or datetime.now().astimezone()
    return now_dt - last_refresh >= timedelta(seconds=interval_seconds)


def mark_dashboard_refreshed(path=RUNTIME_STATUS_FILE, now=None):
    status = load_runtime_status(path)
    status["last_dashboard_refresh_at"] = _iso_now(now)
    save_runtime_status(status, path)
    return status


def _decision_snapshot_payload(plan):
    return {
        "risk_mode": plan.get("risk_mode", "unknown"),
        "cash_reserve_pct": plan.get("cash_reserve_pct"),
        "max_single_position_pct": plan.get("max_single_position_pct"),
        "buy_threshold": plan.get("buy_threshold"),
        "buy_budget_krw": plan.get("buy_budget_krw"),
        "entry_block_reason": plan.get("entry_block_reason"),
        "entry_rejections": plan.get("entry_rejections", []),
        "decisions": plan.get("decisions", []),
    }


def _decision_snapshot_signature(row):
    return {
        "risk_mode": row.get("risk_mode", "unknown"),
        "cash_reserve_pct": row.get("cash_reserve_pct"),
        "max_single_position_pct": row.get("max_single_position_pct"),
        "buy_threshold": row.get("buy_threshold"),
        "buy_budget_krw": row.get("buy_budget_krw"),
        "entry_block_reason": row.get("entry_block_reason"),
        "entry_rejections": row.get("entry_rejections", []),
        "decisions": row.get("decisions", []),
    }


def append_decision_history(plan, path=DECISION_HISTORY_FILE, keep=20):
    rows = load_decision_history(path)
    payload = _decision_snapshot_payload(plan)
    if rows and _decision_snapshot_signature(rows[-1]) == payload:
        return False

    rows.append({"recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"), **payload})
    rows = rows[-keep:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return True


def refresh_dashboard():
    try:
        subprocess.run(["python", "generate_dashboard.py"], check=True, capture_output=True, text=True, timeout=30)
        if DASHBOARD_AUTO_PUBLISH:
            subprocess.run(["python", "publish_dashboard.py"], check=True, capture_output=True, text=True, timeout=30)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(
            "Dashboard refresh error: command=%s returncode=%s stdout=%s stderr=%s",
            e.cmd,
            e.returncode,
            (e.stdout or "").strip() or "-",
            (e.stderr or "").strip() or "-",
        )
    except Exception as e:
        logger.error(f"Dashboard refresh error: {e}")
    return False


def _sum_trade_field(order, field):
    trades = order.get("trades", []) if isinstance(order, dict) else []
    return sum(safe_float(trade.get(field)) for trade in trades if isinstance(trade, dict))


def build_buy_state_record(order=None):
    order = order if isinstance(order, dict) else {}
    return {
        "entry_volume": round(_sum_trade_field(order, "volume") or safe_float(order.get("executed_volume")), 12),
        "entry_funds_krw": round(_sum_trade_field(order, "funds"), 8),
        "entry_fee_krw": round(safe_float(order.get("paid_fee")), 8),
    }


def build_sell_history_record(decision, order=None, entry_state=None):
    order = order if isinstance(order, dict) else {}
    entry_state = entry_state if isinstance(entry_state, dict) else {}
    executed_volume = _sum_trade_field(order, "volume")
    gross_proceeds = _sum_trade_field(order, "funds")
    if executed_volume <= 0 or gross_proceeds <= 0:
        raise ValueError("Realized PnL requires confirmed fills; a holding snapshot is not a fill")
    sell_fee_krw = safe_float(order.get("paid_fee"))
    buy_fee_krw = safe_float(entry_state.get("entry_fee_krw"))
    entry_volume = safe_float(entry_state.get("entry_volume"))
    if buy_fee_krw and entry_volume and executed_volume:
        buy_fee_krw *= min(executed_volume / entry_volume, 1.0)
    fee_krw = buy_fee_krw + sell_fee_krw
    avg_buy_price = safe_float(decision.get("avg_buy_price"))
    avg_sell_price = gross_proceeds / executed_volume if executed_volume else safe_float(decision.get("current_price"))
    cost_basis = executed_volume * avg_buy_price
    profit_krw = gross_proceeds - fee_krw - cost_basis
    invested_krw = cost_basis + buy_fee_krw
    profit_pct = (profit_krw / invested_krw * 100) if invested_krw else safe_float(decision.get("profit_pct"))

    return {
        "order_uuid": order.get("uuid"),
        "executed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "side": "SELL",
        "ticker": decision["ticker"],
        "quantity": round(executed_volume, 12),
        "avg_buy_price": round(avg_buy_price, 8),
        "avg_sell_price": round(avg_sell_price, 8),
        "cost_basis_krw": round(cost_basis, 2),
        "gross_proceeds_krw": round(gross_proceeds, 2),
        "buy_fee_krw": round(buy_fee_krw, 2),
        "sell_fee_krw": round(sell_fee_krw, 2),
        "fee_krw": round(fee_krw, 2),
        "profit_krw": round(profit_krw, 2),
        "profit_pct": round(profit_pct, 4),
        "reason": decision.get("reason", ""),
        "source": "order_detail",
    }


def get_market_context():
    try:
        btc_df = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=80)
        _sleep_api()
        if btc_df is None or len(btc_df) < 30:
            return {"btc_trend": "unknown", "risk_mode": "defensive"}

        btc_df = _completed_candles(btc_df, min_rows=60)
        if btc_df is None:
            return {"btc_trend": "unknown", "risk_mode": "defensive"}
        btc_df.ta.rsi(append=True)
        btc_df["MA_20"] = btc_df["close"].rolling(20).mean()
        btc_df["MA_60"] = btc_df["close"].rolling(60).mean()

        current_price = pyupbit.get_current_price("KRW-BTC")
        _sleep_api()
        rsi = finite_float(btc_df["RSI_14"].iloc[-1], 50.0)
        ma20 = finite_float(btc_df["MA_20"].iloc[-1])
        ma60 = finite_float(btc_df["MA_60"].iloc[-1])
        volatility = finite_float(btc_df["close"].pct_change().std() * 100)

        if current_price > ma20 > ma60 and rsi < 72:
            trend = "bullish"
            risk_mode = "normal"
        elif current_price < ma20 or ma20 < ma60:
            trend = "bearish"
            risk_mode = "defensive"
        else:
            trend = "mixed"
            risk_mode = "balanced"

        if rsi > 72:
            trend += "_overbought"
            risk_mode = "defensive"
        elif rsi < 32:
            trend += "_oversold"

        return {
            "btc_trend": trend,
            "risk_mode": risk_mode,
            "btc_rsi": round(rsi, 2),
            "btc_above_ma20": bool(current_price > ma20),
            "btc_above_ma60": bool(current_price > ma60),
            "market_volatility": "high" if volatility > 3 else "normal",
            "btc_volatility_pct": round(volatility, 2),
        }
    except Exception as e:
        logger.error(f"Market context error: {e}")
        return {"btc_trend": "error", "risk_mode": "defensive"}


def _atr_pct(df, current_price):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(14).mean().iloc[-1]
    if not current_price:
        return 0.0
    return finite_float((atr / current_price) * 100)


def _completed_candles(df, min_rows=30):
    """Drop the latest in-progress candle and keep only completed candles."""
    if df is None or len(df) < min_rows + 1:
        return None
    return df.iloc[:-1].copy()


def _add_basic_indicators(df, ma_long=20):
    df.ta.rsi(append=True)
    df.ta.macd(append=True)
    df["MA_5"] = df["close"].rolling(5).mean()
    df[f"MA_{ma_long}"] = df["close"].rolling(ma_long).mean()
    return df


def _trend_snapshot(df, ma_long=20):
    ma_col = f"MA_{ma_long}"
    return {
        "rsi": round(finite_float(df["RSI_14"].iloc[-1], 50.0), 2),
        "macd_hist": round(finite_float(df["MACDh_12_26_9"].iloc[-1]), 4),
        "ma5_over_long": bool(df["MA_5"].iloc[-1] > df[ma_col].iloc[-1]),
        "price_over_long": bool(df["close"].iloc[-1] > df[ma_col].iloc[-1]),
        "volume_ratio": round(finite_float(df["volume"].iloc[-1] / df["volume"].rolling(20).mean().iloc[-1], 1.0), 2),
    }


def get_market_data(ticker):
    try:
        df = pyupbit.get_ohlcv(ticker, interval="day", count=100)
        _sleep_api()
        if df is None or len(df) < 60:
            return None

        df_1h = pyupbit.get_ohlcv(ticker, interval="minute60", count=80)
        _sleep_api()
        df_15m = pyupbit.get_ohlcv(ticker, interval="minute15", count=80)
        _sleep_api()
        if df_1h is None or len(df_1h) < 30 or df_15m is None or len(df_15m) < 30:
            return None

        df = _completed_candles(df, min_rows=60)
        df_1h = _completed_candles(df_1h, min_rows=30)
        df_15m = _completed_candles(df_15m, min_rows=30)
        if df is None or df_1h is None or df_15m is None:
            return None

        df = _add_basic_indicators(df)
        df["MA_5"] = df["close"].rolling(5).mean()
        df["MA_20"] = df["close"].rolling(20).mean()
        df["MA_60"] = df["close"].rolling(60).mean()
        df_1h = _add_basic_indicators(df_1h)
        df_15m = _add_basic_indicators(df_15m)

        current_price = pyupbit.get_current_price(ticker)
        _sleep_api()
        if not current_price:
            return None

        volume_ratio = finite_float(df["volume"].iloc[-1] / df["volume"].rolling(20).mean().iloc[-1], 1.0)
        price_change_1d = finite_float(df["close"].pct_change().iloc[-1] * 100)
        price_change_3d = finite_float((df["close"].iloc[-1] / df["close"].iloc[-4] - 1) * 100)
        price_change_1h = finite_float((df_15m["close"].iloc[-1] / df_15m["close"].iloc[-5] - 1) * 100)
        price_change_6h = finite_float((df_1h["close"].iloc[-1] / df_1h["close"].iloc[-7] - 1) * 100)
        ma20 = finite_float(df["MA_20"].iloc[-1])
        ma60 = finite_float(df["MA_60"].iloc[-1])
        bb_mid = df["close"].rolling(20).mean()
        bb_std = df["close"].rolling(20).std()
        bb_upper = finite_float((bb_mid + 2 * bb_std).iloc[-1])
        bb_lower = finite_float((bb_mid - 2 * bb_std).iloc[-1])
        bb_range = max(bb_upper - bb_lower, 1)
        bb_position = (current_price - bb_lower) / bb_range

        return {
            "coin": ticker,
            "p": current_price,
            "volume_ratio": round(volume_ratio, 2),
            "price_change_1d": round(price_change_1d, 2),
            "price_change_3d": round(price_change_3d, 2),
            "price_change_1h": round(price_change_1h, 2),
            "price_change_6h": round(price_change_6h, 2),
            "atr_pct": round(_atr_pct(df, current_price), 2),
            "indicators": {
                "daily": {
                    "rsi": round(finite_float(df["RSI_14"].iloc[-1], 50.0), 2),
                    "macd_hist": round(finite_float(df["MACDh_12_26_9"].iloc[-1]), 4),
                    "ma5_over_20": bool(df["MA_5"].iloc[-1] > ma20),
                    "ma20_over_60": bool(ma20 > ma60),
                    "price_over_ma20": bool(current_price > ma20),
                    "bb_position": round(finite_float(bb_position, 0.5), 2),
                },
                "1h": _trend_snapshot(df_1h),
                "15m": _trend_snapshot(df_15m),
            },
        }
    except Exception as e:
        logger.error(f"Error gathering data for {ticker}: {e}")
        return None


def get_current_holdings(upbit):
    holdings = []
    balances = upbit.get_balances()
    error_message = _upbit_error_message(balances)
    if error_message:
        raise RuntimeError(f"Upbit balances API error: {error_message}")
    if not isinstance(balances, list):
        raise RuntimeError(f"Unexpected Upbit balances response type: {type(balances).__name__}")

    for balance in balances:
        if not isinstance(balance, dict):
            raise RuntimeError(f"Unexpected Upbit balance item type: {type(balance).__name__}")
        currency = balance.get("currency")
        amount = safe_float(balance.get("balance"))
        if currency == "KRW" or amount <= 0:
            continue

        ticker = f"KRW-{currency}"
        current_price = pyupbit.get_current_price(ticker)
        _sleep_api()
        avg_buy_price = safe_float(balance.get("avg_buy_price"))
        if not finite_float(current_price) or current_price <= 0:
            logger.warning("Price unavailable for held asset %s; skipping its valuation", ticker)
            continue
        value = amount * current_price if current_price else 0
        profit_pct = ((current_price / avg_buy_price) - 1) * 100 if current_price and avg_buy_price else 0.0

        if value >= MIN_ORDER_KRW:
            holdings.append(
                {
                    "ticker": ticker,
                    "balance": amount,
                    "avg_buy_price": avg_buy_price,
                    "current_price": current_price,
                    "value": round(value, 0),
                    "profit_pct": round(profit_pct, 2),
                }
            )
    return holdings


def _chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def get_top_volume_targets(limit=25):
    all_krw = pyupbit.get_tickers(fiat="KRW")
    rows = []
    for chunk in _chunks(all_krw, 100):
        response = requests.get("https://api.upbit.com/v1/ticker", params={"markets": ",".join(chunk)}, timeout=10)
        response.raise_for_status()
        rows.extend(response.json())
        _sleep_api()

    eligible = [row for row in rows if row["market"] not in EXCLUDED_ENTRY_TICKERS]
    return [row["market"] for row in sorted(eligible, key=lambda x: x["acc_trade_price_24h"], reverse=True)[:limit]]


def cash_reserve_pct(market_context, recent_performance):
    reserve = 25
    risk_mode = market_context.get("risk_mode")

    if risk_mode == "defensive":
        reserve = 60
    elif risk_mode == "balanced":
        reserve = 40

    if market_context.get("market_volatility") == "high":
        reserve += 10

    if recent_performance["count"] >= 5 and recent_performance["avg_profit"] < 0:
        reserve += 10
    if recent_performance["loss_rate"] >= 0.6:
        reserve += 10

    return min(reserve, 85)


def buy_score_threshold(market_context, recent_performance):
    threshold = BASE_BUY_SCORE
    if market_context.get("risk_mode") == "defensive":
        threshold += 1.5
    if market_context.get("market_volatility") == "high":
        threshold += 0.75
    if recent_performance["loss_rate"] >= 0.6:
        threshold += 1.0
    return threshold


def entry_block_reason(data, market_context):
    daily = data["indicators"]["daily"]
    hour = data["indicators"]["1h"]
    minute = data["indicators"]["15m"]

    if data["coin"] in EXCLUDED_ENTRY_TICKERS:
        return "전략 제외 종목"
    if market_context.get("risk_mode") == "defensive" and not ALLOW_DEFENSIVE_BUYS:
        return "BTC 방어장세에서는 신규 매수 차단"
    if data["atr_pct"] > MAX_ENTRY_ATR_PCT:
        return f"ATR {data['atr_pct']}% > {MAX_ENTRY_ATR_PCT}%"
    if not daily["ma20_over_60"]:
        return "일봉 장기 추세 미정렬(MA20<=MA60)"
    if not daily["price_over_ma20"]:
        return "현재가가 일봉 MA20 아래"
    if not (hour["ma5_over_long"] and hour["price_over_long"] and hour["macd_hist"] > 0):
        return "1시간 추세 미정렬"
    if not (minute["ma5_over_long"] and minute["price_over_long"] and minute["macd_hist"] > 0):
        return "15분 추세 미정렬"
    if daily["rsi"] > 72 or hour["rsi"] > 75 or minute["rsi"] > 78:
        return "과열 구간"
    if data["volume_ratio"] > 5 or data["price_change_1d"] > 12 or data["price_change_1h"] > 7:
        return "급등 추격 구간"
    return None


def score_coin(data, market_context):
    daily = data["indicators"]["daily"]
    hour = data["indicators"]["1h"]
    minute = data["indicators"]["15m"]
    rsi = daily["rsi"]
    score = 0.0
    reasons = []

    if daily["ma5_over_20"]:
        score += 1.0
        reasons.append("MA5>MA20")
    if daily["ma20_over_60"]:
        score += 1.0
        reasons.append("MA20>MA60")
    if daily["price_over_ma20"]:
        score += 1.0
        reasons.append("price>MA20")
    if daily["macd_hist"] > 0:
        score += 0.75
        reasons.append("MACD+")
    if 45 <= rsi <= 68:
        score += 0.75
        reasons.append("RSI healthy")
    elif 35 <= rsi < 45:
        score += 0.75
        reasons.append("RSI rebound zone")
    elif rsi > 72:
        score -= 2.0
        reasons.append("RSI overbought")
    elif rsi < 30:
        score -= 0.75
        reasons.append("falling knife risk")

    if hour["ma5_over_long"]:
        score += 1.5
        reasons.append("1h MA5>MA20")
    if hour["price_over_long"]:
        score += 1.5
        reasons.append("1h price>MA20")
    if hour["macd_hist"] > 0:
        score += 1.25
        reasons.append("1h MACD+")
    if 48 <= hour["rsi"] <= 68:
        score += 1.0
        reasons.append("1h RSI ok")
    elif hour["rsi"] > 75:
        score -= 1.25
        reasons.append("1h overheated")

    if minute["ma5_over_long"]:
        score += 1.0
        reasons.append("15m MA5>MA20")
    if minute["price_over_long"]:
        score += 1.0
        reasons.append("15m price>MA20")
    if minute["macd_hist"] > 0:
        score += 1.0
        reasons.append("15m MACD+")
    if 45 <= minute["rsi"] <= 70:
        score += 0.75
        reasons.append("15m RSI ok")
    elif minute["rsi"] > 78:
        score -= 1.5
        reasons.append("15m overheated")

    volume_ratio = data["volume_ratio"]
    if 1.2 <= volume_ratio <= 3.5:
        score += 1.0
        reasons.append("volume expansion")
    elif volume_ratio > 5:
        score -= 1.0
        reasons.append("volume blow-off")

    if -1.5 <= data["price_change_1d"] <= 8:
        score += 0.75
        reasons.append("1d move controlled")
    elif data["price_change_1d"] > 12:
        score -= 1.25
        reasons.append("too extended")

    if 0.2 <= data["price_change_1h"] <= 4:
        score += 0.75
        reasons.append("1h momentum")
    elif data["price_change_1h"] > 7:
        score -= 2.0
        reasons.append("1h too extended")
    elif data["price_change_1h"] < -1:
        score -= 1.0
        reasons.append("1h weak")

    if -2 <= data["price_change_6h"] <= 9:
        score += 0.5
        reasons.append("6h move controlled")

    if data["atr_pct"] > MAX_ENTRY_ATR_PCT:
        score -= 1.0
        reasons.append("ATR too high")

    if market_context.get("risk_mode") == "defensive":
        score -= 1.0
        reasons.append("BTC defensive")

    return round(score, 2), ", ".join(reasons)


def holding_age_seconds(holding, state, now_ts):
    trade = state.get("trades", {}).get(holding["ticker"], {})
    last_buy_ts = trade.get("last_buy_ts")
    if not last_buy_ts:
        return None
    return max(now_ts - last_buy_ts, 0)


def is_buy_cooldown(ticker, state, now_ts):
    trade = state.get("trades", {}).get(ticker, {})
    last_exit_ts = max(trade.get("last_sell_ts", 0), trade.get("last_buy_ts", 0))
    return last_exit_ts and now_ts - last_exit_ts < TRADE_COOLDOWN_SECONDS


def should_sell_holding(holding, data_by_ticker, market_context, state, now_ts):
    ticker = holding["ticker"]
    profit_pct = holding["profit_pct"]
    data = data_by_ticker.get(ticker)
    age = holding_age_seconds(holding, state, now_ts)

    if profit_pct <= STOP_LOSS_PCT:
        return True, f"손실 {profit_pct}%로 손절 기준 도달"

    if not data:
        if market_context.get("risk_mode") == "defensive" and profit_pct < -1.0:
            return True, "방어장세에서 데이터 부족 보유종목 손실 축소"
        return False, "데이터 부족으로 유지"

    daily = data["indicators"]["daily"]
    hour = data["indicators"]["1h"]
    minute = data["indicators"]["15m"]
    trend_broken = not daily["price_over_ma20"] and not daily["ma5_over_20"] and daily["macd_hist"] < 0
    hour_broken = not hour["price_over_long"] and not hour["ma5_over_long"] and hour["macd_hist"] < 0
    short_broken = not minute["price_over_long"] and not minute["ma5_over_long"] and minute["macd_hist"] < 0
    overheated = daily["rsi"] > 72 or daily["bb_position"] > 1.05
    intraday_overheated = hour["rsi"] > 75 or minute["rsi"] > 78

    if profit_pct >= TAKE_PROFIT_PCT and (overheated or intraday_overheated or short_broken):
        return True, f"수익 {profit_pct}% 및 과열 신호로 익절"
    if profit_pct >= PROFIT_PROTECT_PCT and short_broken:
        return True, f"수익 {profit_pct}% 보호: 15분 추세 훼손"
    if age is not None and age < MIN_HOLD_SECONDS and profit_pct > STOP_LOSS_PCT:
        return False, f"최소 보유시간 유지({int(age)}초/{MIN_HOLD_SECONDS}초)"
    if profit_pct < -0.7 and short_broken and hour_broken:
        return True, f"손실 {profit_pct}% 및 15분/1시간 추세 동반 훼손"
    if profit_pct < 0 and trend_broken:
        return True, f"손실 {profit_pct}% 상태에서 추세 훼손"
    if market_context.get("risk_mode") == "defensive" and (trend_broken or hour_broken):
        return True, "BTC 방어장세 및 개별 추세 훼손"

    return False, "보유 추세 유지"


def build_rebalance_plan(market_data, market_context, krw, current_holdings, recent_performance, state=None, now_ts=None):
    state = state or {"trades": {}}
    now_ts = now_ts or time.time()
    data_by_ticker = {row["coin"]: row for row in market_data}
    reserve_pct = cash_reserve_pct(market_context, recent_performance)
    threshold = buy_score_threshold(market_context, recent_performance)
    decisions = []
    entry_rejections = []
    entry_gate = None
    if market_context.get("risk_mode") == "defensive" and not ALLOW_DEFENSIVE_BUYS:
        entry_gate = "BTC 방어장세에서는 신규 매수 차단"

    for holding in current_holdings:
        sell, reason = should_sell_holding(holding, data_by_ticker, market_context, state, now_ts)
        decision = {
            "ticker": holding["ticker"],
            "decision": "SELL" if sell else "HOLD",
            "reason": reason,
        }
        if sell:
            decision.update(
                {
                    "balance": holding["balance"],
                    "avg_buy_price": holding["avg_buy_price"],
                    "current_price": holding["current_price"],
                    "profit_pct": holding["profit_pct"],
                }
            )
        decisions.append(decision)

    held_tickers = {holding["ticker"] for holding in current_holdings}
    sell_tickers = {d["ticker"] for d in decisions if d["decision"] == "SELL"}
    remaining_positions = len(held_tickers - sell_tickers)
    buy_slots = max(MAX_POSITIONS - remaining_positions, 0)
    remaining_value = sum(holding["value"] for holding in current_holdings if holding["ticker"] not in sell_tickers)
    portfolio_value = krw + sum(holding["value"] for holding in current_holdings)
    max_invested_value = portfolio_value * (1 - reserve_pct / 100)
    available_buy_budget_krw = max(max_invested_value - remaining_value, 0)
    max_single_position_krw = portfolio_value * MAX_SINGLE_POSITION_PCT / 100

    scored = []
    for row in market_data:
        ticker = row["coin"]
        if ticker in held_tickers:
            continue
        if is_buy_cooldown(ticker, state, now_ts):
            continue
        rejected = entry_gate or entry_block_reason(row, market_context)
        if rejected:
            if not entry_gate:
                score, _ = score_coin(row, market_context)
                entry_rejections.append({"ticker": ticker, "score": score, "reason": rejected})
            continue
        score, reason = score_coin(row, market_context)
        if score >= threshold:
            scored.append({"ticker": ticker, "score": score, "reason": reason})

    scored.sort(key=lambda x: x["score"], reverse=True)
    selected_candidates = scored[:buy_slots]
    for candidate in selected_candidates:
        decisions.append(
            {
                "ticker": candidate["ticker"],
                "decision": "BUY",
                "score": candidate["score"],
                "reason": f"score {candidate['score']} >= {round(threshold, 2)}: {candidate['reason']}",
            }
        )

    buy_budget_krw = min(
        available_buy_budget_krw,
        max_single_position_krw * len(selected_candidates),
    )

    entry_rejections.sort(key=lambda x: x["score"], reverse=True)
    entry_rejections = entry_rejections[:MAX_RECORDED_ENTRY_REJECTIONS]

    return {
        "decisions": decisions,
        "cash_reserve_pct": reserve_pct,
        "max_single_position_pct": MAX_SINGLE_POSITION_PCT,
        "buy_threshold": round(threshold, 2),
        "buy_budget_krw": round(buy_budget_krw, 0),
        "entry_block_reason": entry_gate,
        "entry_rejections": entry_rejections,
        "risk_mode": market_context.get("risk_mode", "unknown"),
        "krw": krw,
    }


def seconds_until_next_cycle(now_ts=None, interval_seconds=LOOP_SLEEP_SECONDS, buffer_seconds=CANDLE_CLOSE_BUFFER_SECONDS):
    now_ts = now_ts or time.time()
    next_boundary = ((int(now_ts) // interval_seconds) + 1) * interval_seconds + buffer_seconds
    return max(next_boundary - now_ts, 1)


def confirmed_order_detail(upbit, order_uuid):
    """Accept terminal orders only, including a market buy with refunded dust."""
    for attempt in range(ORDER_CONFIRM_ATTEMPTS):
        try:
            order = upbit.get_order(order_uuid)
            if isinstance(order, dict) and order.get("state") in {"done", "cancel"}:
                volume = finite_float(order.get("executed_volume"), -1)
                filled = _sum_trade_field(order, "volume")
                funds = _sum_trade_field(order, "funds")
                fee = finite_float(order.get("paid_fee"), -1)
                if volume == 0 and filled == 0 and order["state"] == "cancel":
                    return dict(order, uuid=order_uuid)
                if (volume > 0 and funds > 0 and math.isfinite(funds) and fee >= 0
                        and math.isclose(filled, volume, rel_tol=1e-7, abs_tol=1e-12)):
                    return dict(order, uuid=order_uuid)
        except Exception as error:
            logger.warning("Order confirmation failed for %s: %s", order_uuid, error)
        if attempt + 1 < ORDER_CONFIRM_ATTEMPTS:
            time.sleep(ORDER_CONFIRM_SLEEP_SECONDS)
    return None


def reconcile_pending_orders(upbit, state):
    """Retry read-only confirmation after timeouts/restarts; never resubmit."""
    history_changed = False
    pending_orders = state.setdefault("pending_orders", {})
    for order_uuid, pending in list(pending_orders.items()):
        order = confirmed_order_detail(upbit, order_uuid)
        if order is None:
            logger.warning("[ORDER PENDING] %s %s", pending["decision"]["ticker"], order_uuid)
            continue
        decision = pending["decision"]
        ticker = decision["ticker"]
        volume = _sum_trade_field(order, "volume")
        if volume > 0:
            # Apply from the persisted pre-order snapshot so crash recovery is idempotent.
            trade_state = dict(pending["entry_state"])
            if decision["decision"] == "BUY":
                trade_state.update(build_buy_state_record(order))
                trade_state["last_buy_ts"] = pending["submitted_at"]
                logger.info("[BUY CONFIRMED] %s volume=%s", ticker, volume)
            else:
                record = build_sell_history_record(decision, order, entry_state=trade_state)
                append_trade_history(record)
                history_changed = True
                trade_state["last_sell_ts"] = pending["submitted_at"]
                entry_volume = safe_float(trade_state.get("entry_volume"))
                remaining_ratio = max(1 - volume / entry_volume, 0) if entry_volume else 0
                for field in ENTRY_STATE_FIELDS:
                    if remaining_ratio > 1e-7:
                        trade_state[field] = safe_float(trade_state.get(field)) * remaining_ratio
                    else:
                        trade_state.pop(field, None)
                logger.info("[REALIZED] %s profit=%s KRW (%s%%)", ticker, record["profit_krw"], record["profit_pct"])
            state["trades"][ticker] = trade_state
        else:
            logger.warning("[ORDER CANCELED WITHOUT FILL] %s %s", ticker, order_uuid)
        del pending_orders[order_uuid]
        save_bot_state(state)
    return history_changed


def track_submitted_order(upbit, result, decision, state):
    order_uuid = result["uuid"]
    state.setdefault("pending_orders", {})[order_uuid] = {
        "decision": dict(decision),
        "entry_state": dict(state["trades"].get(decision["ticker"], {})),
        "submitted_at": time.time(),
    }
    save_bot_state(state)
    return reconcile_pending_orders(upbit, state)


def execute_rebalance_plan(upbit, plan, state=None):
    state = state or {"trades": {}}
    state.setdefault("trades", {})
    pending_at_start = {p["decision"]["ticker"] for p in state.get("pending_orders", {}).values()}
    trade_history_changed = reconcile_pending_orders(upbit, state) if TRADE_ENABLED else False
    decisions = plan.get("decisions", [])
    if not decisions:
        logger.info("No decisions to execute.")
        return trade_history_changed

    sells_completed = True

    for decision in decisions:
        if decision["decision"] != "SELL":
            continue

        ticker = decision["ticker"]
        if ticker in pending_at_start or any(p["decision"]["ticker"] == ticker for p in state.get("pending_orders", {}).values()):
            sells_completed = False
            continue
        balance = upbit.get_balance(ticker.split("-")[1])
        balance = min(finite_float(balance), safe_float(decision.get("balance")))
        current_price = pyupbit.get_current_price(ticker)
        if balance and current_price and balance * current_price >= MIN_ORDER_KRW:
            if not TRADE_ENABLED:
                logger.info(f"[DRY RUN SELL] {ticker} | {decision['reason']}")
                continue
            logger.info(f"[SELL] {ticker} | {decision['reason']}")
            result = upbit.sell_market_order(ticker, balance)
            if result and "uuid" in result:
                changed = track_submitted_order(upbit, result, dict(decision, balance=balance), state)
                trade_history_changed = changed or trade_history_changed
                # A rejected, pending or partial exit cannot fund its planned replacement.
                remaining = upbit.get_balance(ticker.split("-")[1])
                if finite_float(remaining, -1) < 0 or finite_float(remaining) > 1e-10:
                    sells_completed = False
            else:
                logger.error(f"[SELL FAILED] {ticker} : {result}")
                sells_completed = False
            time.sleep(1)
        else:
            sells_completed = False

    buy_targets = [d for d in decisions if d["decision"] == "BUY"]
    if not buy_targets:
        for decision in decisions:
            if decision["decision"] == "HOLD":
                logger.info("[HOLD] %s | %s", decision["ticker"], decision["reason"])
        return trade_history_changed
    if not sells_completed or pending_at_start or state.get("pending_orders"):
        logger.warning("[BUY BLOCKED] An exit is incomplete or an order awaits confirmation")
        return trade_history_changed

    krw = upbit.get_balance("KRW")
    if krw is None or not math.isfinite(float(krw)) or krw < 0:
        raise RuntimeError("Invalid KRW balance; refusing to allocate new entries")
    investable_krw = min(krw, plan.get("buy_budget_krw", krw * (1 - plan["cash_reserve_pct"] / 100)))

    if buy_targets and investable_krw >= MIN_ORDER_KRW:
        amount_per_coin = (investable_krw * ORDER_BUFFER) / len(buy_targets)
        for decision in buy_targets:
            if amount_per_coin < MIN_ORDER_KRW:
                logger.info(f"[BUY SKIP] {decision['ticker']} | order amount below minimum")
                continue
            if not TRADE_ENABLED:
                logger.info(f"[DRY RUN BUY] {decision['ticker']} {int(amount_per_coin)} KRW | {decision['reason']}")
                continue
            result = upbit.buy_market_order(decision["ticker"], amount_per_coin)
            if result and "uuid" in result:
                logger.info(f"[BUY] {decision['ticker']} {int(amount_per_coin)} KRW | {decision['reason']}")
                changed = track_submitted_order(upbit, result, decision, state)
                trade_history_changed = changed or trade_history_changed
                if state.get("pending_orders"):
                    break
            else:
                logger.error(f"[BUY FAILED] {decision['ticker']} : {result}")
            time.sleep(1)

    for decision in decisions:
        if decision["decision"] == "HOLD":
            logger.info(f"[HOLD] {decision['ticker']} | {decision['reason']}")
    return trade_history_changed


class RiskMonitor:
    """Check the existing hard stop between candle scans, without creating entries."""

    def __init__(self, upbit):
        self.upbit = upbit
        self.next_check = 0.0

    def check(self):
        if time.monotonic() < self.next_check:
            return
        self.next_check = time.monotonic() + RISK_CHECK_SECONDS
        try:
            state = load_bot_state()
            changed = reconcile_pending_orders(self.upbit, state) if TRADE_ENABLED else False
            holdings = get_current_holdings(self.upbit)
            decisions = []
            for holding in holdings:
                if holding["profit_pct"] <= STOP_LOSS_PCT:
                    decisions.append(dict(holding, decision="SELL", reason=f"손실 {holding['profit_pct']}%로 손절 기준 도달 (상시 점검)"))
            if decisions:
                plan = {"decisions": decisions, "risk_mode": "stop_loss_monitor", "buy_budget_krw": 0}
                append_decision_history(plan)
                changed = execute_rebalance_plan(self.upbit, plan, state) or changed
            status = load_runtime_status()
            status.update({"risk_check_interval_seconds": RISK_CHECK_SECONDS,
                           "last_risk_check_at": _iso_now(), "risk_check_failures": 0,
                           "pending_order_count": len(state.get("pending_orders", {}))})
            save_runtime_status(status)
            logger.info("[RISK CHECK] holdings=%s stops=%s pending=%s", len(holdings), len(decisions), status["pending_order_count"])
            if changed and refresh_dashboard():
                mark_dashboard_refreshed()
        except Exception as error:
            status = load_runtime_status()
            status.update({"last_risk_error_at": _iso_now(), "last_risk_error_type": type(error).__name__,
                           "risk_check_failures": int(status.get("risk_check_failures", 0)) + 1})
            save_runtime_status(status)
            raise

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                self.check()
            except Exception:
                logger.exception("Risk check failed; retrying on the next risk interval")
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(remaining, max(self.next_check - time.monotonic(), 0.1), 60))


def main():
    try:
        subprocess.Popen(["caffeinate", "-dis"])
    except Exception:
        pass

    upbit = setup_api()
    if not upbit:
        return

    risk_monitor = RiskMonitor(upbit)

    while True:
        try:
            logger.info("\n--- 리밸런싱 사이클 시작 ---")
            mark_cycle_started()
            risk_monitor.check()

            recent_performance = load_recent_performance()
            state = load_bot_state()
            current_holdings = get_current_holdings(upbit)
            market_context = get_market_context()
            targets = get_top_volume_targets(limit=25)
            holding_tickers = [holding["ticker"] for holding in current_holdings]
            targets = list(dict.fromkeys(targets + holding_tickers))

            market_data = []
            for ticker in targets:
                risk_monitor.check()
                data = get_market_data(ticker)
                if data:
                    market_data.append(data)
                _sleep_api()

            # Scanning 25 markets takes over a minute. Re-read both holdings and
            # state because the risk monitor may have exited during the scan.
            current_holdings = get_current_holdings(upbit)
            state = load_bot_state()
            recent_performance = load_recent_performance()
            krw_balance = upbit.get_balance("KRW")
            plan = build_rebalance_plan(
                market_data=market_data,
                market_context=market_context,
                krw=krw_balance,
                current_holdings=current_holdings,
                recent_performance=recent_performance,
                state=state,
                now_ts=time.time(),
            )

            logger.info(
                "Plan: risk_mode=%s cash_reserve=%s%% buy_threshold=%s buy_budget=%s decisions=%s",
                plan["risk_mode"],
                plan["cash_reserve_pct"],
                plan["buy_threshold"],
                int(plan["buy_budget_krw"]),
                json.dumps(plan["decisions"], ensure_ascii=False),
            )
            if plan["entry_rejections"]:
                logger.info("Entry rejections: %s", json.dumps(plan["entry_rejections"], ensure_ascii=False))
            decision_history_changed = append_decision_history(plan)
            trade_history_changed = execute_rebalance_plan(upbit, plan, state)

            sleep_seconds = seconds_until_next_cycle()
            next_expected_cycle_at = datetime.fromtimestamp(time.time() + sleep_seconds).astimezone().isoformat(
                timespec="seconds"
            )
            runtime_status = mark_cycle_succeeded(next_expected_cycle_at=next_expected_cycle_at)
            heartbeat_due = should_refresh_dashboard_for_heartbeat(runtime_status)
            if decision_history_changed or trade_history_changed or heartbeat_due:
                if heartbeat_due and not (decision_history_changed or trade_history_changed):
                    logger.info("Hourly dashboard heartbeat due. Refreshing dashboard.")
                if refresh_dashboard():
                    mark_dashboard_refreshed()
            else:
                logger.info("Decision/trade history unchanged. Skipping dashboard refresh.")

            logger.info(
                "--- 리밸런싱 완료. 다음 %s초 경계 이후 %s초 버퍼까지 %s초 대기합니다. ---",
                LOOP_SLEEP_SECONDS,
                CANDLE_CLOSE_BUFFER_SECONDS,
                int(sleep_seconds),
            )
            if RUN_ONCE:
                logger.info("RUN_ONCE=true. Exiting after one cycle.")
                break
            risk_monitor.wait(seconds_until_next_cycle())
        except Exception as e:
            logger.error(f"Main Loop Error: {e}")
            runtime_status = mark_cycle_failed(e)
            if should_refresh_dashboard_for_heartbeat(runtime_status):
                logger.info("Hourly dashboard heartbeat due after error. Refreshing dashboard.")
                if refresh_dashboard():
                    mark_dashboard_refreshed()
            if RUN_ONCE:
                raise
            risk_monitor.wait(300)


if __name__ == "__main__":
    main()
