"""
dashboard/pages/4_Technical_Signals.py — Technical 시그널 (technical_only mode)
마스터 스위치 / 매크로 무시, 순수 기술지표 기반 시그널
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
DATA_DIR = ROOT_DIR / "data"

USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

st.set_page_config(
    page_title="Technical Signals | AI Trading Assistant",
    layout="wide",
)

from dashboard.style import inject_css
from dashboard.components import signal_card, signal_index_html

st.markdown(inject_css(), unsafe_allow_html=True)


# ── 데이터 로드 ───────────────────────────────────────────

def load_signals_tech() -> dict:
    path = DATA_DIR / "signals_technical.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── 메인 ─────────────────────────────────────────────────

signals_doc = load_signals_tech()

st.markdown(
    '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
    '<h1 style="font-size:22px;font-weight:500;margin:0">Technical Signals</h1>'
    '<span style="display:inline-block;font-size:10px;padding:2px 8px;border-radius:6px;'
    'background:#E6F1FB;color:#0C447C">Technical only</span>'
    '</div>',
    unsafe_allow_html=True,
)

# 안내 배너 — 이 모드의 의미 설명
st.markdown(
    '<div style="background:#E6F1FB;border-left:3px solid #0C447C;border-radius:0;'
    'padding:10px 12px;margin-bottom:14px;font-size:12px;color:#0C447C">'
    '<b>Technical-only mode</b>: 마스터 스위치 · VIX · 30Y 국채 조건을 무시하고 '
    '순수 MACD/RSI/볼린저밴드 기반으로 계산한 시그널입니다. '
    'Market 시그널과 비교해 기술적 강도를 확인하는 용도로 사용하세요.'
    '</div>',
    unsafe_allow_html=True,
)

if not signals_doc:
    st.markdown(
        '<div style="background:#FFF3CD;border-radius:8px;padding:10px 14px;'
        'color:#856404;font-size:12px">'
        'signals_technical.json 없음 — Overview 페이지에서 🔄 Update를 클릭하세요.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

sig_list = signals_doc.get("signals", [])
generated_at = signals_doc.get("generated_at", "")
if generated_at:
    from datetime import datetime, timezone, timedelta
    try:
        dt = datetime.fromisoformat(generated_at).astimezone(timezone(timedelta(hours=9)))
        st.markdown(
            f'<div style="font-size:11px;color:#888;margin-bottom:12px">'
            f'생성: {dt.strftime("%Y-%m-%d %H:%M KST")}</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        pass

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

# 섹션별 렌더링
def render_section(title: str, items: list) -> None:
    if not items:
        return
    st.markdown(f'<div class="sh">{title}</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, s in enumerate(items):
        with cols[i % 2]:
            st.markdown(
                signal_card(s["ticker"], s["action"], s.get("confidence", 50), s.get("rationale", "")),
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
