# AI Trading Assistant — Project Specification v1.0

> **이 문서는 Claude Code에서 구현을 진행하기 위한 종합 기획서입니다.**
> 모든 결정 사항이 확정되어 있으며, 이 문서를 기반으로 Sprint 순서대로 구현을 진행하면 됩니다.

---

## 1. 프로젝트 개요

### 1.1 목표
개인 투자 포트폴리오(토스증권)의 계좌 상태 + 시장 상황 + 전략 규칙을 종합하여,
매일 종목별 액션(매수/매도/대기)을 제안하는 **완전 자동화 시스템**을 구축한다.

### 1.2 핵심 원칙
- **월 운영비 $0**: 모든 구성요소가 무료 (API 비용 없음)
- **규칙 기반**: Claude API 대신 코드화된 전략 규칙 엔진 사용
- **사람이 최종 판단**: 시스템은 제안만 하고, 실행은 사용자가 결정

### 1.3 운용 범위
- 미국 주식 + ETF (채권/금 포함)
- 현재 23개 종목 보유 중 (VOO, BIL, QQQ, SCHD, AAPL, O, JEPI, SOXX, TSLA, TLT, NVDA, PLTR, SPY, UNH, MSFT, GOOGL, AMZN, SLV, TQQQ, SOXL, ETHU, CRCL, BTDR)

---

## 2. 시스템 아키텍처

### 2.1 전체 흐름
```
[Trigger] → [Data Collection] → [Rule Engine] → [Signal Generation] → [Dashboard] → [Telegram Notification]
```

### 2.2 두 가지 트리거
1. **텔레그램 스크린샷**: 사용자가 토스증권 앱 스크린샷을 텔레그램 봇에 전송 → OCR 파싱 → 계좌 업데이트 → 분석 → 대시보드 갱신
2. **매일 오전 7시 KST**: GitHub Actions cron (`0 22 * * *` UTC) → 시장 데이터 수집 → 분석 → 대시보드 갱신

### 2.3 기술 스택
| 구성요소 | 기술 | 비용 |
|----------|------|------|
| OCR | Tesseract OCR (kor+eng) | $0 |
| 시장 데이터 | yfinance | $0 |
| 분석 엔진 | Python 규칙 엔진 (v3.0 전략) | $0 |
| 대시보드 | Streamlit (Community Cloud) | $0 |
| 자동화 | GitHub Actions | $0 |
| 알림 | Telegram Bot API | $0 |
| 데이터 저장 | GitHub repo 내 JSON 파일 | $0 |

### 2.4 GitHub 레포 구조
```
ai-trading-assistant/
├── .github/workflows/
│   ├── daily_report.yml          # cron 7AM KST (0 22 * * * UTC)
│   └── telegram_trigger.yml      # repository_dispatch from telegram
├── src/
│   ├── ocr_parser.py             # Tesseract OCR + Toss screenshot parser
│   ├── market_data.py            # yfinance wrapper (가격, MA, RSI, MACD, BB, VIX, 금리)
│   ├── rule_engine.py            # v3.0 전략 로직 (master switch + 4개 전략 + exit)
│   ├── signal_generator.py       # 규칙 + 매크로 통합 → 시그널 생성
│   ├── rebalance_checker.py      # 리밸런싱 트리거 체크
│   └── telegram_bot.py           # 봇 수신 + 알림 발송
├── dashboard/
│   ├── app.py                    # Streamlit 메인 (Overview)
│   ├── pages/1_Ticker_Detail.py  # 종목별 상세
│   └── pages/2_Signals.py        # 오늘의 시그널
├── config/
│   ├── strategy_v3.yaml          # 전략 규칙 정의
│   ├── tickers.yaml              # 종목 목록 + 분류 + 한글 매핑
│   └── thresholds.yaml           # 매크로 임계값 (VIX, 금리, 환율)
├── data/
│   ├── portfolio.json            # 현재 보유 현황
│   ├── history.json              # 일별 스냅샷 (append)
│   ├── signals.json              # 최신 시그널
│   └── market_cache.json         # 최신 시장 데이터
├── tests/
│   ├── test_ocr_parser.py
│   ├── test_rule_engine.py
│   └── test_signal_generator.py
├── requirements.txt
├── CLAUDE.md                     # Claude Code 프로젝트 지시서
└── README.md
```

---

## 3. OCR 파서 (src/ocr_parser.py)

### 3.1 검증 완료 사항
- 토스증권 앱 스크린샷 3장으로 **23/23 종목 100% 정확도** 검증 완료
- Tesseract OCR (kor+eng, PSM 6) 사용
- 두 가지 OCR 보정 로직 필수:
  1. 달러 금액 내 공백 제거: `$1 7,055` → `$17,055` (regex: `\$(\d)\s+(\d)` → `$\1\2`)
  2. 한글 "은"이 "2"로 인식: `iShares 2 ETF` → SLV로 매핑

### 3.2 한글 → 티커 매핑 테이블
```yaml
# config/tickers.yaml
ticker_map:
  마이크로소프트: MSFT
  알파벳: GOOGL
  아마존닷컴: AMZN
  엔비디아: NVDA
  팔란티어: PLTR
  테슬라: TSLA
  애플: AAPL
  유나이티드헬스: UNH
  리얼티 인컴: O
  써클 인터넷: CRCL
  비트마인: BTDR
  "iShares 2 ETF": SLV    # OCR 보정: "은" → "2"
  "iShares 은": SLV
  "iShares 20": TLT
  "SPDR 1-3": BIL
  "SPDR S&P": SPY
  "Invesco QQQ": QQQ
  "Vanguard S&P": VOO
  SCHD: SCHD
  JEPI: JEPI
  SOXX: SOXX
  "ProShares QQQ": TQQQ
  Direxion: SOXL
  "이더리움 2X": ETHU
```

### 3.3 파싱 로직
1. Tesseract로 이미지 → 텍스트 추출 (lang='kor+eng', config='--psm 6')
2. `clean_dollar()`: 달러 금액 내 공백 제거
3. 줄 단위 순회: 한글 매핑으로 티커 식별
4. 다음 3줄 내에서 regex로 추출:
   - 평가금액: `\$([0-9,]+\.?\d*)` 중 최대값
   - 손익: `([+-])\$([0-9,]+\.?\d*)\s*\((\d+\.?\d*)%\)`
   - 수량: `([\d,.]+)\s*주`
5. 중복 제거 후 portfolio.json으로 출력

### 3.4 출력 포맷 (data/portfolio.json)
```json
{
  "updated_at": "2026-03-28T07:00:00+09:00",
  "source": "toss_securities_ocr",
  "total_value_usd": 431847.25,
  "holdings": [
    {
      "ticker": "VOO",
      "value_usd": 102109.73,
      "pnl_usd": 12079.06,
      "pnl_pct": 13.42,
      "shares": 175.157486
    }
  ]
}
```

---

## 4. 시장 데이터 (src/market_data.py)

### 4.1 yfinance로 수집할 데이터
```python
# 보유 종목별
for ticker in portfolio_tickers:
    - 현재가, 전일 종가
    - MA20, MA50, MA200 (종가 기준 SMA)
    - RSI(14)
    - MACD(12,26,9) + Signal + Histogram
    - Bollinger Bands(20, 2σ)
    - ADX(14) — 성장주 전략에 필요
    - 거래량 + 20일 평균 거래량

# 매크로 지표
macro_tickers:
    - ^GSPC (S&P 500 → MA200 계산)
    - ^VIX (변동성)
    - ^TYX (30년 국채 금리)
    - USDKRW=X (원달러 환율)
    - QQQ, SPY (마스터 스위치용 MA200)
```

### 4.2 출력 포맷 (data/market_cache.json)
```json
{
  "updated_at": "2026-03-28T07:00:00+09:00",
  "master_switch": {
    "qqq_price": 587.82,
    "qqq_ma200": 592.43,
    "qqq_above_ma200": false,
    "spy_price": 645.09,
    "spy_ma200": 657.19,
    "spy_above_ma200": false,
    "status": "RED"
  },
  "macro": {
    "vix": 30.91,
    "vix_tier": "high",
    "treasury_30y": 4.982,
    "usdkrw": 1425.50
  },
  "tickers": {
    "TSLA": {
      "price": 361.88,
      "ma20": 378.50,
      "ma50": 395.20,
      "ma200": 310.00,
      "rsi": 38.2,
      "macd": -3.44,
      "macd_signal": -1.82,
      "macd_histogram": -1.62,
      "macd_hist_trend": "declining_2d",
      "bb_upper": 410.50,
      "bb_lower": 346.50,
      "adx": 28.5,
      "volume": 45000000,
      "volume_avg20": 52000000,
      "volume_ratio": 0.87
    }
  }
}
```

---

## 5. 전략 규칙 엔진 (src/rule_engine.py)

### 5.0 마스터 스위치 (The Master Filter)
```yaml
# config/strategy_v3.yaml — master_switch
master_switch:
  green:
    condition: "qqq_above_ma200 AND spy_above_ma200"
    action: "all strategies active"
    allocation_multiplier: 1.0
  yellow:
    condition: "qqq_above_ma200 XOR spy_above_ma200"
    action: "1st tranche only (20%)"
    allocation_multiplier: 0.5
  red:
    condition: "NOT qqq_above_ma200 AND NOT spy_above_ma200"
    action: "no new equity buys"
    allocation_multiplier: 0.0

vix_override:
  - threshold: 25
    multiplier: 0.7
  - threshold: 30
    multiplier: 0.5
  - threshold: 35
    action: "trigger exit L1 on all positions"
```

### 5.1 종목 자동 분류 (config/tickers.yaml)
```yaml
classifications:
  growth_v22:  # 성장주: 확인 후 진입
    tickers: [NVDA, TSLA, PLTR, MSFT, GOOGL, AMZN, AAPL]
    criteria: "beta > 1.3 OR sector=tech"
  etf_v24:     # ETF: 균형 진입
    tickers: [QQQ, VOO, SPY, SCHD, SOXX, JEPI]
    criteria: "asset_type=ETF"
  energy_v23:  # 에너지/가치: 선제 진입
    tickers: [UNH, O]
    criteria: "sector=healthcare/REIT OR dividend > 2%"
  bond_gold_v26: # 채권/금: 금리 기반
    tickers: [TLT, BIL, SLV]
    criteria: "asset_type=fixed_income/commodity"
  speculative:  # 투기/소형: 별도 관리
    tickers: [TQQQ, SOXL, ETHU, CRCL, BTDR]
    criteria: "leveraged OR micro_cap"
```

### 5.2 진입 전략 (Entry Rules)

#### Growth v2.2 (NVDA, TSLA 등)
```yaml
growth_v22:
  tranche_1:
    size: 0.20
    required: ["macd_histogram_rising_2d"]
    pick_3_of:
      - "rsi <= 38"
      - "adx <= 25"
      - "price_near_bb_lower"
      - "price_below_ma20"
      - "3day_low_hold"
      - "bounce_2pct"
    veto: "rsi > 50"
  tranche_2:
    size: 0.30
    all_required:
      - "double_bottom"
      - "rsi > 35 AND rsi_rising_3d"
      - "macd_golden_cross OR macd_hist_rising_3d"
      - "volume_ratio >= 1.2"
  tranche_3:
    size: 0.50
    all_required:
      - "price_above_ma20_2d"
      - "ma20_slope_rising"
      - "macd_above_zero"
      - "volume_ratio >= 1.3"
    veto: "rsi > 75"
```

#### ETF v2.4 (QQQ, VOO 등)
```yaml
etf_v24:
  tranche_1:
    size: 0.20
    pick_3_of:
      - "rsi <= 40"
      - "price_below_ma20"
      - "price_near_bb_lower"
      - "momentum_declining_slowing"
      - "pullback_5pct"
    veto: "rsi > 70"
  tranche_2:
    size: 0.30
    pick_3_of:
      - "rsi > 42"
      - "macd > macd_signal"
      - "price_above_ma20"
      - "higher_low"
    veto: "rsi > 70"
  tranche_3:
    size: 0.50
    pick_3_of:
      - "price_above_ma20_2d"
      - "ma20_slope_rising"
      - "rsi > 48"
      - "macd_above_zero"
    veto: "rsi > 70"
```

#### Energy/Value v2.3 (UNH, O 등)
```yaml
energy_v23:
  tranche_1: "same as growth_v22.tranche_1"
  tranche_2:
    size: 0.30
    pick_3_of:
      - "double_bottom_3pct"
      - "rsi > 40"
      - "macd > macd_signal"
      - "price_above_ma20"
    veto: "rsi > 70"
  tranche_3:
    size: 0.50
    pick_3_of:
      - "price_above_ma20_2d"
      - "ma20_slope_rising"
      - "macd > macd_signal"
      - "rsi > 45"
    veto: "rsi > 70"
```

#### Bond/Gold v2.6 (TLT, SLV — NEW)
```yaml
bond_v26:
  tranche_1:
    size: 0.20
    all_required:
      - "treasury_30y >= 5.0"
      - "tlt_rsi <= 35"
    note: "독립적 — 마스터 스위치 무시"
  tranche_2:
    size: 0.30
    any_of:
      - "treasury_30y >= 5.2"
      - "tlt_macd_golden_cross"
  tranche_3:
    size: 0.50
    all_required:
      - "tlt_above_ma20_2d"
      - "treasury_30y_declining_from_peak"

gold_v26:
  tranche_1:
    size: 0.20
    pick_2_of:
      - "gld_rsi <= 40"
      - "gld_below_ma20"
      - "vix > 25"
    note: "독립적 — 마스터 스위치 무시. 포트폴리오 5-10% 상한."
  tranche_2:
    size: 0.30
    pick_2_of:
      - "gld_macd > gld_signal"
      - "gld_rsi > 42"
      - "gld_higher_low"
  tranche_3:
    size: 0.50
    pick_2_of:
      - "gld_above_ma20_2d"
      - "gld_ma20_rising"
      - "gld_macd_above_zero"
```

### 5.3 퇴출 시스템 (Exit v2.5)
```yaml
exit_system:
  level_1_early_warning:
    trigger: "2개 이상 충족"
    conditions:
      - "macd_histogram_declining_1_2d"
      - "rsi_65plus_turning_down"
      - "price_inside_bb_from_upper"
      - "volume_divergence_negative"
    action: "신규 매수 금지, 익절 준비"

  level_2_weakening:
    trigger: "2개 이상 충족"
    conditions:
      - "macd_histogram_declining_3d"
      - "rsi_lower_high_divergence"
      - "price_below_ma20_1d"
      - "double_top_or_head_shoulder"
    action: "보유 30% 익절"

  level_3_breakdown:
    trigger: "1개라도 충족"
    conditions:
      - "price_below_ma20_2d_no_recovery"
      - "higher_low_broken"
      - "macd_death_cross_approaching_zero"
      - "drawdown_8pct_from_peak"
    action: "전량 매도 / 전체 청산"

  top_signal:
    trigger: "1개라도 충족 시 즉시"
    conditions:
      - "rsi >= 75"
      - "price_above_bb_upper_2d"
      - "gain_10pct_in_3d"
    action: "강제 일부 익절"
```

### 5.4 매크로 오버레이 (규칙 기반, AI 없음)
```yaml
# config/thresholds.yaml
macro_rules:
  treasury_yield:
    - condition: "treasury_30y >= 5.0"
      effect: "activate bond_v26 strategy"
    - condition: "treasury_30y >= 5.2"
      effect: "downgrade equity entry urgency by 1 tier"

  vix_tiers:
    - range: [0, 20]
      allocation_modifier: 1.0
    - range: [20, 25]
      allocation_modifier: 1.0
    - range: [25, 30]
      allocation_modifier: 0.7
    - range: [30, 35]
      allocation_modifier: 0.5
    - range: [35, 100]
      action: "trigger exit L1 on all positions"

  exchange_rate:
    - condition: "usdkrw > 1450"
      effect: "delay US equity new buys"
    - condition: "usdkrw < 1300"
      effect: "accelerate US equity buys"

  earnings_blackout:
    description: "어닝 발표 3일 전 해당 종목 신규 진입 금지"
    implementation: "config/earnings_calendar.yaml에 날짜 등록"
```

### 5.5 포지션 사이징
```yaml
position_sizing:
  base_tranches: [0.20, 0.30, 0.50]  # 비율은 고정
  total_adjustment:
    green: 1.0   # 계획된 금액 100%
    yellow: 0.5  # 계획된 금액 50%
    red: 0.0     # 신규 없음
  max_single_position: 0.15  # 포트폴리오의 15%
```

### 5.6 리밸런싱 트리거 (주 1회 월요일 체크)
```yaml
rebalance_triggers:
  - name: "single_position_overweight"
    condition: "any ticker > 15% of portfolio"
    action: "trim to 12% at next L1/L2 signal"
  - name: "asset_class_drift"
    condition: "equity > 75% OR bond < 15%"
    action: "redirect new capital to underweight class"
  - name: "dividend_income_limit"
    condition: "projected annual dividend > 18M KRW"
    action: "rotate from high-yield to growth or bond"
    note: "20M 한도에서 2M 안전 버퍼"
  - name: "tax_account_priority"
    condition: "ISA/pension capacity unused"
    action: "prioritize new buys in tax-advantaged accounts"
```

---

## 6. 시그널 생성 (src/signal_generator.py)

### 6.1 출력 포맷 (data/signals.json)
```json
{
  "date": "2026-03-28",
  "master_switch": "RED",
  "vix_tier": "high (30.9)",
  "signals": [
    {
      "ticker": "TSLA",
      "classification": "growth_v22",
      "action": "L1_WARNING",
      "confidence": 72,
      "rationale": "MACD 히스토그램 2일 연속 감소 + RSI 65에서 하락 전환. 신규 매수 중단, L2 발동 시 30% 트림 준비.",
      "conditions_met": ["macd_hist_declining_2d", "rsi_65_turned_down"],
      "conditions_not_met": ["bb_upper_reentry", "volume_divergence"],
      "strategy_stage": {"current": 1, "next_conditions": "double_bottom + RSI>35 rising 3d + MACD golden cross + vol 1.2x"}
    }
  ],
  "rebalance_alerts": [],
  "macro_alerts": [
    {"type": "treasury_yield", "message": "30Y 금리 4.98% — 5.0% 진입 트리거 임박"}
  ]
}
```

### 6.2 확신도 점수 계산
```python
confidence = base_score(conditions_met / total_conditions)
# 가중치: 마스터 스위치 GREEN +20, YELLOW +0, RED -20
# 가중치: VIX < 20 +10, VIX 25-30 +0, VIX > 30 -10
# 최종 범위: 0-100
```

### 6.3 한국어 템플릿 근거 생성
```python
TEMPLATES = {
    "L1_WARNING": "MACD 히스토그램 {hist_days}일 연속 감소 + RSI {rsi_level}에서 하락 전환. {action_text}",
    "TRANCHE_1_BUY": "MACD 히스토그램 2일 연속 상승 + {met_conditions}. 1차 매수(20%) 조건 충족.",
    "HOLD": "특이 신호 없음. RSI {rsi}, MACD {macd_status}. 현재 포지션 유지.",
    "BOND_WATCH": "30Y 금리 {yield}% — {target}% 진입 트리거 {distance}. TLT RSI {rsi}.",
    ...
}
```

---

## 7. 대시보드 (dashboard/)

### 7.1 기술: Streamlit + Plotly
- Streamlit Community Cloud 무료 호스팅 (GitHub repo 연결)
- Plotly로 인터랙티브 차트
- 3페이지 구성 (multipage app)

### 7.2 Page 1: Overview (app.py)
**상단 영역:**
- 마스터 스위치 상태 배지 (GREEN/YELLOW/RED)
- 4개 메트릭 카드: 총자산, 일일 손익, 총수익률, YTD 배당금
- 3개 매크로 지표: QQQ vs MA200, 30Y 금리, VIX

**차트 영역 — 포트폴리오 트렌드 (핵심 차트):**
- 기간 선택: 1M / 3M / 6M / 1Y 버튼
- 메인 라인: 총자산 (area fill, teal 색상)
- 보조 라인: 원가 기준선 (점선, light blue)
- 우측 Y축: 배당금 바 차트 (amber)
- 이벤트 마커: 매수(삼각형, pink), 매도(다이아몬드, red)
- 호버 툴팁: 날짜, 총가치, 원가, 손익(금액+%), 배당금
- 하단 서머리: 기간 내 변동, 최고점, 최저점

**테이블 영역:**
- 보유 종목 테이블: 티커, 종목명, 평가금액, 비중(바 차트), 수익률, 시그널 배지
- 정렬 가능 (금액순, 수익률순)

**시그널 요약:**
- 당일 주요 시그널 카드 (경고/관심/마스터 스위치 순)

### 7.3 Page 2: Ticker Detail (pages/1_Ticker_Detail.py)
**상단:**
- 종목 선택 드롭다운 (st.selectbox)
- 티커 + 전략 분류 배지 + 현재가 + 수익률

**멀티패널 기술 차트 (Plotly subplots, shared_xaxes=True):**
- Panel 1 (높이 60%): 가격 + MA20(점선) + MA50(점선) + 볼린저 밴드(음영) + 매수 마커
- Panel 2 (높이 15%): RSI(14) + 70/30 기준선
- Panel 3 (높이 15%): MACD 히스토그램(초록/빨강) + MACD/Signal 라인
- Panel 4 (높이 10%): 거래량 바

**전략 진행 단계:**
- 3단계 프로그레스 (1차 완료/2차 대기/3차 잠금)
- 각 단계의 충족/미충족 조건 표시

**시그널 이력:**
- 최근 7일 테이블 (날짜, 시그널, 확신도, 근거)

### 7.4 Page 3: Signals (pages/2_Signals.py)
**요약 카드:** 경고 수, 관심 수, 매수 시그널 수, HOLD 수

**마스터 스위치 배너:** 현재 상태 + QQQ/SPY/VIX 수치

**시그널 카드 (우선순위 순):**
1. Exit warnings (L1/L2/L3) — 빨간 왼쪽 보더
2. Watch list (진입 조건 접근) — 주황 왼쪽 보더
3. Buy signals (조건 충족) — 초록 왼쪽 보더
4. Hold (액션 없음) — 그레이 그리드로 축약

**각 시그널 카드 구성:**
- 티커 + 시그널 배지 + 확신도 바
- 한국어 근거 텍스트
- 조건 태그 (충족=초록, 미충족=그레이)

---

## 8. 텔레그램 봇 (src/telegram_bot.py)

### 8.1 수신 기능
- 사용자가 이미지(스크린샷)를 전송하면 수신
- OCR 파싱 → portfolio.json 업데이트
- GitHub Actions `repository_dispatch` 이벤트 트리거

### 8.2 발신 기능
- 분석 완료 후 대시보드 URL 전송
- 메시지 포맷:
```
📊 포트폴리오 업데이트 완료
총자산: $431,847 (-0.97%)
마스터 스위치: 🔴 RED

⚠️ TSLA: L1 경고 (72%)
⚠️ ETHU: L2 약화 (81%)
👀 TLT: 채권 진입 임박

🔗 대시보드: https://your-app.streamlit.app
```

---

## 9. GitHub Actions 워크플로우

### 9.1 daily_report.yml
```yaml
name: Daily Report
on:
  schedule:
    - cron: '0 22 * * *'  # UTC 22:00 = KST 07:00
  workflow_dispatch:       # 수동 실행 가능

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python src/market_data.py         # 시장 데이터 수집
      - run: python src/rule_engine.py         # 규칙 엔진 실행
      - run: python src/signal_generator.py    # 시그널 생성
      - run: python src/rebalance_checker.py   # 리밸런싱 체크
      - name: Commit data
        run: |
          git config user.name "trading-bot"
          git config user.email "bot@trading.local"
          git add data/
          git diff --staged --quiet || git commit -m "daily: $(date +%Y-%m-%d)"
          git push
      - run: python src/telegram_bot.py notify  # 텔레그램 알림
    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

### 9.2 telegram_trigger.yml
```yaml
name: Telegram Trigger
on:
  repository_dispatch:
    types: [portfolio_update]

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: sudo apt-get install -y tesseract-ocr tesseract-ocr-kor
      - run: python src/ocr_parser.py "${{ github.event.client_payload.image_url }}"
      - run: python src/market_data.py
      - run: python src/rule_engine.py
      - run: python src/signal_generator.py
      - name: Commit & push
        run: |
          git config user.name "trading-bot"
          git config user.email "bot@trading.local"
          git add data/
          git diff --staged --quiet || git commit -m "update: telegram $(date +%Y-%m-%d-%H%M)"
          git push
      - run: python src/telegram_bot.py notify
    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

---

## 10. 구현 스프린트 계획

### Sprint 1: Foundation (1주)
- [ ] GitHub 레포 생성 + 기본 구조
- [ ] config/ YAML 파일 작성 (strategy_v3.yaml, tickers.yaml, thresholds.yaml)
- [ ] src/ocr_parser.py 구현 + 테스트
- [ ] src/market_data.py 구현 + 테스트
- [ ] data/ 초기 JSON 파일 생성 (현재 포트폴리오 데이터)
- [ ] requirements.txt
- **Deliverable:** 스크린샷 → JSON + 시장 데이터 수집 작동

### Sprint 2: Brain (1주)
- [ ] src/rule_engine.py — 마스터 스위치 + 4개 전략 + exit v2.5
- [ ] src/signal_generator.py — 시그널 생성 + 확신도 + 한국어 템플릿
- [ ] src/rebalance_checker.py — 리밸런싱 트리거
- [ ] tests/ 테스트 코드
- **Deliverable:** 시장 데이터 → signals.json 생성 작동

### Sprint 3: Dashboard (1주)
- [ ] dashboard/app.py — Overview 페이지 (메트릭 + 트렌드 차트 + 테이블)
- [ ] dashboard/pages/1_Ticker_Detail.py — 멀티패널 기술 차트
- [ ] dashboard/pages/2_Signals.py — 시그널 카드
- [ ] Streamlit Community Cloud 배포
- **Deliverable:** 라이브 대시보드 URL

### Sprint 4: Automation (1주)
- [ ] src/telegram_bot.py — 봇 수신/발신
- [ ] .github/workflows/daily_report.yml
- [ ] .github/workflows/telegram_trigger.yml
- [ ] Telegram bot 생성 + token/chat_id 설정
- [ ] GitHub Secrets 설정
- [ ] End-to-end 테스트
- **Deliverable:** 매일 자동 실행 + 텔레그램 알림

---

## 11. 현재 시장 상태 (2026-03-28 기준, 실제 데이터)

구현 시 테스트 데이터로 활용:
- QQQ: $587.82, MA200: $592.43 → **MA200 아래**
- SPY: $645.09, MA200: $657.19 → **MA200 아래**
- 마스터 스위치: **RED** (둘 다 아래)
- VIX: 30.91 → 고공포 구간 (allocation x0.5)
- 30Y 국채: 4.982% → 5.0% 진입 트리거 임박
- 포트폴리오 총자산: ~$431,847 (23개 종목)

---

## 12. 핵심 주의사항

1. **데이터 정확성**: yfinance는 비공식 API로 가끔 장애 발생 가능. 에러 핸들링 + 캐시 전략 필수.
2. **OCR 보정**: 토스 앱 UI 변경 시 매핑 테이블 업데이트 필요. 파싱 실패 시 텔레그램으로 에러 알림.
3. **건강보험료**: 배당소득 연 2,000만 원 한도 주의. 1,800만 원에서 리밸런싱 트리거.
4. **ISA/연금**: 세금 우대 계좌 우선 활용 규칙 포함.
5. **면책**: 이 시스템은 투자 조언이 아닌 정보 제공 목적이며, 모든 투자 결정은 사용자 본인의 판단과 책임입니다.
