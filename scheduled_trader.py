import argparse
import base64
import json
import logging
import os
import secrets
import sys
from datetime import datetime, time as datetime_time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pyupbit

import autotrade


logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
STATE_FILE = Path(os.getenv("SCHEDULED_TRADING_STATE_FILE", "scheduled_trading_state.json"))
LLM_CONTEXT_FILE = Path(os.getenv("SCHEDULED_LLM_CONTEXT_FILE", "scheduled_llm_context.json"))
TRADE_ENABLED = os.getenv("SCHEDULED_TRADE_ENABLED", "false").lower() == "true"
ACTIVATE_AT = os.getenv("SCHEDULED_ACTIVATE_AT", "").strip()
START_HOUR = int(os.getenv("SCHEDULED_START_HOUR", "2"))
RESTART_HOUR = int(os.getenv("SCHEDULED_RESTART_HOUR", "12"))
TAKE_PROFIT_PCT = float(os.getenv("SCHEDULED_TAKE_PROFIT_PCT", "1.0"))
MAX_LOSS_PCT = float(os.getenv("SCHEDULED_MAX_LOSS_PCT", "0.75"))
SIGNAL_INTERVAL_MINUTES = int(os.getenv("SCHEDULED_SIGNAL_INTERVAL_MINUTES", "15"))
ORDER_BUFFER = float(os.getenv("SCHEDULED_ORDER_BUFFER", "0.999"))
ESTIMATED_SELL_FEE_RATE = float(os.getenv("SCHEDULED_ESTIMATED_SELL_FEE_RATE", "0.0005"))


def _iso(value):
    return value.astimezone(KST).isoformat(timespec="seconds")


def _parse_iso(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def trading_day(now):
    """Return the KST session date for a day that rolls over at START_HOUR."""
    return (now.astimezone(KST) - timedelta(hours=START_HOUR)).date()


def session_start(session_date):
    return datetime.combine(session_date, datetime_time(hour=START_HOUR), tzinfo=KST)


def restart_at(session_date):
    return datetime.combine(session_date, datetime_time(hour=RESTART_HOUR), tzinfo=KST)


def load_state(path=STATE_FILE):
    try:
        state = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    return state if isinstance(state, dict) else {}


def save_state(state, path=STATE_FILE):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_llm_context(path=LLM_CONTEXT_FILE):
    try:
        context = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return context if isinstance(context, dict) else None


def save_llm_context(context, path=LLM_CONTEXT_FILE):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _balances(upbit):
    balances = upbit.get_balances()
    error_message = autotrade._upbit_error_message(balances)
    if error_message:
        raise RuntimeError(f"Upbit balances API error: {error_message}")
    if not isinstance(balances, list):
        raise RuntimeError(f"Unexpected Upbit balances response type: {type(balances).__name__}")
    return balances


def account_snapshot(upbit):
    krw = 0.0
    asset_value = 0.0
    holdings = []

    for balance in _balances(upbit):
        currency = str(balance.get("currency", "")).upper()
        available = autotrade.safe_float(balance.get("balance"))
        locked = autotrade.safe_float(balance.get("locked"))
        amount = available + locked
        if amount <= 0:
            continue
        if currency == "KRW":
            krw += amount
            continue

        ticker = f"KRW-{currency}"
        current_price = autotrade.safe_float(pyupbit.get_current_price(ticker))
        autotrade._sleep_api()
        if current_price <= 0:
            raise RuntimeError(f"Could not value holding {ticker}")
        value = amount * current_price
        asset_value += value
        if available * current_price >= autotrade.MIN_ORDER_KRW:
            avg_buy_price = autotrade.safe_float(balance.get("avg_buy_price"))
            profit_pct = ((current_price / avg_buy_price) - 1) * 100 if avg_buy_price else 0.0
            holdings.append(
                {
                    "ticker": ticker,
                    "balance": available,
                    "avg_buy_price": avg_buy_price,
                    "current_price": current_price,
                    "value": round(available * current_price, 0),
                    "profit_pct": round(profit_pct, 2),
                }
            )

    equity = krw + asset_value
    liquidation_equity = krw + asset_value * (1 - ESTIMATED_SELL_FEE_RATE)
    return {
        "krw": krw,
        "asset_value_krw": asset_value,
        "equity_krw": equity,
        "liquidation_equity_krw": liquidation_equity,
        "holdings": holdings,
    }


def phase_return_pct(snapshot, state):
    baseline = autotrade.safe_float(state.get("phase_start_equity_krw"))
    if baseline <= 0:
        raise RuntimeError("Scheduled trading phase baseline is missing or invalid")
    return (snapshot["liquidation_equity_krw"] / baseline - 1) * 100


def signal_slot(now):
    if SIGNAL_INTERVAL_MINUTES <= 0 or 60 % SIGNAL_INTERVAL_MINUTES:
        raise ValueError("SCHEDULED_SIGNAL_INTERVAL_MINUTES must be a positive divisor of 60")
    minute = (now.minute // SIGNAL_INTERVAL_MINUTES) * SIGNAL_INTERVAL_MINUTES
    return now.replace(minute=minute, second=0, microsecond=0).isoformat(timespec="minutes")


def _new_phase(state, snapshot, now, session_date, phase):
    state.update(
        {
            "session_date": session_date.isoformat(),
            "status": "active",
            "phase": phase,
            "phase_started_at": _iso(now),
            "phase_start_equity_krw": round(snapshot["liquidation_equity_krw"], 4),
            "phase_return_pct": 0.0,
            "last_signal_slot": None,
            "paused_until": None,
            "completed_at": None,
            "completion_reason": None,
        }
    )
    state.setdefault("events", [])


def _record_event(state, now, event, **details):
    state.setdefault("events", []).append({"at": _iso(now), "event": event, **details})
    state["events"] = state["events"][-100:]


def liquidate_all(upbit, snapshot, state, reason):
    decisions = []
    for holding in snapshot["holdings"]:
        decisions.append(
            {
                "ticker": holding["ticker"],
                "decision": "SELL",
                "balance": holding["balance"],
                "avg_buy_price": holding["avg_buy_price"],
                "current_price": holding["current_price"],
                "profit_pct": holding["profit_pct"],
                "reason": reason,
            }
        )
    if not decisions:
        return False
    plan = {
        "decisions": decisions,
        "cash_reserve_pct": 0,
        "buy_budget_krw": 0,
    }
    return autotrade.execute_rebalance_plan(
        upbit,
        plan,
        state=state,
        acquire_lock=False,
        order_buffer=ORDER_BUFFER,
        trade_enabled=TRADE_ENABLED,
    )


def complete_or_retry_liquidation(upbit, state, state_path, now, target_status, reason, return_pct):
    snapshot = account_snapshot(upbit)
    liquidate_all(upbit, snapshot, autotrade.load_bot_state(), reason)
    remaining = account_snapshot(upbit)["holdings"] if TRADE_ENABLED else snapshot["holdings"]
    if remaining:
        state["status"] = "liquidation_pending"
        state["pending_target_status"] = target_status
        state["completion_reason"] = reason
        state["phase_return_pct"] = round(return_pct, 4)
        state["last_tick_at"] = _iso(now)
        _record_event(
            state,
            now,
            "liquidation_retry_needed",
            target_status=target_status,
            remaining=[holding["ticker"] for holding in remaining],
        )
        save_state(state, state_path)
        return {
            "status": "liquidation_pending",
            "return_pct": round(return_pct, 4),
            "action": "retry_next_heartbeat",
            "remaining": [holding["ticker"] for holding in remaining],
        }

    state["status"] = target_status
    state["pending_target_status"] = None
    state["completed_at"] = _iso(now) if target_status.startswith("completed_") else None
    state["completion_reason"] = reason
    state["phase_return_pct"] = round(return_pct, 4)
    state["last_tick_at"] = _iso(now)
    save_state(state, state_path)
    return {
        "status": target_status,
        "return_pct": round(return_pct, 4),
        "action": "liquidated",
    }


def build_llm_context(
    upbit,
    snapshot,
    state,
    now,
    slot,
    state_path=STATE_FILE,
    context_path=LLM_CONTEXT_FILE,
):
    market_context = autotrade.get_market_context()
    targets = autotrade.get_top_volume_targets(limit=25)
    holding_tickers = [holding["ticker"] for holding in snapshot["holdings"]]
    targets = list(dict.fromkeys(targets + holding_tickers))

    market_data = []
    for ticker in targets:
        data = autotrade.get_market_data(ticker)
        if data:
            market_data.append(data)
        autotrade._sleep_api()

    candidates = []
    for row in market_data:
        score, score_reason = autotrade.score_coin(row, market_context)
        candidates.append(
            {
                **row,
                "legacy_score": score,
                "legacy_score_reason": score_reason,
                "legacy_block_reason": autotrade.entry_block_reason(row, market_context),
            }
        )

    decision_token = secrets.token_urlsafe(18)
    context = {
        "status": "needs_decision",
        "decision_token": decision_token,
        "generated_at": _iso(now),
        "signal_slot": slot,
        "session_date": state["session_date"],
        "phase": state["phase"],
        "phase_return_pct": state["phase_return_pct"],
        "market_context": market_context,
        "portfolio": {
            "krw": round(snapshot["krw"], 2),
            "asset_value_krw": round(snapshot["asset_value_krw"], 2),
            "liquidation_equity_krw": round(snapshot["liquidation_equity_krw"], 2),
            "holdings": snapshot["holdings"],
        },
        "candidates": candidates,
        "constraints": {
            "allowed_decisions": ["BUY", "SELL", "HOLD"],
            "max_positions": autotrade.MAX_POSITIONS,
            "cash_reserve_pct": 0,
            "order_buffer": ORDER_BUFFER,
            "buy_tickers_must_be_in_candidates": True,
            "sell_tickers_must_be_current_holdings": True,
            "one_decision_per_ticker": True,
            "stablecoin_like_tickers_excluded": sorted(autotrade.EXCLUDED_ENTRY_TICKERS),
        },
        "required_decision_schema": {
            "decision_token": "copy exactly",
            "decisions": [
                {
                    "ticker": "KRW-BTC",
                    "decision": "BUY|SELL|HOLD",
                    "reason": "brief evidence-based reason",
                }
            ],
        },
    }
    save_llm_context(context, context_path)
    state["pending_decision_token"] = decision_token
    state["pending_signal_slot"] = slot
    save_state(state, state_path)
    return context


def _validated_llm_plan(decision, context, snapshot):
    if not isinstance(decision, dict):
        raise ValueError("LLM decision must be a JSON object")
    if decision.get("decision_token") != context.get("decision_token"):
        raise ValueError("LLM decision token does not match the pending context")
    rows = decision.get("decisions")
    if not isinstance(rows, list):
        raise ValueError("LLM decisions must be a JSON array")

    held_tickers = {holding["ticker"] for holding in snapshot["holdings"]}
    candidate_tickers = {row["coin"] for row in context.get("candidates", [])}
    normalized = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each LLM decision must be a JSON object")
        ticker = str(row.get("ticker", "")).strip().upper()
        action = str(row.get("decision", "")).strip().upper()
        reason = str(row.get("reason", "")).strip()[:500]
        if ticker in seen:
            raise ValueError(f"Duplicate LLM decision for {ticker}")
        if action not in {"BUY", "SELL", "HOLD"}:
            raise ValueError(f"Unsupported LLM decision {action!r}")
        if not reason:
            raise ValueError(f"LLM decision reason is required for {ticker}")
        if action == "BUY" and (ticker not in candidate_tickers or ticker in held_tickers):
            raise ValueError(f"BUY is not allowed for {ticker}")
        if action == "SELL" and ticker not in held_tickers:
            raise ValueError(f"SELL is not allowed for {ticker}")
        if action == "HOLD" and ticker not in held_tickers:
            raise ValueError(f"HOLD is only allowed for a current holding: {ticker}")
        seen.add(ticker)
        normalized.append({"ticker": ticker, "decision": action, "reason": f"GPT-5.6 Sol: {reason}"})

    sell_tickers = {row["ticker"] for row in normalized if row["decision"] == "SELL"}
    buy_rows = [row for row in normalized if row["decision"] == "BUY"]
    remaining_positions = len(held_tickers - sell_tickers)
    if remaining_positions + len(buy_rows) > autotrade.MAX_POSITIONS:
        raise ValueError("LLM decision exceeds MAX_POSITIONS")

    holding_by_ticker = {holding["ticker"]: holding for holding in snapshot["holdings"]}
    for row in normalized:
        holding = holding_by_ticker.get(row["ticker"])
        if row["decision"] == "SELL" and holding:
            row.update(
                {
                    "balance": holding["balance"],
                    "avg_buy_price": holding["avg_buy_price"],
                    "current_price": holding["current_price"],
                    "profit_pct": holding["profit_pct"],
                }
            )
    return {
        "decisions": normalized,
        "cash_reserve_pct": 0,
        "buy_budget_krw": round(snapshot["krw"], 0),
        "entry_block_reason": None,
        "entry_rejections": [],
        "risk_mode": context.get("market_context", {}).get("risk_mode", "unknown"),
        "krw": snapshot["krw"],
        "decision_source": "gpt-5.6-sol/high",
    }


def execute_llm_decision(decision, upbit=None, now=None, state_path=STATE_FILE, context_path=LLM_CONTEXT_FILE):
    now = (now or datetime.now(KST)).astimezone(KST)
    upbit = upbit or autotrade.setup_api()
    if upbit is None:
        raise RuntimeError("Upbit credentials are not configured")

    with autotrade.trade_execution_lock(blocking=False):
        state = load_state(state_path)
        context = load_llm_context(context_path)
        if not context:
            raise RuntimeError("No pending LLM decision context")
        if state.get("pending_decision_token") != context.get("decision_token"):
            raise RuntimeError("Pending LLM context does not match scheduler state")
        generated_at = _parse_iso(context.get("generated_at"))
        if not generated_at or now - generated_at > timedelta(minutes=10):
            raise RuntimeError("Pending LLM decision context is stale")

        snapshot = account_snapshot(upbit)
        current_return = phase_return_pct(snapshot, state)
        if current_return >= TAKE_PROFIT_PCT or current_return <= -MAX_LOSS_PCT:
            raise RuntimeError("Account threshold changed; run prepare tick again before executing an LLM decision")
        plan = _validated_llm_plan(decision, context, snapshot)

        # Consume the token before side effects so retries are at-most-once.
        state["last_signal_slot"] = context["signal_slot"]
        state["pending_decision_token"] = None
        state["pending_signal_slot"] = None
        save_state(state, state_path)

        decision_history_changed = autotrade.append_decision_history(plan)
        trade_history_changed = autotrade.execute_rebalance_plan(
            upbit,
            plan,
            state=autotrade.load_bot_state(),
            acquire_lock=False,
            order_buffer=ORDER_BUFFER,
            trade_enabled=TRADE_ENABLED,
        )
        decisions = [f"{row['decision']}:{row['ticker']}" for row in plan["decisions"]]
        _record_event(state, now, "llm_signal_cycle", slot=context["signal_slot"], decisions=decisions)
        save_state(state, state_path)
        if decision_history_changed or trade_history_changed:
            autotrade.refresh_dashboard()
        return {
            "status": "active",
            "action": "llm_decision_executed",
            "decision_source": "gpt-5.6-sol/high",
            "decisions": decisions,
        }


def run_tick(upbit=None, now=None, state_path=STATE_FILE, context_path=LLM_CONTEXT_FILE):
    now = (now or datetime.now(KST)).astimezone(KST)
    activation = _parse_iso(ACTIVATE_AT)
    if activation and now < activation:
        return {"status": "waiting_activation", "activate_at": _iso(activation), "now": _iso(now)}

    upbit = upbit or autotrade.setup_api()
    if upbit is None:
        raise RuntimeError("Upbit credentials are not configured")

    with autotrade.trade_execution_lock(blocking=False):
        snapshot = account_snapshot(upbit)
        state = load_state(state_path)
        session_date = trading_day(now)

        if state.get("status") == "liquidation_pending":
            pending_session = state.get("session_date")
            reason = state.get("completion_reason") or "예약매매 청산 재시도"
            target_status = state.get("pending_target_status") or "completed_stop"
            return_pct = autotrade.safe_float(state.get("phase_return_pct"))
            result = complete_or_retry_liquidation(
                upbit,
                state,
                state_path,
                now,
                target_status,
                reason,
                return_pct,
            )
            if result["status"] == "liquidation_pending" or pending_session == session_date.isoformat():
                return result
            snapshot = account_snapshot(upbit)
            state = load_state(state_path)

        if state.get("session_date") != session_date.isoformat():
            _new_phase(state, snapshot, now, session_date, phase=1)
            _record_event(state, now, "session_started", equity_krw=round(snapshot["liquidation_equity_krw"], 2))

        if state.get("status") in {"completed_target", "completed_stop"}:
            state["last_tick_at"] = _iso(now)
            state["last_equity_krw"] = round(snapshot["liquidation_equity_krw"], 4)
            save_state(state, state_path)
            return {
                "status": state["status"],
                "session_date": state["session_date"],
                "phase": state["phase"],
                "return_pct": state.get("phase_return_pct"),
                "action": "none_until_next_session",
            }

        if state.get("status") == "waiting_noon":
            resume_at = _parse_iso(state.get("paused_until")) or restart_at(session_date)
            if now < resume_at:
                state["last_tick_at"] = _iso(now)
                save_state(state, state_path)
                return {
                    "status": "waiting_noon",
                    "session_date": state["session_date"],
                    "resume_at": _iso(resume_at),
                    "action": "none",
                }
            _new_phase(state, snapshot, now, session_date, phase=2)
            _record_event(state, now, "noon_restart", equity_krw=round(snapshot["liquidation_equity_krw"], 2))

        return_pct = phase_return_pct(snapshot, state)
        state["phase_return_pct"] = round(return_pct, 4)
        state["last_equity_krw"] = round(snapshot["liquidation_equity_krw"], 4)
        state["last_tick_at"] = _iso(now)

        if return_pct >= TAKE_PROFIT_PCT:
            reason = f"예약매매 단계 수익률 {return_pct:.4f}%가 목표 {TAKE_PROFIT_PCT}% 도달"
            _record_event(state, now, "target_reached", return_pct=round(return_pct, 4))
            result = complete_or_retry_liquidation(
                upbit,
                state,
                state_path,
                now,
                "completed_target",
                reason,
                return_pct,
            )
            autotrade.refresh_dashboard()
            return result

        if return_pct <= -MAX_LOSS_PCT:
            reason = f"예약매매 단계 수익률 {return_pct:.4f}%가 손절 -{MAX_LOSS_PCT}% 도달"
            if now < restart_at(session_date):
                target_status = "waiting_noon"
                state["paused_until"] = _iso(restart_at(session_date))
            else:
                target_status = "completed_stop"
            _record_event(state, now, "stop_loss", return_pct=round(return_pct, 4), next_status=target_status)
            result = complete_or_retry_liquidation(
                upbit,
                state,
                state_path,
                now,
                target_status,
                reason,
                return_pct,
            )
            autotrade.refresh_dashboard()
            if result["status"] == "waiting_noon":
                result["action"] = "liquidated_waiting_noon"
            elif result["status"] == "completed_stop":
                result["action"] = "liquidated_until_next_session"
            return result

        slot = signal_slot(now)
        if state.get("last_signal_slot") == slot:
            save_state(state, state_path)
            return {
                "status": "active",
                "session_date": state["session_date"],
                "phase": state["phase"],
                "return_pct": round(return_pct, 4),
                "action": "heartbeat_only",
            }

        if not TRADE_ENABLED:
            return {
                "status": "active_dry_run",
                "session_date": state["session_date"],
                "phase": state["phase"],
                "return_pct": round(return_pct, 4),
                "action": "signal_skipped",
            }

        pending = load_llm_context(context_path)
        if state.get("pending_signal_slot") == slot and pending:
            return pending
        return build_llm_context(
            upbit,
            snapshot,
            state,
            now,
            slot,
            state_path=state_path,
            context_path=context_path,
        )


def main():
    parser = argparse.ArgumentParser(description="Run one scheduled trading heartbeat tick")
    parser.add_argument("--json", action="store_true", help="Print a compact JSON result")
    parser.add_argument("--decision-base64", help="Execute a base64-encoded GPT-5.6 Sol decision JSON")
    args = parser.parse_args()
    try:
        if args.decision_base64:
            decoded = base64.b64decode(args.decision_base64, validate=True).decode("utf-8")
            result = execute_llm_decision(json.loads(decoded))
        else:
            result = run_tick()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except BlockingIOError:
        result = {"status": "busy", "action": "skip_overlapping_tick"}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        logger.exception("Scheduled trading tick failed")
        print(json.dumps({"status": "error", "error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
