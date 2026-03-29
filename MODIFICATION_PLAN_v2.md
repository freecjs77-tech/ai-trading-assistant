# AI Trading Assistant — 최종 수정 계획서 (Modification Plan v2.0)

> Claude Code가 이 문서를 읽고 수정 작업을 자율적으로 진행합니다.
> 이전 MODIFICATION_PLAN.md를 대체합니다.
> 수정 완료 후 Phase T(테스트)를 자동 실행하여 검증합니다.
> OCR 관련 테스트는 제외합니다.

---

## 수정 항목 전체 요약

| # | 항목 | 핵심 내용 |
|---|------|----------|
| M1 | 라이트 모드 강제 + Streamlit 기본 위젯 제거 | config.toml 테마 고정, 모든 UI를 st.markdown(HTML)로 직접 렌더링 |
| M2 | 대시보드 공통 디자인 시스템 | dashboard/style.py + dashboard/components.py 생성 |
| M3 | 테스트용 실제 포트폴리오 fixture | data/test_portfolio.json + tests/fixtures/mock_market_data.json |
| M4 | Overview 페이지 전면 재작성 | 트렌드 차트 삭제, Update 버튼, USD/KRW 토글, 듀얼 시그널, 인덱스 |
| M5 | Ticker Detail 페이지 재작성 | 멀티패널 Plotly 기술 차트 + 전략 단계 + 시그널 이력 |
| M6 | Signals 페이지 2개 분리 | Market Signals + Technical Signals, signal_generator에 mode 추가 |
| M7 | 테스트 자동 실행 (OCR 제외) | Phase T1~T5 |

---

## M1: 라이트 모드 강제 + Streamlit 기본 위젯 제거

### 문제 원인
1. Streamlit이 시스템 다크모드를 따라가서 배경이 검정으로 표시됨
2. st.metric(), st.dataframe(), st.container() 등 기본 위젯이 자체 스타일을 강하게 적용하여 커스텀 CSS를 덮어씀
3. 시그널 카드의 border-left, 배지 색상 등이 Streamlit 기본 스타일과 충돌

### 해결 1: 테마 고정 (.streamlit/config.toml)
```toml
[theme]
base = "light"
primaryColor = "#0F6E56"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F8F9FA"
textColor = "#1A1A1A"
font = "sans serif"

[server]
headless = true
```

### 해결 2: Streamlit 기본 위젯 사용 금지 목록
```
❌ 사용하지 말 것:
- st.metric()        → st.markdown(HTML) 으로 메트릭 카드 직접 구현
- st.dataframe()     → st.markdown(HTML table) 으로 테이블 직접 구현
- st.container()     → div 태그로 직접 구현
- st.columns() 내부의 기본 스타일 → 최소한만 사용, 내부는 HTML

✅ 사용 가능:
- st.markdown(unsafe_allow_html=True)  → 모든 UI의 핵심 렌더러
- st.plotly_chart()    → Plotly 차트 (자체 렌더링이라 스타일 충돌 없음)
- st.selectbox()       → 종목 선택 드롭다운 (필요한 곳만)
- st.button()          → Update 버튼 (기능 트리거용)
- st.spinner()         → 로딩 표시
- st.set_page_config() → 페이지 설정
- st.sidebar           → 사이드바 (필요시)
```

### 해결 3: Streamlit 기본 스타일 오버라이드 CSS
```css
/* dashboard/style.py의 CUSTOM_CSS에 추가 */

/* Streamlit 기본 여백/패딩 제거 */
.main .block-container {
    max-width: 900px;
    padding: 1rem 1rem 2rem 1rem;
}

/* Streamlit 기본 헤더 숨김 */
header[data-testid="stHeader"] {
    display: none;
}

/* Streamlit 기본 metric 위젯 스타일 무력화 (혹시 남아있을 경우) */
div[data-testid="stMetricValue"] {
    font-size: 18px !important;
    font-weight: 500 !important;
}

/* Streamlit expander 기본 스타일 오버라이드 */
.streamlit-expanderHeader {
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* footer 숨김 */
footer { display: none; }
```

---

## M2: 대시보드 공통 디자인 시스템

### dashboard/style.py
```python
"""공통 CSS — 모든 페이지에서 inject_css() 호출"""
import streamlit as st

CUSTOM_CSS = """
<style>
/* ── Layout ── */
.main .block-container { max-width: 900px; padding: 1rem 1rem 2rem 1rem; }
header[data-testid="stHeader"] { display: none; }
footer { display: none; }

/* ── Metric cards ── */
.metric-card {
    background: #F8F9FA; border-radius: 8px; padding: 10px 12px;
}
.metric-card .label { font-size: 10px; color: #888780; }
.metric-card .value { font-size: 18px; font-weight: 500; color: #1A1A1A; margin-top: 1px; }
.metric-card .change { font-size: 10px; margin-top: 1px; }

/* ── Macro indicator cards ── */
.macro-card {
    background: #F8F9FA; border-radius: 8px; padding: 8px; text-align: center;
}
.macro-card .label { font-size: 10px; color: #888780; }
.macro-card .value { font-size: 13px; font-weight: 500; margin: 1px 0; }
.macro-card .status { font-size: 10px; }

/* ── Signal cards ── */
.signal-card {
    background: #FFFFFF; border: 0.5px solid #E0E0E0;
    border-radius: 10px; padding: 10px; margin-bottom: 6px;
}
.signal-card-warn { border-left: 3px solid #A32D2D; border-radius: 0; }
.signal-card-watch { border-left: 3px solid #BA7517; border-radius: 0; }
.signal-card-buy { border-left: 3px solid #0F6E56; border-radius: 0; }
.signal-card-hold { border-left: 3px solid #888780; border-radius: 0; }

/* ── Badges / Pills ── */
.pill {
    display: inline-block; font-size: 9px; padding: 2px 6px;
    border-radius: 6px; font-weight: 500; margin-left: 4px;
}
.pill-sell { background: #FCEBEB; color: #791F1F; }
.pill-buy { background: #EAF3DE; color: #27500A; }
.pill-hold { background: #F1EFE8; color: #5F5E5A; }
.pill-wait { background: #FAEEDA; color: #633806; }
.pill-bond { background: #E1F5EE; color: #085041; }
.pill-block { background: #EEEDFE; color: #3C3489; }
.pill-top { background: #FCEBEB; color: #791F1F; border: 0.5px solid #F09595; }

/* ── Master switch badges ── */
.switch-badge {
    display: inline-block; font-size: 11px; padding: 3px 10px; border-radius: 8px;
}
.switch-red { background: #FCEBEB; color: #791F1F; }
.switch-green { background: #EAF3DE; color: #27500A; }
.switch-yellow { background: #FAEEDA; color: #633806; }

/* ── Condition tags ── */
.cond-tag {
    display: inline-block; font-size: 9px; padding: 2px 6px;
    border-radius: 4px; margin: 2px;
}
.cond-met { background: #EAF3DE; color: #27500A; }
.cond-not { background: #F0F0F0; color: #999; }

/* ── Confidence bar ── */
.conf-bar {
    height: 4px; border-radius: 2px; background: #E0E0E0;
    display: inline-block; width: 60px; vertical-align: middle; margin-right: 4px;
}
.conf-fill { height: 4px; border-radius: 2px; display: block; }

/* ── Holdings table ── */
.holdings-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.holdings-table th {
    text-align: left; padding: 7px 5px; color: #888780;
    font-weight: 400; border-bottom: 0.5px solid #E0E0E0; font-size: 10px;
}
.holdings-table td { padding: 7px 5px; border-bottom: 0.5px solid #E0E0E0; }
.tk { font-weight: 500; font-size: 12px; }
.nm { color: #888780; font-size: 10px; }

/* ── Weight bar ── */
.bar-bg {
    height: 5px; border-radius: 3px; background: #E0E0E0;
    width: 60px; display: inline-block; vertical-align: middle;
}
.bar-fill { height: 5px; border-radius: 3px; display: block; }

/* ── Currency toggle ── */
.toggle-grp {
    display: inline-flex; background: #F8F9FA; border-radius: 8px; padding: 2px;
    font-size: 11px;
}
.toggle-grp .opt {
    padding: 4px 12px; border-radius: 6px; cursor: pointer; color: #888780;
}
.toggle-grp .opt.on {
    background: #FFFFFF; color: #1A1A1A; font-weight: 500;
}

/* ── Strategy progress ── */
.step-done { background: #EAF3DE; color: #27500A; }
.step-cur { background: #FAEEDA; color: #633806; }
.step-lock { background: #F0F0F0; color: #999; }

/* ── Colors ── */
.up { color: #0F6E56; }
.dn { color: #A32D2D; }

/* ── Rate label ── */
.rate-label { font-size: 10px; color: #888780; text-align: right; margin-bottom: 10px; }

/* ── Section header ── */
.section-hdr { font-size: 16px; font-weight: 500; margin-bottom: 10px; color: #1A1A1A; }

/* ── Separator ── */
.sep { border: none; border-top: 0.5px solid #E0E0E0; margin: 14px 0; }

/* ── Index section ── */
.idx-grid {
    display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px;
}
.idx-item {
    display: flex; gap: 8px; padding: 8px 10px;
    border-radius: 8px; background: #F8F9FA;
}
.idx-name { font-size: 11px; font-weight: 500; color: #1A1A1A; }
.idx-desc { font-size: 10px; color: #888780; line-height: 1.4; margin-top: 1px; }
</style>
"""

def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
```

### dashboard/components.py
```python
"""재사용 HTML 컴포넌트 — 모든 페이지에서 import하여 사용"""

def metric_card(label, value, change="", change_class=""):
    ch = f'<div class="change {change_class}">{change}</div>' if change else ""
    return f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value}</div>{ch}</div>'

def signal_card(ticker, action, confidence, rationale, conds_met=[], conds_not=[], card_class=""):
    pill_map = {"L1_WARNING":"pill-sell","L2_WARNING":"pill-sell","L3_BREAKDOWN":"pill-sell",
        "TRANCHE_1_BUY":"pill-buy","TRANCHE_2_BUY":"pill-buy","TRANCHE_3_BUY":"pill-buy",
        "HOLD":"pill-hold","WATCH":"pill-wait","BOND_WATCH":"pill-bond","BLOCKED":"pill-block",
        "CASH":"pill-hold","TOP_SIGNAL":"pill-top"}
    pc = pill_map.get(action,"pill-hold")
    conf_c = "#A32D2D" if "WARNING" in action or "BREAKDOWN" in action or "TOP" in action else (
        "#0F6E56" if "BUY" in action else "#BA7517")
    tags = "".join(f'<span class="cond-tag cond-met">{c}</span>' for c in conds_met)
    tags += "".join(f'<span class="cond-tag cond-not">{c}</span>' for c in conds_not)
    label = action.replace("_"," ")
    return f'''<div class="signal-card {card_class}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
            <span style="font-weight:500;font-size:13px">{ticker} <span class="pill {pc}">{label}</span></span>
            <span style="font-size:10px;color:#888"><span class="conf-bar"><span class="conf-fill" style="width:{confidence}%;background:{conf_c}"></span></span>{confidence}%</span>
        </div>
        <div style="font-size:11px;color:#666;line-height:1.5">{rationale}</div>
        {"<div style='margin-top:6px'>"+tags+"</div>" if tags else ""}
    </div>'''

def master_switch_banner(status, qqq_price, qqq_ma200, spy_price, spy_ma200, vix):
    cls = {"RED":"switch-red","GREEN":"switch-green","YELLOW":"switch-yellow"}[status]
    border_c = {"RED":"#A32D2D","GREEN":"#0F6E56","YELLOW":"#BA7517"}[status]
    return f'''<div class="signal-card" style="border-left:3px solid {border_c};border-radius:0">
        <div style="font-weight:500;font-size:14px;margin-bottom:6px">
            Master switch: <span class="switch-badge {cls}">{status}</span></div>
        <div style="font-size:12px;color:#666">
            QQQ ${qqq_price:,.0f} vs MA200 ${qqq_ma200:,.0f} •
            SPY ${spy_price:,.0f} vs MA200 ${spy_ma200:,.0f} •
            VIX {vix:.1f}</div>
    </div>'''

def format_krw(usd_amount, rate):
    """USD 금액을 한국식 원화 표기로 변환"""
    krw = usd_amount * rate
    if abs(krw) >= 100_000_000:
        return f"₩{krw/100_000_000:.2f}억"
    elif abs(krw) >= 10_000_000:
        return f"₩{krw/10_000:,.0f}만"
    elif abs(krw) >= 1_000_000:
        return f"₩{krw/10_000:,.0f}만"
    else:
        return f"₩{krw:,.0f}"

def signal_index_html():
    """Overview 하단 시그널 인덱스 레퍼런스 패널"""
    return '''
    <div style="padding-top:14px;border-top:0.5px solid #E0E0E0;margin-top:14px">
    <div style="font-size:14px;font-weight:500;margin-bottom:10px">Signal reference</div>

    <div style="font-size:12px;font-weight:500;color:#888;margin:10px 0 6px">Entry signals</div>
    <div class="idx-grid">
        <div class="idx-item"><div><span class="pill pill-buy">1st BUY</span></div><div><div class="idx-name">1st tranche (20%)</div><div class="idx-desc">MACD hist 상승 + RSI/BB/MA 조건. 정찰 매수.</div></div></div>
        <div class="idx-item"><div><span class="pill pill-buy">2nd BUY</span></div><div><div class="idx-name">2nd tranche (30%)</div><div class="idx-desc">이중바닥 + MACD 골든크로스. 본격 비중 확대.</div></div></div>
        <div class="idx-item"><div><span class="pill pill-buy">3rd BUY</span></div><div><div class="idx-name">3rd tranche (50%)</div><div class="idx-desc">MA20 돌파 + MACD 0선. 추세 전환 확인.</div></div></div>
        <div class="idx-item"><div><span class="pill pill-bond">BOND</span></div><div><div class="idx-name">Bond/gold entry</div><div class="idx-desc">30Y 금리 5.0% 또는 GLD 조건. 마스터 독립.</div></div></div>
    </div>

    <div style="font-size:12px;font-weight:500;color:#888;margin:10px 0 6px">Hold / watch</div>
    <div class="idx-grid">
        <div class="idx-item"><div><span class="pill pill-hold">HOLD</span></div><div><div class="idx-name">Position maintained</div><div class="idx-desc">특이 신호 없음. 현 포지션 유지.</div></div></div>
        <div class="idx-item"><div><span class="pill pill-wait">WATCH</span></div><div><div class="idx-name">Entry approaching</div><div class="idx-desc">진입 조건 근접 중. 아직 미충족.</div></div></div>
        <div class="idx-item"><div><span class="pill pill-block">BLOCKED</span></div><div><div class="idx-name">Master switch block</div><div class="idx-desc">기술적 조건 충족이나 마스터 RED로 차단.</div></div></div>
        <div class="idx-item"><div><span class="pill pill-hold">CASH</span></div><div><div class="idx-name">Cash equivalent</div><div class="idx-desc">BIL 등 현금성. 시장 하락 방어.</div></div></div>
    </div>

    <div style="font-size:12px;font-weight:500;color:#888;margin:10px 0 6px">Exit signals (escalation)</div>
    <div class="idx-grid">
        <div class="idx-item"><div><span class="pill pill-sell">L1 WARN</span></div><div><div class="idx-name">Early warning</div><div class="idx-desc">MACD 둔화 + RSI 꺾임. 매수 중단.</div></div></div>
        <div class="idx-item"><div><span class="pill pill-sell">L2 WEAK</span></div><div><div class="idx-name">Trend weakening</div><div class="idx-desc">MACD 3d 하락 + MA20 이탈. 30% 트림.</div></div></div>
        <div class="idx-item"><div><span class="pill pill-sell">L3 EXIT</span></div><div><div class="idx-name">Trend breakdown</div><div class="idx-desc">MA20 2d 이탈 또는 -8%. 전량 매도.</div></div></div>
        <div class="idx-item"><div><span class="pill pill-top">TOP</span></div><div><div class="idx-name">Overheated</div><div class="idx-desc">RSI 75+ 또는 3d +10%. 강제 익절.</div></div></div>
    </div>

    <div style="font-size:12px;font-weight:500;color:#888;margin:10px 0 6px">Master switch / confidence</div>
    <div style="display:flex;gap:6px;margin-bottom:8px">
        <div style="flex:1;padding:6px 8px;border-radius:8px;text-align:center;background:#EAF3DE"><div style="font-size:10px;font-weight:500;color:#27500A">GREEN</div><div style="font-size:9px;color:#3B6D11">전 전략 가동</div></div>
        <div style="flex:1;padding:6px 8px;border-radius:8px;text-align:center;background:#FAEEDA"><div style="font-size:10px;font-weight:500;color:#633806">YELLOW</div><div style="font-size:9px;color:#854F0B">1차만 허용</div></div>
        <div style="flex:1;padding:6px 8px;border-radius:8px;text-align:center;background:#FCEBEB"><div style="font-size:10px;font-weight:500;color:#791F1F">RED</div><div style="font-size:9px;color:#A32D2D">매수 전면 금지</div></div>
    </div>
    <div style="font-size:10px;color:#888;margin:3px 0;display:flex;align-items:center;gap:5px"><span class="conf-bar" style="width:60px"><span class="conf-fill" style="width:85%;background:#0F6E56"></span></span> 80-100%: 높은 확신</div>
    <div style="font-size:10px;color:#888;margin:3px 0;display:flex;align-items:center;gap:5px"><span class="conf-bar" style="width:60px"><span class="conf-fill" style="width:55%;background:#BA7517"></span></span> 50-79%: 중간 확신</div>
    <div style="font-size:10px;color:#888;margin:3px 0;display:flex;align-items:center;gap:5px"><span class="conf-bar" style="width:60px"><span class="conf-fill" style="width:25%;background:#A32D2D"></span></span> 0-49%: 주의 필요</div>
    </div>'''
```

---

## M3: 테스트용 실제 포트폴리오 fixture

### data/test_portfolio.json
23개 종목 실제 데이터 (2026-03-28 토스증권 스크린샷 기준).
이전 MODIFICATION_PLAN.md의 M3 섹션과 동일. 그대로 사용.

### tests/fixtures/mock_market_data.json
23개 종목 + 매크로 지표 mock 데이터.
이전 MODIFICATION_PLAN.md의 M3 섹션과 동일. 그대로 사용.

---

## M4: Overview 페이지 전면 재작성 (dashboard/app.py)

### 페이지 구조 (위에서 아래 순서)
```
┌─────────────────────────────────────────────────────┐
│ Portfolio dashboard          Master:RED [USD/KRW] [Update] │
│ 2026-03-28 07:00 KST                                │
│ (KRW 선택시) 1 USD = ₩1,425.50 (2026-03-28)        │
├─────────────────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│ │Total   │ │Daily   │ │Total   │ │YTD     │       │
│ │₩6.16억 │ │-₩603만 │ │+₩7,390만│ │₩263만  │       │
│ └────────┘ └────────┘ └────────┘ └────────┘       │
├─────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│ │QQQ<MA200 │ │30Y 4.98% │ │VIX 30.9  │            │
│ └──────────┘ └──────────┘ └──────────┘            │
├─────────────────────────────────────────────────────┤
│ Holdings (23)                                       │
│ ┌──────┬───────┬──────┬──────┬────────┬──────────┐ │
│ │Ticker│Value  │Weight│Return│Market  │Technical │ │
│ ├──────┼───────┼──────┼──────┼────────┼──────────┤ │
│ │VOO   │₩1.46억│23.6% │+13.4%│HOLD    │WATCH     │ │
│ │BIL   │₩1.31억│21.2% │+10.5%│CASH    │HOLD      │ │
│ │...   │...    │...   │...   │...     │...       │ │
│ └──────┴───────┴──────┴──────┴────────┴──────────┘ │
├─────────────────────────────────────────────────────┤
│  [M] Market signals     │  [T] Technical signals    │
│  2 warn / 1 watch /     │  2 warn / 3 watch /       │
│  0 buy / 20 hold        │  2 buy / 16 hold          │
│                         │                           │
│  TSLA L1 WARN 72%      │  TLT 1st BUY 78%          │
│  ETHU L2 WEAK 81%      │  SLV 1st BUY 70%          │
│  TLT BOND WATCH 65%    │  TSLA L1 WARN 72%         │
│                         │  NVDA WATCH 55%            │
├─────────────────────────────────────────────────────┤
│ Signal reference                                     │
│ [Entry] 1st BUY / 2nd BUY / 3rd BUY / BOND         │
│ [Hold]  HOLD / WATCH / BLOCKED / CASH               │
│ [Exit]  L1 WARN / L2 WEAK / L3 EXIT / TOP          │
│ [Master] GREEN / YELLOW / RED                        │
│ [Confidence] 80-100% / 50-79% / 0-49%              │
└─────────────────────────────────────────────────────┘
```

### USD/KRW 토글 구현 (Streamlit)
```python
# st.session_state로 통화 상태 관리
if "currency" not in st.session_state:
    st.session_state.currency = "USD"

# 헤더에 토글 배치
col_title, col_controls = st.columns([3, 2])
with col_controls:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.markdown(master_switch_badge_html, unsafe_allow_html=True)
    with c2:
        currency = st.radio("", ["USD", "KRW"], horizontal=True,
                           index=0 if st.session_state.currency=="USD" else 1,
                           label_visibility="collapsed")
        st.session_state.currency = currency
    with c3:
        if st.button("Update"):
            run_update_pipeline()
            st.rerun()

# KRW 선택시 환율 표시
if st.session_state.currency == "KRW":
    rate = market_data["macro"]["usdkrw"]  # yfinance USDKRW=X
    st.markdown(f'<div class="rate-label">1 USD = ₩{rate:,.2f}</div>', unsafe_allow_html=True)

# 금액 표시 함수
def display_value(usd_amount):
    if st.session_state.currency == "KRW":
        return format_krw(usd_amount, rate)
    else:
        return f"${usd_amount:,.0f}" if usd_amount >= 1000 else f"${usd_amount:,.2f}"
```

### 보유 종목 테이블: Market + Technical 듀얼 시그널 컬럼
```python
# holdings 테이블 HTML 생성
def holdings_table_html(holdings, market_signals, tech_signals, display_fn):
    rows = ""
    for h in sorted(holdings, key=lambda x: x["value_usd"], reverse=True):
        ticker = h["ticker"]
        ms = market_signals.get(ticker, {"action": "HOLD"})
        ts = tech_signals.get(ticker, {"action": "HOLD"})
        weight = h["value_usd"] / portfolio["total_value_usd"] * 100
        bar_w = min(weight / 25 * 100, 100)  # 25%를 100%로 스케일
        bar_c = "#0F6E56" if h["pnl_pct"] >= 0 else "#A32D2D"
        pnl_cls = "up" if h["pnl_pct"] >= 0 else "dn"
        ms_pill = pill_html(ms["action"])
        ts_pill = pill_html(ts["action"])

        rows += f'''<tr>
            <td><span class="tk">{ticker}</span><br><span class="nm">{h["name"]}</span></td>
            <td style="text-align:right">{display_fn(h["value_usd"])}</td>
            <td style="text-align:right">{weight:.1f}%<br>
                <span class="bar-bg"><span class="bar-fill" style="width:{bar_w}%;background:{bar_c}"></span></span></td>
            <td style="text-align:right" class="{pnl_cls}">{h["pnl_pct"]:+.1f}%</td>
            <td style="text-align:center">{ms_pill}</td>
            <td style="text-align:center">{ts_pill}</td>
        </tr>'''

    return f'''<table class="holdings-table">
        <thead><tr>
            <th>Ticker</th>
            <th style="text-align:right">Value</th>
            <th style="text-align:right">Weight</th>
            <th style="text-align:right">Return</th>
            <th style="text-align:center">Market</th>
            <th style="text-align:center">Technical</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>'''
```

### 듀얼 시그널 섹션 (좌우 2열)
```python
# Overview 하단: Market vs Technical 시그널 나란히
col_m, col_t = st.columns(2)

with col_m:
    st.markdown('''<h3 style="font-size:13px;font-weight:500;display:flex;align-items:center;gap:6px">
        <span class="switch-badge switch-red" style="font-size:10px;padding:2px 8px">M</span>
        Market signals</h3>''', unsafe_allow_html=True)
    # 시그널 요약 카운트
    # 경고/관심/매수/홀드 시그널 카드들

with col_t:
    st.markdown('''<h3 style="font-size:13px;font-weight:500;display:flex;align-items:center;gap:6px">
        <span style="display:inline-block;font-size:10px;padding:2px 8px;border-radius:6px;background:#E6F1FB;color:#0C447C">T</span>
        Technical signals</h3>''', unsafe_allow_html=True)
    # Technical 모드에서는 BUY 시그널이 더 많이 나타남

# 하단: Signal reference 인덱스
st.markdown(signal_index_html(), unsafe_allow_html=True)
```

---

## M5: Ticker Detail 페이지 (dashboard/pages/1_Ticker_Detail.py)

이전 MODIFICATION_PLAN.md의 M4 섹션과 동일. 변경 없음.
추가 사항: Plotly 차트도 라이트 모드 고정 (plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF').

```python
fig.update_layout(
    plot_bgcolor='#FFFFFF',
    paper_bgcolor='#FFFFFF',
    font_color='#1A1A1A',
    ...
)
```

---

## M6: Signals 페이지 2개 분리

이전 MODIFICATION_PLAN.md의 M5 섹션과 동일. 변경 없음.
추가 사항:
- 두 페이지 모두 라이트 모드 CSS 적용 (inject_css() 호출)
- Streamlit 기본 위젯 대신 st.markdown(HTML)로 시그널 카드 렌더링
- Technical Signals 페이지 상단 경고 배너도 HTML로 직접 작성 (st.warning() 사용 금지)

```python
# st.warning() 대신:
st.markdown('''
<div style="background:#FFF3CD;border:0.5px solid #FFEEBA;border-radius:8px;padding:12px 16px;margin-bottom:16px">
    <div style="font-size:13px;font-weight:500;color:#856404;margin-bottom:4px">
        ⚠ 시장 상황 무시 분석</div>
    <div style="font-size:12px;color:#856404;line-height:1.5">
        이 페이지는 마스터 스위치, VIX, 금리를 무시하고 순수 기술지표(RSI·MACD·MA·BB)만으로 분석한 결과입니다.<br>
        실제 매매 시에는 반드시 Market Signals 페이지를 함께 확인하세요.</div>
</div>''', unsafe_allow_html=True)
```

---

## M7: 테스트 (OCR 제외)

이전 MODIFICATION_PLAN.md의 M6 섹션과 동일. 변경 없음.
추가 테스트 항목:

### Phase T0: 테마 검증 (신규)
```bash
# .streamlit/config.toml 존재 확인
cat .streamlit/config.toml | grep "base = \"light\""

# 검증: "light" 테마 설정 존재
# 실패 시: config.toml 생성/수정
```

### Phase T4 대시보드 시각 검증: 추가 체크 항목
```
[전체 페이지 공통 — 신규]
□ 배경이 흰색 (#FFFFFF)
□ 텍스트가 검정 (#1A1A1A)
□ 다크모드 잔재 없음 (검정 배경, 회색 카드 없음)
□ Streamlit 기본 메트릭 위젯 미사용 확인
□ 시그널 카드 border-left 색상 정상 표시

[Overview 신규]
□ USD/KRW 토글 존재
□ KRW 모드에서 "₩6.16억" 형식 표시
□ 환율 라벨 "1 USD = ₩1,425.50" 표시
□ 보유 테이블에 Market + Technical 2개 시그널 컬럼
□ 하단 Signal reference 인덱스 존재
□ 듀얼 시그널 섹션 (좌: Market, 우: Technical)
□ Market 시그널: 대부분 HOLD (master RED)
□ Technical 시그널: BUY/WATCH 시그널 존재 (master 무시)
□ Update 버튼 존재
□ 트렌드 차트 없음 (삭제 확인)
```

---

## 실행 순서 (Claude Code용)

```
이 프로젝트의 MODIFICATION_PLAN_v2.md를 읽고 아래 순서로 수정을 진행해줘.

1. M1 먼저: .streamlit/config.toml 생성 (라이트 모드 고정)
2. M3: test fixture 파일 생성 (이미 있으면 확인만)
3. M2: dashboard/style.py + dashboard/components.py 생성
4. M6의 signal_generator.py 수정: mode 파라미터 추가 (full, technical_only)
5. M4: dashboard/app.py 전면 재작성 (Overview — 모든 UI를 st.markdown HTML로)
6. M5: dashboard/pages/1_Ticker_Detail.py 재작성
7. M6 계속: dashboard/pages/2_Market_Signals.py + 3_Technical_Signals.py 작성
8. M7: 테스트 실행 (Phase T0→T5)

핵심 원칙:
- st.metric(), st.dataframe(), st.container(), st.warning() 사용 금지
- 모든 UI는 st.markdown(unsafe_allow_html=True)로 HTML 직접 렌더링
- Plotly 차트만 st.plotly_chart() 사용 허용
- 모든 색상은 style.py의 디자인 시스템 색상 사용
- 라이트 모드 전용 (다크모드 고려 불필요)
- test fixture(mock 데이터)로 yfinance 없이 전체 테스트 가능하도록

각 단계에서 테스트 실패 시 원인 분석 → 코드 수정 → 재테스트 (최대 3회).
```
