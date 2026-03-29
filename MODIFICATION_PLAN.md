# AI Trading Assistant — 수정 계획서 (Modification Plan v1.1)

> Claude Code가 이 문서를 읽고 수정 작업을 자율적으로 진행합니다.
> 수정 완료 후 Phase T(테스트)를 자동 실행하여 검증합니다.
> OCR 관련 테스트는 제외합니다.

---

## 수정 항목 요약

| # | 항목 | 범위 |
|---|------|------|
| M1 | 대시보드 UI를 디자인 스펙과 동일하게 재작성 | dashboard/ 전체 |
| M2 | Overview: 트렌드 차트 삭제 + 업데이트 버튼 추가 | dashboard/app.py |
| M3 | 테스트용 실제 포트폴리오 fixture 생성 | data/ + tests/fixtures/ |
| M4 | Ticker Detail 페이지 디자인 스펙대로 재작성 | dashboard/pages/1_Ticker_Detail.py |
| M5 | Signals 페이지를 2개로 분리 | dashboard/pages/2_Market_Signals.py, 3_Technical_Signals.py |
| M6 | 테스트 자동 실행 (OCR 제외) | tests/ |

---

## M1: 대시보드 UI 디자인 통일

### 목표
Streamlit 대시보드의 모든 페이지를 아래 디자인 시스템으로 통일합니다.
현재 Streamlit 기본 테마가 아닌, 커스텀 CSS로 디자인 스펙을 적용합니다.

### 디자인 시스템 (dashboard/style.py)
```python
# 모든 페이지에서 공통으로 사용하는 CSS와 컴포넌트

CUSTOM_CSS = """
<style>
/* 전체 배경 및 폰트 */
.main .block-container { max-width: 900px; padding: 1rem 1rem; }

/* 메트릭 카드 */
.metric-card {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 12px 14px;
    text-align: left;
}
.metric-card .label {
    font-size: 11px;
    color: #888780;
    margin-bottom: 2px;
}
.metric-card .value {
    font-size: 20px;
    font-weight: 500;
    color: #1a1a1a;
}
.metric-card .change {
    font-size: 11px;
    margin-top: 2px;
}

/* 매크로 지표 카드 */
.macro-card {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 10px;
    text-align: center;
}
.macro-card .label { font-size: 10px; color: #888780; }
.macro-card .value { font-size: 14px; font-weight: 500; margin: 2px 0; }
.macro-card .status { font-size: 10px; }

/* 시그널 카드 */
.signal-card {
    background: #ffffff;
    border: 0.5px solid #e0e0e0;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 8px;
}
.signal-card-warn { border-left: 3px solid #A32D2D; border-radius: 0; }
.signal-card-watch { border-left: 3px solid #BA7517; border-radius: 0; }
.signal-card-buy { border-left: 3px solid #0F6E56; border-radius: 0; }
.signal-card-hold { border-left: 3px solid #888780; border-radius: 0; }

/* 시그널 배지 */
.pill {
    display: inline-block;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 8px;
    margin-left: 4px;
}
.pill-sell { background: #FCEBEB; color: #791F1F; }
.pill-buy { background: #EAF3DE; color: #27500A; }
.pill-hold { background: #F1EFE8; color: #5F5E5A; }
.pill-wait { background: #FAEEDA; color: #633806; }
.pill-bond { background: #E1F5EE; color: #085041; }

/* 마스터 스위치 배지 */
.switch-badge {
    display: inline-block;
    font-size: 12px;
    padding: 4px 12px;
    border-radius: 8px;
}
.switch-red { background: #FCEBEB; color: #791F1F; }
.switch-green { background: #EAF3DE; color: #27500A; }
.switch-yellow { background: #FAEEDA; color: #633806; }

/* 조건 태그 */
.cond-tag {
    display: inline-block;
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    margin: 2px;
}
.cond-met { background: #EAF3DE; color: #27500A; }
.cond-not { background: #f0f0f0; color: #999; }

/* 확신도 바 */
.conf-bar {
    height: 4px;
    border-radius: 2px;
    background: #e0e0e0;
    display: inline-block;
    width: 60px;
    vertical-align: middle;
    margin-right: 4px;
}
.conf-fill {
    height: 4px;
    border-radius: 2px;
    display: block;
}

/* 테이블 스타일 */
.holdings-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.holdings-table th {
    text-align: left;
    padding: 8px 6px;
    color: #888780;
    font-weight: 400;
    border-bottom: 0.5px solid #e0e0e0;
    font-size: 11px;
}
.holdings-table td {
    padding: 8px 6px;
    border-bottom: 0.5px solid #e0e0e0;
}

/* 색상 유틸리티 */
.up { color: #0F6E56; }
.dn { color: #A32D2D; }

/* 전략 단계 프로그레스 */
.step-done { background: #EAF3DE; color: #27500A; }
.step-cur { background: #FAEEDA; color: #633806; }
.step-lock { background: #f0f0f0; color: #999; }
</style>
"""

def inject_css():
    """모든 페이지 상단에서 호출"""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
```

### 공통 컴포넌트 함수 (dashboard/components.py)
```python
"""재사용 가능한 UI 컴포넌트"""
import streamlit as st

def metric_card(label: str, value: str, change: str = "", change_class: str = ""):
    """메트릭 카드 HTML 생성"""
    change_html = f'<div class="change {change_class}">{change}</div>' if change else ""
    return f'''
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        {change_html}
    </div>'''

def signal_card(ticker: str, action: str, confidence: int, rationale: str,
                conditions_met: list, conditions_not_met: list, card_class: str = ""):
    """시그널 카드 HTML 생성"""
    pill_class = {
        "L1_WARNING": "pill-sell", "L2_WARNING": "pill-sell", "L3_BREAKDOWN": "pill-sell",
        "TRANCHE_1_BUY": "pill-buy", "TRANCHE_2_BUY": "pill-buy",
        "HOLD": "pill-hold", "WATCH": "pill-wait", "BOND_WATCH": "pill-bond",
    }.get(action, "pill-hold")

    conf_color = "#A32D2D" if "WARNING" in action or "BREAKDOWN" in action else (
        "#0F6E56" if "BUY" in action else "#BA7517")

    tags = "".join(f'<span class="cond-tag cond-met">{c}</span>' for c in conditions_met)
    tags += "".join(f'<span class="cond-tag cond-not">{c}</span>' for c in conditions_not_met)

    return f'''
    <div class="signal-card {card_class}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-weight:500;font-size:14px">{ticker}
                <span class="pill {pill_class}">{action.replace("_"," ")}</span></span>
            <span style="font-size:11px;color:#888">
                <span class="conf-bar"><span class="conf-fill" style="width:{confidence}%;background:{conf_color}"></span></span>
                {confidence}%</span>
        </div>
        <div style="font-size:12px;color:#666;line-height:1.6">{rationale}</div>
        <div style="margin-top:6px">{tags}</div>
    </div>'''

def master_switch_banner(status: str, qqq_price: float, qqq_ma200: float,
                         spy_price: float, spy_ma200: float, vix: float):
    """마스터 스위치 배너 HTML"""
    cls = {"RED": "switch-red", "GREEN": "switch-green", "YELLOW": "switch-yellow"}[status]
    return f'''
    <div class="signal-card" style="border-left:3px solid {'#A32D2D' if status=='RED' else '#0F6E56' if status=='GREEN' else '#BA7517'};border-radius:0">
        <div style="font-weight:500;font-size:14px;margin-bottom:6px">
            Master switch: <span class="switch-badge {cls}">{status}</span></div>
        <div style="font-size:12px;color:#666">
            QQQ ${qqq_price:.0f} vs MA200 ${qqq_ma200:.0f} •
            SPY ${spy_price:.0f} vs MA200 ${spy_ma200:.0f} •
            VIX {vix:.1f}</div>
    </div>'''
```

---

## M2: Overview 페이지 수정 (dashboard/app.py)

### 변경 사항
1. **삭제**: 포트폴리오 트렌드 차트 (히스토리 기반 라인 차트 제거)
2. **추가**: "Update" 버튼 — 클릭 시 portfolio.json 기반 데이터 리로드 + 시그널 재생성
3. **유지/개선**: 메트릭 카드, 매크로 지표, 보유 종목 테이블, 당일 시그널 요약

### 페이지 구조
```python
# dashboard/app.py 구조

import streamlit as st
from style import inject_css
from components import metric_card, signal_card, master_switch_banner
import json

st.set_page_config(page_title="AI Trading Assistant", layout="wide")
inject_css()

# ── 헤더 + 업데이트 버튼 ──
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.markdown("# Portfolio dashboard")
    st.caption(f"Updated: {portfolio['updated_at']}")
with col_btn:
    if st.button("🔄 Update", use_container_width=True):
        # 1. portfolio.json 리로드
        # 2. market_data.py 실행 (yfinance fetch)
        # 3. rule_engine.py 실행
        # 4. signal_generator.py 실행 (both modes)
        # 5. st.rerun()
        run_update_pipeline()
        st.rerun()

# ── 마스터 스위치 배지 ──
st.markdown(master_switch_banner(...), unsafe_allow_html=True)

# ── 4개 메트릭 카드 (한 줄) ──
c1, c2, c3, c4 = st.columns(4)
# 총자산, 일일 손익, 총수익률, YTD 배당금

# ── 3개 매크로 지표 (한 줄) ──
m1, m2, m3 = st.columns(3)
# QQQ vs MA200, 30Y 금리, VIX

# ── 보유 종목 테이블 ──
# st.markdown()으로 커스텀 HTML 테이블 생성
# 컬럼: Ticker, 종목명, 평가금액, 비중(바차트), 수익률, 시그널 배지
# portfolio.json의 holdings를 금액 기준 내림차순 정렬

# ── 당일 시그널 요약 (상위 3개만) ──
# 경고 > 관심 > 매수 순으로 최대 3개 표시
```

### Update 버튼 로직
```python
def run_update_pipeline():
    """수동 업데이트 파이프라인"""
    import subprocess
    with st.spinner("시장 데이터 수집 중..."):
        subprocess.run(["python", "../src/market_data.py"], check=True)
    with st.spinner("규칙 엔진 실행 중..."):
        subprocess.run(["python", "../src/rule_engine.py"], check=True)
    with st.spinner("시그널 생성 중..."):
        subprocess.run(["python", "../src/signal_generator.py", "--mode", "both"], check=True)
    st.success("업데이트 완료!")
```

---

## M3: 테스트용 실제 포트폴리오 fixture

### 생성할 파일

#### data/test_portfolio.json
```json
{
  "updated_at": "2026-03-28T06:22:00+09:00",
  "source": "toss_securities_ocr",
  "total_value_usd": 431847.25,
  "holdings": [
    {"ticker": "VOO",  "name": "Vanguard S&P 500 ETF",       "shares": 175.157486,  "value_usd": 102109.73, "pnl_usd": 12079.06,  "pnl_pct": 13.42,  "classification": "etf_v24"},
    {"ticker": "BIL",  "name": "SPDR 1-3 Month Treasury",    "shares": 1000,        "value_usd": 91629.97,  "pnl_usd": 8681.28,   "pnl_pct": 10.47,  "classification": "bond_gold_v26"},
    {"ticker": "QQQ",  "name": "Invesco QQQ Trust ETF",      "shares": 135.643587,  "value_usd": 76310.31,  "pnl_usd": 8740.33,   "pnl_pct": 12.94,  "classification": "etf_v24"},
    {"ticker": "SCHD", "name": "Schwab US Dividend Equity",   "shares": 1512.010124, "value_usd": 46025.07,  "pnl_usd": 8970.72,   "pnl_pct": 24.21,  "classification": "etf_v24"},
    {"ticker": "AAPL", "name": "Apple Inc.",                  "shares": 79.349225,   "value_usd": 19742.07,  "pnl_usd": 6163.48,   "pnl_pct": 45.39,  "classification": "growth_v22"},
    {"ticker": "O",    "name": "Realty Income Corp",          "shares": 281.032653,  "value_usd": 17055.77,  "pnl_usd": 2707.80,   "pnl_pct": 18.87,  "classification": "energy_v23"},
    {"ticker": "JEPI", "name": "JPMorgan Equity Premium",     "shares": 254.066847,  "value_usd": 14113.35,  "pnl_usd": 1233.91,   "pnl_pct": 9.58,   "classification": "etf_v24"},
    {"ticker": "SOXX", "name": "iShares Semiconductor ETF",   "shares": 30.889879,   "value_usd": 9992.24,   "pnl_usd": 4322.33,   "pnl_pct": 76.23,  "classification": "etf_v24"},
    {"ticker": "TSLA", "name": "Tesla Inc.",                  "shares": 26.931576,   "value_usd": 9744.64,   "pnl_usd": -759.24,   "pnl_pct": -7.23,  "classification": "growth_v22"},
    {"ticker": "TLT",  "name": "iShares 20+ Year Treasury",  "shares": 100,         "value_usd": 8563.99,   "pnl_usd": 158.81,    "pnl_pct": 1.89,   "classification": "bond_gold_v26"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation",          "shares": 48.700507,   "value_usd": 8158.30,   "pnl_usd": 130.27,    "pnl_pct": 1.62,   "classification": "growth_v22"},
    {"ticker": "PLTR", "name": "Palantir Technologies",       "shares": 56.829293,   "value_usd": 8129.98,   "pnl_usd": 313.74,    "pnl_pct": 4.01,   "classification": "growth_v22"},
    {"ticker": "SPY",  "name": "SPDR S&P 500 ETF Trust",     "shares": 8.887535,    "value_usd": 5635.49,   "pnl_usd": 1112.34,   "pnl_pct": 24.59,  "classification": "etf_v24"},
    {"ticker": "UNH",  "name": "UnitedHealth Group",          "shares": 18,          "value_usd": 4662.36,   "pnl_usd": -400.56,   "pnl_pct": -7.91,  "classification": "energy_v23"},
    {"ticker": "MSFT", "name": "Microsoft Corporation",        "shares": 11.999013,   "value_usd": 4280.89,   "pnl_usd": -431.73,   "pnl_pct": -9.16,  "classification": "growth_v22"},
    {"ticker": "GOOGL","name": "Alphabet Inc. Class A",        "shares": 10.676876,   "value_usd": 2929.09,   "pnl_usd": -246.18,   "pnl_pct": -7.75,  "classification": "growth_v22"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.",              "shares": 5.84814,     "value_usd": 1165.77,   "pnl_usd": -54.17,    "pnl_pct": -4.44,  "classification": "growth_v22"},
    {"ticker": "SLV",  "name": "iShares Silver Trust",        "shares": 12,          "value_usd": 761.28,    "pnl_usd": -10.22,    "pnl_pct": -1.32,  "classification": "bond_gold_v26"},
    {"ticker": "TQQQ", "name": "ProShares UltraPro QQQ",      "shares": 5,           "value_usd": 290.25,    "pnl_usd": -25.88,    "pnl_pct": -8.19,  "classification": "speculative"},
    {"ticker": "SOXL", "name": "Direxion Daily Semi 3X",      "shares": 5,           "value_usd": 233.05,    "pnl_usd": -35.06,    "pnl_pct": -13.08, "classification": "speculative"},
    {"ticker": "ETHU", "name": "ProShares Ultra Ether ETF",   "shares": 10,          "value_usd": 201.60,    "pnl_usd": -57.98,    "pnl_pct": -22.34, "classification": "speculative"},
    {"ticker": "CRCL", "name": "Circle Internet Group",       "shares": 1,           "value_usd": 93.66,     "pnl_usd": -30.15,    "pnl_pct": -24.35, "classification": "speculative"},
    {"ticker": "BTDR", "name": "Bitdeer Technologies",        "shares": 1,           "value_usd": 18.39,     "pnl_usd": -11.40,    "pnl_pct": -38.26, "classification": "speculative"}
  ]
}
```

#### tests/fixtures/mock_market_data.json
```json
{
  "updated_at": "2026-03-28T07:00:00+09:00",
  "master_switch": {
    "qqq_price": 587.82, "qqq_ma200": 592.43, "qqq_above_ma200": false,
    "spy_price": 645.09, "spy_ma200": 657.19, "spy_above_ma200": false,
    "status": "RED"
  },
  "macro": {
    "vix": 30.91, "vix_tier": "high", "vix_multiplier": 0.5,
    "treasury_30y": 4.982, "usdkrw": 1425.50
  },
  "tickers": {
    "VOO":  {"price":582.50,"ma20":595.00,"ma50":605.00,"ma200":570.00,"rsi":36.5,"macd":-5.20,"macd_signal":-4.10,"macd_histogram":-1.10,"macd_hist_trend":"declining_2d","bb_upper":625.00,"bb_lower":560.00,"adx":32,"volume":8500000,"volume_avg20":9200000,"volume_ratio":0.92},
    "BIL":  {"price":91.63,"ma20":91.50,"ma50":91.30,"ma200":90.80,"rsi":52.0,"macd":0.05,"macd_signal":0.03,"macd_histogram":0.02,"macd_hist_trend":"flat","bb_upper":92.10,"bb_lower":90.90,"adx":12,"volume":3000000,"volume_avg20":2800000,"volume_ratio":1.07},
    "QQQ":  {"price":587.82,"ma20":599.66,"ma50":608.66,"ma200":592.43,"rsi":34.75,"macd":-7.12,"macd_signal":-5.80,"macd_histogram":-1.32,"macd_hist_trend":"declining_3d","bb_upper":635.00,"bb_lower":565.00,"adx":30,"volume":52000000,"volume_avg20":48000000,"volume_ratio":1.08},
    "SCHD": {"price":30.44,"ma20":31.20,"ma50":31.80,"ma200":29.50,"rsi":38.0,"macd":-0.35,"macd_signal":-0.28,"macd_histogram":-0.07,"macd_hist_trend":"flat","bb_upper":33.00,"bb_lower":29.50,"adx":22,"volume":4500000,"volume_avg20":4200000,"volume_ratio":1.07},
    "AAPL": {"price":248.80,"ma20":255.00,"ma50":260.00,"ma200":230.00,"rsi":40.2,"macd":-2.80,"macd_signal":-2.20,"macd_histogram":-0.60,"macd_hist_trend":"declining_1d","bb_upper":270.00,"bb_lower":240.00,"adx":25,"volume":35000000,"volume_avg20":38000000,"volume_ratio":0.92},
    "O":    {"price":60.68,"ma20":61.50,"ma50":62.00,"ma200":58.00,"rsi":42.5,"macd":-0.40,"macd_signal":-0.30,"macd_histogram":-0.10,"macd_hist_trend":"flat","bb_upper":64.00,"bb_lower":59.00,"adx":18,"volume":5000000,"volume_avg20":4800000,"volume_ratio":1.04},
    "JEPI": {"price":55.56,"ma20":56.20,"ma50":56.80,"ma200":54.50,"rsi":44.0,"macd":-0.25,"macd_signal":-0.18,"macd_histogram":-0.07,"macd_hist_trend":"flat","bb_upper":58.00,"bb_lower":54.50,"adx":15,"volume":3200000,"volume_avg20":3000000,"volume_ratio":1.07},
    "SOXX": {"price":323.50,"ma20":340.00,"ma50":355.00,"ma200":290.00,"rsi":32.0,"macd":-8.50,"macd_signal":-6.80,"macd_histogram":-1.70,"macd_hist_trend":"declining_3d","bb_upper":380.00,"bb_lower":300.00,"adx":35,"volume":2800000,"volume_avg20":2500000,"volume_ratio":1.12},
    "TSLA": {"price":361.88,"ma20":378.50,"ma50":395.20,"ma200":310.00,"rsi":38.2,"macd":-3.44,"macd_signal":-1.82,"macd_histogram":-1.62,"macd_hist_trend":"declining_2d","bb_upper":410.50,"bb_lower":346.50,"adx":28,"volume":45000000,"volume_avg20":52000000,"volume_ratio":0.87},
    "TLT":  {"price":85.64,"ma20":87.20,"ma50":88.50,"ma200":90.10,"rsi":34.0,"macd":-0.80,"macd_signal":-0.60,"macd_histogram":-0.20,"macd_hist_trend":"declining_1d","bb_upper":92.00,"bb_lower":83.00,"adx":20,"volume":22000000,"volume_avg20":20000000,"volume_ratio":1.10},
    "NVDA": {"price":167.55,"ma20":172.30,"ma50":180.10,"ma200":135.00,"rsi":35.8,"macd":-2.10,"macd_signal":-1.50,"macd_histogram":-0.60,"macd_hist_trend":"rising_1d","bb_upper":195.00,"bb_lower":155.00,"adx":26,"volume":42000000,"volume_avg20":45000000,"volume_ratio":0.93},
    "PLTR": {"price":143.05,"ma20":148.00,"ma50":152.00,"ma200":120.00,"rsi":41.0,"macd":-1.80,"macd_signal":-1.40,"macd_histogram":-0.40,"macd_hist_trend":"flat","bb_upper":160.00,"bb_lower":135.00,"adx":22,"volume":18000000,"volume_avg20":20000000,"volume_ratio":0.90},
    "SPY":  {"price":645.09,"ma20":668.59,"ma50":680.65,"ma200":657.19,"rsi":35.99,"macd":-7.92,"macd_signal":-6.20,"macd_histogram":-1.72,"macd_hist_trend":"declining_2d","bb_upper":700.00,"bb_lower":630.00,"adx":34,"volume":85000000,"volume_avg20":78000000,"volume_ratio":1.09},
    "UNH":  {"price":259.02,"ma20":270.00,"ma50":280.00,"ma200":250.00,"rsi":33.5,"macd":-4.50,"macd_signal":-3.20,"macd_histogram":-1.30,"macd_hist_trend":"declining_3d","bb_upper":295.00,"bb_lower":245.00,"adx":30,"volume":4200000,"volume_avg20":3800000,"volume_ratio":1.11},
    "MSFT": {"price":356.80,"ma20":368.00,"ma50":378.00,"ma200":340.00,"rsi":37.0,"macd":-3.20,"macd_signal":-2.50,"macd_histogram":-0.70,"macd_hist_trend":"declining_1d","bb_upper":390.00,"bb_lower":345.00,"adx":24,"volume":22000000,"volume_avg20":24000000,"volume_ratio":0.92},
    "GOOGL":{"price":274.30,"ma20":282.00,"ma50":290.00,"ma200":260.00,"rsi":36.5,"macd":-2.80,"macd_signal":-2.10,"macd_histogram":-0.70,"macd_hist_trend":"declining_2d","bb_upper":300.00,"bb_lower":265.00,"adx":26,"volume":16000000,"volume_avg20":18000000,"volume_ratio":0.89},
    "AMZN": {"price":199.30,"ma20":205.00,"ma50":212.00,"ma200":188.00,"rsi":38.5,"macd":-2.20,"macd_signal":-1.70,"macd_histogram":-0.50,"macd_hist_trend":"flat","bb_upper":220.00,"bb_lower":190.00,"adx":22,"volume":28000000,"volume_avg20":30000000,"volume_ratio":0.93},
    "SLV":  {"price":63.44,"ma20":67.50,"ma50":72.00,"ma200":52.00,"rsi":36.1,"macd":-1.80,"macd_signal":-1.30,"macd_histogram":-0.50,"macd_hist_trend":"declining_1d","bb_upper":78.00,"bb_lower":60.00,"adx":28,"volume":18000000,"volume_avg20":16000000,"volume_ratio":1.13},
    "TQQQ": {"price":58.05,"ma20":62.00,"ma50":66.00,"ma200":50.00,"rsi":30.5,"macd":-1.50,"macd_signal":-1.10,"macd_histogram":-0.40,"macd_hist_trend":"declining_2d","bb_upper":72.00,"bb_lower":52.00,"adx":32,"volume":25000000,"volume_avg20":22000000,"volume_ratio":1.14},
    "SOXL": {"price":46.61,"ma20":52.00,"ma50":58.00,"ma200":38.00,"rsi":28.0,"macd":-2.80,"macd_signal":-2.10,"macd_histogram":-0.70,"macd_hist_trend":"declining_3d","bb_upper":65.00,"bb_lower":40.00,"adx":36,"volume":15000000,"volume_avg20":13000000,"volume_ratio":1.15},
    "ETHU": {"price":20.16,"ma20":23.00,"ma50":26.00,"ma200":18.00,"rsi":28.5,"macd":-1.20,"macd_signal":-0.90,"macd_histogram":-0.30,"macd_hist_trend":"declining_3d","bb_upper":28.00,"bb_lower":18.00,"adx":34,"volume":800000,"volume_avg20":700000,"volume_ratio":1.14},
    "CRCL": {"price":93.66,"ma20":100.00,"ma50":108.00,"ma200":80.00,"rsi":32.0,"macd":-3.00,"macd_signal":-2.20,"macd_histogram":-0.80,"macd_hist_trend":"declining_2d","bb_upper":115.00,"bb_lower":85.00,"adx":30,"volume":500000,"volume_avg20":450000,"volume_ratio":1.11},
    "BTDR": {"price":18.39,"ma20":22.00,"ma50":25.00,"ma200":15.00,"rsi":25.0,"macd":-1.50,"macd_signal":-1.10,"macd_histogram":-0.40,"macd_hist_trend":"declining_3d","bb_upper":28.00,"bb_lower":16.00,"adx":38,"volume":300000,"volume_avg20":250000,"volume_ratio":1.20}
  }
}
```

### 사용법
```python
# 테스트나 대시보드에서 mock 데이터 사용
import json

def load_data(use_test=True):
    prefix = "test_" if use_test else ""
    with open(f"data/{prefix}portfolio.json") as f:
        portfolio = json.load(f)
    with open(f"tests/fixtures/mock_market_data.json" if use_test else "data/market_cache.json") as f:
        market = json.load(f)
    return portfolio, market
```

---

## M4: Ticker Detail 페이지 (dashboard/pages/1_Ticker_Detail.py)

### 디자인 스펙
```
┌─────────────────────────────────────────────┐
│ [Breadcrumb] Dashboard / TSLA               │
│                                             │
│ TSLA  [Growth v2.2]          $9,745         │
│ Tesla Inc. / 26.93 shares    -$759 (-7.23%) │
│                                             │
│ ┌──────┬──────┬──────┬──────┐              │
│ │ Avg  │ Curr │Weight│Stage │              │
│ │$390  │$362  │2.3%  │1st   │              │
│ └──────┴──────┴──────┴──────┘              │
│                                             │
│ [Plotly subplot — shared X axis]            │
│ ┌───────────────────────────────┐ 60%      │
│ │ Price + MA20 + MA50 + BB band │          │
│ │ + buy/sell markers            │          │
│ └───────────────────────────────┘          │
│ ┌───────────────────────────────┐ 15%      │
│ │ RSI(14) + 70/30 lines        │          │
│ └───────────────────────────────┘          │
│ ┌───────────────────────────────┐ 15%      │
│ │ MACD histogram + lines        │          │
│ └───────────────────────────────┘          │
│ ┌───────────────────────────────┐ 10%      │
│ │ Volume bars                   │          │
│ └───────────────────────────────┘          │
│                                             │
│ Strategy progress: Growth v2.2              │
│ [●1st done] [◐2nd waiting] [○3rd locked]   │
│ ⚠ Master switch RED: equity buys suspended  │
│                                             │
│ Signal history (last 7 days)                │
│ ┌────┬────────┬─────┬──────────────┐       │
│ │Date│Signal  │Conf │Rationale     │       │
│ └────┴────────┴─────┴──────────────┘       │
└─────────────────────────────────────────────┘
```

### Plotly 멀티패널 차트 구현
```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_technical_chart(ticker_data: dict, ticker: str):
    """4-panel technical chart"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=None
    )

    # Row 1: Price + MA + BB
    # - 가격: 실선 (teal #0F6E56)
    # - MA20: 점선 (light blue #85B7EB)
    # - MA50: 점선 (gray #D3D1C7)
    # - BB: 반투명 영역 (amber #EF9F27, opacity 0.1)
    # - 매수 마커: 삼각형 (pink #F09595)

    # Row 2: RSI
    # - RSI 라인: purple #534AB7
    # - 70선: 점선 red
    # - 30선: 점선 green

    # Row 3: MACD
    # - 히스토그램: 양수=teal, 음수=red
    # - MACD 라인: blue #378ADD
    # - Signal 라인: coral #D85A30 (점선)

    # Row 4: Volume
    # - 바: gray with low opacity

    fig.update_layout(
        height=500,
        showlegend=False,
        margin=dict(l=0, r=50, t=10, b=30),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    # Y축: 오른쪽 배치
    # X축: 마지막 패널에만 표시
    return fig
```

---

## M5: Signals 페이지 2개 분리

### 5A. Market Signals (dashboard/pages/2_Market_Signals.py)
마스터 스위치 + 매크로 오버레이를 반영한 종합 시그널.

```
시그널 생성 모드: signal_generator.py --mode full
- 마스터 스위치 RED → 모든 주식 매수 차단
- VIX 30.91 → allocation x0.5
- 30Y 금리 4.98% → 채권 전략 근접
- 결과: 대부분 HOLD 또는 WARNING, 채권만 WATCH
```

### 5B. Technical Signals (dashboard/pages/3_Technical_Signals.py)
마스터 스위치와 매크로를 완전히 무시하고, 개별 종목의 기술지표만으로 판단.

```
시그널 생성 모드: signal_generator.py --mode technical_only
- 마스터 스위치: 무시
- VIX 오버라이드: 무시
- 금리/환율: 무시
- 순수하게 RSI, MACD, MA, BB, 거래량만으로 진입/퇴출 판단
- 결과: RED 시장에서도 기술적 매수 조건 충족 종목이 보임
```

### signal_generator.py 수정
```python
def generate_signals(portfolio, market_data, mode="full"):
    """
    mode="full": 마스터 스위치 + 매크로 + 기술지표 모두 반영
    mode="technical_only": 기술지표만 반영, 마스터 스위치/매크로 무시
    """
    signals = []
    for holding in portfolio["holdings"]:
        ticker = holding["ticker"]
        td = market_data["tickers"].get(ticker, {})
        classification = holding.get("classification", "unknown")

        if mode == "full":
            # 마스터 스위치 체크
            master = market_data["master_switch"]["status"]
            if master == "RED" and classification not in ["bond_gold_v26"]:
                # 주식 신규 매수 차단
                ...
            # VIX 오버라이드 적용
            # 매크로 룰 적용
        elif mode == "technical_only":
            # 마스터 스위치 무시
            # VIX 무시
            # 순수 기술지표로만 판단
            ...

        signals.append(signal)
    return signals
```

### 5B 페이지의 상단 경고 배너
```python
# Technical Signals 페이지 최상단에 경고 표시
st.warning("""
⚠️ 이 페이지는 시장 상황(마스터 스위치, VIX, 금리)을 무시하고
순수 기술지표만으로 분석한 결과입니다.
실제 매매 시에는 반드시 Market Signals 페이지를 함께 확인하세요.
""")
```

---

## M6: 테스트 계획 (OCR 제외)

### Phase T1: 규칙 엔진 테스트 (pytest 자동)
```bash
pytest tests/test_rule_engine.py -v --tb=short
```
- 마스터 스위치 3상태 (GREEN/YELLOW/RED) 검증
- VIX 3단계 오버라이드 검증
- 성장주/ETF/에너지/채권 4개 전략 진입 조건 검증
- Exit L1/L2/L3 에스컬레이션 검증
- Top Signal 강제 익절 검증
- 리밸런싱 트리거 4종 검증

### Phase T2: 시그널 생성 테스트 (pytest 자동)
```bash
pytest tests/test_signal_generator.py -v --tb=short
```
- full 모드: 23개 종목 시그널 생성, master=RED 반영 확인
- technical_only 모드: 23개 종목 시그널 생성, master 무시 확인
- 두 모드의 차이점 검증: technical_only에서 매수 시그널이 더 많아야 함
- 확신도 0-100 범위
- 한국어 rationale 비어있지 않음
- JSON 스키마 완전성

### Phase T3: 대시보드 기동 테스트 (자동)
```bash
# Streamlit 서버 시작
cd dashboard
streamlit run app.py --server.port 8501 --server.headless true &
sleep 10

# 4 페이지 HTTP 200 확인
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501          # Overview
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/Ticker_Detail     # Ticker
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/Market_Signals    # Market
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/Technical_Signals # Technical

kill %1
```

### Phase T4: 대시보드 시각 검증 (playwright 반자동)
```bash
pip install playwright && playwright install chromium
python tests/capture_dashboard.py
```

Claude Code가 캡처된 4장의 스크린샷을 view로 확인:
```
[Overview]
□ 마스터 스위치 "RED" 배지
□ 총자산 ~$431,847
□ 4개 메트릭 카드
□ 3개 매크로 지표
□ 보유 종목 테이블 23행
□ Update 버튼 존재
□ 트렌드 차트 없음 (삭제 확인)

[Ticker Detail]
□ 종목 선택 드롭다운
□ 4-panel 기술 차트 렌더링
□ 전략 단계 프로그레스
□ 시그널 이력 테이블

[Market Signals]
□ 마스터 스위치 배너
□ 요약 카드 (경고/관심/매수/홀드)
□ 시그널 카드 with 조건 태그
□ 대부분 HOLD (master RED)

[Technical Signals]
□ 경고 배너 ("시장 상황 무시" 안내)
□ 요약 카드 — Market보다 매수 시그널 많음
□ 시그널 카드 with 조건 태그
□ 마스터 스위치 관련 내용 없음
```

### Phase T5: 전체 통합 Smoke Test
```bash
bash tests/smoke_test.sh
# 1. mock 데이터 로드
# 2. rule engine 실행
# 3. signal generator (full + technical_only)
# 4. signals.json 스키마 확인
# 5. pytest 전체 실행
# 6. Streamlit 기동 + 4페이지 200 OK
# ALL PASSED 출력
```

### 합격 기준
```
[필수 — 전부 통과해야 합격]
✅ pytest 0 failures
✅ 23개 종목 모두 signals.json에 존재 (both modes)
✅ full 모드: master=RED 정확 반영
✅ technical_only 모드: master 무시 확인
✅ technical_only에서 full보다 BUY 시그널 수 >= (같거나 많음)
✅ 대시보드 4페이지 모두 HTTP 200
✅ Update 버튼 존재 확인
✅ 트렌드 차트 삭제 확인

[권장]
☑ 대시보드 스크린샷 시각 검증 통과
☑ 한국어 렌더링 정상
☑ Plotly 차트 렌더링 확인
```

---

## 실행 명령 (Claude Code용)

```
이 프로젝트의 MODIFICATION_PLAN.md를 읽고 M1부터 M6까지 순서대로 수정을 진행해줘.

수정 순서:
1. M3 먼저: test fixture 파일 생성 (data/test_portfolio.json, tests/fixtures/mock_market_data.json)
2. M1: dashboard/style.py + dashboard/components.py 생성
3. M5: signal_generator.py에 mode 파라미터 추가 (full, technical_only)
4. M2: dashboard/app.py 재작성 (Overview — 트렌드 차트 삭제 + Update 버튼)
5. M4: dashboard/pages/1_Ticker_Detail.py 재작성
6. M5 계속: dashboard/pages/2_Market_Signals.py + 3_Technical_Signals.py 작성
7. M6: 테스트 실행 (Phase T1→T5)

각 단계에서 테스트 실패 시 원인 분석 → 코드 수정 → 재테스트 (최대 3회).
test fixture(mock 데이터)를 사용하여 yfinance 없이도 전체 테스트 가능하도록 해줘.
대시보드는 test_portfolio.json + mock_market_data.json으로 테스트 모드 실행.
```
