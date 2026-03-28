"""
dashboard/pages/2_Signals.py — 시그널 카드 페이지
경고/관심/매수/홀드 우선순위 순 표시
"""

import json
import sys
from pathlib import Path
from typing import Optional

import streamlit as st

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
DATA_DIR = ROOT_DIR / "data"

st.set_page_config(page_title="Signals", page_icon="🔔", layout="wide")

ACTION_COLORS = {
    "L3_BREAKDOWN": "#dc2626", "L2_WEAKENING": "#ef4444", "L1_WARNING": "#f97316",
    "TOP_SIGNAL": "#dc2626", "BUY_T3": "#16a34a", "BUY_T2": "#22c55e",
    "BUY_T1": "#4ade80", "WATCH": "#f59e0b", "HOLD": "#6b7280",
}

ACTION_LABELS_KO = {
    "L3_BREAKDOWN": "L3 붕괴", "L2_WEAKENING": "L2 약화", "L1_WARNING": "L1 경고",
    "TOP_SIGNAL": "상단 시그널", "BUY_T3": "3차 매수", "BUY_T2": "2차 매수",
    "BUY_T1": "1차 매수", "WATCH": "주시", "HOLD": "홀드",
}

TICKER_NAMES = {
    "VOO": "Vanguard S&P 500", "BIL": "SPDR 단기채", "QQQ": "Invesco QQQ",
    "SCHD": "Schwab 배당", "AAPL": "애플", "O": "리얼티 인컴",
    "JEPI": "JPMorgan 프리미엄", "SOXX": "iShares 반도체", "TSLA": "테슬라",
    "TLT": "iShares 20년+ 국채", "NVDA": "엔비디아", "PLTR": "팔란티어",
    "SPY": "SPDR S&P 500", "UNH": "유나이티드헬스", "MSFT": "마이크로소프트",
    "GOOGL": "알파벳", "AMZN": "아마존", "SLV": "iShares 은",
    "TQQQ": "ProShares 2x QQQ", "SOXL": "Direxion 3x 반도체",
    "ETHU": "이더리움 2X", "CRCL": "써클 인터넷", "BTDR": "비트마인",
}


@st.cache_data(ttl=300)
def load_signals() -> Optional[dict]:
    path = DATA_DIR / "signals.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render_signal_card(sig: dict) -> None:
    """단일 시그널 카드"""
    action = sig["action"]
    color = ACTION_COLORS.get(action, "#6b7280")
    label = ACTION_LABELS_KO.get(action, action)
    ticker = sig["ticker"]
    name = TICKER_NAMES.get(ticker, ticker)
    confidence = sig.get("confidence", 0)
    rationale = sig.get("rationale", "")
    conditions_met = sig.get("conditions_met", [])
    conditions_not_met = sig.get("conditions_not_met", [])
    tranche = sig.get("tranche")

    tranche_text = f" · {tranche}차 트랜치" if tranche else ""

    st.markdown(
        f"""<div style="border-left:4px solid {color}; background:{color}0d;
            padding:16px; border-radius:8px; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <span style="font-size:18px; font-weight:700;">{ticker}</span>
                <span style="color:#9ca3af; font-size:13px; margin-left:8px;">{name}</span>
                <span style="color:#6b7280; font-size:12px;">{tranche_text}</span>
              </div>
              <span style="background:{color}25; color:{color};
                padding:4px 12px; border-radius:16px; font-size:13px; font-weight:600;">
                {label}</span>
            </div>
            <div style="margin-top:10px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <div style="flex:1; background:#374151; border-radius:4px; height:8px;">
                  <div style="background:{color}; border-radius:4px;
                    height:8px; width:{confidence}%;"></div>
                </div>
                <span style="color:#9ca3af; font-size:12px; min-width:40px;">
                  확신도 {confidence}%</span>
              </div>
            </div>
            <div style="margin-top:10px; font-size:13px; color:#d1d5db; line-height:1.6;">
              {rationale}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # 조건 태그
    if conditions_met or conditions_not_met:
        tag_html = ""
        for c in conditions_met:
            tag_html += (
                f'<span style="background:#16a34a20; color:#4ade80; '
                f'padding:2px 8px; border-radius:12px; font-size:11px; '
                f'margin:2px; display:inline-block;">✓ {c}</span>'
            )
        for c in conditions_not_met[:5]:
            tag_html += (
                f'<span style="background:#37415120; color:#6b7280; '
                f'padding:2px 8px; border-radius:12px; font-size:11px; '
                f'margin:2px; display:inline-block;">○ {c}</span>'
            )
        if tag_html:
            st.markdown(tag_html, unsafe_allow_html=True)


def render_hold_grid(hold_signals: list[dict]) -> None:
    """HOLD 종목 축약 그리드"""
    if not hold_signals:
        return

    st.markdown("**HOLD 종목**")
    cols = st.columns(4)
    for i, sig in enumerate(hold_signals):
        ticker = sig["ticker"]
        col = cols[i % 4]
        col.markdown(
            f'<div style="background:#1f293780; border:1px solid #374151; '
            f'padding:8px; border-radius:6px; text-align:center; margin-bottom:6px;">'
            f'<span style="font-weight:600;">{ticker}</span><br>'
            f'<span style="font-size:11px; color:#6b7280;">'
            f'{TICKER_NAMES.get(ticker, "")[:12]}</span></div>',
            unsafe_allow_html=True,
        )


def main() -> None:
    st.title("🔔 오늘의 시그널")

    signals_doc = load_signals()

    if not signals_doc:
        st.error("signals.json 없음. signal_generator.py를 실행하세요.")
        st.code("python src/signal_generator.py")
        return

    signals = signals_doc.get("signals", [])
    macro_alerts = signals_doc.get("macro_alerts", [])
    summary = signals_doc.get("summary", {})
    date = signals_doc.get("date", "")

    # 날짜 + 업데이트
    st.caption(f"기준일: {date}")

    # 마스터 스위치 배너
    ms = signals_doc.get("master_switch", "N/A")
    ms_colors = {"GREEN": "#00d4aa", "YELLOW": "#fbbf24", "RED": "#ef4444"}
    ms_color = ms_colors.get(ms, "#6b7280")
    vix_tier = signals_doc.get("vix_tier", "")
    treasury = signals_doc.get("treasury_30y")
    alloc_mod = signals_doc.get("allocation_modifier", 1.0)

    col_ms, col_info = st.columns([2, 5])
    with col_ms:
        st.markdown(
            f"""<div style="background:{ms_color}20; border:2px solid {ms_color};
                padding:16px; border-radius:12px; text-align:center;">
                <div style="color:{ms_color}; font-size:28px; font-weight:700;">
                  ● {ms}</div>
                <div style="color:#9ca3af; font-size:12px;">마스터 스위치</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_info:
        info_cols = st.columns(3)
        info_cols[0].metric("VIX", vix_tier)
        if treasury:
            info_cols[1].metric("30Y 국채", f"{treasury:.3f}%")
        info_cols[2].metric("배분 배율", f"x{alloc_mod:.1f}")

    st.divider()

    # 요약 카드
    sum_cols = st.columns(7)
    summary_items = [
        ("L3 붕괴", summary.get("l3_breakdown", 0), "#dc2626"),
        ("L2 약화", summary.get("l2_weakening", 0), "#ef4444"),
        ("L1 경고", summary.get("l1_warning", 0), "#f97316"),
        ("상단 시그널", summary.get("top_signal", 0), "#dc2626"),
        ("매수", summary.get("buy", 0), "#16a34a"),
        ("주시", summary.get("watch", 0), "#f59e0b"),
        ("홀드", summary.get("hold", 0), "#6b7280"),
    ]
    for col, (label, count, color) in zip(sum_cols, summary_items):
        col.markdown(
            f'<div style="text-align:center; padding:8px;">'
            f'<div style="font-size:24px; font-weight:700; color:{color};">{count}</div>'
            f'<div style="font-size:12px; color:#9ca3af;">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # 매크로 알림
    if macro_alerts:
        for alert in macro_alerts:
            level = alert.get("level", "info")
            msg = alert["message"]
            if level == "danger":
                st.error(f"🚨 {msg}")
            elif level == "warning":
                st.warning(f"⚠️ {msg}")
            elif level == "caution":
                st.warning(f"⚡ {msg}")
            else:
                st.info(f"ℹ️ {msg}")

    # 시그널 필터
    filter_options = ["전체", "경고만", "매수만", "주시만"]
    filter_sel = st.radio("필터", filter_options, horizontal=True)

    # 필터링
    exit_actions = {"L3_BREAKDOWN", "L2_WEAKENING", "L1_WARNING", "TOP_SIGNAL"}
    buy_actions = {"BUY_T1", "BUY_T2", "BUY_T3"}

    if filter_sel == "경고만":
        filtered = [s for s in signals if s["action"] in exit_actions]
    elif filter_sel == "매수만":
        filtered = [s for s in signals if s["action"] in buy_actions]
    elif filter_sel == "주시만":
        filtered = [s for s in signals if s["action"] == "WATCH"]
    else:
        filtered = signals

    # 섹션별 분리
    exit_sigs = [s for s in filtered if s["action"] in exit_actions]
    watch_sigs = [s for s in filtered if s["action"] == "WATCH"]
    buy_sigs = [s for s in filtered if s["action"] in buy_actions]
    hold_sigs = [s for s in filtered if s["action"] == "HOLD"]

    # 경고/퇴출
    if exit_sigs:
        st.subheader("🚨 경고 / 퇴출 시그널")
        cols = st.columns(min(len(exit_sigs), 2))
        for i, sig in enumerate(exit_sigs):
            with cols[i % 2]:
                render_signal_card(sig)

    # 주시
    if watch_sigs:
        st.subheader("👀 주시 종목")
        cols = st.columns(min(len(watch_sigs), 2))
        for i, sig in enumerate(watch_sigs):
            with cols[i % 2]:
                render_signal_card(sig)

    # 매수
    if buy_sigs:
        st.subheader("💚 매수 시그널")
        cols = st.columns(min(len(buy_sigs), 2))
        for i, sig in enumerate(buy_sigs):
            with cols[i % 2]:
                render_signal_card(sig)

    # HOLD 그리드
    if hold_sigs and filter_sel in ("전체",):
        st.divider()
        render_hold_grid(hold_sigs)

    # 리밸런싱 알림
    rebalance_alerts = signals_doc.get("rebalance_alerts", [])
    if rebalance_alerts:
        st.divider()
        st.subheader("⚖️ 리밸런싱 알림")
        for alert in rebalance_alerts:
            severity = alert.get("severity", "info")
            if severity == "warning":
                st.warning(f"⚠️ {alert['message']}")
            elif severity == "caution":
                st.info(f"💡 {alert['message']}")
            else:
                st.caption(f"• {alert['message']}")


if __name__ == "__main__":
    main()
else:
    main()
