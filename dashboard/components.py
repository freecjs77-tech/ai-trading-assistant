"""
dashboard/components.py — 재사용 HTML 컴포넌트 (overview_target.html 기준)
"""

from typing import Optional


# ── 액션 → pill 클래스 매핑 ──────────────────────────────

ACTION_PILL = {
    "L1_WARNING":   ("pill-sell", "L1 WARN"),
    "L2_WEAKENING": ("pill-sell", "L2 WEAK"),
    "L3_BREAKDOWN": ("pill-sell", "L3 EXIT"),
    "TOP_SIGNAL":   ("pill-top",  "TOP"),
    "BUY_T1":       ("pill-buy",  "1st BUY"),
    "BUY_T2":       ("pill-buy",  "2nd BUY"),
    "BUY_T3":       ("pill-buy",  "3rd BUY"),
    "TRANCHE_1_BUY":("pill-buy",  "1st BUY"),
    "TRANCHE_2_BUY":("pill-buy",  "2nd BUY"),
    "TRANCHE_3_BUY":("pill-buy",  "3rd BUY"),
    "BOND_WATCH":   ("pill-bond", "BOND WATCH"),
    "WATCH":        ("pill-wait", "WATCH"),
    "CASH":         ("pill-hold", "CASH"),
    "HOLD":         ("pill-hold", "HOLD"),
    "BLOCKED":      ("pill-block","BLOCKED"),
}


def pill_html(action: str) -> str:
    """액션 → pill HTML 문자열"""
    cls, label = ACTION_PILL.get(action, ("pill-hold", action))
    return f'<span class="pill {cls}">{label}</span>'


# ── 원화 포맷 ─────────────────────────────────────────────

def format_krw(usd: float, rate: float) -> str:
    """USD → 한국식 원화 표기 (억/만)
    예: 102109.73 USD × 1425.50 = 145,560,121,415 원 → "1.46억"
    """
    krw = usd * rate
    if krw >= 1_0000_0000:  # 1억 이상
        val = krw / 1_0000_0000
        return f"₩{val:.2f}억"
    elif krw >= 10000:  # 1만 이상
        val = krw / 10000
        return f"₩{val:,.0f}만"
    else:
        return f"₩{krw:,.0f}"


# ── 메트릭 카드 ───────────────────────────────────────────

def metric_card(label: str, value: str, change: str = "", change_class: str = "") -> str:
    ch_html = f'<div class="ch {change_class}">{change}</div>' if change else ""
    return f"""<div class="mc">
  <div class="lb">{label}</div>
  <div class="vl">{value}</div>
  {ch_html}
</div>"""


def metrics_row(cards: list[str]) -> str:
    inner = "\n".join(cards)
    return f'<div class="metrics">{inner}</div>'


# ── 매크로 카드 ───────────────────────────────────────────

def macro_card(label: str, value: str, status: str = "", status_class: str = "") -> str:
    st_html = f'<div class="st {status_class}">{status}</div>' if status else ""
    return f"""<div class="ma">
  <div class="lb">{label}</div>
  <div class="vl {status_class}">{value}</div>
  {st_html}
</div>"""


def macro_row(cards: list[str]) -> str:
    inner = "\n".join(cards)
    return f'<div class="macro">{inner}</div>'


# ── 마스터 스위치 배너 ────────────────────────────────────

def master_switch_banner(
    status: str,
    qqq_price: float = 0,
    qqq_ma200: float = 0,
    spy_price: float = 0,
    spy_ma200: float = 0,
    vix: float = 0,
) -> str:
    sw_cls = {"RED": "sw-r", "YELLOW": "sw-y", "GREEN": "sw-g"}.get(status, "sw-r")
    banner_cls = {"RED": "", "YELLOW": " ms-banner-y", "GREEN": " ms-banner-g"}.get(status, "")
    detail = (f"QQQ ${qqq_price:,.0f} vs MA200 ${qqq_ma200:,.0f}"
              f"  •  SPY ${spy_price:,.0f} vs MA200 ${spy_ma200:,.0f}"
              f"  •  VIX {vix:.1f}")
    return f"""<div class="ms-banner{banner_cls}">
  <div class="title">Master switch: <span class="sw {sw_cls}">{status}</span></div>
  <div class="detail">{detail}</div>
</div>"""


# ── 보유 테이블 ───────────────────────────────────────────

def holdings_table_html(
    holdings: list[dict],
    signals_market: dict,
    signals_tech: dict,
    currency: str = "USD",
    usdkrw: float = 1400.0,
    max_value: float = 1.0,
) -> str:
    """보유 테이블 HTML (Market + Technical 듀얼 시그널 컬럼)"""
    rows = []
    for h in holdings:
        ticker = h["ticker"]
        name = h.get("name", "")
        value_usd = h.get("value_usd", 0)
        pnl_pct = h.get("pnl_pct", 0)
        weight = value_usd / max_value * 100 if max_value > 0 else 0

        if currency == "KRW":
            val_str = format_krw(value_usd, usdkrw)
        else:
            val_str = f"${value_usd:,.0f}"

        pnl_cls = "up" if pnl_pct >= 0 else "dn"
        pnl_str = f"+{pnl_pct:.1f}%" if pnl_pct >= 0 else f"{pnl_pct:.1f}%"

        bar_color = "#0F6E56" if pnl_pct >= 0 else "#A32D2D"
        bar_w = min(100, weight / 25 * 100)

        m_action = signals_market.get(ticker, "HOLD")
        t_action = signals_tech.get(ticker, "HOLD")

        rows.append(f"""<tr>
  <td><span class="tk">{ticker}</span><br><span class="nm">{name}</span></td>
  <td style="text-align:right">{val_str}</td>
  <td style="text-align:right">{weight:.1f}%<br>
    <span class="bar-bg"><span class="bar-f" style="width:{bar_w:.0f}%;background:{bar_color}"></span></span>
  </td>
  <td style="text-align:right" class="{pnl_cls}">{pnl_str}</td>
  <td style="text-align:center">{pill_html(m_action)}</td>
  <td style="text-align:center">{pill_html(t_action)}</td>
</tr>""")

    rows_html = "\n".join(rows)
    n = len(holdings)
    return f"""<div class="sh">Holdings ({n})</div>
<table class="tbl">
<thead><tr>
  <th>Ticker</th>
  <th style="text-align:right">Value</th>
  <th style="text-align:right">Weight</th>
  <th style="text-align:right">Return</th>
  <th style="text-align:center">Market</th>
  <th style="text-align:center">Technical</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>"""


# ── 시그널 카드 ───────────────────────────────────────────

def signal_card(
    ticker: str,
    action: str,
    confidence: int,
    rationale: str,
) -> str:
    pill = pill_html(action)
    # 카드 테두리 색
    if action in ("L1_WARNING", "L2_WEAKENING", "L3_BREAKDOWN", "TOP_SIGNAL"):
        card_cls = "sig-card-warn"
        conf_color = "#A32D2D"
    elif action in ("BUY_T1", "BUY_T2", "BUY_T3", "TRANCHE_1_BUY", "TRANCHE_2_BUY", "TRANCHE_3_BUY"):
        card_cls = "sig-card-buy"
        conf_color = "#0F6E56"
    elif action in ("BOND_WATCH", "WATCH"):
        card_cls = "sig-card-watch"
        conf_color = "#BA7517"
    else:
        card_cls = ""
        conf_color = "#888"

    conf_w = min(100, confidence)
    return f"""<div class="sig-card {card_cls}">
  <div class="sig-h">
    <span class="sig-tk">{ticker} {pill}</span>
    <span class="conf">
      <span class="conf-bar"><span class="conf-fill" style="width:{conf_w}%;background:{conf_color}"></span></span>
      {confidence}%
    </span>
  </div>
  <div class="sig-body">{rationale}</div>
</div>"""


# ── 시그널 인덱스 ─────────────────────────────────────────

def signal_index_html() -> str:
    return """<div class="idx">
<div class="idx-hdr">Signal reference</div>
<div class="idx-sub">Entry signals</div>
<div class="idx-grid">
  <div class="idx-item"><div><span class="pill pill-buy">1st BUY</span></div><div>
    <div class="idx-name">1st tranche (20%)</div>
    <div class="idx-desc">MACD hist 상승 + RSI/BB/MA 조건. 정찰 매수.</div>
  </div></div>
  <div class="idx-item"><div><span class="pill pill-buy">2nd BUY</span></div><div>
    <div class="idx-name">2nd tranche (30%)</div>
    <div class="idx-desc">이중바닥 + MACD 골든크로스.</div>
  </div></div>
  <div class="idx-item"><div><span class="pill pill-buy">3rd BUY</span></div><div>
    <div class="idx-name">3rd tranche (50%)</div>
    <div class="idx-desc">MA20 돌파 + MACD 0선.</div>
  </div></div>
  <div class="idx-item"><div><span class="pill pill-bond">BOND WATCH</span></div><div>
    <div class="idx-name">Bond/gold entry</div>
    <div class="idx-desc">30Y 금리 5.0% 또는 GLD 조건.</div>
  </div></div>
</div>
<div class="idx-sub">Hold / watch</div>
<div class="idx-grid">
  <div class="idx-item"><div><span class="pill pill-hold">HOLD</span></div><div>
    <div class="idx-name">Position maintained</div>
    <div class="idx-desc">특이 신호 없음.</div>
  </div></div>
  <div class="idx-item"><div><span class="pill pill-wait">WATCH</span></div><div>
    <div class="idx-name">Entry approaching</div>
    <div class="idx-desc">진입 조건 근접.</div>
  </div></div>
  <div class="idx-item"><div><span class="pill pill-block">BLOCKED</span></div><div>
    <div class="idx-name">Master switch block</div>
    <div class="idx-desc">기술적 충족이나 RED로 차단.</div>
  </div></div>
  <div class="idx-item"><div><span class="pill pill-hold">CASH</span></div><div>
    <div class="idx-name">Cash equivalent</div>
    <div class="idx-desc">BIL 등 현금성.</div>
  </div></div>
</div>
<div class="idx-sub">Exit signals</div>
<div class="idx-grid">
  <div class="idx-item"><div><span class="pill pill-sell">L1 WARN</span></div><div>
    <div class="idx-name">Early warning</div>
    <div class="idx-desc">MACD 둔화 + 거래량 감소.</div>
  </div></div>
  <div class="idx-item"><div><span class="pill pill-sell">L2 WEAK</span></div><div>
    <div class="idx-name">Trend weakening</div>
    <div class="idx-desc">MACD 3d 하락 + 손실 -15~-30%.</div>
  </div></div>
  <div class="idx-item"><div><span class="pill pill-sell">L3 EXIT</span></div><div>
    <div class="idx-name">Trend breakdown</div>
    <div class="idx-desc">MA20 2d 이탈 또는 -8%.</div>
  </div></div>
  <div class="idx-item"><div><span class="pill pill-top">TOP</span></div><div>
    <div class="idx-name">Overheated</div>
    <div class="idx-desc">RSI 75+ 또는 BB 상단 돌파.</div>
  </div></div>
</div>
<div class="idx-sub">Master switch / confidence</div>
<div class="sw-row">
  <div class="sw-card sw-gg"><div class="sl">GREEN</div><div class="sd">전 전략 가동</div></div>
  <div class="sw-card sw-yy"><div class="sl">YELLOW</div><div class="sd">1차만 허용</div></div>
  <div class="sw-card sw-rr"><div class="sl">RED</div><div class="sd">매수 전면 금지</div></div>
</div>
<div class="rate-label">
  <span class="conf-bar" style="width:60px"><span class="conf-fill" style="width:85%;background:#0F6E56"></span></span>
  80-100%: 높은 확신
</div>
<div class="rate-label">
  <span class="conf-bar" style="width:60px"><span class="conf-fill" style="width:55%;background:#BA7517"></span></span>
  50-79%: 중간 확신
</div>
<div class="rate-label">
  <span class="conf-bar" style="width:60px"><span class="conf-fill" style="width:25%;background:#A32D2D"></span></span>
  0-49%: 주의 필요
</div>
</div>"""


# ── 전략 프로그레스 ───────────────────────────────────────

def strategy_progress(current_tranche: int, classification: str) -> str:
    stages = [
        ("1차", "20%", current_tranche >= 1),
        ("2차", "30%", current_tranche >= 2),
        ("3차", "50%", current_tranche >= 3),
    ]
    items = []
    for name, pct, done in stages:
        color = "#0F6E56" if done else "#E0E0E0"
        items.append(
            f'<div style="flex:1;text-align:center;font-size:10px">'
            f'<div style="height:4px;background:{color};border-radius:2px;margin-bottom:3px"></div>'
            f'{name} ({pct})</div>'
        )
    return (
        f'<div style="display:flex;gap:4px;margin-bottom:8px">{"".join(items)}</div>'
    )
