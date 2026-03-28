"""
dashboard/pages/1_Ticker_Detail.py — 종목 상세 기술 차트
4패널: 가격+BB+MA / RSI / MACD / 거래량
"""

import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
DATA_DIR = ROOT_DIR / "data"

st.set_page_config(page_title="Ticker Detail", page_icon="📈", layout="wide")

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

CLASS_LABELS = {
    "growth_v22": "성장주 v2.2",
    "etf_v24": "ETF v2.4",
    "energy_v23": "에너지/가치 v2.3",
    "bond_gold_v26": "채권/금 v2.6",
    "speculative": "투기종목",
}

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


@st.cache_data(ttl=600)
def fetch_ohlcv(ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """yfinance에서 OHLCV 데이터 로드"""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=period, auto_adjust=True)
        if hist.empty:
            return None
        return hist
    except Exception:
        return None


def calc_indicators(hist: pd.DataFrame) -> pd.DataFrame:
    """기술 지표 계산"""
    close = hist["Close"]

    # MA
    hist["ma20"] = close.rolling(20).mean()
    hist["ma50"] = close.rolling(50).mean()

    # 볼린저 밴드
    hist["bb_mid"] = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    hist["bb_upper"] = hist["bb_mid"] + 2 * bb_std
    hist["bb_lower"] = hist["bb_mid"] - 2 * bb_std

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
    rs = gain / loss.replace(0, float("nan"))
    hist["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    hist["macd"] = ema12 - ema26
    hist["macd_signal"] = hist["macd"].ewm(span=9, adjust=False).mean()
    hist["macd_hist"] = hist["macd"] - hist["macd_signal"]

    return hist


def render_technical_chart(ticker: str, hist: pd.DataFrame, holding: dict) -> None:
    """4패널 기술 차트"""
    hist = calc_indicators(hist)

    dates = hist.index
    close = hist["Close"]

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.15, 0.15, 0.10],
        vertical_spacing=0.02,
        subplot_titles=("가격 + MA + Bollinger Band", "RSI (14)", "MACD", "거래량"),
    )

    # ── Row 1: 가격 + MA + BB ──
    # BB 음영
    fig.add_trace(go.Scatter(
        x=list(dates) + list(dates[::-1]),
        y=list(hist["bb_upper"]) + list(hist["bb_lower"][::-1]),
        fill="toself",
        fillcolor="rgba(100, 149, 237, 0.07)",
        line=dict(color="rgba(255,255,255,0)"),
        name="BB Band",
        showlegend=False,
        hoverinfo="skip",
    ), row=1, col=1)

    # BB 상단/하단 라인
    fig.add_trace(go.Scatter(
        x=dates, y=hist["bb_upper"],
        line=dict(color="rgba(100,149,237,0.5)", width=1, dash="dot"),
        name="BB Upper", showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=hist["bb_lower"],
        line=dict(color="rgba(100,149,237,0.5)", width=1, dash="dot"),
        name="BB Lower", showlegend=False,
    ), row=1, col=1)

    # MA20, MA50
    fig.add_trace(go.Scatter(
        x=dates, y=hist["ma20"],
        line=dict(color="#fbbf24", width=1.5, dash="dot"),
        name="MA20",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=hist["ma50"],
        line=dict(color="#f87171", width=1.5, dash="dot"),
        name="MA50",
    ), row=1, col=1)

    # 가격 라인
    fig.add_trace(go.Scatter(
        x=dates, y=close,
        line=dict(color="#0d9488", width=2),
        name="Price",
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>가격: $%{y:,.2f}<extra></extra>",
    ), row=1, col=1)

    # 매수 마커 (보유 평균가 표시)
    avg_cost = None
    pnl_usd = holding.get("pnl_usd")
    value = holding.get("value_usd")
    shares = holding.get("shares")
    if value and pnl_usd is not None and shares and shares > 0:
        avg_cost = (value - pnl_usd) / shares
        if avg_cost > 0:
            fig.add_hline(
                y=avg_cost, line_dash="dash",
                line_color="#f472b6", line_width=1.5,
                annotation_text=f"매수단가 ${avg_cost:,.2f}",
                annotation_position="top right",
                row=1, col=1,
            )

    # ── Row 2: RSI ──
    fig.add_trace(go.Scatter(
        x=dates, y=hist["rsi"],
        line=dict(color="#a78bfa", width=1.5),
        name="RSI(14)",
        hovertemplate="RSI: %{y:.1f}<extra></extra>",
    ), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", line_width=1, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", line_width=1, row=2, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(167,139,250,0.05)",
                  line_width=0, row=2, col=1)

    # ── Row 3: MACD ──
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in hist["macd_hist"].fillna(0)]
    fig.add_trace(go.Bar(
        x=dates, y=hist["macd_hist"],
        marker_color=colors,
        name="MACD Hist",
        opacity=0.7,
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=hist["macd"],
        line=dict(color="#60a5fa", width=1.5),
        name="MACD",
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=hist["macd_signal"],
        line=dict(color="#f97316", width=1.5),
        name="Signal",
    ), row=3, col=1)
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=1, row=3, col=1)

    # ── Row 4: 거래량 ──
    vol_colors = ["#22c55e" if close.iloc[i] >= close.iloc[i-1] else "#ef4444"
                  for i in range(len(close))]
    fig.add_trace(go.Bar(
        x=dates, y=hist["Volume"],
        marker_color=vol_colors,
        name="거래량",
        opacity=0.6,
    ), row=4, col=1)

    fig.update_layout(
        height=700,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.02),
        hovermode="x unified",
        xaxis4=dict(showticklabels=True),
    )
    for i in range(1, 5):
        fig.update_xaxes(showgrid=False, row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", row=i, col=1)

    st.plotly_chart(fig, use_container_width=True)


def render_strategy_stage(signal: dict) -> None:
    """전략 진행 단계 표시"""
    action = signal.get("action", "HOLD")
    classification = signal.get("classification", "")
    stage = signal.get("strategy_stage", {})
    current_stage = stage.get("current", 0)
    next_conds = stage.get("next_conditions", "")

    st.markdown("**전략 진행 단계**")

    stages = ["1차 진입 (20%)", "2차 추가 (30%)", "풀포지션 (50%)"]
    cols = st.columns(3)

    for i, (col, label) in enumerate(zip(cols, stages)):
        stage_num = i + 1
        if action == f"BUY_T{stage_num}":
            col.success(f"✅ {label}")
        elif current_stage and stage_num < current_stage:
            col.success(f"✅ {label}")
        elif current_stage and stage_num == current_stage:
            col.warning(f"🔄 {label}")
        else:
            col.info(f"🔒 {label}")

    if next_conds:
        st.caption(f"다음 단계 조건: {next_conds}")

    # 충족/미충족 조건
    met = signal.get("conditions_met", [])
    not_met = signal.get("conditions_not_met", [])

    if met or not_met:
        col_m, col_nm = st.columns(2)
        with col_m:
            st.markdown("**✅ 충족 조건**")
            for c in met:
                st.markdown(f"<span style='color:#22c55e; font-size:12px;'>● {c}</span>",
                            unsafe_allow_html=True)
        with col_nm:
            st.markdown("**⬜ 미충족 조건**")
            for c in not_met[:6]:
                st.markdown(f"<span style='color:#6b7280; font-size:12px;'>○ {c}</span>",
                            unsafe_allow_html=True)


def main() -> None:
    st.title("📈 종목 상세 분석")

    portfolio = load_portfolio()
    signals = load_signals()

    if not portfolio:
        st.error("portfolio.json 없음")
        return

    holdings = portfolio.get("holdings", [])
    tickers = [h["ticker"] for h in holdings]
    holding_map = {h["ticker"]: h for h in holdings}

    signal_map = {}
    if signals:
        for s in signals.get("signals", []):
            signal_map[s["ticker"]] = s

    # 종목 선택
    selected = st.selectbox(
        "종목 선택",
        tickers,
        format_func=lambda t: f"{t} — {TICKER_NAMES.get(t, t)}",
    )

    if not selected:
        return

    holding = holding_map.get(selected, {})
    signal = signal_map.get(selected, {})

    # 헤더
    col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
    with col1:
        st.markdown(f"### {selected}")
        cls = signal.get("classification", "")
        cls_label = CLASS_LABELS.get(cls, cls)
        st.caption(cls_label)
    with col2:
        st.markdown(f"**{TICKER_NAMES.get(selected, '')}**")
        value = holding.get("value_usd", 0)
        st.write(f"평가금액: ${value:,.0f}")
    with col3:
        pnl_pct = holding.get("pnl_pct")
        if pnl_pct is not None:
            color = "green" if pnl_pct >= 0 else "red"
            st.markdown(f"<h3 style='color:{color}'>{pnl_pct:+.1f}%</h3>",
                        unsafe_allow_html=True)
    with col4:
        action = signal.get("action", "N/A")
        badge_color = ACTION_COLORS.get(action, "#6b7280")
        label = ACTION_LABELS_KO.get(action, action)
        confidence = signal.get("confidence", 0)
        st.markdown(
            f'<span style="background:{badge_color}30; color:{badge_color}; '
            f'padding:6px 14px; border-radius:16px; font-size:14px; font-weight:600;">'
            f'{label} ({confidence}%)</span>',
            unsafe_allow_html=True,
        )

    st.divider()

    # 기술 차트
    period_map = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y"}
    period_sel = st.radio("기간", list(period_map.keys()), horizontal=True, index=2)
    yf_period = period_map[period_sel]

    with st.spinner(f"{selected} 데이터 로드 중..."):
        hist = fetch_ohlcv(selected, yf_period)

    if hist is None or hist.empty:
        st.warning(f"{selected}: 차트 데이터 로드 실패")
    else:
        render_technical_chart(selected, hist, holding)

    st.divider()

    # 전략 단계 + 시그널 근거
    col_stage, col_rationale = st.columns([3, 2])

    with col_stage:
        render_strategy_stage(signal)

    with col_rationale:
        st.markdown("**오늘의 시그널 근거**")
        rationale = signal.get("rationale", "데이터 없음")
        notes = signal.get("notes", [])
        st.info(rationale)
        for note in notes:
            st.caption(f"• {note}")


if __name__ == "__main__":
    main()
else:
    main()
