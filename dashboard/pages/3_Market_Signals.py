"""
dashboard/pages/3_Signals.py — 통합 시그널 페이지 (v4.0)
마스터 스위치/VIX 비포함 순수 기술 지표 기반 시그널
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR))
DATA_DIR = ROOT_DIR / "data"

USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

st.set_page_config(
    page_title="Signals | AI Trading Assistant",
    layout="wide",
)

from dashboard.style import inject_css, inject_sidebar_css
from dashboard.components import signal_card, signal_index_html

st.markdown(inject_css(), unsafe_allow_html=True)
st.markdown(inject_sidebar_css(), unsafe_allow_html=True)


# ── 데이터 로드 ────────────────────────────────────────────────

def load_signals() -> dict:
    path = DATA_DIR / "signals.json"
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


# ── 메인 ──────────────────────────────────────────────────────────

market = load_market()
signals_doc = load_signals()

ms = market.get("master_switch", {})
ms_status = ms.get("status", "RED")
macro = market.get("macro", {})
sw_cls = {"RED": "sw-r", "YELLOW": "sw-y", "GREEN": "sw-g"}.get(ms_status, "sw-r")

st.markdown(
    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">'
    f'<h1 style="font-size:22px;font-weight:500;margin:0">Signals</h1>'
    f'<span class="sw {sw_cls}">{ms_status}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

if not signals_doc:
    st.markdown(
        '<div style="background:#FFF3CD;border-radius:8px;padding:10px 14px;'
        'color:#856404;font-size:12px">'
        'signals.json 없음 — Overview 페이지에서 \ud83d\udd04 Update를 클릭하세요.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ── 매크로 경고 배너 (표시 전용) ──────────────────────────────

_macro_alerts = signals_doc.get("macro_alerts", [])
for _alert in _macro_alerts:
    _lvl = _alert.get("level", "info")
    _bg = {"danger": "#FDECEA", "warning": "#FFF3CD", "caution": "#FFF8E1", "info": "#E8F4FD"}.get(_lvl, "#F5F5F5")
    _color = {"danger": "#C62828", "warning": "#856404", "caution": "#6D4C00", "info": "#1565C0"}.get(_lvl, "#333")
    _icon = {"danger": "🚨", "warning": "⚠️", "caution": "⚡", "info": "ℹ️"}.get(_lvl, "")
    st.markdown(
        f'<div style="background:{_bg};border-radius:6px;padding:8px 12px;margin-bottom:6px;'
        f'color:{_color};font-size:12px">{_icon} {_alert.get("message","")}'
        f'<span style="font-size:10px;opacity:0.6;margin-left:8px">(표시 전용)</span></div>',
        unsafe_allow_html=True,
    )

sig_list = signals_doc.get("signals", [])
date_label = signals_doc.get("date", "")
if date_label:
    st.markdown(
        f'<div style="font-size:11px;color:#888;margin-bottom:12px">생성: {date_label}</div>',
        unsafe_allow_html=True,
    )

# 카테고리별 분류
WARN_ACTIONS  = {"L1_WARNING", "L2_WEAKENING", "L3_BREAKDOWN", "TOP_SIGNAL"}
BUY_ACTIONS   = {"BUY_T1", "BUY_T2", "BUY_T3", "TRANCHE_1_BUY", "TRANCHE_2_BUY", "TRANCHE_3_BUY"}
WATCH_ACTIONS = {"WATCH", "BOND_WATCH"}

warns  = [s for s in sig_list if s.get("action") in WARN_ACTIONS]
buys   = [s for s in sig_list if s.get("action") in BUY_ACTIONS]
watchs = [s for s in sig_list if s.get("action") in WATCH_ACTIONS]
holds  = [s for s in sig_list if s.get("action") not in WARN_ACTIONS | BUY_ACTIONS | WATCH_ACTIONS]

# 요약 카운트
st.markdown(
    f'<div class="sig-sm" style="margin-bottom:14px">'
    f'<span class="cnt">{len(warns)} warnings</span>'
    f'<span class="cnt">{len(watchs)} watch</span>'
    f'<span class="cnt">{len(buys)} buy</span>'
    f'<span class="cnt">{len(holds)} hold/cash</span>'
    f'</div>',
    unsafe_allow_html=True,
)


def render_section(title: str, items: list) -> None:
    if not items:
        return
    st.markdown(f'<div class="sh">{title}</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, s in enumerate(items):
        with cols[i % 2]:
            cond_met = s.get("conditions_met", [])
            cond_not = s.get("conditions_not_met", [])
            detail = ""
            if cond_met:
                detail += "\u2713 " + ", ".join(cond_met[:3])
            if cond_not:
                detail += ("  " if detail else "") + "\u2717 " + ", ".join(cond_not[:2])
            st.markdown(
                signal_card(
                    s["ticker"], s["action"],
                    s.get("confidence", 50),
                    s.get("rationale", "") + (f'<div style="font-size:10px;color:#999;margin-top:4px">{detail}</div>' if detail else ""),
                ),
                unsafe_allow_html=True,
            )


render_section("Exit / Warning", warns)
render_section("Buy signals", buys)
render_section("Watch", watchs)

if holds:
    with st.expander(f"Hold / Cash ({len(holds)})"):
        cols = st.columns(2)
        for i, s in enumerate(holds):
            with cols[i % 2]:
                st.markdown(
                    signal_card(s["ticker"], s["action"], s.get("confidence", 50), s.get("rationale", "")),
                    unsafe_allow_html=True,
                )

st.markdown('<hr class="sep">', unsafe_allow_html=True)
st.markdown(signal_index_html(), unsafe_allow_html=True)
