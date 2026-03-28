"""
dashboard/app.py — Streamlit 메인 대시보드 (Overview)
포트폴리오 트렌드 차트 + 메트릭 카드 + 종목 테이블 + 시그널 요약
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# 프로젝트 루트를 sys.path에 추가
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
DATA_DIR = ROOT_DIR / "data"
KST = timezone(timedelta(hours=9))

st.set_page_config(
    page_title="AI Trading Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_portfolio() -> Optional[dict]:
    path = DATA_DIR / "portfolio.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=300)
def load_signals() -> Optional[dict]:
    path = DATA_DIR / "signals.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=300)
def load_market_cache() -> Optional[dict]:
    path = DATA_DIR / "market_cache.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def load_history() -> Optional[dict]:
    path = DATA_DIR / "history.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# 스타일
# ─────────────────────────────────────────────

COLORS = {
    "GREEN": "#00d4aa",
    "YELLOW": "#fbbf24",
    "RED": "#ef4444",
    "teal": "#0d9488",
    "light_blue": "#7dd3fc",
    "amber": "#f59e0b",
    "pink": "#f472b6",
    "gray": "#6b7280",
}

ACTION_COLORS = {
    "L3_BREAKDOWN": "#dc2626",
    "L2_WEAKENING": "#ef4444",
    "L1_WARNING": "#f97316",
    "TOP_SIGNAL": "#dc2626",
    "BUY_T3": "#16a34a",
    "BUY_T2": "#22c55e",
    "BUY_T1": "#4ade80",
    "WATCH": "#f59e0b",
    "HOLD": "#6b7280",
}

ACTION_LABELS_KO = {
    "L3_BREAKDOWN": "L3 붕괴",
    "L2_WEAKENING": "L2 약화",
    "L1_WARNING": "L1 경고",
    "TOP_SIGNAL": "상단 시그널",
    "BUY_T3": "3차 매수",
    "BUY_T2": "2차 매수",
    "BUY_T1": "1차 매수",
    "WATCH": "주시",
    "HOLD": "홀드",
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


# ─────────────────────────────────────────────
# 컴포넌트: 마스터 스위치 배지
# ─────────────────────────────────────────────

def render_master_switch(signals: Optional[dict]) -> None:
    if not signals:
        return
    status = signals.get("master_switch", "N/A")
    color = COLORS.get(status, "#6b7280")
    vix_tier = signals.get("vix_tier", "")
    treasury = signals.get("treasury_30y")
    tr_text = f" | 30Y {treasury:.3f}%" if treasury else ""
    st.markdown(
        f"""<div style="background:{color}20; border-left:4px solid {color};
            padding:12px 20px; border-radius:8px; margin-bottom:16px;">
            <span style="color:{color}; font-size:20px; font-weight:700;">
            ● 마스터 스위치: {status}</span>
            <span style="color:#9ca3af; font-size:14px; margin-left:16px;">
            VIX {vix_tier}{tr_text}</span></div>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# 컴포넌트: 메트릭 카드
# ─────────────────────────────────────────────

def render_metric_cards(portfolio: dict, market: Optional[dict]) -> None:
    total_value = portfolio.get("total_value_usd", 0)
    holdings = portfolio.get("holdings", [])

    # 총 손익 계산
    total_pnl = sum(
        h.get("pnl_usd", 0) or 0 for h in holdings
    )
    total_cost = total_value - total_pnl
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    # 일일 손익 (시장 데이터에서 추정)
    daily_change = 0.0
    if market:
        for h in holdings:
            t_data = market.get("tickers", {}).get(h["ticker"], {})
            price = t_data.get("price")
            shares = h.get("shares")
            # 단순 추정: 현재가와 MA20 차이로 근사 (실제는 전일 종가 필요)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="총자산",
            value=f"${total_value:,.0f}",
            delta=f"${total_pnl:+,.0f} ({total_pnl_pct:+.1f}%)" if total_pnl else None,
        )
    with col2:
        st.metric(label="보유 종목", value=f"{len(holdings)}개")
    with col3:
        if market:
            ms = market.get("master_switch", {})
            qqq_price = ms.get("qqq_price")
            qqq_ma200 = ms.get("qqq_ma200")
            if qqq_price and qqq_ma200:
                gap_pct = (qqq_price - qqq_ma200) / qqq_ma200 * 100
                st.metric(
                    label="QQQ vs MA200",
                    value=f"${qqq_price:,.2f}",
                    delta=f"{gap_pct:+.1f}% vs MA200 ${qqq_ma200:,.2f}",
                    delta_color="normal",
                )
            else:
                st.metric(label="QQQ vs MA200", value="N/A")
        else:
            st.metric(label="QQQ vs MA200", value="N/A")
    with col4:
        if market:
            vix = market.get("macro", {}).get("vix")
            treasury = market.get("macro", {}).get("treasury_30y")
            if vix:
                st.metric(label="VIX", value=f"{vix:.1f}", delta=None)
            if treasury:
                st.metric(label="30Y 국채", value=f"{treasury:.3f}%")
        else:
            st.metric(label="VIX | 30Y 국채", value="N/A")


# ─────────────────────────────────────────────
# 컴포넌트: 포트폴리오 트렌드 차트
# ─────────────────────────────────────────────

def render_trend_chart(portfolio: dict) -> None:
    """포트폴리오 트렌드 차트 (history.json 있으면 실제 데이터, 없으면 샘플)"""
    history = load_history()

    if history and history.get("snapshots"):
        snapshots = history["snapshots"]
        dates = [s["date"] for s in snapshots]
        values = [s["total_value_usd"] for s in snapshots]
        costs = [s.get("total_cost_usd", s["total_value_usd"] * 0.92) for s in snapshots]
        dividends = [s.get("dividend_usd", 0) for s in snapshots]
    else:
        # 샘플 데이터 (history.json 없을 때)
        import numpy as np
        n = 90
        base_dates = pd.date_range(end=datetime.now(), periods=n, freq="D")
        dates = [d.strftime("%Y-%m-%d") for d in base_dates]
        np.random.seed(42)
        values = [400000 + i * 400 + np.random.randn() * 2000 for i in range(n)]
        costs = [380000 + i * 200 for i in range(n)]
        dividends = [200 if i % 30 == 0 else 0 for i in range(n)]

    # 기간 선택 버튼
    col_btns = st.columns([1, 1, 1, 1, 8])
    period_labels = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}

    if "chart_period" not in st.session_state:
        st.session_state.chart_period = "3M"

    for i, (label, _) in enumerate(period_labels.items()):
        with col_btns[i]:
            if st.button(label, key=f"period_{label}",
                         type="primary" if st.session_state.chart_period == label else "secondary"):
                st.session_state.chart_period = label

    # 기간 필터링
    days = period_labels[st.session_state.chart_period]
    if len(dates) > days:
        dates = dates[-days:]
        values = values[-days:]
        costs = costs[-days:]
        dividends = dividends[-days:]

    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]],
    )

    # 총자산 area fill (teal)
    fig.add_trace(
        go.Scatter(
            x=dates, y=values,
            name="총자산",
            line=dict(color=COLORS["teal"], width=2),
            fill="tozeroy",
            fillcolor="rgba(13, 148, 136, 0.12)",
            hovertemplate="<b>%{x}</b><br>총자산: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 원가 기준선 (점선, light blue)
    fig.add_trace(
        go.Scatter(
            x=dates, y=costs,
            name="원가",
            line=dict(color=COLORS["light_blue"], width=1.5, dash="dot"),
            hovertemplate="원가: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 배당금 bar (amber, 우측 Y축)
    fig.add_trace(
        go.Bar(
            x=dates, y=dividends,
            name="배당금",
            marker_color=COLORS["amber"],
            opacity=0.7,
            hovertemplate="배당: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.05, x=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickprefix="$"),
        yaxis2=dict(showgrid=False, tickprefix="$", title="배당금",
                    range=[0, max(dividends) * 8 if any(dividends) else 1000]),
    )

    st.plotly_chart(fig, use_container_width=True)

    # 서머리
    if values:
        period_change = values[-1] - values[0]
        period_pct = period_change / values[0] * 100
        col1, col2, col3 = st.columns(3)
        col1.metric("기간 변동", f"${period_change:+,.0f}", f"{period_pct:+.1f}%")
        col2.metric("최고점", f"${max(values):,.0f}")
        col3.metric("최저점", f"${min(values):,.0f}")


# ─────────────────────────────────────────────
# 컴포넌트: 보유 종목 테이블
# ─────────────────────────────────────────────

def render_holdings_table(portfolio: dict, signals: Optional[dict]) -> None:
    holdings = portfolio.get("holdings", [])
    if not holdings:
        st.info("보유 종목 없음")
        return

    total_value = portfolio.get("total_value_usd", 1)
    signal_map = {}
    if signals:
        for s in signals.get("signals", []):
            signal_map[s["ticker"]] = s

    # 정렬 옵션
    sort_by = st.selectbox("정렬", ["평가금액순", "수익률순"], key="sort_holdings")

    rows = []
    for h in holdings:
        ticker = h["ticker"]
        value = h.get("value_usd", 0)
        pnl_pct = h.get("pnl_pct")
        weight = value / total_value * 100

        sig = signal_map.get(ticker, {})
        action = sig.get("action", "N/A")
        confidence = sig.get("confidence", 0)

        rows.append({
            "ticker": ticker,
            "name": TICKER_NAMES.get(ticker, ticker),
            "value": value,
            "weight": weight,
            "pnl_pct": pnl_pct,
            "action": action,
            "confidence": confidence,
        })

    # 정렬
    if sort_by == "평가금액순":
        rows.sort(key=lambda x: x["value"], reverse=True)
    else:
        rows.sort(key=lambda x: x["pnl_pct"] or 0, reverse=True)

    # 테이블 렌더링
    header_cols = st.columns([1, 3, 2, 3, 2, 2])
    headers = ["티커", "종목명", "평가금액", "비중", "수익률", "시그널"]
    for col, h_text in zip(header_cols, headers):
        col.markdown(f"**{h_text}**")
    st.divider()

    for row in rows:
        cols = st.columns([1, 3, 2, 3, 2, 2])
        cols[0].write(f"**{row['ticker']}**")
        cols[1].write(row["name"])
        cols[2].write(f"${row['value']:,.0f}")

        # 비중 바
        pct = row["weight"]
        bar_html = f"""
        <div style="background:#1f2937; border-radius:4px; height:18px; width:100%;">
          <div style="background:{COLORS['teal']}; border-radius:4px; height:18px;
                width:{min(pct*4, 100):.0f}%; display:flex; align-items:center;
                padding-left:4px; font-size:11px; color:white;">{pct:.1f}%</div>
        </div>"""
        cols[3].markdown(bar_html, unsafe_allow_html=True)

        # 수익률
        pnl = row["pnl_pct"]
        if pnl is not None:
            color = "#22c55e" if pnl >= 0 else "#ef4444"
            cols[4].markdown(f'<span style="color:{color}">{pnl:+.1f}%</span>',
                             unsafe_allow_html=True)
        else:
            cols[4].write("-")

        # 시그널 배지
        action = row["action"]
        badge_color = ACTION_COLORS.get(action, "#6b7280")
        label = ACTION_LABELS_KO.get(action, action)
        cols[5].markdown(
            f'<span style="background:{badge_color}30; color:{badge_color}; '
            f'padding:2px 8px; border-radius:12px; font-size:12px;">{label}</span>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# 컴포넌트: 시그널 요약 카드
# ─────────────────────────────────────────────

def render_signal_summary(signals: Optional[dict]) -> None:
    if not signals:
        st.info("시그널 없음 (signal_generator.py 실행 필요)")
        return

    sig_list = signals.get("signals", [])
    macro_alerts = signals.get("macro_alerts", [])

    # 매크로 알림
    for alert in macro_alerts[:3]:
        level = alert.get("level", "info")
        if level == "danger":
            st.error(f"🚨 {alert['message']}")
        elif level == "warning":
            st.warning(f"⚠️ {alert['message']}")
        elif level == "caution":
            st.warning(f"⚡ {alert['message']}")
        else:
            st.info(f"ℹ️ {alert['message']}")

    # 주요 시그널 카드 (경고/관심/매수 우선)
    important = [s for s in sig_list if s["action"] not in ("HOLD",)][:6]
    if not important:
        st.success("✅ 모든 종목 HOLD — 특이 시그널 없음")
        return

    cols_per_row = 3
    for i in range(0, len(important), cols_per_row):
        row_signals = important[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, sig in zip(cols, row_signals):
            action = sig["action"]
            color = ACTION_COLORS.get(action, "#6b7280")
            label = ACTION_LABELS_KO.get(action, action)
            confidence = sig.get("confidence", 0)
            rationale = sig.get("rationale", "")[:80]
            with col:
                st.markdown(
                    f"""<div style="border-left:4px solid {color}; background:{color}12;
                        padding:12px; border-radius:8px; margin-bottom:8px;">
                        <div style="display:flex; justify-content:space-between;">
                          <span style="font-weight:700; font-size:16px;">{sig['ticker']}</span>
                          <span style="background:{color}30; color:{color};
                            padding:2px 8px; border-radius:12px; font-size:12px;">{label}</span>
                        </div>
                        <div style="margin-top:6px;">
                          <div style="background:#374151; border-radius:4px; height:6px;">
                            <div style="background:{color}; border-radius:4px;
                              height:6px; width:{confidence}%;"></div>
                          </div>
                          <span style="font-size:11px; color:#9ca3af;">확신도 {confidence}%</span>
                        </div>
                        <div style="font-size:12px; color:#d1d5db; margin-top:8px;">
                          {rationale}...</div>
                    </div>""",
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────
# 메인 레이아웃
# ─────────────────────────────────────────────

def main() -> None:
    st.title("📊 AI Trading Assistant")
    st.caption(f"토스증권 포트폴리오 자동 분석 | 규칙 기반 시그널 엔진 v3.0")

    portfolio = load_portfolio()
    signals = load_signals()
    market = load_market_cache()

    if not portfolio:
        st.error("portfolio.json 없음. 텔레그램 스크린샷 전송 또는 초기 데이터를 확인하세요.")
        return

    # 마스터 스위치
    render_master_switch(signals)

    # 메트릭 카드
    render_metric_cards(portfolio, market)

    st.divider()

    # 포트폴리오 트렌드 차트
    st.subheader("📈 포트폴리오 트렌드")
    render_trend_chart(portfolio)

    st.divider()

    # 두 열: 보유 테이블 + 시그널 요약
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("📋 보유 종목")
        render_holdings_table(portfolio, signals)

    with col_right:
        st.subheader("🔔 오늘의 시그널")
        render_signal_summary(signals)

    # 업데이트 시각
    updated_at = portfolio.get("updated_at", "")
    if updated_at:
        st.caption(f"마지막 업데이트: {updated_at}")


if __name__ == "__main__":
    main()
else:
    main()
