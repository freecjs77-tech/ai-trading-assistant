"""
dashboard/components.py — 재사용 HTML 컴포넌트
모든 페이지에서 import하여 사용
"""
from __future__ import annotations


def metric_card(label: str, value: str, change: str = "", change_class: str = "") -> str:
    ch = f'<div class="change {change_class}">{change}</div>' if change else ""
    return (
        f'<div class="metric-card">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f'{ch}</div>'
    )


def macro_card(label: str, value: str, status: str = "", status_class: str = "") -> str:
    st_html = f'<div class="status {status_class}">{status}</div>' if status else ""
    return (
        f'<div class="macro-card">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f'{st_html}</div>'
    )


_PILL_CLASS: dict[str, str] = {
    "L1_WARNING":    "pill-sell",
    "L2_WEAKENING":  "pill-sell",
    "L3_BREAKDOWN":  "pill-sell",
    "TOP_SIGNAL":    "pill-top",
    "BUY_T1":        "pill-buy",
    "BUY_T2":        "pill-buy",
    "BUY_T3":        "pill-buy",
    "TRANCHE_1_BUY": "pill-buy",
    "TRANCHE_2_BUY": "pill-buy",
    "TRANCHE_3_BUY": "pill-buy",
    "WATCH":         "pill-wait",
    "BOND_WATCH":    "pill-bond",
    "BLOCKED":       "pill-block",
    "CASH":          "pill-hold",
    "HOLD":          "pill-hold",
}

_CARD_CLASS: dict[str, str] = {
    "L1_WARNING":   "signal-card-warn",
    "L2_WEAKENING": "signal-card-warn",
    "L3_BREAKDOWN": "signal-card-warn",
    "TOP_SIGNAL":   "signal-card-warn",
    "BUY_T1":       "signal-card-buy",
    "BUY_T2":       "signal-card-buy",
    "BUY_T3":       "signal-card-buy",
    "WATCH":        "signal-card-watch",
    "BOND_WATCH":   "signal-card-watch",
    "HOLD":         "signal-card-hold",
    "BLOCKED":      "signal-card-hold",
    "CASH":         "signal-card-hold",
}


def _conf_color(action: str) -> str:
    if any(x in action for x in ("WARNING", "BREAKDOWN", "WEAKENING", "TOP")):
        return "#A32D2D"
    if "BUY" in action:
        return "#0F6E56"
    return "#BA7517"


def pill_html(action: str) -> str:
    cls   = _PILL_CLASS.get(action, "pill-hold")
    label = action.replace("_", " ")
    return f'<span class="pill {cls}">{label}</span>'


def signal_card(
    ticker: str,
    action: str,
    confidence: int,
    rationale: str,
    conditions_met: list[str] | None = None,
    conditions_not_met: list[str] | None = None,
) -> str:
    conds_met  = conditions_met or []
    conds_not  = conditions_not_met or []
    pc         = _PILL_CLASS.get(action, "pill-hold")
    card_cls   = _CARD_CLASS.get(action, "signal-card-hold")
    conf_c     = _conf_color(action)
    label      = action.replace("_", " ")
    tags = "".join(f'<span class="cond-tag cond-met">{c}</span>' for c in conds_met[:4])
    tags += "".join(f'<span class="cond-tag cond-not">{c}</span>' for c in conds_not[:3])
    tags_html = f'<div style="margin-top:6px">{tags}</div>' if tags else ""
    return (
        f'<div class="signal-card {card_cls}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">'
        f'<span style="font-weight:500;font-size:13px">{ticker} '
        f'<span class="pill {pc}">{label}</span></span>'
        f'<span style="font-size:10px;color:#888">'
        f'<span class="conf-bar"><span class="conf-fill" style="width:{confidence}%;background:{conf_c}"></span></span>'
        f'{confidence}%</span></div>'
        f'<div style="font-size:11px;color:#666;line-height:1.5">{rationale}</div>'
        f'{tags_html}</div>'
    )


def master_switch_banner(
    status: str,
    qqq_price: float,
    qqq_ma200: float,
    spy_price: float,
    spy_ma200: float,
    vix: float,
) -> str:
    cls      = {"RED": "switch-red", "GREEN": "switch-green", "YELLOW": "switch-yellow"}.get(status, "switch-red")
    border_c = {"RED": "#A32D2D",   "GREEN": "#0F6E56",      "YELLOW": "#BA7517"}.get(status, "#888")
    return (
        f'<div class="signal-card" style="border-left:3px solid {border_c};border-radius:0">'
        f'<div style="font-weight:500;font-size:14px;margin-bottom:6px">'
        f'Master switch: <span class="switch-badge {cls}">{status}</span></div>'
        f'<div style="font-size:12px;color:#666">'
        f'QQQ ${qqq_price:,.0f} vs MA200 ${qqq_ma200:,.0f} &nbsp;•&nbsp; '
        f'SPY ${spy_price:,.0f} vs MA200 ${spy_ma200:,.0f} &nbsp;•&nbsp; '
        f'VIX {vix:.1f}</div></div>'
    )


def format_krw(usd_amount: float, rate: float) -> str:
    """USD → 한국식 원화 표기"""
    krw = usd_amount * rate
    sign = "-" if krw < 0 else ""
    krw = abs(krw)
    if krw >= 100_000_000:
        return f"{sign}₩{krw/100_000_000:.2f}억"
    elif krw >= 10_000_000:
        return f"{sign}₩{krw/10_000:,.0f}만"
    elif krw >= 1_000_000:
        return f"{sign}₩{krw/10_000:,.0f}만"
    else:
        return f"{sign}₩{krw:,.0f}"


def strategy_progress(stage: dict, classification: str) -> str:
    if not stage:
        return ""
    label_map = {
        "growth_v22":    ("1차(20%)", "2차(30%)", "3차(50%)"),
        "etf_v24":       ("1차(20%)", "2차(30%)", "3차(50%)"),
        "energy_v23":    ("1차(25%)", "2차(25%)", "3차(50%)"),
        "bond_gold_v26": ("1차 TLT",  "2차 TLT",  "BIL/SLV"),
        "speculative":   ("진입",     "홀드",      "—"),
    }
    labels  = label_map.get(classification, ("1st", "2nd", "3rd"))
    current = stage.get("current_tranche", 0)
    steps = []
    for i, lbl in enumerate(labels, 1):
        if i < current:
            steps.append(f'<span class="step-done">✓ {lbl}</span>')
        elif i == current:
            steps.append(f'<span class="step-cur">▶ {lbl}</span>')
        else:
            steps.append(f'<span class="step-lock">○ {lbl}</span>')
    return "".join(steps)


def signal_index_html() -> str:
    """Overview 하단 시그널 레퍼런스 패널"""
    return '''
<div style="padding-top:14px;border-top:0.5px solid #E0E0E0;margin-top:14px">
<div style="font-size:14px;font-weight:500;margin-bottom:10px">Signal reference</div>

<div style="font-size:12px;font-weight:500;color:#888;margin:10px 0 6px">Entry signals</div>
<div class="idx-grid">
  <div class="idx-item"><div><span class="pill pill-buy">1st BUY</span></div><div><div class="idx-name">1st tranche (20%)</div><div class="idx-desc">MACD hist 상승 + RSI/BB/MA 조건. 정찰 매수.</div></div></div>
  <div class="idx-item"><div><span class="pill pill-buy">2nd BUY</span></div><div><div class="idx-name">2nd tranche (30%)</div><div class="idx-desc">이중바닥 + MACD 골든크로스. 본격 비중 확대.</div></div></div>
  <div class="idx-item"><div><span class="pill pill-buy">3rd BUY</span></div><div><div class="idx-name">3rd tranche (50%)</div><div class="idx-desc">MA20 돌파 + MACD 0선. 추세 전환 확인.</div></div></div>
  <div class="idx-item"><div><span class="pill pill-bond">BOND</span></div><div><div class="idx-name">Bond/gold entry</div><div class="idx-desc">30Y 금리 5.0% 또는 GLD 조건. 마스터 독립.</div></div></div>
</div>

<div style="font-size:12px;font-weight:500;color:#888;margin:10px 0 6px">Hold / watch</div>
<div class="idx-grid">
  <div class="idx-item"><div><span class="pill pill-hold">HOLD</span></div><div><div class="idx-name">Position maintained</div><div class="idx-desc">특이 신호 없음. 현 포지션 유지.</div></div></div>
  <div class="idx-item"><div><span class="pill pill-wait">WATCH</span></div><div><div class="idx-name">Entry approaching</div><div class="idx-desc">진입 조건 근접 중. 아직 미충족.</div></div></div>
  <div class="idx-item"><div><span class="pill pill-block">BLOCKED</span></div><div><div class="idx-name">Master switch block</div><div class="idx-desc">기술적 조건 충족이나 마스터 RED로 차단.</div></div></div>
  <div class="idx-item"><div><span class="pill pill-hold">CASH</span></div><div><div class="idx-name">Cash equivalent</div><div class="idx-desc">BIL 등 현금성. 시장 하락 방어.</div></div></div>
</div>

<div style="font-size:12px;font-weight:500;color:#888;margin:10px 0 6px">Exit signals (escalation)</div>
<div class="idx-grid">
  <div class="idx-item"><div><span class="pill pill-sell">L1 WARN</span></div><div><div class="idx-name">Early warning</div><div class="idx-desc">MACD 둔화 + RSI 꺾임. 매수 중단.</div></div></div>
  <div class="idx-item"><div><span class="pill pill-sell">L2 WEAK</span></div><div><div class="idx-name">Trend weakening</div><div class="idx-desc">MACD 3d 하락 + MA20 이탈. 30% 트림.</div></div></div>
  <div class="idx-item"><div><span class="pill pill-sell">L3 EXIT</span></div><div><div class="idx-name">Trend breakdown</div><div class="idx-desc">MA20 2d 이탈 또는 -8%. 전량 매도.</div></div></div>
  <div class="idx-item"><div><span class="pill pill-top">TOP</span></div><div><div class="idx-name">Overheated</div><div class="idx-desc">RSI 75+ 또는 3d +10%. 강제 익절.</div></div></div>
</div>

<div style="font-size:12px;font-weight:500;color:#888;margin:10px 0 6px">Master switch / confidence</div>
<div style="display:flex;gap:6px;margin-bottom:8px">
  <div style="flex:1;padding:6px 8px;border-radius:8px;text-align:center;background:#EAF3DE"><div style="font-size:10px;font-weight:500;color:#27500A">GREEN</div><div style="font-size:9px;color:#3B6D11">전 전략 가동</div></div>
  <div style="flex:1;padding:6px 8px;border-radius:8px;text-align:center;background:#FAEEDA"><div style="font-size:10px;font-weight:500;color:#633806">YELLOW</div><div style="font-size:9px;color:#854F0B">1차만 허용</div></div>
  <div style="flex:1;padding:6px 8px;border-radius:8px;text-align:center;background:#FCEBEB"><div style="font-size:10px;font-weight:500;color:#791F1F">RED</div><div style="font-size:9px;color:#A32D2D">매수 전면 금지</div></div>
</div>
<div style="font-size:10px;color:#888;margin:3px 0;display:flex;align-items:center;gap:5px"><span class="conf-bar" style="width:60px"><span class="conf-fill" style="width:85%;background:#0F6E56"></span></span> 80-100%: 높은 확신</div>
<div style="font-size:10px;color:#888;margin:3px 0;display:flex;align-items:center;gap:5px"><span class="conf-bar" style="width:60px"><span class="conf-fill" style="width:55%;background:#BA7517"></span></span> 50-79%: 중간 확신</div>
<div style="font-size:10px;color:#888;margin:3px 0;display:flex;align-items:center;gap:5px"><span class="conf-bar" style="width:60px"><span class="conf-fill" style="width:25%;background:#A32D2D"></span></span> 0-49%: 주의 필요</div>
</div>'''
