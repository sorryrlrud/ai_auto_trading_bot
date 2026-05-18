import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TRADE_HISTORY_FILE = ROOT / "trade_history.json"
DECISION_HISTORY_FILE = ROOT / "decision_history.json"
DASHBOARD_FILE = ROOT / "docs" / "index.html"


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def load_realized_trades(path=TRADE_HISTORY_FILE):
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        rows = []

    trades = []
    for row in rows:
        if row.get("side", "SELL") != "SELL":
            continue
        trades.append(
            {
                "executed_at": row.get("executed_at") or row.get("date", ""),
                "ticker": row.get("ticker", ""),
                "profit_pct": safe_float(row.get("profit_pct", row.get("profit"))),
                "profit_krw": safe_float(row["profit_krw"]) if "profit_krw" in row else None,
                "cost_basis_krw": safe_float(row["cost_basis_krw"]) if "cost_basis_krw" in row else None,
                "gross_proceeds_krw": safe_float(row["gross_proceeds_krw"]) if "gross_proceeds_krw" in row else None,
                "fee_krw": safe_float(row["fee_krw"]) if "fee_krw" in row else None,
                "reason": row.get("reason", ""),
                "source": row.get("source", "legacy"),
            }
        )
    return trades


def load_recent_decisions(path=DECISION_HISTORY_FILE, limit=3):
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        rows = []

    if not isinstance(rows, list):
        return []
    return rows[-limit:]


def summarize(trades):
    amount_rows = [row for row in trades if row["profit_krw"] is not None and row["cost_basis_krw"]]
    total_profit_krw = sum(row["profit_krw"] for row in amount_rows)
    pct_rows = [row["profit_pct"] for row in trades]
    won = [value for value in pct_rows if value > 0]
    cost_basis = sum(row["cost_basis_krw"] for row in amount_rows)
    return {
        "trade_count": len(trades),
        "win_rate": round(len(won) / len(trades) * 100, 2) if trades else 0.0,
        "amount_trade_count": len(amount_rows),
        "total_profit_krw": round(total_profit_krw, 2) if amount_rows else None,
        "avg_profit_pct": round(sum(pct_rows) / len(pct_rows), 4) if pct_rows else 0.0,
        "total_return_pct": round(total_profit_krw / cost_basis * 100, 4) if cost_basis else None,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def build_html(trades, recent_decisions):
    summary = summarize(trades)
    payload = json.dumps(
        {"summary": summary, "trades": trades, "recent_decisions": recent_decisions},
        ensure_ascii=False,
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Auto Trading Dashboard</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #101214;
      --panel: #171a1d;
      --muted: #96a0aa;
      --text: #f2f5f7;
      --line: #2a3036;
      --green: #4ade80;
      --red: #fb7185;
      --accent: #60a5fa;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 32px auto 48px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-end;
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    .muted {{ color: var(--muted); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    .stat {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .value {{
      font-size: 24px;
      font-weight: 700;
    }}
    .positive {{ color: var(--green); }}
    .negative {{ color: var(--red); }}
    .table-wrap {{
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .section-title {{
      margin: 28px 0 12px;
      font-size: 18px;
    }}
    .decision-grid {{
      display: grid;
      gap: 12px;
      margin-bottom: 20px;
    }}
    .decision-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .decision-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 12px;
    }}
    .decision-list {{
      display: grid;
      gap: 8px;
    }}
    .decision-item {{
      display: grid;
      grid-template-columns: 92px 64px minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      font-size: 14px;
    }}
    .badge {{
      display: inline-flex;
      justify-content: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 600;
    }}
    .badge.buy {{ color: var(--green); }}
    .badge.sell {{ color: var(--red); }}
    .badge.hold {{ color: var(--accent); }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 13px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      font-size: 14px;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      background: rgba(255, 255, 255, 0.02);
    }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    td.num, th.num {{ text-align: right; }}
    .empty {{
      padding: 36px 16px;
      text-align: center;
      color: var(--muted);
    }}
    @media (max-width: 760px) {{
      header {{
        display: block;
      }}
      .stats {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .table-wrap {{
        overflow-x: auto;
      }}
      table {{
        min-width: 760px;
      }}
      .decision-item {{
        grid-template-columns: 1fr;
        gap: 4px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Auto Trading Dashboard</h1>
        <div class="muted">실현 완료된 매도 기록 기준</div>
      </div>
      <div class="muted" id="generated-at"></div>
    </header>

    <section class="stats">
      <article class="stat">
        <div class="label">누적 실현손익</div>
        <div class="value" id="total-profit"></div>
      </article>
      <article class="stat">
        <div class="label">누적 수익률</div>
        <div class="value" id="total-return"></div>
      </article>
      <article class="stat">
        <div class="label">승률</div>
        <div class="value" id="win-rate"></div>
      </article>
      <article class="stat">
        <div class="label">완료 매매</div>
        <div class="value" id="trade-count"></div>
      </article>
    </section>

    <h2 class="section-title">최근 판단 로그</h2>
    <section class="decision-grid" id="decision-cards"></section>
    <div class="empty" id="decision-empty" hidden>아직 공개할 판단 로그가 없습니다.</div>

    <h2 class="section-title">실현 매매 기록</h2>
    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>체결 시각</th>
            <th>종목</th>
            <th class="num">손익금액</th>
            <th class="num">수익률</th>
            <th class="num">매수원가</th>
            <th class="num">수수료</th>
            <th>매도 사유</th>
          </tr>
        </thead>
        <tbody id="trade-rows"></tbody>
      </table>
      <div class="empty" id="empty-state" hidden>아직 공개할 실현 매매 기록이 없습니다.</div>
    </section>
  </main>

  <script id="dashboard-data" type="application/json">{payload}</script>
  <script>
    const data = JSON.parse(document.getElementById("dashboard-data").textContent);
    const won = new Intl.NumberFormat("ko-KR", {{ maximumFractionDigits: 0 }});
    const pct = new Intl.NumberFormat("ko-KR", {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
    const signedWon = (value) => value == null ? "-" : `${{value > 0 ? "+" : ""}}${{won.format(value)}}원`;
    const signedPct = (value) => value == null ? "-" : `${{value > 0 ? "+" : ""}}${{pct.format(value)}}%`;
    const tone = (value) => value > 0 ? "positive" : value < 0 ? "negative" : "";

    document.getElementById("generated-at").textContent =
      `마지막 갱신 ${{data.summary.generated_at}}`;

    const statMap = [
      ["total-profit", signedWon(data.summary.total_profit_krw), data.summary.total_profit_krw],
      ["total-return", signedPct(data.summary.total_return_pct), data.summary.total_return_pct],
      ["win-rate", `${{pct.format(data.summary.win_rate)}}%`, data.summary.win_rate],
      ["trade-count", `${{won.format(data.summary.trade_count)}}건`, 0],
    ];
    for (const [id, text, value] of statMap) {{
      const node = document.getElementById(id);
      node.textContent = text;
      const valueTone = tone(value);
      if (valueTone) {{
        node.classList.add(valueTone);
      }}
    }}

    const decisionCards = document.getElementById("decision-cards");
    const decisionEmpty = document.getElementById("decision-empty");
    if (!data.recent_decisions.length) {{
      decisionEmpty.hidden = false;
    }} else {{
      for (const entry of [...data.recent_decisions].reverse()) {{
        const card = document.createElement("article");
        card.className = "decision-card";
        const meta = document.createElement("div");
        meta.className = "decision-meta";
        const entryBlock = entry.entry_block_reason ? ` · entry_block=${{entry.entry_block_reason}}` : "";
        meta.textContent =
          `${{entry.recorded_at || "-"}} · risk=${{entry.risk_mode || "-"}} · cash=${{entry.cash_reserve_pct ?? "-"}}% · threshold=${{entry.buy_threshold ?? "-"}} · budget=${{entry.buy_budget_krw == null ? "-" : `${{won.format(entry.buy_budget_krw)}}원`}}${{entryBlock}}`;
        card.appendChild(meta);

        const list = document.createElement("div");
        list.className = "decision-list";
        const decisions = entry.decisions || [];
        for (const decision of decisions) {{
          const item = document.createElement("div");
          item.className = "decision-item";
          const ticker = document.createElement("div");
          ticker.textContent = decision.ticker || "-";
          const badge = document.createElement("div");
          badge.className = `badge ${{String(decision.decision || "").toLowerCase()}}`;
          badge.textContent = decision.decision || "-";
          const reason = document.createElement("div");
          reason.textContent = decision.reason || "-";
          item.append(ticker, badge, reason);
          list.appendChild(item);
        }}
        if (!decisions.length && entry.entry_block_reason) {{
          const item = document.createElement("div");
          item.className = "muted";
          item.textContent = `신규 진입 차단: ${{entry.entry_block_reason}}`;
          list.appendChild(item);
        }}
        card.appendChild(list);
        decisionCards.appendChild(card);
      }}
    }}

    const rows = document.getElementById("trade-rows");
    const empty = document.getElementById("empty-state");
    if (!data.trades.length) {{
      rows.closest("table").hidden = true;
      empty.hidden = false;
    }} else {{
      for (const trade of [...data.trades].reverse()) {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{trade.executed_at || "-"}}</td>
          <td>${{trade.ticker}}</td>
          <td class="num ${{tone(trade.profit_krw)}}">${{signedWon(trade.profit_krw)}}</td>
          <td class="num ${{tone(trade.profit_pct)}}">${{signedPct(trade.profit_pct)}}</td>
          <td class="num">${{trade.cost_basis_krw == null ? "-" : `${{won.format(trade.cost_basis_krw)}}원`}}</td>
          <td class="num">${{trade.fee_krw == null ? "-" : `${{won.format(trade.fee_krw)}}원`}}</td>
          <td>${{trade.reason || "-"}}</td>
        `;
        rows.appendChild(tr);
      }}
    }}
  </script>
</body>
</html>
"""


def main():
    trades = load_realized_trades()
    recent_decisions = load_recent_decisions()
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_FILE.write_text(build_html(trades, recent_decisions), encoding="utf-8")
    print(f"Wrote {DASHBOARD_FILE}")


if __name__ == "__main__":
    main()
