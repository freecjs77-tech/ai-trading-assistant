"""
dashboard/pages/3_Technical_Signals.py — 기술지표 전용 시그널
마스터 스위치/VIX/금리 무시, 순수 기술지표만으로 판단.
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

st.set_page_config(page_title="Technical Signals | AI Trading Assistant", page_icon="📉", layout="wide")

from style import inject_css
from components import signal_card, metric_card

inject_css()


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=60)
def load_signals_technical() -> Optional[dict]:
    return _load_json(DATA_DIR / "signals_technical.json")


@st.cache_data(ttl=60)
def load_signals_full() -> Optional[dict]:
    return _load_json(DATA_DIR / "signals.json")


def gen_mock_signals() -> Optional[dict]:
    port = _load_json(DATA_DIR / "test_portfolio.json")
    mkt  = _load_json(FIXTURES_DIR / "mock_market_data.json")
    if not port or not mkt:
        return None
    from signal_generator import generate_signals
    return generate_signals(mode="technical_only", portfolio_data=port, market_data=mkt)


# ─────────────────────────────────────────────

if USE_MOCK:
    signals = gen_mock_signals()
    if not signals:
        st.markdown('<div style="background:#FCEBEB;border-radius:8px;padding:12px;color:#791F1F;font-size:12px">mock 데이터 생성 실패</div>', unsafe_allow_html=True)
        st.stop()
else:
    signals = load_signals_technical()

# ── 헤더 ──
st.markdown(
    '<div style="font-size:22px;font-weight:600;color:#1A1A1A;margin-bottom:2px">Technical Signals</div>'
    '<div style="font-size:11px;color:#888780">순수 기술지표(RSI·MACD·MA·BB)만으로 분석 — 마스터 스위치 무시</div>',
    unsafe_allow_html=True,
)

# ── 경고 배너 (HTML) ──
st.markdown(
    '<div style="background:#FFF3CD;border:0.5px solid #FFEEBA;border-radius:8px;'
    'padding:12px 16px;margin:12px 0">'
    '<div style="font-size:13px;font-weight:500;color:#856404;margin-bottom:4px">'
    '⚠ 시장 상황 무시 분석</div>'
    '<div style="font-size:12px;color:#856404;line-height:1.5">'
    '이 페이지는 마스터 스위치, VIX, 금리를 무시하고 순수 기술지표(RSI·MACD·MA·BB)만으로 분석한 결과입니다.<br>'
    '실제 매매 시에는 반드시 <b>Market Signals</b> 페이지를 함께 확인하세요.</div>'
    '</div>',
    unsafe_allow_html=True,
)

if not signals:
    st.markdown(
        '<div style="background:#FFF3CD;border-radius:8px;padding:12px 16px;color:#856404;font-size:12px">'
        'signals_technical.json 없음 — Overview에서 Update 버튼을 누르세요.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

st.markdown('<hr style="border:none;border-top:0.5px solid #E0E0E0;margin:12px 0">', unsafe_allow_html=True)

# ── 요약 카드 ──
summary = signals.get("summary", {})
full_signals = load_signals_full() if not USE_MOCK else None
full_buy = full_signals["summary"].get("buy", 0) if full_signals else 0
tech_buy = summary.get("buy", 0)
warn_cnt = summary.get("l3_breakdown", 0) + summary.get("l2_weakening", 0) + summary.get("l1_warning", 0) + summary.get("top_signal", 0)

delta_buy = tech_buy - full_buy
delta_txt = f"+{delta_buy} vs Market" if delta_buy > 0 else ""

c1, c2, c3, c4 = st.columns(4)
c1.markdown(metric_card("경고", str(warn_cnt)), unsafe_allow_html=True)
c2.markdown(metric_card("매수 (기술)", str(tech_buy), delta_txt, "up" if delta_buy > 0 else ""), unsafe_allow_html=True)
c3.markdown(metric_card("관심", str(summary.get("watch", 0))), unsafe_allow_html=True)
c4.markdown(metric_card("홀드", str(summary.get("hold", 0))), unsafe_allow_html=True)

st.markdown(
    '<div style="font-size:10px;color:#888;margin-top:6px">'
    '마스터 스위치: <b>무시됨</b> (GREEN으로 처리) &nbsp;|&nbsp; '
    'VIX 오버라이드: <b>무시됨</b> &nbsp;|&nbsp; 배분 배율: <b>x1.0 고정</b></div>',
    unsafe_allow_html=True,
)

st.markdown('<hr style="border:none;border-top:0.5px solid #E0E0E0;margin:12px 0">', unsafe_allow_html=True)

# ── 시그널 카드 ──
_GROUP_ORDER = [
    "L3_BREAKDOWN", "TOP_SIGNAL", "L2_WEAKENING", "L1_WARNING",
    "BUY_T3", "BUY_T2", "BUY_T1", "WATCH", "HOLD",
]
_GROUP_LABEL = {
    "L3_BREAKDOWN": "⛔ L3 붕괴 (기술적)", "L2_WEAKENING": "🔴 L2 약화 (기술적)",
    "L1_WARNING":   "🟠 L1 경고 (기술적)", "TOP_SIGNAL":   "🔴 과매수 (기술적)",
    "BUY_T1":       "🟢 1차 매수 가능",    "BUY_T2":       "🟢 2차 매수 가능",
    "BUY_T3":       "🟢 3차 매수 가능",    "WATCH":        "🟡 관심 (기술적)",
    "HOLD":         "⚪ 홀드",
}

sig_list = signals.get("signals", [])
non_hold = [s for s in sig_list if s["action"] != "HOLD"]
if not non_hold:
    st.markdown('<div style="color:#888;font-size:12px">주목 시그널 없음</div>', unsafe_allow_html=True)

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
