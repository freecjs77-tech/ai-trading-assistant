"""
dashboard/components.py — 재사용 가능한 UI 컴포넌트
"""

from __future__ import annotations


def metric_card(label: str, value: str, change: str = "", change_class: str = "") -> str:
    """메트릭 카드 HTML"""
    change_html = f'<div class="change {change_class}">{change}</div>' if change else ""
    return f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        {change_html}
    </div>"""


def macro_card(label: str, value: str, status: str = "", status_class: str = "") -> str:
    """매크로 지표 카드 HTML"""
    status_html = f'<div class="status {status_class}">{status}</div>' if status else ""
    return f"""
    <div class="macro-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        {status_html}
    </div>"""


# 액션 → 배지 클래스 매핑
_PILL_CLASS: dict[str, str] = {
    "L1_WARNING":    "pill-sell",
    "L2_WEAKENING":  "pill-sell",
    "L3_BREAKDOWN":  "pill-sell",
    "TOP_SIGNAL":    "pill-sell",
    "TRANCHE_1_BUY": "pill-buy",
    "TRANCHE_2_BUY": "pill-buy",
    "BUY_T1":        "pill-buy",
    "BUY_T2":        "pill-buy",
    "BUY_T3":        "pill-buy",
    "WATCH":         "pill-wait",
    "BOND_WATCH":    "pill-bond",
    "HOLD":          "pill-hold",
}

# 액션 → 카드 클래스 매핑
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
}

# 확신도 색상
def _conf_color(action: str) -> str:
    if any(x in action for x in ("WARNING", "BREAKDOWN", "WEAKENING", "TOP")):
        return "#A32D2D"
    if "BUY" in action:
        return "#0F6E56"
    if "WATCH" in action:
        return "#BA7517"
    return "#888780"


def signal_card(
    ticker: str,
    action: str,
    confidence: int,
    rationale: str,
    conditions_met: list[str],
    conditions_not_met: list[str],
) -> str:
    """시그널 카드 HTML"""
    pill_cls  = _PILL_CLASS.get(action, "pill-hold")
    card_cls  = _CARD_CLASS.get(action, "signal-card-hold")
    conf_col  = _conf_color(action)
    label     = action.replace("_", " ")

    met_tags = "".join(
        f'<span class="cond-tag cond-met">{c}</span>' for c in conditions_met[:4]
    )
    not_tags = "".join(
        f'<span class="cond-tag cond-not">{c}</span>' for c in conditions_not_met[:3]
    )

    return f"""
    <div class="signal-card {card_cls}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-weight:500;font-size:14px">{ticker}
                <span class="pill {pill_cls}">{label}</span></span>
            <span style="font-size:11px;color:#888">
                <span class="conf-bar"><span class="conf-fill"
                    style="width:{confidence}%;background:{conf_col}"></span></span>
                {confidence}%
            </span>
        </div>
        <div style="font-size:12px;color:#555;line-height:1.6">{rationale}</div>
        <div style="margin-top:6px">{met_tags}{not_tags}</div>
    </div>"""


def master_switch_banner(
    status: str,
    qqq_price: float,
    qqq_ma200: float,
    spy_price: float,
    spy_ma200: float,
    vix: float,
) -> str:
    """마스터 스위치 배너 HTML"""
    border_color = {"RED": "#A32D2D", "GREEN": "#0F6E56", "YELLOW": "#BA7517"}.get(status, "#888")
    cls = {"RED": "switch-red", "GREEN": "switch-green", "YELLOW": "switch-yellow"}.get(status, "switch-red")
    return f"""
    <div class="signal-card" style="border-left:3px solid {border_color};border-radius:0 12px 12px 0">
        <div style="font-weight:500;font-size:14px;margin-bottom:6px">
            Master switch: <span class="switch-badge {cls}">{status}</span>
        </div>
        <div style="font-size:12px;color:#666">
            QQQ ${qqq_price:.0f} vs MA200 ${qqq_ma200:.0f} &nbsp;•&nbsp;
            SPY ${spy_price:.0f} vs MA200 ${spy_ma200:.0f} &nbsp;•&nbsp;
            VIX {vix:.1f}
        </div>
    </div>"""


def strategy_progress(stage: dict, classification: str) -> str:
    """전략 단계 프로그레스 HTML"""
    if not stage:
        return ""

    label_map = {
        "growth_v22":   ("1차(20%)", "2차(30%)", "3차(50%)"),
        "etf_v24":      ("1차(20%)", "2차(30%)", "3차(50%)"),
        "energy_v23":   ("1차(25%)", "2차(25%)", "3차(50%)"),
        "bond_gold_v26":("1차 TLT", "2차 TLT", "BIL/SLV"),
        "speculative":  ("진입", "홀드", "—"),
    }
    labels = label_map.get(classification, ("1st", "2nd", "3rd"))
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
