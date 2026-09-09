"""Offline diagnostics from a VM snapshot; never imports the bot or calls an API.

Example:
    python review_strategy.py --history /tmp/vm/trade_history.json \
        --log /tmp/vm/trading.log --since 2026-08-29 --output /tmp/review.json

Entry filtering holds recorded exits, quantities and fees fixed. It is NOT a
portfolio backtest: new opportunities, cash reuse, different exits and changed
position sizes cannot be reconstructed from a log of actual trades.
"""

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


KST = timezone(timedelta(hours=9))
BUY_LINE = re.compile(
    r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ - INFO - "
    r"\[BUY\] (KRW-\S+) \d+ KRW \| (score .+)$"
)


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (result if result.tzinfo else result.replace(tzinfo=KST)).timestamp()


def summarize(rows):
    profits = [float(row["profit_krw"]) for row in rows]
    wins = sum(p > 0 for p in profits)
    gain = sum(p for p in profits if p > 0)
    loss = -sum(p for p in profits if p < 0)
    fees_known = all(row.get("fee_krw") is not None for row in rows)
    return {
        "sell_count": len(rows),
        "wins": wins,
        "losses": sum(p < 0 for p in profits),
        "win_rate_pct": round(wins / len(rows) * 100, 2) if rows else None,
        "net_profit_krw": round(sum(profits), 2),
        "profit_factor": round(gain / loss, 4) if loss else None,
        "fees_krw": round(sum(float(row["fee_krw"]) for row in rows), 2) if rows and fees_known else None,
    }


def match_entries(rows, log_text):
    buys = defaultdict(list)
    for line in log_text.splitlines():
        match = BUY_LINE.match(line)
        if match:
            buys[match[2]].append({"at": timestamp(match[1]), "reason": match[3]})
    matched, unmatched = [], []
    for row in rows:
        sold_at = timestamp(row["executed_at"])
        candidates = [buy for buy in buys[row["ticker"]] if buy["at"] <= sold_at]
        if not candidates:
            unmatched.append(row)
            continue
        buy = max(candidates, key=lambda item: item["at"])
        matched.append(dict(row, entry_ts=buy["at"], exit_ts=sold_at,
                            # Historical logs expose this exact existing score reason.
                            negative_hour_momentum="1h weak" in buy["reason"]))
    return matched, unmatched


def filter_recorded_entries(rows, block_negative_momentum=False, cooldown_seconds=7200):
    """Chronological selection diagnostic, using only retained earlier losses."""
    events = []
    for index, row in enumerate(rows):
        events.extend([(row["entry_ts"], 1, index), (row["exit_ts"], 0, index)])
    accepted, reasons = set(), {}
    last_loss = None
    for at, side, index in sorted(events):
        row = rows[index]
        if side == 1:
            if last_loss is not None and at - last_loss < cooldown_seconds:
                reasons[index] = "loss_cooldown"
            elif block_negative_momentum and row["negative_hour_momentum"]:
                reasons[index] = "negative_hour_momentum"
            else:
                accepted.add(index)
        elif index in accepted and float(row["profit_krw"]) < 0:
            last_loss = at
    return [row for index, row in enumerate(rows) if index in accepted], reasons


def make_review(history, log_text, since):
    # Explicit SELL records are the evidence; test-looking log messages are not.
    all_rows = [row for row in history if row.get("side") == "SELL"
                and row.get("profit_krw") is not None and row.get("executed_at")]
    all_rows.sort(key=lambda row: timestamp(row["executed_at"]))
    rows = [row for row in all_rows if timestamp(row["executed_at"]) >= timestamp(since)]
    matched, unmatched = match_entries(rows, log_text)
    # Multiple partial exits of a single entry need position-level replay. Refuse
    # to model them as independent buys, while still reporting actual sell PnL.
    entry_keys = [(row["ticker"], row["entry_ts"]) for row in matched]
    ambiguous_entries = len(set(entry_keys)) != len(entry_keys)
    groups = defaultdict(list)
    for row in rows:
        reason = row.get("reason", "")
        group = ("hard_stop" if "손절" in reason else "take_profit" if "익절" in reason
                 else "profit_protection" if "보호" in reason else "trend_exit")
        groups[group].append(row)
    report = {
        "since": since,
        "all_realized": summarize(all_rows),
        "period_realized": summarize(rows),
        "exit_reasons": {key: summarize(value) for key, value in groups.items()},
        "matched_sells": len(matched),
        "unmatched_sells": len(unmatched),
        "negative_hour_momentum_entries": summarize([r for r in matched if r["negative_hour_momentum"]]),
        "diagnostic_limitations": [
            "Realized sell PnL is not account return; deposits and open positions are not included.",
            "Entry time is the latest preceding scored BUY log for the same ticker.",
            "A prior-rule trade sample is not out-of-sample evidence for the current strategy.",
            "Filtering fixes actual quantities, fees and exits; it cannot model replacement entries or capital reuse.",
            "Cooldown starts from the selected sample's observed losses; earlier open positions are not replayed.",
        ],
    }
    if ambiguous_entries:
        report["filter_diagnostic_unavailable"] = "Several sells match the same entry; partial-position replay is required."
    else:
        baseline, _ = filter_recorded_entries(matched)
        candidate, _ = filter_recorded_entries(matched, block_negative_momentum=True)
        report["entry_filter_diagnostic"] = {
            "current_two_hour_cooldown": summarize(baseline),
            "with_negative_momentum_gate": summarize(candidate),
        }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--since", required=True, help="ISO date/time; an absent zone means KST")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = make_review(json.loads(args.history.read_text(encoding="utf-8")),
                         args.log.read_text(encoding="utf-8"), args.since)
    result = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
