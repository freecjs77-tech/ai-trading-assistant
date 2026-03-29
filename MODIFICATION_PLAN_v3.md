# AI Trading Assistant — 최종 수정 계획서 (Modification Plan v3.0)

> **이 문서 하나가 모든 수정 사항의 Single Source of Truth입니다.**
> 이전 v2.0, Addendum, VISUAL_FIX_GUIDE를 모두 통합했습니다.
> Claude Code는 이 문서 + docs/design_reference/overview_target.html을 참조하여 수정합니다.
> OCR 관련 테스트는 제외합니다.

---

## 수정 항목 전체 요약

| # | 항목 | 핵심 내용 | 대상 파일 |
|---|------|----------|----------|
| M1 | 라이트 모드 + 기본 위젯 제거 | config.toml, st.markdown(HTML) 전환 | .streamlit/config.toml |
| M2 | 공통 디자인 시스템 | CSS/컴포넌트 통일 | dashboard/style.py, components.py |
| M3 | 테스트 fixture | 23개 종목 + mock 시장 데이터 | data/test_portfolio.json, tests/fixtures/ |
| M4 | 시그널 로직 수정 (Critical) | exit 과다 판정 + Market/Technical 분리 | src/rule_engine.py, signal_generator.py |
| M5 | Portfolio Management (신규) | 수량/단가 편집, 삭제, OCR 연동 | dashboard/pages/1_Portfolio_Management.py |
| M6 | Overview 전면 재작성 | 듀얼 시그널, USD/KRW, 인덱스, M5 참조 | dashboard/app.py |
| M7 | Ticker Detail 재작성 | 4단 Plotly + 전략 단계 | dashboard/pages/2_Ticker_Detail.py |
| M8 | Signals 2개 분리 | Market + Technical | pages/3_Market_Signals.py, 4_Technical_Signals.py |
| M9 | 사이드바 정리 | 5페이지만, 설정 제거, app→Overview | dashboard/pages/ |
| M10 | 테스트 (OCR 제외) | Phase T0~T5 | tests/ |

---

## M1: 라이트 모드 강제 + Streamlit 기본 위젯 제거

### 문제
1. Streamlit이 시스템 다크모드를 따라가서 배경이 검정으로 표시
2. st.metric() 등 기본 위젯이 자체 스타일을 강제하여 커스텀 CSS를 덮어씀
3. 시그널 카드 border-left, 배지 색상이 Streamlit 기본 스타일과 충돌

### .streamlit/config.toml 생성
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

### Streamlit 위젯 사용 규칙
```
❌ 사용 금지 (자체 스타일이 커스텀 CSS를 덮어씀):
  st.metric()       → st.markdown(HTML)로 메트릭 카드 직접 구현
  st.dataframe()    → st.markdown(HTML table)로 직접 구현
  st.container()    → div 태그로 직접 구현
  st.warning()      → HTML div로 직접 구현
  st.info()         → HTML div로 직접 구현
  st.success()      → HTML div로 직접 구현

✅ 사용 가능:
  st.markdown(unsafe_allow_html=True) → 핵심 렌더러
  st.plotly_chart()    → Plotly 차트 (Ticker Detail)
  st.selectbox()       → 종목 선택 드롭다운
  st.button()          → Update, Save 등 버튼
  st.number_input()    → Portfolio Management 편집 필드
  st.radio()           → USD/KRW 토글 (label_visibility="collapsed")
  st.spinner()         → 로딩 표시
  st.set_page_config() → 페이지 설정
  st.columns()         → 레이아웃 (내부는 HTML로)
  st.session_state     → 상태 관리
```

### Streamlit 기본 스타일 오버라이드 CSS (style.py에 포함)
```css
.main .block-container { max-width: 900px; padding: 1rem 1rem 2rem 1rem; }
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
```

---

## M2: 공통 디자인 시스템

### dashboard/style.py
**overview_target.html의 CSS를 그대로 복사하여 CUSTOM_CSS 변수에 저장.**
모든 페이지에서 inject_css()를 호출.

핵심 색상:
```
카드 배경:    #F8F9FA (border 없음, border-radius: 8px)
상승:         #0F6E56 (teal)
하락:         #A32D2D (red)
경고/대기:    #BA7517 (amber)
채권:         #085041 (dark teal), 배지 배경 #E1F5EE
차단:         #3C3489 (purple), 배지 배경 #EEEDFE
구분선:       0.5px solid #E0E0E0
텍스트 기본:  #1A1A1A
텍스트 보조:  #888780
```

시그널 배지 (pill) 색상:
```
pill-sell:   bg #FCEBEB, text #791F1F  (L1/L2/L3/TOP)
pill-buy:    bg #EAF3DE, text #27500A  (1st/2nd/3rd BUY)
pill-hold:   bg #F1EFE8, text #5F5E5A  (HOLD, CASH)
pill-wait:   bg #FAEEDA, text #633806  (WATCH)
pill-bond:   bg #E1F5EE, text #085041  (BOND WATCH)
pill-block:  bg #EEEDFE, text #3C3489  (BLOCKED)
pill-top:    bg #FCEBEB, text #791F1F, border 0.5px #F09595 (TOP SIGNAL)
```

### dashboard/components.py
재사용 함수:
- metric_card(), signal_card(), master_switch_banner()
- format_krw(), pill_html(), signal_index_html(), holdings_table_html()

**중요: overview_target.html을 열어서 CSS와 HTML 구조를 직접 확인하고 동일하게 구현.**

---

## M3: 테스트 fixture

### data/test_portfolio.json
23개 종목, 2026-03-28 토스증권 기준. avg_cost 포함.
(전체 JSON은 이 계획서 말미의 [부록 A]에 수록)

### tests/fixtures/mock_market_data.json
23개 종목 + 매크로 지표 mock 데이터.
마스터: RED (QQQ $587 < MA200 $592, SPY $645 < MA200 $657), VIX 30.91, 30Y 4.982%.
(전체 JSON은 이 계획서 말미의 [부록 B]에 수록)

---

## M4: 시그널 로직 수정 (Critical)

### 문제 1: 거의 모든 종목이 L3 BREAKDOWN
exit 조건이 너무 공격적. "MA20 아래 + MACD 음수"만으로 L3를 트리거하면 안 됨.
Exit L3는 "MA20 아래 2일 회복 없음 + 상승 저점 붕괴 + MACD 데스크로스 + 고점 -8%" 중 **1개라도** 충족 시에만 발동.
히스토리 없이 단일 시점 데이터만으로는 L3 판정 불가 → HOLD로 처리.

### 문제 2: Market vs Technical 동일값
signal_generator.py의 mode 분기가 미작동.

### 수정 기준 (EXPECTED — pytest에서 이 값과 일치해야 합격)
```python
EXPECTED_MARKET_SIGNALS = {
    "VOO": "HOLD",       "BIL": "CASH",        "QQQ": "HOLD",
    "SCHD": "HOLD",      "AAPL": "HOLD",       "O": "HOLD",
    "JEPI": "HOLD",      "SOXX": "HOLD",       "TSLA": "L1_WARNING",
    "TLT": "BOND_WATCH", "NVDA": "HOLD",       "PLTR": "HOLD",
    "SPY": "HOLD",       "UNH": "HOLD",        "MSFT": "HOLD",
    "GOOGL": "HOLD",     "AMZN": "HOLD",       "SLV": "HOLD",
    "TQQQ": "HOLD",      "SOXL": "HOLD",       "ETHU": "L2_WARNING",
    "CRCL": "HOLD",      "BTDR": "HOLD"
}

EXPECTED_TECH_SIGNALS = {
    "VOO": "WATCH",      "BIL": "HOLD",        "QQQ": "WATCH",
    "SCHD": "HOLD",      "AAPL": "HOLD",       "O": "HOLD",
    "JEPI": "HOLD",      "SOXX": "WATCH",      "TSLA": "L1_WARNING",
    "TLT": "TRANCHE_1_BUY", "NVDA": "WATCH",   "PLTR": "HOLD",
    "SPY": "HOLD",       "UNH": "HOLD",        "MSFT": "HOLD",
    "GOOGL": "HOLD",     "AMZN": "HOLD",       "SLV": "TRANCHE_1_BUY",
    "TQQQ": "HOLD",      "SOXL": "WATCH",      "ETHU": "L2_WARNING",
    "CRCL": "HOLD",      "BTDR": "HOLD"
}
```

### signal_generator.py mode 분기
```python
def generate_signals(portfolio, market_data, mode="full"):
    if mode == "full":
        master = market_data["master_switch"]["status"]
        vix_mult = market_data["macro"]["vix_multiplier"]
    elif mode == "technical_only":
        master = "GREEN"   # 마스터 강제 GREEN 취급
        vix_mult = 1.0     # VIX 오버라이드 무시
```

---

## M5: Portfolio Management 페이지 (신규)

### 파일: dashboard/pages/1_Portfolio_Management.py

### 데이터 흐름
```
Telegram OCR → portfolio.json 업데이트 → Portfolio Management 자동 반영
                                         ↓ 사용자 편집 (수량/단가/삭제)
                                         ↓ Save 클릭 → portfolio.json 저장
                                         ↓
Overview (Update 버튼) → portfolio.json 참조 → 시그널 재생성
```

### 페이지 구조
- 헤더: "Portfolio management" + [Discard] [Save changes] 버튼
- 데이터 흐름: [Telegram OCR] → [This page] → [Overview] (시각적 플로우)
- 동기 상태: "Last sync: 2026-03-28 06:22 KST (23/23 matched)" 배너
- 메트릭 3개: Holdings 수, Total value, Cost basis
- 편집 테이블: #, Ticker(+이름), Class, Shares(편집), Avg cost(편집), Current(자동), Value(자동), Return, × 삭제
- 편집된 필드: 노란색 하이라이트 + "edited" 태그
- 삭제된 행: 빨간 배경 + 취소선 + Undo 버튼
- 하단: 사용법 설명 (Telegram OCR / Manual edit / Delete / Save)

### 핵심 구현
- 편집: st.number_input()으로 Shares, Avg cost 수정. st.session_state.edits에 저장
- 삭제: × 버튼 → st.session_state.deletions에 추가. Save 전까지 Undo 가능
- Save: portfolio.json에 반영 후 저장. Overview의 Update가 이 파일 참조
- Current: yfinance 또는 market_cache.json. 편집 불가
- Value = Shares × Current (자동 계산)

---

## M6: Overview 전면 재작성

### 정답 참조: docs/design_reference/overview_target.html

핵심 변경:
1. 트렌드 차트 삭제
2. Update 버튼: portfolio.json(M5에서 관리) 참조 → yfinance → 시그널 재생성
3. USD/KRW 토글 (yfinance USDKRW=X, 한국식 "1.46억", "1,390만")
4. 메트릭 카드: #F8F9FA 배경, border 없음
5. 매크로 지표: #F8F9FA, 가운데 정렬
6. 보유 테이블: Market + Technical 듀얼 시그널 컬럼, 종목명 서브타이틀
7. 듀얼 시그널 섹션: 좌 [M] Market / 우 [T] Technical
8. Signal reference 인덱스: 페이지 최하단
9. 날짜: "2026-03-28 07:00 KST" (ISO raw 금지)

**overview_target.html을 브라우저로 열어서 CSS, 색상, 간격을 동일하게 재현.**

---

## M7: Ticker Detail 재작성

### 파일: dashboard/pages/2_Ticker_Detail.py

Plotly make_subplots(rows=4, shared_xaxes=True):
- Row 1 (55%): 가격 + MA20(점선 #85B7EB) + MA50(점선 #D3D1C7) + BB(음영) + 매수 마커
- Row 2 (15%): RSI(14, #534AB7) + 70/30 기준선
- Row 3 (15%): MACD 히스토그램 + MACD(#378ADD)/Signal(#D85A30 점선)
- Row 4 (15%): 거래량 바

라이트 모드: plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF', font_color='#1A1A1A'
상단: 종목 선택 + 분류 배지 + 현재가 + 수익률
하단: 전략 프로그레스(1차/2차/3차) + 시그널 이력 테이블(최근 7일)

---

## M8: Signals 2페이지 분리

### dashboard/pages/3_Market_Signals.py
마스터 + VIX + 매크로 반영. signal_generator(mode="full").

### dashboard/pages/4_Technical_Signals.py
마스터 무시, 순수 기술지표. signal_generator(mode="technical_only").

경고 배너 (st.warning 금지, HTML로):
```html
<div style="background:#FFF3CD;border:0.5px solid #FFEEBA;border-radius:8px;padding:12px 16px;margin-bottom:16px">
  <div style="font-size:13px;font-weight:500;color:#856404">⚠ 시장 상황 무시 분석</div>
  <div style="font-size:12px;color:#856404;line-height:1.5">
    이 페이지는 마스터 스위치, VIX, 금리를 무시하고 순수 기술지표만으로 분석한 결과입니다.<br>
    실제 매매 시에는 반드시 Market Signals 페이지를 함께 확인하세요.</div>
</div>
```

---

## M9: 사이드바 정리

### 삭제 대상
- 기존 단일 Signals 페이지 파일
- 사이드바 설정 섹션 (테스트 모드, HOLD 토글, 분류 필터)

### 테스트 모드 → 환경변수
```python
import os
USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
```

### 최종 사이드바
```
Overview                ← app.py
Portfolio Management    ← pages/1_Portfolio_Management.py
Ticker Detail           ← pages/2_Ticker_Detail.py
Market Signals          ← pages/3_Market_Signals.py
Technical Signals       ← pages/4_Technical_Signals.py
(설정 섹션 없음)
```

---

## M10: 테스트 (OCR 제외)

### Phase T0: 테마 검증
```bash
grep 'base = "light"' .streamlit/config.toml
```

### Phase T1: 시그널 로직 (pytest)
```bash
pytest tests/test_rule_engine.py tests/test_signal_generator.py -v --tb=short
```
- 마스터 GREEN/YELLOW/RED, VIX 오버라이드, Exit L1/L2/L3
- EXPECTED_MARKET_SIGNALS, EXPECTED_TECH_SIGNALS 일치
- Technical BUY 수 >= Market BUY 수

### Phase T2: Portfolio Management (pytest)
```bash
pytest tests/test_portfolio_management.py -v --tb=short
```
- 로드/저장, 수량 편집, 삭제, Discard, Overview 참조

### Phase T3: 대시보드 기동
```bash
USE_MOCK_DATA=true streamlit run dashboard/app.py --server.port 8501 --server.headless true &
sleep 10
for p in "" "Portfolio_Management" "Ticker_Detail" "Market_Signals" "Technical_Signals"; do
  curl -s -o /dev/null -w "%{http_code} $p\n" "http://localhost:8501/$p"
done
kill %1
```

### Phase T4: 스크린샷 시각 검증
```bash
python tests/capture_dashboard.py
# view overview_target.png vs current_overview.png
```

체크리스트:
- [Overview] 배경 흰색, 카드 #F8F9FA, 듀얼 시그널, 인덱스, USD/KRW, 날짜 KST
- [Portfolio Management] 편집 필드, 삭제, Save/Discard, 데이터 흐름
- [Ticker Detail] 4-panel Plotly, 전략 프로그레스
- [Market Signals] 마스터 배너, 대부분 HOLD
- [Technical Signals] 경고 배너, BUY 존재
- [사이드바] 5페이지, 설정 없음, "Overview" 표시

### Phase T5: 통합 Smoke Test
```bash
bash tests/smoke_test.sh
# T0→T4 순서 실행 → ALL PHASES COMPLETE
```

---

## 실행 순서 (Claude Code용)

```
docs/MODIFICATION_PLAN_v3.md를 읽고 M1~M10을 순서대로 진행해줘.
docs/design_reference/overview_target.html이 Overview 페이지의 정답 디자인이야.
이 HTML을 브라우저에서 열어서 CSS, 색상, 레이아웃을 확인하고 Streamlit에서 동일하게 구현해.

진행 순서:
1. .streamlit/config.toml 생성 (라이트 모드 고정)
2. data/test_portfolio.json 생성 (M3의 23개 종목 실제 데이터)
3. dashboard/style.py + components.py 생성 (overview_target.html의 CSS 참조)
4. rule_engine.py + signal_generator.py 수정 (M4의 EXPECTED 딕셔너리와 일치하도록)
5. dashboard/pages/1_Portfolio_Management.py 신규 생성 (수량/단가 편집, 삭제, Save)
6. dashboard/app.py 전면 재작성 (overview_target.html과 동일하게)
7. dashboard/pages/2_Ticker_Detail.py 재작성 (4-panel Plotly)
8. dashboard/pages/3_Market_Signals.py + 4_Technical_Signals.py 생성
9. 기존 불필요 Signals 파일 삭제, 사이드바 설정 섹션 제거
10. 테스트 실행 (Phase T0~T5)

핵심 원칙:
- st.metric(), st.dataframe(), st.warning() 사용 금지. 모든 UI는 st.markdown(unsafe_allow_html=True)
- Plotly 차트만 st.plotly_chart() 허용
- overview_target.html이 정답. 이 파일의 모든 색상과 구조를 그대로 재현
- 시그널: M4의 EXPECTED_MARKET_SIGNALS, EXPECTED_TECH_SIGNALS와 일치해야 함
- Portfolio Management가 portfolio.json의 소유자. Overview는 이 파일을 참조만 함
- 테스트 실패 시 원인 분석 → 수정 → 재테스트 (최대 3회)
- 자동 승인 모드니 멈추지 말고 끝까지 진행해
```

---

## [부록 A] data/test_portfolio.json

```json
{
  "updated_at": "2026-03-28T06:22:00+09:00",
  "source": "toss_securities_ocr",
  "total_value_usd": 431847.25,
  "total_cost_usd": 379295.75,
  "holdings": [
    {"ticker":"VOO","name":"Vanguard S&P 500 ETF","shares":175.157486,"avg_cost":514.07,"value_usd":102109.73,"pnl_usd":12079.06,"pnl_pct":13.42,"classification":"etf_v24"},
    {"ticker":"BIL","name":"SPDR 1-3 Month Treasury","shares":1000.0,"avg_cost":82.95,"value_usd":91629.97,"pnl_usd":8681.28,"pnl_pct":10.47,"classification":"bond_gold_v26"},
    {"ticker":"QQQ","name":"Invesco QQQ Trust ETF","shares":135.643587,"avg_cost":498.22,"value_usd":76310.31,"pnl_usd":8740.33,"pnl_pct":12.94,"classification":"etf_v24"},
    {"ticker":"SCHD","name":"Schwab US Dividend Equity","shares":1512.010124,"avg_cost":24.52,"value_usd":46025.07,"pnl_usd":8970.72,"pnl_pct":24.21,"classification":"etf_v24"},
    {"ticker":"AAPL","name":"Apple Inc.","shares":79.349225,"avg_cost":171.14,"value_usd":19742.07,"pnl_usd":6163.48,"pnl_pct":45.39,"classification":"growth_v22"},
    {"ticker":"O","name":"Realty Income Corp","shares":281.032653,"avg_cost":51.02,"value_usd":17055.77,"pnl_usd":2707.80,"pnl_pct":18.87,"classification":"energy_v23"},
    {"ticker":"JEPI","name":"JPMorgan Equity Premium","shares":254.066847,"avg_cost":50.70,"value_usd":14113.35,"pnl_usd":1233.91,"pnl_pct":9.58,"classification":"etf_v24"},
    {"ticker":"SOXX","name":"iShares Semiconductor ETF","shares":30.889879,"avg_cost":183.63,"value_usd":9992.24,"pnl_usd":4322.33,"pnl_pct":76.23,"classification":"etf_v24"},
    {"ticker":"TSLA","name":"Tesla Inc.","shares":26.931576,"avg_cost":389.90,"value_usd":9744.64,"pnl_usd":-759.24,"pnl_pct":-7.23,"classification":"growth_v22"},
    {"ticker":"TLT","name":"iShares 20+ Year Treasury","shares":100.0,"avg_cost":84.05,"value_usd":8563.99,"pnl_usd":158.81,"pnl_pct":1.89,"classification":"bond_gold_v26"},
    {"ticker":"NVDA","name":"NVIDIA Corporation","shares":48.700507,"avg_cost":164.86,"value_usd":8158.30,"pnl_usd":130.27,"pnl_pct":1.62,"classification":"growth_v22"},
    {"ticker":"PLTR","name":"Palantir Technologies","shares":56.829293,"avg_cost":137.42,"value_usd":8129.98,"pnl_usd":313.74,"pnl_pct":4.01,"classification":"growth_v22"},
    {"ticker":"SPY","name":"SPDR S&P 500 ETF Trust","shares":8.887535,"avg_cost":509.30,"value_usd":5635.49,"pnl_usd":1112.34,"pnl_pct":24.59,"classification":"etf_v24"},
    {"ticker":"UNH","name":"UnitedHealth Group","shares":18.0,"avg_cost":281.27,"value_usd":4662.36,"pnl_usd":-400.56,"pnl_pct":-7.91,"classification":"energy_v23"},
    {"ticker":"MSFT","name":"Microsoft Corporation","shares":11.999013,"avg_cost":392.72,"value_usd":4280.89,"pnl_usd":-431.73,"pnl_pct":-9.16,"classification":"growth_v22"},
    {"ticker":"GOOGL","name":"Alphabet Inc. Class A","shares":10.676876,"avg_cost":297.39,"value_usd":2929.09,"pnl_usd":-246.18,"pnl_pct":-7.75,"classification":"growth_v22"},
    {"ticker":"AMZN","name":"Amazon.com Inc.","shares":5.84814,"avg_cost":208.55,"value_usd":1165.77,"pnl_usd":-54.17,"pnl_pct":-4.44,"classification":"growth_v22"},
    {"ticker":"SLV","name":"iShares Silver Trust","shares":12.0,"avg_cost":64.29,"value_usd":761.28,"pnl_usd":-10.22,"pnl_pct":-1.32,"classification":"bond_gold_v26"},
    {"ticker":"TQQQ","name":"ProShares UltraPro QQQ","shares":5.0,"avg_cost":63.23,"value_usd":290.25,"pnl_usd":-25.88,"pnl_pct":-8.19,"classification":"speculative"},
    {"ticker":"SOXL","name":"Direxion Daily Semi 3X","shares":5.0,"avg_cost":53.62,"value_usd":233.05,"pnl_usd":-35.06,"pnl_pct":-13.08,"classification":"speculative"},
    {"ticker":"ETHU","name":"ProShares Ultra Ether ETF","shares":10.0,"avg_cost":25.96,"value_usd":201.60,"pnl_usd":-57.98,"pnl_pct":-22.34,"classification":"speculative"},
    {"ticker":"CRCL","name":"Circle Internet Group","shares":1.0,"avg_cost":123.81,"value_usd":93.66,"pnl_usd":-30.15,"pnl_pct":-24.35,"classification":"speculative"},
    {"ticker":"BTDR","name":"Bitdeer Technologies","shares":1.0,"avg_cost":29.79,"value_usd":18.39,"pnl_usd":-11.40,"pnl_pct":-38.26,"classification":"speculative"}
  ]
}
```

---

## [부록 B] tests/fixtures/mock_market_data.json

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
    "VOO":{"price":582.50,"ma20":595.00,"ma50":605.00,"ma200":570.00,"rsi":36.5,"macd":-5.20,"macd_signal":-4.10,"macd_histogram":-1.10,"macd_hist_trend":"declining_2d","bb_upper":625.00,"bb_lower":560.00,"adx":32,"volume":8500000,"volume_avg20":9200000,"volume_ratio":0.92},
    "BIL":{"price":91.63,"ma20":91.50,"ma50":91.30,"ma200":90.80,"rsi":52.0,"macd":0.05,"macd_signal":0.03,"macd_histogram":0.02,"macd_hist_trend":"flat","bb_upper":92.10,"bb_lower":90.90,"adx":12,"volume":3000000,"volume_avg20":2800000,"volume_ratio":1.07},
    "QQQ":{"price":587.82,"ma20":599.66,"ma50":608.66,"ma200":592.43,"rsi":34.75,"macd":-7.12,"macd_signal":-5.80,"macd_histogram":-1.32,"macd_hist_trend":"declining_3d","bb_upper":635.00,"bb_lower":565.00,"adx":30,"volume":52000000,"volume_avg20":48000000,"volume_ratio":1.08},
    "SCHD":{"price":30.44,"ma20":31.20,"ma50":31.80,"ma200":29.50,"rsi":38.0,"macd":-0.35,"macd_signal":-0.28,"macd_histogram":-0.07,"macd_hist_trend":"flat","bb_upper":33.00,"bb_lower":29.50,"adx":22,"volume":4500000,"volume_avg20":4200000,"volume_ratio":1.07},
    "AAPL":{"price":248.80,"ma20":255.00,"ma50":260.00,"ma200":230.00,"rsi":40.2,"macd":-2.80,"macd_signal":-2.20,"macd_histogram":-0.60,"macd_hist_trend":"declining_1d","bb_upper":270.00,"bb_lower":240.00,"adx":25,"volume":35000000,"volume_avg20":38000000,"volume_ratio":0.92},
    "O":{"price":60.68,"ma20":61.50,"ma50":62.00,"ma200":58.00,"rsi":42.5,"macd":-0.40,"macd_signal":-0.30,"macd_histogram":-0.10,"macd_hist_trend":"flat","bb_upper":64.00,"bb_lower":59.00,"adx":18,"volume":5000000,"volume_avg20":4800000,"volume_ratio":1.04},
    "JEPI":{"price":55.56,"ma20":56.20,"ma50":56.80,"ma200":54.50,"rsi":44.0,"macd":-0.25,"macd_signal":-0.18,"macd_histogram":-0.07,"macd_hist_trend":"flat","bb_upper":58.00,"bb_lower":54.50,"adx":15,"volume":3200000,"volume_avg20":3000000,"volume_ratio":1.07},
    "SOXX":{"price":323.50,"ma20":340.00,"ma50":355.00,"ma200":290.00,"rsi":32.0,"macd":-8.50,"macd_signal":-6.80,"macd_histogram":-1.70,"macd_hist_trend":"declining_3d","bb_upper":380.00,"bb_lower":300.00,"adx":35,"volume":2800000,"volume_avg20":2500000,"volume_ratio":1.12},
    "TSLA":{"price":361.88,"ma20":378.50,"ma50":395.20,"ma200":310.00,"rsi":38.2,"macd":-3.44,"macd_signal":-1.82,"macd_histogram":-1.62,"macd_hist_trend":"declining_2d","bb_upper":410.50,"bb_lower":346.50,"adx":28,"volume":45000000,"volume_avg20":52000000,"volume_ratio":0.87},
    "TLT":{"price":85.64,"ma20":87.20,"ma50":88.50,"ma200":90.10,"rsi":34.0,"macd":-0.80,"macd_signal":-0.60,"macd_histogram":-0.20,"macd_hist_trend":"declining_1d","bb_upper":92.00,"bb_lower":83.00,"adx":20,"volume":22000000,"volume_avg20":20000000,"volume_ratio":1.10},
    "NVDA":{"price":167.55,"ma20":172.30,"ma50":180.10,"ma200":135.00,"rsi":35.8,"macd":-2.10,"macd_signal":-1.50,"macd_histogram":-0.60,"macd_hist_trend":"rising_1d","bb_upper":195.00,"bb_lower":155.00,"adx":26,"volume":42000000,"volume_avg20":45000000,"volume_ratio":0.93},
    "PLTR":{"price":143.05,"ma20":148.00,"ma50":152.00,"ma200":120.00,"rsi":41.0,"macd":-1.80,"macd_signal":-1.40,"macd_histogram":-0.40,"macd_hist_trend":"flat","bb_upper":160.00,"bb_lower":135.00,"adx":22,"volume":18000000,"volume_avg20":20000000,"volume_ratio":0.90},
    "SPY":{"price":645.09,"ma20":668.59,"ma50":680.65,"ma200":657.19,"rsi":35.99,"macd":-7.92,"macd_signal":-6.20,"macd_histogram":-1.72,"macd_hist_trend":"declining_2d","bb_upper":700.00,"bb_lower":630.00,"adx":34,"volume":85000000,"volume_avg20":78000000,"volume_ratio":1.09},
    "UNH":{"price":259.02,"ma20":270.00,"ma50":280.00,"ma200":250.00,"rsi":33.5,"macd":-4.50,"macd_signal":-3.20,"macd_histogram":-1.30,"macd_hist_trend":"declining_3d","bb_upper":295.00,"bb_lower":245.00,"adx":30,"volume":4200000,"volume_avg20":3800000,"volume_ratio":1.11},
    "MSFT":{"price":356.80,"ma20":368.00,"ma50":378.00,"ma200":340.00,"rsi":37.0,"macd":-3.20,"macd_signal":-2.50,"macd_histogram":-0.70,"macd_hist_trend":"declining_1d","bb_upper":390.00,"bb_lower":345.00,"adx":24,"volume":22000000,"volume_avg20":24000000,"volume_ratio":0.92},
    "GOOGL":{"price":274.30,"ma20":282.00,"ma50":290.00,"ma200":260.00,"rsi":36.5,"macd":-2.80,"macd_signal":-2.10,"macd_histogram":-0.70,"macd_hist_trend":"declining_2d","bb_upper":300.00,"bb_lower":265.00,"adx":26,"volume":16000000,"volume_avg20":18000000,"volume_ratio":0.89},
    "AMZN":{"price":199.30,"ma20":205.00,"ma50":212.00,"ma200":188.00,"rsi":38.5,"macd":-2.20,"macd_signal":-1.70,"macd_histogram":-0.50,"macd_hist_trend":"flat","bb_upper":220.00,"bb_lower":190.00,"adx":22,"volume":28000000,"volume_avg20":30000000,"volume_ratio":0.93},
    "SLV":{"price":63.44,"ma20":67.50,"ma50":72.00,"ma200":52.00,"rsi":36.1,"macd":-1.80,"macd_signal":-1.30,"macd_histogram":-0.50,"macd_hist_trend":"declining_1d","bb_upper":78.00,"bb_lower":60.00,"adx":28,"volume":18000000,"volume_avg20":16000000,"volume_ratio":1.13},
    "TQQQ":{"price":58.05,"ma20":62.00,"ma50":66.00,"ma200":50.00,"rsi":30.5,"macd":-1.50,"macd_signal":-1.10,"macd_histogram":-0.40,"macd_hist_trend":"declining_2d","bb_upper":72.00,"bb_lower":52.00,"adx":32,"volume":25000000,"volume_avg20":22000000,"volume_ratio":1.14},
    "SOXL":{"price":46.61,"ma20":52.00,"ma50":58.00,"ma200":38.00,"rsi":28.0,"macd":-2.80,"macd_signal":-2.10,"macd_histogram":-0.70,"macd_hist_trend":"declining_3d","bb_upper":65.00,"bb_lower":40.00,"adx":36,"volume":15000000,"volume_avg20":13000000,"volume_ratio":1.15},
    "ETHU":{"price":20.16,"ma20":23.00,"ma50":26.00,"ma200":18.00,"rsi":28.5,"macd":-1.20,"macd_signal":-0.90,"macd_histogram":-0.30,"macd_hist_trend":"declining_3d","bb_upper":28.00,"bb_lower":18.00,"adx":34,"volume":800000,"volume_avg20":700000,"volume_ratio":1.14},
    "CRCL":{"price":93.66,"ma20":100.00,"ma50":108.00,"ma200":80.00,"rsi":32.0,"macd":-3.00,"macd_signal":-2.20,"macd_histogram":-0.80,"macd_hist_trend":"declining_2d","bb_upper":115.00,"bb_lower":85.00,"adx":30,"volume":500000,"volume_avg20":450000,"volume_ratio":1.11},
    "BTDR":{"price":18.39,"ma20":22.00,"ma50":25.00,"ma200":15.00,"rsi":25.0,"macd":-1.50,"macd_signal":-1.10,"macd_histogram":-0.40,"macd_hist_trend":"declining_3d","bb_upper":28.00,"bb_lower":16.00,"adx":38,"volume":300000,"volume_avg20":250000,"volume_ratio":1.20}
  }
}
```
