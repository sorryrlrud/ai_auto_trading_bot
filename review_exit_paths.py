"""Offline, fixed-entry exit diagnostic using private VM observation snapshots.

This is not a portfolio backtest or a reconstruction of 60-second prices.
Only observed holding prices are used, never candle highs or a hypothetical
fill at a stop threshold. Missing paths and partial-position exits are excluded.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from review_strategy import timestamp, summarize


def compare_exits(history, observations, *, arm_pct=1.2, keep_ratio=0.5,
                  min_net_pct=0.2, sell_fee_rate=0.0005, slippage_pct=0.1,
                  split_at="2026-09-24T00:00:00+09:00", mode="trend_memory"):
    if mode not in ("trend_memory", "price_trail"):
        raise ValueError("Unknown exit diagnostic mode")
    if not (arm_pct > 0 and 0 < keep_ratio < 1 and 0 <= min_net_pct < arm_pct
            and 0 <= sell_fee_rate < 0.01 and slippage_pct >= 0):
        raise ValueError("Invalid exit diagnostic parameters")
    rows = [r for r in history if r.get("side") == "SELL" and r.get("executed_at")
            and r.get("profit_krw") is not None]
    keys = Counter(r.get("entry_order_uuid") or (r["ticker"], r.get("entry_submitted_at")) for r in rows)
    paths = {}
    for observation in observations:
        at = timestamp(observation.get("planned_at") or observation["recorded_at"])
        exits = {d["ticker"] for d in observation.get("plan", {}).get("decisions", [])
                 if d.get("decision") == "SELL"}
        signals = {s["coin"]: s for s in observation.get("market_data", [])}
        for holding in observation.get("holdings", []):
            minute = signals.get(holding["ticker"], {}).get("indicators", {}).get("15m", {})
            broken = (minute.get("price_over_long") is False
                      and minute.get("ma5_over_long") is False and minute.get("macd_hist", 0) < 0)
            paths.setdefault(holding["ticker"], []).append((at, holding, holding["ticker"] in exits, broken))
    for path in paths.values():
        path.sort(key=lambda point: point[0])

    results, skipped = [], Counter()
    for row in rows:
        key = row.get("entry_order_uuid") or (row["ticker"], row.get("entry_submitted_at"))
        if not row.get("entry_submitted_at"):
            skipped["missing_entry_time"] += 1
            continue
        if keys[key] != 1:
            skipped["partial_or_ambiguous_entry"] += 1
            continue
        start, end = timestamp(row["entry_submitted_at"]), timestamp(row["executed_at"])
        avg_buy = float(row["avg_buy_price"])
        quantity = float(row["quantity"])
        if avg_buy <= 0 or quantity <= 0 or row.get("buy_fee_krw") is None:
            skipped["missing_cost_or_fee"] += 1
            continue
        path = [(at, h, exiting, broken) for at, h, exiting, broken in paths.get(row["ticker"], [])
                if start < at < end and float(h.get("current_price", 0)) > 0
                and abs(float(h.get("avg_buy_price", 0)) / avg_buy - 1) < 1e-6]
        if not path:
            skipped["missing_holding_path"] += 1
            continue
        basis = avg_buy * quantity + float(row["buy_fee_krw"])
        candidate = float(row["profit_krw"])
        peak, trigger_at = 0.0, None
        for at, holding, already_exiting, short_broken in path:
            price = float(holding["current_price"])
            peak = max(peak, price)
            if already_exiting:
                # The original strategy exits at this same snapshot: use its
                # actual fill, rather than manufacture an incremental benefit.
                break
            if peak < avg_buy * (1 + arm_pct / 100):
                continue
            peak_net = (peak * quantity * (1 - sell_fee_rate) / basis - 1) * 100
            net = (price * quantity * (1 - sell_fee_rate) / basis - 1) * 100
            trigger = short_broken if mode == "trend_memory" else net <= max(min_net_pct, peak_net * keep_ratio)
            if trigger:
                fill_price = price * (1 - slippage_pct / 100)
                candidate = fill_price * quantity * (1 - sell_fee_rate) - basis
                trigger_at = at
                break
        times = [start] + [point[0] for point in path] + [end]
        results.append({"ticker": row["ticker"], "entry_at": row["entry_submitted_at"],
                        "exit_at": row["executed_at"], "entry_strategy_version":
                        (row.get("entry_context") or {}).get("strategy_version"),
                        "baseline_profit_krw": float(row["profit_krw"]),
                        "candidate_profit_krw": round(candidate, 2),
                        "trigger_at_ts": trigger_at, "observations": len(path),
                        "max_gap_seconds": round(max(b - a for a, b in zip(times, times[1:])), 1)})

    def group(items):
        return {"count": len(items),
                "baseline": summarize([{"profit_krw": r["baseline_profit_krw"]} for r in items]),
                "candidate": summarize([{"profit_krw": r["candidate_profit_krw"]} for r in items]),
                "earlier_exits": sum(r["trigger_at_ts"] is not None for r in items)}

    return {"parameters": {"mode": mode, "arm_pct": arm_pct, "keep_ratio": keep_ratio,
                           "min_net_pct": min_net_pct, "sell_fee_rate": sell_fee_rate,
                           "slippage_pct": slippage_pct, "split_at": split_at},
            "all": group(results),
            "before_split": group([r for r in results if timestamp(r["entry_at"]) < timestamp(split_at)]),
            "since_split": group([r for r in results if timestamp(r["entry_at"]) >= timestamp(split_at)]),
            "skipped": dict(skipped), "trades": results,
            "limitations": [
                "Retrospective fixed-entry diagnostic, not evidence of maximum or future profit.",
                "Sparse 15-minute observations cannot reproduce 60-second monitoring or intraperiod gaps.",
                "Actual entries, original exits and sizes are fixed; replacement trades/cooldowns are not replayed.",
                "Estimated earlier exits include recorded buy fees, estimated sell fees and adverse slippage.",
                "Earlier exits may cut profitable recoveries; the chronological split is not an untouched holdout.",
                "Peak prices before the first available snapshot are unknown; see per-trade maximum gaps.",
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--observations", type=Path, nargs="+", required=True)
    parser.add_argument("--slippage-pct", type=float, default=0.1)
    parser.add_argument("--mode", choices=("trend_memory", "price_trail"), default="trend_memory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    observations = [json.loads(line) for path in args.observations
                    for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = compare_exits(json.loads(args.history.read_text(encoding="utf-8")), observations,
                           slippage_pct=args.slippage_pct, mode=args.mode)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "trades"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
