"""
dashboard/pages/2_Market_Signals.py — 종합 시그널 (마스터 스위치 + 매크로 반영)
라이트 모드 전용. 모든 UI는 HTML로 직접 렌더링.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import streamlit as st

ROOT_DIR     = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))
DATA_DIR     = ROOT_DIR / "data"
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"

USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

st.set_page_config(page_title="Market Signals | AI Trading Assistant", page_icon="📡", layout="wide")

from style import inject_css
from components import signal_card, master_switch_banner, metric_card

inject_css()


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=60)
def load_signals() -> Optional[dict]:
    return _load_json(DATA_DIR / "signals.json")


@st.cache_data(ttl=60)
def load_market() -> Optional[dict]:
    if USE_MOCK:
        return _load_json(FIXTURES_DIR / "mock_market_data.json")
    return _load_json(DATA_DIR / "market_cache.json")


def gen_mock_signals() -> Optional[dict]:
    port = _load_json(DATA_DIR / "test_portfolio.json")
    mkt  = _load_json(FIXTURES_DIR / "mock_market_data.json")
    if not port or not mkt:
        return None
    from signal_generator import generate_signals
    return generate_signals(mode="full", portfolio_data=port, market_data=mkt)


# ─────────────────────────────────────────────

market = load_market()

if USE_MOCK:
    signals = gen_mock_signals()
    if not signals:
        st.markdown('<div style="background:#FCEBEB;border-radius:8px;padding:12px;color:#791F1F;font-size:12px">mock 데이터 생성 실패</div>', unsafe_allow_html=True)
        st.stop()
else:
    signals = load_signals()

# ── 헤더 ──
st.markdown(
    '<div style="font-size:22px;font-weight:600;color:#1A1A1A;margin-bottom:2px">Market Signals</div>'
    '<div style="font-size:11px;color:#888780">마스터 스위치 + VIX + 금리 등 매크로 환경 반영</div>',
    unsafe_allow_html=True,
)

if not signals:
    st.markdown(
        '<div style="background:#FFF3CD;border-radius:8px;padding:12px 16px;color:#856404;font-size:12px;margin-top:12px">'
        'signals.json 없음 — Overview에서 Update 버튼을 누르세요.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ── 마스터 스위치 배너 ──
if market:
    ms    = market.get("master_switch", {})
    macro = market.get("macro", {})
    st.markdown(
        master_switch_banner(
            status=ms.get("status", "RED"),
            qqq_price=ms.get("qqq_price", 0),
            qqq_ma200=ms.get("qqq_ma200", 0),
            spy_price=ms.get("spy_price", 0),
            spy_ma200=ms.get("spy_ma200", 0),
            vix=macro.get("vix", 0),
        ),
        unsafe_allow_html=True,
    )

# ── 매크로 알림 (HTML) ──
for alert in signals.get("macro_alerts", []):
    level = alert.get("level", "info")
    msg   = alert.get("message", "")
    if level in ("warning", "danger"):
        bg, color = "#FCEBEB", "#791F1F"
    elif level == "caution":
        bg, color = "#FFF3CD", "#856404"
    else:
        bg, color = "#E8F4FD", "#0C447C"
    st.markdown(
        f'<div style="background:{bg};border-radius:8px;padding:10px 14px;'
        f'color:{color};font-size:12px;margin-bottom:6px">{msg}</div>',
        unsafe_allow_html=True,
    )

st.markdown('<hr style="border:none;border-top:0.5px solid #E0E0E0;margin:12px 0">', unsafe_allow_html=True)

# ── 요약 카드 ──
summary = signals.get("summary", {})
alloc   = signals.get("allocation_modifier", 1.0)
alloc_note = signals.get("allocation_note", "")
warn_cnt = summary.get("l3_breakdown", 0) + summary.get("l2_weakening", 0) + summary.get("l1_warning", 0) + summary.get("top_signal", 0)

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(metric_card("경고", str(warn_cnt), change_class="dn"), unsafe_allow_html=True)
c2.markdown(metric_card("매수", str(summary.get("buy", 0)), change_class="up"), unsafe_allow_html=True)
c3.markdown(metric_card("관심", str(summary.get("watch", 0))), unsafe_allow_html=True)
c4.markdown(metric_card("홀드", str(summary.get("hold", 0))), unsafe_allow_html=True)
c5.markdown(metric_card("배분", f"x{alloc:.1f}", alloc_note), unsafe_allow_html=True)

st.markdown('<hr style="border:none;border-top:0.5px solid #E0E0E0;margin:12px 0">', unsafe_allow_html=True)

# ── 시그널 카드 ──
_GROUP_ORDER = [
    "L3_BREAKDOWN", "TOP_SIGNAL", "L2_WEAKENING", "L1_WARNING",
    "BUY_T3", "BUY_T2", "BUY_T1", "WATCH", "HOLD",
]
_GROUP_LABEL = {
    "L3_BREAKDOWN": "⛔ L3 붕괴",    "L2_WEAKENING": "🔴 L2 약화",
    "L1_WARNING":   "🟠 L1 경고",    "TOP_SIGNAL":   "🔴 과매수",
    "BUY_T1":       "🟢 1차 매수",   "BUY_T2":       "🟢 2차 매수",
    "BUY_T3":       "🟢 3차 매수",   "WATCH":        "🟡 관심",
    "HOLD":         "⚪ 홀드",
}

sig_list = signals.get("signals", [])
# HOLD 제외 (기본)
non_hold = [s for s in sig_list if s["action"] != "HOLD"]
if not non_hold:
    st.markdown('<div style="color:#888;font-size:12px">주목 시그널 없음 (모두 HOLD)</div>', unsafe_allow_html=True)

shown: set[str] = set()
for action in _GROUP_ORDER:
    group = [s for s in non_hold if s["action"] == action]
    if not group:
        continue
    st.markdown(
        f'<div style="font-size:12px;font-weight:500;color:#555;margin:10px 0 4px">'
        f'{_GROUP_LABEL.get(action, action)} ({len(group)})</div>',
        unsafe_allow_html=True,
    )
    for s in group:
        st.markdown(
            signal_card(
                ticker=s["ticker"], action=s["action"],
                confidence=s.get("confidence", 0), rationale=s.get("rationale", ""),
                conditions_met=s.get("conditions_met", []),
                conditions_not_met=s.get("conditions_not_met", []),
            ),
            unsafe_allow_html=True,
        )
        shown.add(s["ticker"])
