"""
dashboard/pages/2_Ticker_Detail.py — 종목 기술 차트 상세 페이지
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
sys.path.insert(0, str(ROOT_DIR))
DATA_DIR     = ROOT_DIR / "data"
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"

USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

st.set_page_config(
    page_title="Ticker Detail | AI Trading Assistant",
    layout="wide",
)

from dashboard.style import inject_css, inject_sidebar_css
from dashboard.components import strategy_progress, signal_card, metric_card, metrics_row

st.markdown(inject_css(), unsafe_allow_html=True)
st.markdown(inject_sidebar_css(), unsafe_allow_html=True)


# ── 데이터 로드 ───────────────────────────────────────────

def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_portfolio() -> Optional[dict]:
    fname = "test_portfolio.json" if USE_MOCK else "portfolio.json"
    return _load_json(DATA_DIR / fname)


def load_market() -> Optional[dict]:
    if USE_MOCK:
        return _load_json(FIXTURES_DIR / "mock_market_data.json")
    return _load_json(DATA_DIR / "market_cache.json")


def load_signals(mode: str = "full") -> Optional[dict]:
    fname = "signals_technical.json" if mode == "technical_only" else "signals.json"
    return _load_json(DATA_DIR / fname)


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


# ── 기술 차트 생성 ────────────────────────────────────────

_C = {
    "price":    "#0F6E56",
    "ma20":     "#85B7EB",
    "ma50":     "#D3D1C7",
    "bb_fill":  "rgba(239,159,39,0.08)",
    "bb_line":  "rgba(239,159,39,0.35)",
    "rsi":      "#534AB7",
    "macd_pos": "#0F6E56",
    "macd_neg": "#A32D2D",
    "macd_l":   "#378ADD",
    "sig_l":    "#D85A30",
    "volume":   "rgba(100,116,139,0.45)",
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

    # Row 1: BB 영역 + MA + 가격
    fig.add_trace(go.Scatter(
        x=list(hist.index) + list(hist.index)[::-1],
        y=list(bb_upper) + list(bb_lower)[::-1],
        fill="toself", fillcolor=_C["bb_fill"],
        line=dict(color=_C["bb_line"], width=0.5),
        name="BB", hoverinfo="skip",
    ), row=1, col=1)
    for y_series, lbl in [(bb_upper, "BB↑"), (bb_lower, "BB↓")]:
        fig.add_trace(go.Scatter(
            x=hist.index, y=y_series, mode="lines",
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


# ── 메인 ─────────────────────────────────────────────────

portfolio = load_portfolio()
market    = load_market()
signals   = load_signals("full")

holdings    = sorted(portfolio.get("holdings", []) if portfolio else [],
                     key=lambda h: h.get("value_usd", 0), reverse=True)
tickers     = [h["ticker"] for h in holdings]
holding_map = {h["ticker"]: h for h in holdings}

st.markdown('<h1 style="font-size:22px;font-weight:500;margin-bottom:8px">Ticker Detail</h1>',
            unsafe_allow_html=True)

if not tickers:
    st.markdown(
        '<div style="background:#FFF3CD;border-radius:8px;padding:10px 14px;'
        'color:#856404;font-size:12px">포트폴리오 데이터 없음</div>',
        unsafe_allow_html=True,
    )
    st.stop()

selected = st.selectbox(
    "종목 선택", tickers,
    format_func=lambda t: f"{t} — {holding_map[t].get('name', '')}",
    label_visibility="collapsed",
)
h = holding_map[selected]

# 헤더
shares   = h.get("shares", 0)
avg_cost = h.get("avg_cost", 0)
value    = h.get("value_usd", 0)
pnl_pct  = h.get("pnl_pct", 0)
pnl_usd  = value - shares * avg_cost
total_v  = portfolio.get("total_value_usd", 1) if portfolio else 1
weight   = value / total_v * 100 if total_v > 0 else 0
pnl_cls  = "up" if pnl_pct >= 0 else "dn"
pnl_sign = "+" if pnl_pct >= 0 else ""
cls_lbl  = h.get("classification", "").replace("_v2", "").replace("2", "").replace("bond_gold6", "bond")

col_l, col_r = st.columns([3, 1])
with col_l:
    st.markdown(
        f'<div style="margin-bottom:4px">'
        f'<span style="font-size:20px;font-weight:500;color:#1A1A1A">{selected}</span>'
        f'&nbsp;<span style="font-size:11px;background:#F1EFE8;padding:2px 8px;'
        f'border-radius:6px;color:#5F5E5A">{cls_lbl}</span></div>'
        f'<div style="font-size:11px;color:#888">{h.get("name","")} · {shares:,.3f} shares · avg ${avg_cost:.2f}</div>',
        unsafe_allow_html=True,
    )
with col_r:
    st.markdown(
        f'<div style="text-align:right">'
        f'<div style="font-size:20px;font-weight:500">${value:,.0f}</div>'
        f'<div class="{pnl_cls}" style="font-size:13px">'
        f'{pnl_sign}${abs(pnl_usd):,.0f} ({pnl_sign}{pnl_pct:.1f}%)</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# FIX: market_cache 비어있으면 portfolio의 current_price를 폴백으로 사용
curr_price = (market.get("tickers", {}).get(selected, {}).get("price")
              if market else None) or h.get("current_price", 0)

# 메트릭 카드 행
st.markdown(metrics_row([
    metric_card("평균단가", f"${avg_cost:,.2f}"),
    metric_card("현재가",   f"${curr_price:,.2f}"),
    metric_card("비중",     f"{weight:.1f}%"),
    metric_card("보유 수량", f"{shares:,.3f}"),
]), unsafe_allow_html=True)

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# 기술 차트
st.markdown(f'<div class="sh">{selected} 기술 차트</div>', unsafe_allow_html=True)

if USE_MOCK:
    if market:
        hist_df = make_mock_ohlcv(selected, market)
        fig = create_technical_chart(hist_df, selected)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown(
            '<div style="background:#FFF3CD;border-radius:8px;padding:10px;'
            'color:#856404;font-size:12px">mock 데이터 없음</div>',
            unsafe_allow_html=True,
        )
else:
    hist_df, err_msg = fetch_ohlcv(selected, "6mo")
    if hist_df is None:
        st.markdown(
            f'<div style="background:#FFF3CD;border-radius:8px;padding:10px;'
            f'color:#856404;font-size:12px">{selected}: {err_msg}</div>',
            unsafe_allow_html=True,
        )
    else:
        fig = create_technical_chart(hist_df, selected)
        st.plotly_chart(fig, use_container_width=True)

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# 전략 단계
if h.get("classification"):
    st.markdown('<div class="sh">전략 단계</div>', unsafe_allow_html=True)
    # signals에서 현재 tranche 찾기
    current_tranche = 1
    if signals:
        for s in signals.get("signals", []):
            if s["ticker"] == selected:
                current_tranche = s.get("strategy_stage", {}).get("current_tranche", 1)
                break
    st.markdown(
        strategy_progress(current_tranche, h.get("classification", "")),
        unsafe_allow_html=True,
    )
    if market:
        ms_status = market.get("master_switch", {}).get("status", "RED")
        if ms_status == "RED" and h.get("classification") != "bond_gold_v26":
            st.markdown(
                '<div style="background:#FCEBEB;border-radius:8px;padding:8px 12px;'
                'color:#791F1F;font-size:12px;margin-top:6px">'
                'Master switch RED: 주식 신규 매수 중단</div>',
                unsafe_allow_html=True,
            )

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# 현재 시그널
st.markdown('<div class="sh">현재 시그널</div>', unsafe_allow_html=True)
if signals:
    for s in signals.get("signals", []):
        if s["ticker"] == selected:
            st.markdown(
                signal_card(
                    ticker=s["ticker"],
                    action=s["action"],
                    confidence=s.get("confidence", 50),
                    rationale=s.get("rationale", ""),
                ),
                unsafe_allow_html=True,
            )
            break
    else:
        st.markdown(
            '<div style="font-size:11px;color:#888">시그널 데이터 없음 — Overview에서 Update 버튼을 누르세요.</div>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div style="font-size:11px;color:#888">signals.json 없음</div>',
        unsafe_allow_html=True,
    )
