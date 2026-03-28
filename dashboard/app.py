"""
dashboard/app.py — Overview (메인 대시보드)
라이트 모드 전용. 모든 UI는 st.markdown HTML로 직접 렌더링.
테스트 모드: USE_MOCK_DATA=true streamlit run app.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import streamlit as st

ROOT_DIR     = Path(__file__).parent.parent
DASH_DIR     = Path(__file__).parent
DATA_DIR     = ROOT_DIR / "data"
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"

sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(DASH_DIR))

from style import inject_css
from components import (
    metric_card, macro_card, signal_card, master_switch_banner,
    pill_html, format_krw, signal_index_html,
)

# ── 테스트 모드: 환경변수 USE_MOCK_DATA ──
USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

st.set_page_config(
    page_title="Overview | AI Trading Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)
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
def load_portfolio() -> Optional[dict]:
    fname = "test_portfolio.json" if USE_MOCK else "portfolio.json"
    return _load_json(DATA_DIR / fname)


@st.cache_data(ttl=60)
def load_market() -> Optional[dict]:
    if USE_MOCK:
        return _load_json(FIXTURES_DIR / "mock_market_data.json")
    return _load_json(DATA_DIR / "market_cache.json")


@st.cache_data(ttl=60)
def load_signals() -> Optional[dict]:
    return _load_json(DATA_DIR / "signals.json")


@st.cache_data(ttl=60)
def load_signals_tech() -> Optional[dict]:
    return _load_json(DATA_DIR / "signals_technical.json")


def gen_mock_signals(mode: str) -> Optional[dict]:
    """테스트 모드: mock 데이터로 즉시 시그널 생성"""
    port = _load_json(DATA_DIR / "test_portfolio.json")
    mkt  = _load_json(FIXTURES_DIR / "mock_market_data.json")
    if not port or not mkt:
        return None
    from signal_generator import generate_signals
    return generate_signals(mode=mode, portfolio_data=port, market_data=mkt)


# ─────────────────────────────────────────────
# Update 파이프라인
# ─────────────────────────────────────────────

def run_update_pipeline():
    src = str(ROOT_DIR / "src")
    steps = [
        ("시장 데이터 수집 중...", ["python", str(ROOT_DIR / "src" / "market_data.py")]),
        ("시그널 생성 중...", ["python", str(ROOT_DIR / "src" / "signal_generator.py"), "--mode", "both"]),
    ]
    for msg, cmd in steps:
        with st.spinner(msg):
            try:
                subprocess.run(cmd, check=True, cwd=src, capture_output=True)
            except subprocess.CalledProcessError as e:
                st.markdown(
                    f'<div style="background:#FCEBEB;border-radius:8px;padding:10px 14px;'
                    f'color:#791F1F;font-size:12px">오류: {e.stderr.decode()[:200]}</div>',
                    unsafe_allow_html=True,
                )
                return
    st.cache_data.clear()


# ─────────────────────────────────────────────
# 데이터
# ─────────────────────────────────────────────

portfolio = load_portfolio()
market    = load_market()

if USE_MOCK:
    signals_full = gen_mock_signals("full")
    signals_tech = gen_mock_signals("technical_only")
else:
    signals_full = load_signals()
    signals_tech = load_signals_tech()

ms     = market.get("master_switch", {}) if market else {}
macro  = market.get("macro", {})          if market else {}
rate   = macro.get("usdkrw", 1425.50)

# 통화 상태
if "currency" not in st.session_state:
    st.session_state.currency = "USD"

def display_value(usd: float) -> str:
    if st.session_state.currency == "KRW":
        return format_krw(usd, rate)
    return f"${usd:,.0f}" if abs(usd) >= 1000 else f"${usd:,.2f}"


# ─────────────────────────────────────────────
# 헤더
# ─────────────────────────────────────────────

ms_status   = ms.get("status", "RED")
ms_cls      = {"RED": "switch-red", "GREEN": "switch-green", "YELLOW": "switch-yellow"}.get(ms_status, "switch-red")
updated_at  = portfolio.get("updated_at", "—") if portfolio else "—"

col_title, col_ctrl = st.columns([3, 2])
with col_title:
    st.markdown(
        f'<div style="font-size:22px;font-weight:600;color:#1A1A1A">Portfolio dashboard</div>'
        f'<div style="font-size:11px;color:#888780;margin-top:2px">{updated_at}</div>',
        unsafe_allow_html=True,
    )

with col_ctrl:
    c_ms, c_cur, c_btn = st.columns([1, 1, 1])
    with c_ms:
        st.markdown(
            f'<div style="padding-top:8px">'
            f'<span class="switch-badge {ms_cls}">{ms_status}</span></div>',
            unsafe_allow_html=True,
        )
    with c_cur:
        currency = st.radio(
            "", ["USD", "KRW"], horizontal=True,
            index=0 if st.session_state.currency == "USD" else 1,
            label_visibility="collapsed",
        )
        st.session_state.currency = currency
    with c_btn:
        if st.button("🔄 Update", use_container_width=True, disabled=USE_MOCK,
                     help="실데이터 수집 (USE_MOCK_DATA=false 필요)"):
            run_update_pipeline()
            st.rerun()

if st.session_state.currency == "KRW":
    st.markdown(
        f'<div class="rate-label">1 USD = ₩{rate:,.2f} ({updated_at[:10]})</div>',
        unsafe_allow_html=True,
    )

# ── 마스터 스위치 배너 ──
if market:
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

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 4개 메트릭 카드
# ─────────────────────────────────────────────

if portfolio:
    holdings  = portfolio.get("holdings", [])
    total_val = portfolio.get("total_value_usd", 0)
    total_cost = sum(h["value_usd"] - h.get("pnl_usd", 0) for h in holdings)
    total_pnl  = total_val - total_cost
    total_pct  = total_pnl / total_cost * 100 if total_cost else 0

    # YTD 배당
    ytd_div = 0.0
    hist_path = DATA_DIR / "history.json"
    if hist_path.exists():
        with open(hist_path, encoding="utf-8") as f:
            for s in json.load(f).get("snapshots", []):
                if s.get("date", "").startswith("2026"):
                    ytd_div += s.get("dividend_usd", 0)

    pnl_cls  = "up" if total_pnl >= 0 else "dn"
    pnl_sign = "+" if total_pnl >= 0 else ""

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        metric_card("Total assets", display_value(total_val),
                    f'<span class="{pnl_cls}">{pnl_sign}{display_value(total_pnl)} ({pnl_sign}{total_pct:.1f}%)</span>'),
        unsafe_allow_html=True,
    )
    c2.markdown(
        metric_card("Holdings", f"{len(holdings)} 종목"),
        unsafe_allow_html=True,
    )
    c3.markdown(
        metric_card("Total return",
                    f'<span class="{pnl_cls}">{pnl_sign}{total_pct:.1f}%</span>',
                    f'{pnl_sign}{display_value(total_pnl)}', pnl_cls),
        unsafe_allow_html=True,
    )
    c4.markdown(
        metric_card("YTD dividends", display_value(ytd_div)),
        unsafe_allow_html=True,
    )

# ── 3개 매크로 카드 ──
if market:
    vix  = macro.get("vix", 0)
    t30y = macro.get("treasury_30y", 0)
    qqq_pct = (ms.get("qqq_price", 0) / ms.get("qqq_ma200", 1) - 1) * 100

    vix_status  = "극공포" if vix >= 30 else ("공포" if vix >= 25 else ("경계" if vix >= 20 else "정상"))
    t30y_status = "5.2%↑ 위험" if t30y >= 5.2 else ("5.0%↑ TLT 활성" if t30y >= 5.0 else "관찰")

    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown(
        macro_card("QQQ vs MA200", f"${ms.get('qqq_price',0):,.0f}",
                   f'{"▼" if qqq_pct < 0 else "▲"} {qqq_pct:+.1f}%',
                   "dn" if qqq_pct < 0 else "up"),
        unsafe_allow_html=True,
    )
    m2.markdown(
        macro_card("30Y Treasury", f"{t30y:.3f}%", t30y_status),
        unsafe_allow_html=True,
    )
    m3.markdown(
        macro_card("VIX", f"{vix:.1f}", vix_status,
                   "dn" if vix >= 25 else ""),
        unsafe_allow_html=True,
    )

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 보유 종목 테이블 (Market + Technical 듀얼 시그널)
# ─────────────────────────────────────────────

if portfolio:
    holdings = sorted(portfolio.get("holdings", []), key=lambda h: h["value_usd"], reverse=True)
    total_val = portfolio.get("total_value_usd", 1)

    # 시그널 맵
    ms_map: dict[str, str] = {}
    ts_map: dict[str, str] = {}
    if signals_full:
        for s in signals_full.get("signals", []):
            ms_map[s["ticker"]] = s["action"]
    if signals_tech:
        for s in signals_tech.get("signals", []):
            ts_map[s["ticker"]] = s["action"]

    rows = []
    for h in holdings:
        ticker  = h["ticker"]
        weight  = h["value_usd"] / total_val * 100
        pnl_p   = h.get("pnl_pct", 0)
        pnl_cls = "up" if pnl_p >= 0 else "dn"
        sign    = "+" if pnl_p >= 0 else ""
        bar_c   = "#0F6E56" if pnl_p >= 0 else "#A32D2D"
        bar_w   = min(int(weight / 25 * 100), 100)

        m_pill = pill_html(ms_map.get(ticker, "HOLD"))
        t_pill = pill_html(ts_map.get(ticker, "HOLD"))

        rows.append(
            f"<tr>"
            f"<td><span class='tk'>{ticker}</span><br><span class='nm'>{h.get('name','')}</span></td>"
            f"<td style='text-align:right'>{display_value(h['value_usd'])}</td>"
            f"<td style='text-align:right'>{weight:.1f}%<br>"
            f"<span class='bar-bg'><span class='bar-fill' style='width:{bar_w}%;background:{bar_c}'></span></span></td>"
            f"<td style='text-align:right' class='{pnl_cls}'>{sign}{pnl_p:.1f}%</td>"
            f"<td style='text-align:center'>{m_pill}</td>"
            f"<td style='text-align:center'>{t_pill}</td>"
            f"</tr>"
        )

    st.markdown(
        f'<div class="section-hdr">Holdings ({len(holdings)})</div>'
        f'<table class="holdings-table"><thead><tr>'
        f'<th>Ticker</th>'
        f'<th style="text-align:right">Value</th>'
        f'<th style="text-align:right">Weight</th>'
        f'<th style="text-align:right">Return</th>'
        f'<th style="text-align:center">Market</th>'
        f'<th style="text-align:center">Technical</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>',
        unsafe_allow_html=True,
    )

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 듀얼 시그널 섹션 (Market | Technical)
# ─────────────────────────────────────────────

_GROUP_ORDER = [
    "L3_BREAKDOWN", "TOP_SIGNAL", "L2_WEAKENING", "L1_WARNING",
    "BUY_T3", "BUY_T2", "BUY_T1", "WATCH", "HOLD",
]


def _summary_text(sig_doc: Optional[dict]) -> str:
    if not sig_doc:
        return "데이터 없음"
    s = sig_doc.get("summary", {})
    warn = s.get("l3_breakdown", 0) + s.get("l2_weakening", 0) + s.get("l1_warning", 0) + s.get("top_signal", 0)
    return (
        f'<span class="dn">{warn} 경고</span> / '
        f'<span>{s.get("watch",0)} 관심</span> / '
        f'<span class="up">{s.get("buy",0)} 매수</span> / '
        f'<span style="color:#888">{s.get("hold",0)} 홀드</span>'
    )


def _render_signal_list(sig_doc: Optional[dict], max_items: int = 5):
    if not sig_doc:
        st.markdown('<div style="color:#888;font-size:12px">시그널 없음</div>', unsafe_allow_html=True)
        return
    sig_list = [s for s in sig_doc.get("signals", []) if s["action"] != "HOLD"][:max_items]
    if not sig_list:
        st.markdown('<div style="color:#888;font-size:12px">주목 시그널 없음 (모두 HOLD)</div>',
                    unsafe_allow_html=True)
        return
    for s in sig_list:
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


col_m, col_t = st.columns(2)

with col_m:
    st.markdown(
        '<div style="font-size:13px;font-weight:500;display:flex;align-items:center;gap:6px;margin-bottom:6px">'
        '<span class="switch-badge switch-red" style="font-size:10px;padding:2px 8px">M</span>'
        'Market signals</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-size:11px;margin-bottom:8px">{_summary_text(signals_full)}</div>',
        unsafe_allow_html=True,
    )
    _render_signal_list(signals_full)

with col_t:
    st.markdown(
        '<div style="font-size:13px;font-weight:500;display:flex;align-items:center;gap:6px;margin-bottom:6px">'
        '<span style="display:inline-block;font-size:10px;padding:2px 8px;border-radius:6px;'
        'background:#E6F1FB;color:#0C447C">T</span>Technical signals</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-size:11px;margin-bottom:8px">{_summary_text(signals_tech)}</div>',
        unsafe_allow_html=True,
    )
    _render_signal_list(signals_tech)

# ─────────────────────────────────────────────
# Signal reference 인덱스
# ─────────────────────────────────────────────

st.markdown(signal_index_html(), unsafe_allow_html=True)

if USE_MOCK:
    st.markdown(
        '<div style="font-size:10px;color:#888;text-align:center;margin-top:20px">'
        'USE_MOCK_DATA=true — test_portfolio.json + mock_market_data.json</div>',
        unsafe_allow_html=True,
    )
