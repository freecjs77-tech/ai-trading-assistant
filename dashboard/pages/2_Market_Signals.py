"""
dashboard/pages/2_Market_Signals.py — 종합 시그널 (마스터 스위치 + 매크로 반영)
signal_generator.py --mode full 결과 표시
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

st.set_page_config(page_title="Market Signals", page_icon="📡", layout="wide",
                   initial_sidebar_state="collapsed")

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
def load_market(test_mode: bool = False) -> Optional[dict]:
    if test_mode:
        return _load_json(FIXTURES_DIR / "mock_market_data.json")
    return _load_json(DATA_DIR / "market_cache.json")


def generate_signals_from_mock():
    """테스트 모드: mock 데이터로 즉시 시그널 생성"""
    import json
    portfolio = _load_json(DATA_DIR / "test_portfolio.json")
    market    = _load_json(FIXTURES_DIR / "mock_market_data.json")
    if not portfolio or not market:
        return None
    from signal_generator import generate_signals
    return generate_signals(mode="full", portfolio_data=portfolio, market_data=market)


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

market = load_market(test_mode)

if test_mode:
    signals = generate_signals_from_mock()
    if not signals:
        st.error("mock 데이터 생성 실패")
        st.stop()
else:
    signals = load_signals()

# ─────────────────────────────────────────────
# 헤더
# ─────────────────────────────────────────────

st.markdown("← [Dashboard](/) &nbsp;/&nbsp; Market Signals", unsafe_allow_html=True)
st.markdown("## 📡 Market Signals")
st.caption("마스터 스위치 + VIX + 금리 등 매크로 환경을 반영한 종합 시그널")

if not signals:
    st.info("signals.json 없음 — Overview에서 Update 버튼을 누르거나 테스트 모드를 사용하세요.")
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

# 매크로 알림
for alert in signals.get("macro_alerts", []):
    level = alert.get("level", "info")
    msg   = alert.get("message", "")
    if level in ("warning", "danger"):
        st.warning(msg)
    elif level == "caution":
        st.info(msg)

st.markdown("---")

# ── 요약 카드 ──
summary = signals.get("summary", {})
alloc   = signals.get("allocation_modifier", 1.0)
alloc_note = signals.get("allocation_note", "")

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(
    metric_card("⛔ 경고",
                str(summary.get("l3_breakdown", 0) + summary.get("l2_weakening", 0) + summary.get("l1_warning", 0)),
                change_class="dn"),
    unsafe_allow_html=True,
)
c2.markdown(
    metric_card("🟢 매수", str(summary.get("buy", 0)), change_class="up"),
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
c5.markdown(
    metric_card("배분 배율", f"x{alloc:.1f}", alloc_note),
    unsafe_allow_html=True,
)

st.markdown("---")

# ── 시그널 카드 목록 ──
sig_list = signals.get("signals", [])

# 필터 적용
if filter_cls:
    sig_list = [s for s in sig_list if s.get("classification") in filter_cls]
if not show_hold:
    sig_list = [s for s in sig_list if s["action"] != "HOLD"]

if not sig_list:
    st.info("표시할 시그널 없음 (필터 조정 또는 HOLD 표시 옵션 활성화)")
    st.stop()

# 그룹별 표시
_GROUP_ORDER = ["L3_BREAKDOWN", "TOP_SIGNAL", "L2_WEAKENING", "L1_WARNING",
                "BUY_T3", "BUY_T2", "BUY_T1", "WATCH", "HOLD"]
_GROUP_LABEL = {
    "L3_BREAKDOWN": "⛔ L3 붕괴",
    "L2_WEAKENING": "🔴 L2 약화",
    "L1_WARNING":   "🟠 L1 경고",
    "TOP_SIGNAL":   "🔴 과매수",
    "BUY_T1":       "🟢 1차 매수",
    "BUY_T2":       "🟢 2차 매수",
    "BUY_T3":       "🟢 3차 매수",
    "WATCH":        "🟡 관심",
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

# 매핑 안 된 나머지
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
