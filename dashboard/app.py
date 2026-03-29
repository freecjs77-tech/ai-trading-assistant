"""
dashboard/app.py — Overview 페이지 (overview_target.html 기준)
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from dashboard.style import inject_css
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

KST = timezone(timedelta(hours=9))
DATA_DIR = ROOT_DIR / "data"
USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"


# ── 데이터 로드 ───────────────────────────────────────────

def load_portfolio() -> dict:
    path = DATA_DIR / ("test_portfolio.json" if USE_MOCK else "portfolio.json")
    if not path.exists():
        path = DATA_DIR / "portfolio.json"
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


def load_signals_doc(mode: str = "full") -> dict:
    fname = "signals_technical.json" if mode == "technical_only" else "signals.json"
    path = DATA_DIR / fname
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def gen_signals(market: dict, portfolio: dict, mode: str = "full") -> dict:
    try:
        from signal_generator import generate_signals
        return generate_signals(mode=mode, portfolio_data=portfolio, market_data=market)
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


# ── 초기 데이터 ──────────────────────────────────────────

portfolio = load_portfolio()
market = load_market()
holdings = portfolio.get("holdings", [])
ms = market.get("master_switch", {})
macro = market.get("macro", {})
ms_status = ms.get("status", "RED")
usdkrw = macro.get("usdkrw") or 1400.0

sig_full_doc = load_signals_doc("full")
sig_tech_doc = load_signals_doc("technical_only")
if not sig_full_doc and market and portfolio:
    sig_full_doc = gen_signals(market, portfolio, "full")
if not sig_tech_doc and market and portfolio:
    sig_tech_doc = gen_signals(market, portfolio, "technical_only")

sig_m = signals_dict(sig_full_doc)
sig_t = signals_dict(sig_tech_doc)

total_value = portfolio.get("total_value_usd", 0)
total_cost = portfolio.get("total_cost_usd", sum(
    h.get("shares", 0) * h.get("avg_cost", 0) for h in holdings
))

# ── 헤더 ─────────────────────────────────────────────────

col_title, col_ctrl = st.columns([2, 2])

with col_title:
    updated_at = portfolio.get("updated_at", "")
    date_str = fmt_date(updated_at) if updated_at else datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    st.markdown(f"""<div class="hdr">
  <div><h1>Portfolio dashboard</h1><span class="meta">{date_str}</span></div>
</div>""", unsafe_allow_html=True)

with col_ctrl:
    c1, c2, c3 = st.columns([1.2, 1.5, 1])
    sw_cls = {"RED": "sw-r", "YELLOW": "sw-y", "GREEN": "sw-g"}.get(ms_status, "sw-r")
    with c1:
        st.markdown(f'<div style="padding-top:8px"><span class="sw {sw_cls}">Master: {ms_status}</span></div>',
                    unsafe_allow_html=True)
    with c2:
        currency = st.radio("통화", ["USD", "KRW"], horizontal=True,
                            label_visibility="collapsed", key="currency")
    with c3:
        update_clicked = st.button("🔄 Update", use_container_width=True)

if st.session_state.get("currency") == "KRW":
    st.markdown(
        f'<div class="rate">1 USD = ₩{usdkrw:,.2f} ({datetime.now(KST).strftime("%Y-%m-%d")} via yfinance)</div>',
        unsafe_allow_html=True)

if update_clicked:
    with st.spinner("업데이트 중..."):
        try:
            from market_data import update_market_data
            update_market_data()
        except Exception:
            pass
        market = load_market()
        sig_full_doc = gen_signals(market, portfolio, "full")
        sig_tech_doc = gen_signals(market, portfolio, "technical_only")
        sig_m = signals_dict(sig_full_doc)
        sig_t = signals_dict(sig_tech_doc)
        st.rerun()

# ── 마스터 스위치 배너 ────────────────────────────────────

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

# ── 메트릭 카드 ───────────────────────────────────────────

pnl_usd = total_value - total_cost
pnl_pct = (pnl_usd / total_cost * 100) if total_cost > 0 else 0
pnl_cls = "up" if pnl_usd >= 0 else "dn"
pnl_sign = "+" if pnl_usd >= 0 else ""
ytd_div = sum(h.get("ytd_dividend_usd", 0) for h in holdings) or 1791.0

curr = st.session_state.get("currency", "USD")
if curr == "KRW":
    val_str = format_krw(total_value, usdkrw)
    pnl_str = ("+" if pnl_usd >= 0 else "") + format_krw(abs(pnl_usd), usdkrw)
    div_str = format_krw(ytd_div, usdkrw)
else:
    val_str = f"${total_value:,.0f}"
    pnl_str = f"{pnl_sign}${abs(pnl_usd):,.0f}"
    div_str = f"${ytd_div:,.0f}"

st.markdown(metrics_row([
    metric_card("Total value", val_str, f"{pnl_sign}{pnl_pct:.1f}%", pnl_cls),
    metric_card("Holdings", f"{len(holdings)} 종목"),
    metric_card("Total return", f"{pnl_sign}{pnl_pct:.1f}%", pnl_str, pnl_cls),
    metric_card("YTD dividend", div_str),
]), unsafe_allow_html=True)

# ── 매크로 카드 ───────────────────────────────────────────

vix = macro.get("vix") or 0
treasury = macro.get("treasury_30y") or 0
qqq_price = ms.get("qqq_price") or 0
qqq_ma200 = ms.get("qqq_ma200") or 0

qqq_diff_pct = ((qqq_price - qqq_ma200) / qqq_ma200 * 100) if qqq_ma200 > 0 else 0
qqq_cls = "up" if qqq_diff_pct >= 0 else "dn"
qqq_sign = "▲" if qqq_diff_pct >= 0 else "▼"

vix_label = "정상" if vix < 20 else ("주의" if vix < 25 else ("공포" if vix < 30 else "극공포"))
vix_cls = "up" if vix < 20 else ("warn" if vix < 25 else "dn")
tsy_cls = "up" if treasury < 4.5 else ("warn" if treasury < 5.0 else "dn")
tsy_label = "정상" if treasury < 4.5 else ("관찰" if treasury < 5.0 else "위험")

st.markdown(macro_row([
    macro_card("QQQ vs MA200", f"${qqq_price:,.0f}", f"{qqq_sign} {qqq_diff_pct:.1f}%", qqq_cls),
    macro_card("30Y Treasury", f"{treasury:.3f}%", tsy_label, tsy_cls),
    macro_card("VIX", f"{vix:.1f}", vix_label, vix_cls),
]), unsafe_allow_html=True)

# ── 보유 테이블 ───────────────────────────────────────────

max_value = max((h.get("value_usd", 0) for h in holdings), default=1)

st.markdown(
    holdings_table_html(
        holdings=holdings,
        signals_market=sig_m,
        signals_tech=sig_t,
        currency=curr,
        usdkrw=usdkrw,
        max_value=max_value,
    ),
    unsafe_allow_html=True,
)

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ── 듀얼 시그널 섹션 ─────────────────────────────────────

HOLD_ACTIONS = {"HOLD", "CASH"}

def count_summary(d: dict) -> dict:
    c = {"warn": 0, "watch": 0, "buy": 0, "hold": 0}
    for a in d.values():
        if not isinstance(a, str):
            c["hold"] += 1
            continue
        if a in ("L1_WARNING", "L2_WEAKENING", "L3_BREAKDOWN", "TOP_SIGNAL"):
            c["warn"] += 1
        elif a in ("WATCH", "BOND_WATCH"):
            c["watch"] += 1
        elif "BUY" in a:
            c["buy"] += 1
        else:
            c["hold"] += 1
    return c


def render_signal_col(sig_list: list, mode: str) -> str:
    active = [s for s in sig_list if s.get("action") not in HOLD_ACTIONS]
    hold_n = sum(1 for s in sig_list if s.get("action") in HOLD_ACTIONS)
    cards = "".join(
        signal_card(s["ticker"], s["action"], s.get("confidence", 50), s.get("rationale", ""))
        for s in active[:6]
    )
    note = ""
    if hold_n > 0:
        label = "master RED: 주식 매수 정지" if mode == "full" and ms_status == "RED" else "순수 기술지표"
        note = f'<div style="font-size:10px;color:#888;padding:4px 0">{hold_n} tickers in HOLD ({label})</div>'
    return cards + note


c_m = count_summary(sig_m)
c_t = count_summary(sig_t)
sw_b = f'<span class="sw sw-{ms_status[0].lower()}" style="font-size:10px;padding:2px 8px">M</span>'
tech_b = '<span style="display:inline-block;font-size:10px;padding:2px 8px;border-radius:6px;background:#E6F1FB;color:#0C447C">T</span>'

sig_full_list = sig_full_doc.get("signals", [])
sig_tech_list = sig_tech_doc.get("signals", [])

st.markdown(f"""<div class="sig-row">
<div class="sig-col">
  <h3>{sw_b} Market signals</h3>
  <div class="sig-sm">
    <span class="cnt">{c_m['warn']} warnings</span>
    <span class="cnt">{c_m['watch']} watch</span>
    <span class="cnt">{c_m['buy']} buy</span>
    <span class="cnt">{c_m['hold']} hold</span>
  </div>
  {render_signal_col(sig_full_list, 'full')}
</div>
<div class="sig-col">
  <h3>{tech_b} Technical signals</h3>
  <div class="sig-sm">
    <span class="cnt">{c_t['warn']} warnings</span>
    <span class="cnt">{c_t['watch']} watch</span>
    <span class="cnt">{c_t['buy']} buy</span>
    <span class="cnt">{c_t['hold']} hold</span>
  </div>
  {render_signal_col(sig_tech_list, 'technical_only')}
</div>
</div>""", unsafe_allow_html=True)

# ── Signal reference 인덱스 ──────────────────────────────

st.markdown(signal_index_html(), unsafe_allow_html=True)
