"""
dashboard/pages/1_Portfolio_Management.py
포트폴리오 편집: 수량/단가 수정, 삭제, Save/Discard
데이터 소유자: 이 페이지가 portfolio.json을 관리
"""

import json
import os
from pathlib import Path

import streamlit as st

sys_path = Path(__file__).parent.parent.parent / "src"
import sys
if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from dashboard.style import inject_css
from dashboard.components import metric_card, metrics_row, format_krw

st.set_page_config(
    page_title="Portfolio Management | AI Trading Assistant",
    layout="wide",
)
st.markdown(inject_css(), unsafe_allow_html=True)

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"


# ── 데이터 로드 ───────────────────────────────────────────

def load_portfolio() -> dict:
    path = DATA_DIR / ("test_portfolio.json" if USE_MOCK else "portfolio.json")
    if not path.exists():
        path = DATA_DIR / "portfolio.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_market_cache() -> dict:
    path = DATA_DIR / "market_cache.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(data: dict) -> None:
    path = DATA_DIR / "portfolio.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 세션 상태 초기화 ──────────────────────────────────────

if "pm_portfolio" not in st.session_state:
    st.session_state.pm_portfolio = load_portfolio()
if "pm_edits" not in st.session_state:
    st.session_state.pm_edits = {}       # {ticker: {shares, avg_cost}}
if "pm_deletions" not in st.session_state:
    st.session_state.pm_deletions = set()  # 삭제 대기 티커 집합
if "pm_saved" not in st.session_state:
    st.session_state.pm_saved = False

portfolio = st.session_state.pm_portfolio
holdings = portfolio.get("holdings", [])
cache = load_market_cache()
tickers_cache = cache.get("tickers", {})

# ── 헤더 ─────────────────────────────────────────────────

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('<h1 style="font-size:22px;font-weight:500;margin-bottom:2px">Portfolio management</h1>',
                unsafe_allow_html=True)
    updated = portfolio.get("updated_at", "")
    if updated:
        from datetime import datetime, timezone, timedelta
        try:
            dt = datetime.fromisoformat(updated)
            dt_kst = dt.astimezone(timezone(timedelta(hours=9)))
            sync_str = dt_kst.strftime("%Y-%m-%d %H:%M KST")
        except Exception:
            sync_str = updated
        n_match = len([h for h in holdings if h["ticker"] not in st.session_state.pm_deletions])
        st.markdown(
            f'<div style="font-size:11px;background:#E1F5EE;border-radius:6px;padding:4px 10px;'
            f'display:inline-block;color:#085041">Last sync: {sync_str} ({n_match}/{len(holdings)} matched)</div>',
            unsafe_allow_html=True)

with col_h2:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("↩ Discard", use_container_width=True):
            st.session_state.pm_edits = {}
            st.session_state.pm_deletions = set()
            st.session_state.pm_portfolio = load_portfolio()
            st.rerun()
    with c2:
        if st.button("💾 Save changes", use_container_width=True, type="primary"):
            # 저장 처리
            new_holdings = []
            for h in holdings:
                if h["ticker"] in st.session_state.pm_deletions:
                    continue
                edit = st.session_state.pm_edits.get(h["ticker"], {})
                hh = dict(h)
                if "shares" in edit:
                    hh["shares"] = edit["shares"]
                if "avg_cost" in edit:
                    hh["avg_cost"] = edit["avg_cost"]
                # current 가격으로 value_usd 재계산
                t_data = tickers_cache.get(h["ticker"], {})
                price = t_data.get("price", hh.get("value_usd", 0) / max(hh.get("shares", 1), 0.001))
                hh["value_usd"] = round(hh["shares"] * price, 2)
                new_holdings.append(hh)
            portfolio["holdings"] = new_holdings
            portfolio["total_value_usd"] = sum(h["value_usd"] for h in new_holdings)
            save_portfolio(portfolio)
            st.session_state.pm_portfolio = portfolio
            st.session_state.pm_edits = {}
            st.session_state.pm_deletions = set()
            st.session_state.pm_saved = True
            st.rerun()

if st.session_state.pm_saved:
    st.markdown(
        '<div style="background:#EAF3DE;border-radius:8px;padding:8px 14px;'
        'font-size:12px;color:#27500A;margin-bottom:8px">✓ 저장 완료. Overview에서 Update를 눌러 시그널을 재생성하세요.</div>',
        unsafe_allow_html=True)
    st.session_state.pm_saved = False

# ── 데이터 흐름 안내 ──────────────────────────────────────

st.markdown("""<div class="pm-flow">
  <div class="box">📱 Telegram OCR</div>
  <div class="arr">→</div>
  <div class="box box-active">📋 This page</div>
  <div class="arr">→</div>
  <div class="box">📊 Overview</div>
</div>""", unsafe_allow_html=True)

# ── 메트릭 ───────────────────────────────────────────────

active_holdings = [h for h in holdings if h["ticker"] not in st.session_state.pm_deletions]
total_value = sum(h.get("value_usd", 0) for h in active_holdings)
total_cost = sum(h.get("shares", 0) * h.get("avg_cost", 0) for h in active_holdings)

st.markdown(metrics_row([
    metric_card("Holdings", str(len(active_holdings)), f"{len(st.session_state.pm_deletions)} deleted" if st.session_state.pm_deletions else ""),
    metric_card("Total value", f"${total_value:,.0f}"),
    metric_card("Cost basis", f"${total_cost:,.0f}"),
]), unsafe_allow_html=True)

st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ── 편집 테이블 ───────────────────────────────────────────

st.markdown('<div class="sh">Holdings editor</div>', unsafe_allow_html=True)

# 헤더
header_cols = st.columns([0.4, 1.4, 0.8, 0.9, 0.9, 0.9, 0.9, 0.8, 0.4])
labels = ["#", "Ticker", "Class", "Shares", "Avg cost", "Current", "Value", "Return", "×"]
for col, lbl in zip(header_cols, labels):
    col.markdown(f'<div style="font-size:10px;color:#888;padding-bottom:4px">{lbl}</div>',
                 unsafe_allow_html=True)

st.markdown('<hr class="sep" style="margin:4px 0">', unsafe_allow_html=True)

for i, h in enumerate(holdings):
    ticker = h["ticker"]
    is_deleted = ticker in st.session_state.pm_deletions
    edit = st.session_state.pm_edits.get(ticker, {})
    is_edited = bool(edit)

    t_data = tickers_cache.get(ticker, {})
    current_price = t_data.get("price")
    shares_display = edit.get("shares", h.get("shares", 0))
    avg_cost_display = edit.get("avg_cost", h.get("avg_cost", 0))
    value = shares_display * (current_price or 0) if current_price else h.get("value_usd", 0)
    cost_basis = shares_display * avg_cost_display
    ret_pct = ((value - cost_basis) / cost_basis * 100) if cost_basis > 0 else 0

    row_style = ""
    if is_deleted:
        row_style = "opacity:0.4;text-decoration:line-through;"
    elif is_edited:
        row_style = "background:#FFFBE6;"

    cols = st.columns([0.4, 1.4, 0.8, 0.9, 0.9, 0.9, 0.9, 0.8, 0.4])

    with cols[0]:
        st.markdown(f'<div style="font-size:11px;color:#888;padding-top:6px;{row_style}">{i+1}</div>',
                    unsafe_allow_html=True)
    with cols[1]:
        edited_tag = ' <span style="font-size:8px;background:#FFF3CD;color:#856404;border-radius:4px;padding:1px 4px">edited</span>' if is_edited else ""
        st.markdown(
            f'<div style="font-size:12px;font-weight:500;padding-top:6px;{row_style}">'
            f'{ticker}{edited_tag}<br>'
            f'<span style="font-size:10px;color:#888;font-weight:400">{h.get("name","")[:20]}</span></div>',
            unsafe_allow_html=True)
    with cols[2]:
        cls_short = h.get("classification", "").replace("_v2", "").replace("2", "").replace("bond_gold6","bond")
        st.markdown(f'<div style="font-size:10px;color:#888;padding-top:6px;{row_style}">{cls_short}</div>',
                    unsafe_allow_html=True)

    if is_deleted:
        with cols[3]:
            st.markdown(f'<div style="font-size:11px;padding-top:6px;{row_style}">{h.get("shares",0):.3f}</div>',
                        unsafe_allow_html=True)
        with cols[4]:
            st.markdown(f'<div style="font-size:11px;padding-top:6px;{row_style}">${h.get("avg_cost",0):.2f}</div>',
                        unsafe_allow_html=True)
    else:
        with cols[3]:
            new_shares = st.number_input("shares", value=float(shares_display), step=0.001,
                                         format="%.3f", label_visibility="collapsed",
                                         key=f"shares_{ticker}")
            if abs(new_shares - h.get("shares", 0)) > 0.0001:
                st.session_state.pm_edits.setdefault(ticker, {})["shares"] = new_shares
        with cols[4]:
            new_avg = st.number_input("avg_cost", value=float(avg_cost_display), step=0.01,
                                      format="%.2f", label_visibility="collapsed",
                                      key=f"avg_{ticker}")
            if abs(new_avg - h.get("avg_cost", 0)) > 0.001:
                st.session_state.pm_edits.setdefault(ticker, {})["avg_cost"] = new_avg

    with cols[5]:
        price_str = f"${current_price:.2f}" if current_price else "–"
        st.markdown(f'<div style="font-size:11px;color:#888;padding-top:6px">{price_str}</div>',
                    unsafe_allow_html=True)
    with cols[6]:
        st.markdown(f'<div style="font-size:11px;padding-top:6px;{row_style}">${value:,.0f}</div>',
                    unsafe_allow_html=True)
    with cols[7]:
        ret_cls = "up" if ret_pct >= 0 else "dn"
        ret_str = f"+{ret_pct:.1f}%" if ret_pct >= 0 else f"{ret_pct:.1f}%"
        st.markdown(f'<div style="font-size:11px;padding-top:6px" class="{ret_cls}">{ret_str}</div>',
                    unsafe_allow_html=True)
    with cols[8]:
        if is_deleted:
            if st.button("↩", key=f"undo_{ticker}"):
                st.session_state.pm_deletions.discard(ticker)
                st.rerun()
        else:
            if st.button("×", key=f"del_{ticker}"):
                st.session_state.pm_deletions.add(ticker)
                st.rerun()

# ── 사용법 안내 ───────────────────────────────────────────

st.markdown('<hr class="sep">', unsafe_allow_html=True)
st.markdown("""
<div style="font-size:11px;color:#888;line-height:1.8">
  <b>사용 방법</b><br>
  • <b>Telegram OCR</b>: 토스 스크린샷을 텔레그램 봇으로 전송 → portfolio.json 자동 업데이트<br>
  • <b>Manual edit</b>: Shares / Avg cost 직접 수정 → Save changes<br>
  • <b>Delete</b>: × 버튼 → Undo로 취소 가능 → Save changes 후 확정<br>
  • <b>Overview 반영</b>: Save 후 Overview 페이지에서 🔄 Update 버튼 클릭
</div>
""", unsafe_allow_html=True)
