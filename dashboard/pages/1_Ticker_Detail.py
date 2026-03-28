"""
dashboard/pages/1_Ticker_Detail.py — 종목 기술 차트 상세 페이지
4-panel Plotly 차트 + 전략 단계 + 시그널
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

ROOT_DIR     = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))
DATA_DIR     = ROOT_DIR / "data"
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"

USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

st.set_page_config(page_title="Ticker Detail | AI Trading Assistant", page_icon="📈", layout="wide")

from style import inject_css
from components import strategy_progress, signal_card, metric_card

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


@st.cache_data(ttl=300)
def fetch_ohlcv(ticker: str, period: str = "6mo") -> tuple[Optional[pd.DataFrame], str]:
    for attempt in range(2):
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(period=period, auto_adjust=True)
            if hist.empty:
                return None, "데이터 없음"
            return hist, ""
        except Exception as e:
            err = str(e)
            if "Rate limit" in err or "Too Many Requests" in err or "429" in err:
                if attempt == 0:
                    time.sleep(3)
                    continue
                return None, "Yahoo Finance API 일시 제한 — 1~2분 후 새로고침"
            return None, f"로드 오류: {err[:80]}"
    return None, "재시도 실패"


# ─────────────────────────────────────────────
# 기술 차트 생성
# ─────────────────────────────────────────────

_C = {
    "price":   "#0F6E56",
    "ma20":    "#85B7EB",
    "ma50":    "#D3D1C7",
    "bb_fill": "rgba(239,159,39,0.08)",
    "bb_line": "rgba(239,159,39,0.35)",
    "rsi":     "#534AB7",
    "macd_pos":"#0F6E56",
    "macd_neg":"#A32D2D",
    "macd_l":  "#378ADD",
    "sig_l":   "#D85A30",
    "volume":  "rgba(100,116,139,0.45)",
}


def create_technical_chart(hist: pd.DataFrame, ticker: str) -> go.Figure:
    close = hist["Close"]
    ma20  = close.rolling(20).mean()
    ma50  = close.rolling(50).mean()
    bb_std   = close.rolling(20).std()
    bb_upper = ma20 + 2 * bb_std
    bb_lower = ma20 - 2 * bb_std

    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, float("nan"))
    rsi   = 100 - 100 / (1 + rs)

    ema12    = close.ewm(span=12, adjust=False).mean()
    ema26    = close.ewm(span=26, adjust=False).mean()
    macd     = ema12 - ema26
    macd_sig = macd.ewm(span=9, adjust=False).mean()
    macd_h   = macd - macd_sig

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.55, 0.15, 0.15, 0.15],
    )

    # Row 1: BB 영역
    fig.add_trace(go.Scatter(
        x=list(hist.index) + list(hist.index)[::-1],
        y=list(bb_upper) + list(bb_lower)[::-1],
        fill="toself", fillcolor=_C["bb_fill"],
        line=dict(color=_C["bb_line"], width=0.5),
        name="BB", hoverinfo="skip",
    ), row=1, col=1)
    for y, lbl in [(bb_upper, "BB↑"), (bb_lower, "BB↓")]:
        fig.add_trace(go.Scatter(
            x=hist.index, y=y, mode="lines",
            line=dict(color=_C["bb_line"], width=0.8, dash="dot"),
            name=lbl, hoverinfo="skip",
        ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=ma50, mode="lines",
        line=dict(color=_C["ma50"], width=1, dash="dash"), name="MA50",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=ma20, mode="lines",
        line=dict(color=_C["ma20"], width=1.2), name="MA20",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=close, mode="lines",
        line=dict(color=_C["price"], width=2), name=ticker,
        hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2f}<extra></extra>",
    ), row=1, col=1)

    # Row 2: RSI
    fig.add_hline(y=70, line=dict(color="#A32D2D", width=0.8, dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="#0F6E56", width=0.8, dash="dash"), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=rsi, mode="lines",
        line=dict(color=_C["rsi"], width=1.5), name="RSI",
        hovertemplate="RSI: %{y:.1f}<extra></extra>",
    ), row=2, col=1)

    # Row 3: MACD
    fig.add_trace(go.Bar(
        x=hist.index, y=macd_h.clip(lower=0),
        marker_color=_C["macd_pos"], name="MACD+", hoverinfo="skip",
    ), row=3, col=1)
    fig.add_trace(go.Bar(
        x=hist.index, y=macd_h.clip(upper=0),
        marker_color=_C["macd_neg"], name="MACD-", hoverinfo="skip",
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=macd, mode="lines",
        line=dict(color=_C["macd_l"], width=1.2), name="MACD",
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=macd_sig, mode="lines",
        line=dict(color=_C["sig_l"], width=1, dash="dash"), name="Signal",
    ), row=3, col=1)

    # Row 4: Volume
    fig.add_trace(go.Bar(
        x=hist.index, y=hist["Volume"],
        marker_color=_C["volume"], name="Volume",
        hovertemplate="Vol: %{y:,.0f}<extra></extra>",
    ), row=4, col=1)

    fig.update_layout(
        height=520, showlegend=False,
        margin=dict(l=0, r=50, t=10, b=20),
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", font_color="#1A1A1A",
        hovermode="x unified", bargap=0,
    )
    for row in range(1, 5):
        fig.update_yaxes(side="right", showgrid=True,
                         gridcolor="rgba(0,0,0,0.05)", row=row, col=1)
    for row in range(1, 4):
        fig.update_xaxes(showticklabels=False, row=row, col=1)
    fig.update_xaxes(showticklabels=True, row=4, col=1)
    fig.update_yaxes(range=[0, 100], row=2, col=1)
    return fig


def make_mock_ohlcv(ticker: str, market: dict, days: int = 180) -> pd.DataFrame:
    """테스트 모드용 가상 OHLCV"""
    import numpy as np
    from datetime import date
    ticker_d   = market.get("tickers", {}).get(ticker, {})
    curr_price = ticker_d.get("price", 100)
    dates      = pd.date_range(end=date.today(), periods=days, freq="B")
    np.random.seed(abs(hash(ticker)) % 2**32)
    pcts   = np.random.normal(0, 0.015, days)
    prices = [curr_price * 1.15]
    for p in pcts[1:]:
        prices.append(prices[-1] * (1 + p))
    prices[-1] = curr_price
    vol_base = ticker_d.get("volume", 1_000_000)
    return pd.DataFrame({
        "Close":  prices,
        "Open":   [p * 0.998 for p in prices],
        "High":   [p * 1.008 for p in prices],
        "Low":    [p * 0.992 for p in prices],
        "Volume": [int(vol_base * np.random.uniform(0.7, 1.3)) for _ in prices],
    }, index=dates)


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

yf_period = "6mo"  # 기본 차트 기간

portfolio = load_portfolio()
market    = load_market()
signals   = load_signals()

holdings    = sorted(portfolio.get("holdings", []) if portfolio else [],
                     key=lambda h: h["value_usd"], reverse=True)
tickers     = [h["ticker"] for h in holdings]
holding_map = {h["ticker"]: h for h in holdings}

st.markdown("← [Dashboard](/) &nbsp;/&nbsp; Ticker Detail", unsafe_allow_html=True)
st.markdown("---")

if not tickers:
    st.markdown(
        '<div style="background:#FFF3CD;border-radius:8px;padding:10px 14px;color:#856404;font-size:12px">'
        '포트폴리오 데이터 없음</div>',
        unsafe_allow_html=True,
    )
    st.stop()

selected = st.selectbox(
    "종목 선택", tickers,
    format_func=lambda t: f"{t} — {holding_map[t].get('name', '')}"
)
h = holding_map[selected]

# 헤더
cost    = h["value_usd"] - h.get("pnl_usd", 0)
avg     = cost / h.get("shares", 1) if h.get("shares") else 0
weight  = h["value_usd"] / portfolio.get("total_value_usd", 1) * 100
pnl_cls = "up" if h.get("pnl_usd", 0) >= 0 else "dn"
sign    = "+" if h.get("pnl_usd", 0) >= 0 else ""
cls_lbl = h.get("classification", "").replace("_", " ").title()

col_l, col_r = st.columns([3, 1])
with col_l:
    st.markdown(
        f"### {selected} &nbsp;"
        f"<span style='font-size:13px;background:#f0f0f0;padding:3px 8px;"
        f"border-radius:6px;color:#555'>{cls_lbl}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f'<div style="font-size:11px;color:#888780">{h.get("name","")} / {h.get("shares",0):,.3f} shares</div>', unsafe_allow_html=True)
with col_r:
    st.markdown(
        f"<div style='text-align:right'>"
        f"<div style='font-size:20px;font-weight:500'>${h['value_usd']:,.0f}</div>"
        f"<div class='{pnl_cls}' style='font-size:13px'>"
        f"{sign}${h.get('pnl_usd',0):,.0f} ({sign}{h.get('pnl_pct',0):.1f}%)</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

curr_price = market["tickers"].get(selected, {}).get("price", 0) if market else 0
stage_info: dict = {}
if signals:
    for s in signals.get("signals", []):
        if s["ticker"] == selected:
            stage_info = s.get("strategy_stage", {})
            break

m1, m2, m3, m4 = st.columns(4)
m1.markdown(metric_card("평균단가", f"${avg:,.2f}"), unsafe_allow_html=True)
m2.markdown(metric_card("현재가",   f"${curr_price:,.2f}"), unsafe_allow_html=True)
m3.markdown(metric_card("비중",     f"{weight:.1f}%"), unsafe_allow_html=True)
m4.markdown(metric_card("현재 단계", f"{stage_info.get('current_tranche', 1)}차" if stage_info else "—"),
            unsafe_allow_html=True)

st.markdown("---")

# 기술 차트
st.markdown(f"#### 📊 {selected} 기술 차트")

if USE_MOCK:
    if market:
        hist_df = make_mock_ohlcv(selected, market)
        fig = create_technical_chart(hist_df, selected)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown('<div style="background:#FFF3CD;border-radius:8px;padding:10px;color:#856404;font-size:12px">mock 데이터 없음</div>', unsafe_allow_html=True)
else:
    hist_df, err_msg = fetch_ohlcv(selected, yf_period)
    if hist_df is None:
        st.markdown(f'<div style="background:#FFF3CD;border-radius:8px;padding:10px;color:#856404;font-size:12px">{selected}: {err_msg}</div>', unsafe_allow_html=True)
    else:
        fig = create_technical_chart(hist_df, selected)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 전략 단계
if h.get("classification"):
    st.markdown("#### 📈 전략 단계")
    stage_html = strategy_progress(
        stage_info if stage_info else {"current_tranche": 1},
        h.get("classification", "")
    )
    st.markdown(stage_html, unsafe_allow_html=True)
    if market:
        ms_status = market.get("master_switch", {}).get("status", "RED")
        if ms_status == "RED" and h.get("classification") != "bond_gold_v26":
            st.markdown(
                '<div style="background:#FCEBEB;border-radius:8px;padding:8px 12px;'
                'color:#791F1F;font-size:12px;margin-top:6px">'
                '⚠ Master switch RED: 주식 신규 매수 중단</div>',
                unsafe_allow_html=True,
            )

st.markdown("---")

# 현재 시그널
if signals:
    st.markdown("#### 📡 현재 시그널")
    for s in signals.get("signals", []):
        if s["ticker"] == selected:
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
            break
    else:
        st.markdown('<div style="font-size:11px;color:#888780">시그널 데이터 없음 — Overview에서 Update 버튼을 누르세요.</div>', unsafe_allow_html=True)
