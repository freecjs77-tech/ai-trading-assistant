"""
dashboard/app.py — Overview 페이지
메트릭 카드 + 매크로 지표 + 보유 종목 테이블 + 당일 시그널 요약
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import streamlit as st

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
DATA_DIR = ROOT_DIR / "data"
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"

st.set_page_config(
    page_title="AI Trading Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 스타일 주입 (dashboard/ 기준 import)
sys.path.insert(0, str(Path(__file__).parent))
from style import inject_css
from components import metric_card, macro_card, signal_card, master_switch_banner

inject_css()


# ─────────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────────

def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=60)
def load_portfolio(test_mode: bool = False) -> Optional[dict]:
    fname = "test_portfolio.json" if test_mode else "portfolio.json"
    return _load_json(DATA_DIR / fname)


@st.cache_data(ttl=60)
def load_market(test_mode: bool = False) -> Optional[dict]:
    if test_mode:
        return _load_json(FIXTURES_DIR / "mock_market_data.json")
    return _load_json(DATA_DIR / "market_cache.json")


@st.cache_data(ttl=60)
def load_signals() -> Optional[dict]:
    return _load_json(DATA_DIR / "signals.json")


# ─────────────────────────────────────────────
# Update 파이프라인
# ─────────────────────────────────────────────

def run_update_pipeline():
    """수동 업데이트 파이프라인 (실제 yfinance 호출)"""
    src = str(ROOT_DIR / "src")
    steps = [
        ("시장 데이터 수집 중...", ["python", str(ROOT_DIR / "src" / "market_data.py")]),
        ("시그널 생성 중...",       ["python", str(ROOT_DIR / "src" / "signal_generator.py"), "--mode", "both"]),
    ]
    for msg, cmd in steps:
        with st.spinner(msg):
            try:
                subprocess.run(cmd, check=True, cwd=src, capture_output=True)
            except subprocess.CalledProcessError as e:
                st.error(f"오류: {e.stderr.decode()[:200]}")
                return
    st.success("업데이트 완료!")
    st.cache_data.clear()


# ─────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────

ACTION_LABEL = {
    "L3_BREAKDOWN":  "⛔ L3 붕괴",
    "L2_WEAKENING":  "🔴 L2 약화",
    "L1_WARNING":    "🟠 L1 경고",
    "TOP_SIGNAL":    "🔴 과매수",
    "BUY_T1":        "🟢 1차 매수",
    "BUY_T2":        "🟢 2차 매수",
    "BUY_T3":        "🟢 3차 매수",
    "WATCH":         "🟡 관심",
    "HOLD":          "⚪ 홀드",
}

ACTION_PRIORITY = {
    "L3_BREAKDOWN": 0, "TOP_SIGNAL": 1, "L2_WEAKENING": 2,
    "L1_WARNING": 3, "BUY_T3": 4, "BUY_T2": 5, "BUY_T1": 6,
    "WATCH": 7, "HOLD": 8,
}


def signal_pill(action: str) -> str:
    cls_map = {
        "L1_WARNING": "pill-sell", "L2_WEAKENING": "pill-sell",
        "L3_BREAKDOWN": "pill-sell", "TOP_SIGNAL": "pill-sell",
        "BUY_T1": "pill-buy", "BUY_T2": "pill-buy", "BUY_T3": "pill-buy",
        "WATCH": "pill-wait", "HOLD": "pill-hold",
    }
    cls = cls_map.get(action, "pill-hold")
    lbl = action.replace("_", " ")
    return f'<span class="pill {cls}">{lbl}</span>'


# ─────────────────────────────────────────────
# 메인 레이아웃
# ─────────────────────────────────────────────

# 사이드바: 테스트 모드 토글
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    test_mode = st.toggle("테스트 모드 (mock 데이터)", value=False)
    if test_mode:
        st.info("test_portfolio.json + mock_market_data.json 사용 중")

portfolio = load_portfolio(test_mode)
market    = load_market(test_mode)
signals   = load_signals()

# ── 헤더 ──
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.markdown("## Portfolio dashboard")
    updated = portfolio.get("updated_at", "—") if portfolio else "—"
    st.caption(f"Updated: {updated}")
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Update", use_container_width=True, disabled=test_mode,
                 help="실시간 데이터 수집 (테스트 모드 OFF 필요)"):
        run_update_pipeline()
        st.rerun()

# ── 마스터 스위치 배너 ──
if market:
    ms = market.get("master_switch", {})
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

st.markdown("---")

# ── 4개 메트릭 카드 ──
if portfolio:
    total_val = portfolio.get("total_value_usd", 0)
    holdings  = portfolio.get("holdings", [])
    total_cost = sum(h["value_usd"] - h.get("pnl_usd", 0) for h in holdings)
    total_pnl  = total_val - total_cost
    total_pct  = total_pnl / total_cost * 100 if total_cost else 0

    # YTD 배당 (history.json 있으면)
    history_path = DATA_DIR / "history.json"
    ytd_div = 0.0
    if history_path.exists():
        with open(history_path, encoding="utf-8") as f:
            hist = json.load(f)
        for s in hist.get("snapshots", []):
            if s.get("date", "").startswith("2026"):
                ytd_div += s.get("dividend_usd", 0)

    c1, c2, c3, c4 = st.columns(4)
    pnl_cls = "up" if total_pnl >= 0 else "dn"
    pnl_sign = "+" if total_pnl >= 0 else ""

    c1.markdown(
        metric_card("총자산", f"${total_val:,.0f}",
                    f'<span class="{pnl_cls}">{pnl_sign}${total_pnl:,.0f} ({pnl_sign}{total_pct:.1f}%)</span>'),
        unsafe_allow_html=True,
    )
    c2.markdown(
        metric_card("보유 종목", f"{len(holdings)}개"),
        unsafe_allow_html=True,
    )
    c3.markdown(
        metric_card("총 수익률", f"{pnl_sign}{total_pct:.1f}%",
                    f'<span class="{pnl_cls}">{pnl_sign}${total_pnl:,.0f}</span>'),
        unsafe_allow_html=True,
    )
    c4.markdown(
        metric_card("YTD 배당금", f"${ytd_div:,.0f}"),
        unsafe_allow_html=True,
    )

# ── 3개 매크로 지표 ──
if market:
    macro = market.get("macro", {})
    ms    = market.get("master_switch", {})
    vix   = macro.get("vix", 0)
    t30y  = macro.get("treasury_30y", 0)
    usd   = macro.get("usdkrw", 0)

    vix_status = "🔴 극공포" if vix >= 30 else ("🟠 공포" if vix >= 25 else ("🟡 경계" if vix >= 20 else "🟢 정상"))
    t30y_status = "🔴 5.2%↑ 위험" if t30y >= 5.2 else ("🟠 5.0%↑ 활성" if t30y >= 5.0 else "🟡 관찰")
    qqq_pct = (ms.get("qqq_price", 0) / ms.get("qqq_ma200", 1) - 1) * 100

    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(
        macro_card("QQQ vs MA200", f"${ms.get('qqq_price', 0):,.0f}",
                   f'{"🔴" if qqq_pct < 0 else "🟢"} {qqq_pct:+.1f}%'),
        unsafe_allow_html=True,
    )
    m2.markdown(
        macro_card("30Y 국채", f"{t30y:.3f}%", t30y_status),
        unsafe_allow_html=True,
    )
    m3.markdown(
        macro_card("VIX", f"{vix:.1f}", vix_status),
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── 보유 종목 테이블 ──
if portfolio:
    st.markdown("### 📋 보유 종목")
    holdings = sorted(portfolio.get("holdings", []), key=lambda h: h["value_usd"], reverse=True)
    total_val = portfolio.get("total_value_usd", 1)

    # 시그널 맵
    sig_map: dict[str, str] = {}
    if signals:
        for s in signals.get("signals", []):
            sig_map[s["ticker"]] = s["action"]

    rows = []
    for h in holdings:
        ticker = h["ticker"]
        weight = h["value_usd"] / total_val * 100
        pnl    = h.get("pnl_usd", 0)
        pnl_p  = h.get("pnl_pct", 0)
        pnl_cls = "up" if pnl >= 0 else "dn"
        sign    = "+" if pnl >= 0 else ""
        action  = sig_map.get(ticker, "")
        pill    = signal_pill(action) if action else ""

        # 비중 바
        bar_w = min(int(weight / 30 * 100), 100)  # 30% 기준 100%
        bar_html = (
            f'<div style="display:inline-block;width:{bar_w}px;max-width:80px;height:4px;'
            f'background:#0F6E56;border-radius:2px;vertical-align:middle;margin-right:4px"></div>'
            f'{weight:.1f}%'
        )
        rows.append(
            f"<tr>"
            f"<td><b>{ticker}</b></td>"
            f"<td style='color:#555;font-size:12px'>{h.get('name','')}</td>"
            f"<td>${h['value_usd']:>10,.0f}</td>"
            f"<td>{bar_html}</td>"
            f"<td class='{pnl_cls}'>{sign}{pnl_p:.1f}%</td>"
            f"<td>{pill}</td>"
            f"</tr>"
        )

    table_html = f"""
    <table class="holdings-table">
        <thead><tr>
            <th>Ticker</th><th>종목명</th><th>평가금액</th>
            <th>비중</th><th>수익률</th><th>시그널</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)

st.markdown("---")

# ── 당일 시그널 요약 (상위 3개) ──
if signals:
    st.markdown("### 📡 오늘의 시그널 (상위 3)")
    sig_list = signals.get("signals", [])
    top3 = [s for s in sig_list if s["action"] != "HOLD"][:3]
    if not top3:
        top3 = sig_list[:3]

    for s in top3:
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
    if len(sig_list) > 3:
        st.caption(f"전체 {len(sig_list)}개 시그널 → Market Signals 페이지에서 확인")
elif not test_mode:
    st.info("signals.json 없음 — Update 버튼을 눌러 데이터를 생성하세요.")
