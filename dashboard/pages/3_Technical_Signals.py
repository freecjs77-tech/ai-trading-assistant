"""
dashboard/pages/3_Technical_Signals.py — 기술지표 전용 시그널
마스터 스위치/VIX/금리 무시, 순수 기술지표(RSI/MACD/MA/BB)만으로 판단
"""

import json
import sys
from pathlib import Path
from typing import Optional

import streamlit as st

ROOT_DIR     = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))
DATA_DIR     = ROOT_DIR / "data"
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"

st.set_page_config(page_title="Technical Signals", page_icon="📉", layout="wide",
                   initial_sidebar_state="collapsed")

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


def generate_technical_signals_from_mock():
    """테스트 모드: mock 데이터로 즉시 technical_only 시그널 생성"""
    portfolio = _load_json(DATA_DIR / "test_portfolio.json")
    market    = _load_json(FIXTURES_DIR / "mock_market_data.json")
    if not portfolio or not market:
        return None
    from signal_generator import generate_signals
    return generate_signals(mode="technical_only", portfolio_data=portfolio, market_data=market)


@st.cache_data(ttl=60)
def load_signals_full() -> Optional[dict]:
    """비교용 full 모드 시그널"""
    return _load_json(DATA_DIR / "signals.json")


# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ 설정")
    test_mode  = st.toggle("테스트 모드 (mock 데이터)", value=False)
    show_hold  = st.toggle("HOLD 종목 표시", value=False)
    filter_cls = st.multiselect(
        "분류 필터",
        ["growth_v22", "etf_v24", "energy_v23", "bond_gold_v26", "speculative"],
        default=[],
        placeholder="전체 표시",
    )

# ─────────────────────────────────────────────
# 헤더 + 경고 배너
# ─────────────────────────────────────────────

st.markdown("← [Dashboard](/) &nbsp;/&nbsp; Technical Signals", unsafe_allow_html=True)
st.markdown("## 📉 Technical Signals")

st.warning(
    "⚠️ 이 페이지는 시장 상황(마스터 스위치, VIX, 금리)을 무시하고 "
    "순수 기술지표(RSI·MACD·MA·BB)만으로 분석한 결과입니다.  \n"
    "실제 매매 시에는 반드시 **Market Signals** 페이지를 함께 확인하세요."
)

if test_mode:
    signals = generate_technical_signals_from_mock()
    if not signals:
        st.error("mock 데이터 생성 실패")
        st.stop()
else:
    signals = load_signals_technical()

if not signals:
    st.info("signals_technical.json 없음 — Overview에서 Update 버튼을 누르거나 테스트 모드를 사용하세요.")
    st.stop()

st.markdown("---")

# ── 요약 카드 ──
summary = signals.get("summary", {})

# full 모드 비교
full_signals = load_signals_full() if not test_mode else None
full_buy = full_signals["summary"].get("buy", 0) if full_signals else 0
tech_buy = summary.get("buy", 0)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    metric_card("⛔ 경고",
                str(summary.get("l3_breakdown", 0) + summary.get("l2_weakening", 0) + summary.get("l1_warning", 0))),
    unsafe_allow_html=True,
)
c2.markdown(
    metric_card("🟢 매수 (기술)", str(tech_buy),
                f"+{tech_buy - full_buy} vs Market" if full_signals and tech_buy > full_buy else ""),
    unsafe_allow_html=True,
)
c3.markdown(
    metric_card("🟡 관심", str(summary.get("watch", 0))),
    unsafe_allow_html=True,
)
c4.markdown(
    metric_card("⚪ 홀드", str(summary.get("hold", 0))),
    unsafe_allow_html=True,
)

st.caption(
    "📌 마스터 스위치 상태: **무시됨** (GREEN으로 처리) | "
    "VIX 오버라이드: **무시됨** | 배분 배율: **x1.0 (고정)**"
)

st.markdown("---")

# ── 시그널 카드 목록 ──
sig_list = signals.get("signals", [])

if filter_cls:
    sig_list = [s for s in sig_list if s.get("classification") in filter_cls]
if not show_hold:
    sig_list = [s for s in sig_list if s["action"] != "HOLD"]

if not sig_list:
    st.info("표시할 시그널 없음 (필터 조정 또는 HOLD 표시 옵션 활성화)")
    st.stop()

_GROUP_ORDER = ["L3_BREAKDOWN", "TOP_SIGNAL", "L2_WEAKENING", "L1_WARNING",
                "BUY_T3", "BUY_T2", "BUY_T1", "WATCH", "HOLD"]
_GROUP_LABEL = {
    "L3_BREAKDOWN": "⛔ L3 붕괴 (기술적)",
    "L2_WEAKENING": "🔴 L2 약화 (기술적)",
    "L1_WARNING":   "🟠 L1 경고 (기술적)",
    "TOP_SIGNAL":   "🔴 과매수 (기술적)",
    "BUY_T1":       "🟢 1차 매수 가능 (기술적)",
    "BUY_T2":       "🟢 2차 매수 가능 (기술적)",
    "BUY_T3":       "🟢 3차 매수 가능 (기술적)",
    "WATCH":        "🟡 관심 (기술적)",
    "HOLD":         "⚪ 홀드",
}

shown = set()
for action in _GROUP_ORDER:
    group = [s for s in sig_list if s["action"] == action]
    if not group:
        continue
    st.markdown(f"**{_GROUP_LABEL.get(action, action)}** ({len(group)})")
    for s in group:
        st.markdown(
            signal_card(
                ticker=s["ticker"],
                action=s["action"],
                confidence=s.get("confidence", 0),
                rationale=s.get("rationale", ""),
                conditions_met=s.get("conditions_met", []),
                conditions_not_met=s.get("conditions_not_met", []),
            ),
            unsafe_allow_html=True,
        )
        shown.add(s["ticker"])

rest = [s for s in sig_list if s["ticker"] not in shown]
for s in rest:
    st.markdown(
        signal_card(
            ticker=s["ticker"],
            action=s["action"],
            confidence=s.get("confidence", 0),
            rationale=s.get("rationale", ""),
            conditions_met=s.get("conditions_met", []),
            conditions_not_met=s.get("conditions_not_met", []),
        ),
        unsafe_allow_html=True,
    )
