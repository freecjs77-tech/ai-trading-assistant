"""
dashboard/app.py — Overview 페이지 (v4.0: 단일 시그널 + 매크로 경고 배너)
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR))

from dashboard.style import inject_css, inject_sidebar_css
from dashboard.components import (
    metric_card, metrics_row,
    macro_card, macro_row,
    master_switch_banner,
    holdings_table_html,
    signal_card,
    signal_index_html,
    format_krw,
)

st.set_page_config(
    page_title="Overview | AI Trading Assistant",
    layout="wide",
)
st.markdown(inject_css(), unsafe_allow_html=True)
st.markdown(inject_sidebar_css(), unsafe_allow_html=True)

KST = timezone(timedelta(hours=9))
DATA_DIR = ROOT_DIR / "data"
USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"


# ── 데이터 로드 ──────────────────────────────────────────

def load_portfolio() -> dict:
    path = DATA_DIR / "portfolio.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_market() -> dict:
    if USE_MOCK:
        mock = ROOT_DIR / "tests" / "fixtures" / "mock_market_data.json"
        if mock.exists():
            with open(mock, encoding="utf-8") as f:
                return json.load(f)
    path = DATA_DIR / "market_cache.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_signals_doc() -> dict:
    path = DATA_DIR / "signals.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def gen_signals(market: dict, portfolio: dict) -> dict:
    try:
        from signal_generator import generate_signals
        return generate_signals(portfolio_data=portfolio, market_data=market)
    except Exception:
        return {}


def fmt_date(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
    except Exception:
        return iso_str


def signals_dict(doc: dict) -> dict:
    return {s["ticker"]: s["action"] for s in doc.get("signals", [])}


# ── 시작 ────────────────────────────────────────────────────────

portfolio = load_portfolio()
market = load_market()
holdings = portfolio.get("holdings", [])
ms = market.get("master_switch", {})
macro = market.get("macro", {})
ms_status = ms.get("status", "RED")
usdkrw = macro.get("usdkrw") or 1400.0

sig_doc = load_signals_doc()
if not sig_doc and market and portfolio:
    sig_doc = gen_signals(market, portfolio)

sig = signals_dict(sig_doc)

# ── 헤더 ────────────────────────────────────────────────────────

generated_at = sig_doc.get("generated_at", "")
date_str = fmt_date(generated_at) if generated_at else sig_doc.get("date", "N/A")

col_title, col_upd = st.columns([8, 2])
with col_title:
    st.markdown(
        f'<h1 style="font-size:22px;font-weight:500;margin:0">Overview</h1>'
        f'<div style="font-size:11px;color:#888;margin-top:2px">Updated: {date_str}</div>',
        unsafe_allow_html=True,
    )
with col_upd:
    if st.button("🔄 Update", use_container_width=True):
        new_doc = gen_signals(market, portfolio)
        if new_doc:
            sig_doc = new_doc
            sig = signals_dict(sig_doc)

# ── 매크로 경고 배너 (표시 전용) ────────────────────────────

_macro_alerts = sig_doc.get("macro_alerts", [])
for _alert in _macro_alerts:
    _lvl = _alert.get("level", "info")
    _bg = {"danger": "#FDECEA", "warning": "#FFF3CD", "caution": "#FFF8E1", "info": "#E8F4FD"}.get(_lvl, "#F5F5F5")
    _color = {"danger": "#C62828", "warning": "#856404", "caution": "#6D4C00", "info": "#1565C0"}.get(_lvl, "#333")
    _icon = {"danger": "🚨", "warning": "⚠️", "caution": "⚡", "info": "ℹ️"}.get(_lvl, "")
    st.markdown(
        f'<div style="background:{_bg};border-radius:6px;padding:8px 12px;margin-bottom:6px;'
        f'color:{_color};font-size:12px">{_icon} {_alert.get("message","")}'
        f'<span style="font-size:10px;opacity:0.7;margin-left:8px">(표시 전용 — 시그널 평가 미반영)</span></div>',
        unsafe_allow_html=True,
    )

# ── 마스터 스위치 배너 ──────────────────────────────────────────

st.markdown(
    master_switch_banner(
        status=ms_status,
        qqq_price=ms.get("qqq_price") or 0,
        qqq_ma200=ms.get("qqq_ma200") or 0,
        spy_price=ms.get("spy_price") or 0,
        spy_ma200=ms.get("spy_ma200") or 0,
        vix=macro.get("vix") or 0,
    ),
    unsafe_allow_html=True,
)


# ── 메트릭 카드 ────────────────────────────────────────────────────

total_value = sum(h.get("value_usd", 0) for h in holdings)
total_cost = sum(h.get("cost_usd", 0) for h in holdings)
curr = st.session_state.get("currency", "USD")

pnl_usd = total_value - total_cost
pnl_pct = (pnl_usd / total_cost * 100) if total_cost > 0 else 0
pnl_cls = "up" if pnl_usd >= 0 else "dn"
pnl_sign = "+" if pnl_usd >= 0 else ""
est_annual_div = 0
_div_yields = {
    "VOO": 1.25, "QQQ": 0.55, "SPY": 1.20, "SCHD": 3.40, "AAPL": 0.44,
    "O": 5.60, "JEPI": 7.30, "SOXX": 0.65, "TSLA": 0.0, "TLT": 3.50,
    "NVDA": 0.03, "PLTR": 0.0, "UNH": 1.50, "MSFT": 0.72, "GOOGL": 0.45,
    "AMZN": 0.0, "SLV": 0.0, "BIL": 4.80, "TQQQ": 0.0, "SOXL": 0.0,
    "ETHU": 0.0, "CRCL": 0.0, "BTDR": 0.0,
}
for _h in holdings:
    _dy = _div_yields.get(_h["ticker"], 0) / 100
    est_annual_div += _h.get("value_usd", 0) * _dy
est_annual_div = round(est_annual_div, 0)

_c1, _c2, _c3 = st.columns([6, 1, 1])
with _c2:
    if st.button("USD", use_container_width=True):
        st.session_state["currency"] = "USD"
        st.rerun()
with _c3:
    if st.button("KRW", use_container_width=True):
        st.session_state["currency"] = "KRW"
        st.rerun()


def fmt_val(v: float) -> str:
    return format_krw(v, usdkrw) if curr == "KRW" else f"${v:,.0f}"


st.markdown(
    metrics_row([
        metric_card("Portfolio Value", fmt_val(total_value), ""),
        metric_card("Total P&L", f"{pnl_sign}{fmt_val(abs(pnl_usd))}", f"{pnl_sign}{pnl_pct:.1f}%", pnl_cls),
        metric_card("Est. Annual Div", fmt_val(est_annual_div), ""),
        metric_card("Positions", str(len(holdings)), ""),
    ]),
    unsafe_allow_html=True,
)

# ── 매크로 지표 카드 ────────────────────────────────────────────

treasury = macro.get("treasury_30y") or 0
vix = macro.get("vix") or 0
qqq_price = ms.get("qqq_price") or 0
qqq_ma200_val = ms.get("qqq_ma200") or 0
qqq_diff_pct = ((qqq_price - qqq_ma200_val) / qqq_ma200_val * 100) if qqq_ma200_val > 0 else 0
qqq_cls = "up" if qqq_diff_pct >= 0 else "dn"
qqq_sign = "+" if qqq_diff_pct >= 0 else ""
tsy_cls = "dn" if treasury >= 5.0 else ("warn" if treasury >= 4.8 else "up")
tsy_label = "High" if treasury >= 5.0 else ("Watch" if treasury >= 4.8 else "Normal")
vix_cls = "dn" if vix >= 30 else ("warn" if vix >= 20 else "up")
vix_label = "Panic" if vix >= 30 else ("Fear" if vix >= 20 else "Normal")

st.markdown(macro_row([
    macro_card("QQQ vs MA200", f"${qqq_price:,.0f}", f"{qqq_sign} {qqq_diff_pct:.1f}%", qqq_cls),
    macro_card("30Y Treasury", f"{treasury:.3f}%", tsy_label, tsy_cls),
    macro_card("VIX", f"{vix:.1f}", vix_label, vix_cls),
]), unsafe_allow_html=True)

# ── 보유 테이블 ────────────────────────────────────────────────

max_value = max((h.get("value_usd", 0) for h in holdings), default=1)

st.markdown(
    holdings_table_html(
        holdings=holdings,
        signals=sig,
        currency=curr,
        usdkrw=usdkrw,
        max_value=max_value,
        total_value=total_value,
    ),
    unsafe_allow_html=True,
)

st.markdown('<hr class="sep">', unsafe_allow_html=True)


# ── 시그널 섹션 ─────────────────────────────────────────────────────

HOLD_ACTIONS = {"HOLD", "CASH"}


def count_summary(sig_dict: dict) -> dict:
    c = {"warn": 0, "watch": 0, "buy": 0, "hold": 0}
    for a in sig_dict.values():
        if not isinstance(a, str):
            c["hold"] += 1
        elif a in ("L1_WARNING", "L2_WEAKENING", "L3_BREAKDOWN", "TOP_SIGNAL"):
            c["warn"] += 1
        elif a in ("WATCH", "BOND_WATCH"):
            c["watch"] += 1
        elif "BUY" in a:
            c["buy"] += 1
        else:
            c["hold"] += 1
    return c


def render_signal_col(sig_list: list) -> str:
    active = [s for s in sig_list if s.get("action") not in HOLD_ACTIONS]
    hold_n = sum(1 for s in sig_list if s.get("action") in HOLD_ACTIONS)
    cards = "".join(
        signal_card(s["ticker"], s["action"], s.get("confidence", 50), s.get("rationale", ""))
        for s in active[:6]
    )
    note = ""
    if hold_n > 0:
        note = f'<div style="font-size:10px;color:#888;padding:4px 0">{hold_n}개 종목 HOLD/CASH</div>'
    return cards + note


c_s = count_summary(sig)
sw_b = f'<span class="sw sw-{ms_status[0].lower()}" style="font-size:11px;vertical-align:middle">{ms_status}</span>'

sig_list = sig_doc.get("signals", [])

st.markdown(
    f"""<div class="sig-row" style="display:flex;gap:16px">
<div class="sig-col" style="flex:1">
  <h3 style="font-size:14px;font-weight:600;margin:0 0 8px">{sw_b} Signals</h3>
  <div class="sig-sm">
    <span class="cnt">{c_s['warn']} warnings</span>
    <span class="cnt">{c_s['watch']} watch</span>
    <span class="cnt">{c_s['buy']} buy</span>
    <span class="cnt">{c_s['hold']} hold</span>
  </div>
  {render_signal_col(sig_list)}
</div>
</div>""",
    unsafe_allow_html=True,
)

# ── Signal reference 인덱스 ───────────────────────────────────

st.markdown(signal_index_html(), unsafe_allow_html=True)
