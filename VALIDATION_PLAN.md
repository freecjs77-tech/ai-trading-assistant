# AI Trading Assistant — 검증 계획서 (Validation Plan)

> **이 문서는 Claude Code가 전체 시스템을 자동으로 검증하기 위한 계획서입니다.**
> 모든 테스트는 실제 포트폴리오 데이터(2026-03-28 토스증권 스크린샷 기준)를 사용합니다.
> Claude Code는 이 문서를 읽고 전체 검증을 자율적으로 진행하되, 실패 시 원인을 파악하고 수정한 후 재검증합니다.

---

## 검증 원칙

1. **모든 테스트는 자동화**: 수동 확인 없이 Claude Code가 실행하고 판단
2. **실패 시 자동 수정**: 테스트 실패 → 원인 분석 → 코드 수정 → 재테스트 (최대 3회 반복)
3. **실제 데이터 사용**: 하드코딩된 mock 데이터가 아닌 실제 포트폴리오 기반 fixture
4. **대시보드 직접 확인**: Streamlit을 로컬 실행하여 스크린샷 캡처 + 시각적 검증
5. **End-to-End 통합 테스트**: 개별 모듈 테스트 후 전체 파이프라인 검증

---

## Phase 0: 환경 검증

### 0.1 의존성 설치 확인
```bash
# 실행 명령
pip install -r requirements.txt
pip install pytest pytest-cov

# Tesseract OCR 설치 확인
tesseract --version
tesseract --list-langs  # 'kor' 포함 확인

# 검증 기준
# - 모든 패키지 설치 성공
# - tesseract 버전 출력
# - 'kor' 언어팩 존재
# 실패 시: requirements.txt 누락 패키지 추가, apt-get install tesseract-ocr-kor 실행
```

### 0.2 설정 파일 무결성 확인
```bash
# 실행 명령
python -c "
import yaml
for f in ['config/tickers.yaml', 'config/strategy_v3.yaml', 'config/thresholds.yaml']:
    with open(f) as fh:
        data = yaml.safe_load(fh)
        print(f'{f}: OK ({len(str(data))} chars)')
"

# 검증 기준
# - 3개 YAML 파일 모두 파싱 성공
# - tickers.yaml에 23개 종목 매핑 존재
# - strategy_v3.yaml에 master_switch, growth_v22, etf_v24, energy_v23, bond_v26, exit_system 섹션 존재
# - thresholds.yaml에 vix_tiers, treasury_yield, exchange_rate 섹션 존재
# 실패 시: YAML 문법 오류 수정, 누락 섹션 추가
```

---

## Phase 1: OCR 파서 검증 (src/ocr_parser.py)

### 1.1 테스트 데이터
실제 토스증권 스크린샷 3장에서 추출한 정답 데이터:

```python
# tests/fixtures/expected_portfolio.py
EXPECTED_HOLDINGS = {
    "VOO":  {"value": 102109.73, "pnl": 12079.06, "pnl_pct": 13.42, "shares": 175.157486},
    "BIL":  {"value": 91629.97,  "pnl": 8681.28,  "pnl_pct": 10.47, "shares": 1000},
    "QQQ":  {"value": 76310.31,  "pnl": 8740.33,  "pnl_pct": 12.94, "shares": 135.643587},
    "SCHD": {"value": 46025.07,  "pnl": 8970.72,  "pnl_pct": 24.21, "shares": 1512.010124},
    "AAPL": {"value": 19742.07,  "pnl": 6163.48,  "pnl_pct": 45.39, "shares": 79.349225},
    "O":    {"value": 17055.77,  "pnl": 2707.80,  "pnl_pct": 18.87, "shares": 281.032653},
    "JEPI": {"value": 14113.35,  "pnl": 1233.91,  "pnl_pct": 9.58,  "shares": 254.066847},
    "SOXX": {"value": 9992.24,   "pnl": 4322.33,  "pnl_pct": 76.23, "shares": 30.889879},
    "TSLA": {"value": 9744.64,   "pnl": -759.24,  "pnl_pct": -7.23, "shares": 26.931576},
    "TLT":  {"value": 8563.99,   "pnl": 158.81,   "pnl_pct": 1.89,  "shares": 100},
    "NVDA": {"value": 8158.30,   "pnl": 130.27,   "pnl_pct": 1.62,  "shares": 48.700507},
    "PLTR": {"value": 8129.98,   "pnl": 313.74,   "pnl_pct": 4.01,  "shares": 56.829293},
    "SPY":  {"value": 5635.49,   "pnl": 1112.34,  "pnl_pct": 24.59, "shares": 8.887535},
    "UNH":  {"value": 4662.36,   "pnl": -400.56,  "pnl_pct": -7.91, "shares": 18},
    "MSFT": {"value": 4280.89,   "pnl": -431.73,  "pnl_pct": -9.16, "shares": 11.999013},
    "GOOGL":{"value": 2929.09,   "pnl": -246.18,  "pnl_pct": -7.75, "shares": 10.676876},
    "AMZN": {"value": 1165.77,   "pnl": -54.17,   "pnl_pct": -4.44, "shares": 5.84814},
    "SLV":  {"value": 761.28,    "pnl": -10.22,   "pnl_pct": -1.32, "shares": 12},
    "TQQQ": {"value": 290.25,    "pnl": -25.88,   "pnl_pct": -8.19, "shares": 5},
    "SOXL": {"value": 233.05,    "pnl": -35.06,   "pnl_pct": -13.08,"shares": 5},
    "ETHU": {"value": 201.60,    "pnl": -57.98,   "pnl_pct": -22.34,"shares": 10},
    "CRCL": {"value": 93.66,     "pnl": -30.15,   "pnl_pct": -24.35,"shares": 1},
    "BTDR": {"value": 18.39,     "pnl": -11.40,   "pnl_pct": -38.26,"shares": 1},
}
EXPECTED_TOTAL = 431847.25  # 허용 오차: ±500
EXPECTED_COUNT = 23
```

### 1.2 단위 테스트 (tests/test_ocr_parser.py)
```python
# 테스트 항목 및 검증 기준

class TestOCRParser:

    def test_clean_dollar_spacing(self):
        """달러 금액 내 공백 제거 검증"""
        # 입력: "$1 7,055.77" → 기대: "$17,055.77"
        # 입력: "$91,629.97" → 기대: "$91,629.97" (정상값 보존)
        # 입력: "$1,165.77" → 기대: "$1,165.77" (1천대 보존)
        # 검증: assert clean_dollar("$1 7,055.77") == "$17,055.77"

    def test_ticker_mapping_completeness(self):
        """23개 종목 매핑 존재 확인"""
        # 검증: 매핑 테이블에 23개 이상의 한글→티커 쌍 존재
        # 검증: "iShares 2 ETF" → "SLV" 매핑 존재 (OCR 보정)

    def test_ticker_mapping_priority(self):
        """긴 문자열 우선 매칭 확인"""
        # "iShares 20+ Year" → TLT (not SLV)
        # "iShares 2 ETF" → SLV (not TLT)
        # "SPDR S&P 500" → SPY (not VOO)

    def test_parse_screenshot_images(self):
        """실제 스크린샷 3장 파싱 → 23개 종목 정확도 검증"""
        # 스크린샷 파일이 없으면 skip (CI 환경)
        # 파일이 있으면:
        #   검증 1: 파싱된 종목 수 == 23
        #   검증 2: 각 종목 value_usd 오차 < $1.00
        #   검증 3: 총합 오차 < $500

    def test_parse_with_fixture_text(self):
        """OCR 출력 텍스트를 fixture로 저장하여 이미지 없이도 테스트"""
        # tests/fixtures/toss_ocr_output.txt에 실제 OCR 텍스트 저장
        # 이 텍스트로 파싱 → 동일한 정확도 검증
        # 검증: 23개 종목, 각 value 오차 < $1.00

    def test_output_json_format(self):
        """portfolio.json 출력 포맷 검증"""
        # 필수 키: updated_at, source, total_value_usd, holdings
        # holdings 각 항목: ticker, value_usd, pnl_usd, pnl_pct, shares
        # 모든 숫자 필드가 None이 아닌 실수값

    def test_duplicate_removal(self):
        """중복 종목 제거 검증 (스크린샷 겹침)"""
        # MSFT가 Image 1, Image 2에 모두 등장 → 1개만 남아야 함
        # 검증: 파싱 결과에서 ticker 중복 없음
```

### 1.3 OCR 텍스트 Fixture 생성
```
# tests/fixtures/toss_ocr_output.txt
# 실제 Tesseract 출력을 저장하여 이미지 없이도 파서 테스트 가능
# Claude Code가 스크린샷으로 OCR을 실행하고 결과를 이 파일에 저장
# 이후 테스트는 이 fixture를 사용
```

### 1.4 검증 실행 및 판정
```bash
pytest tests/test_ocr_parser.py -v --tb=short

# 합격 기준:
# - 전체 테스트 PASSED
# - 종목 인식률 23/23 = 100%
# - 금액 정확도: 각 종목 오차 < $1.00
# - 총합 오차 < $500

# 실패 시 자동 수정 절차:
# 1. 실패한 종목 확인 → 한글 매핑 누락이면 tickers.yaml에 추가
# 2. 금액 오류면 clean_dollar() 정규식 패턴 확장
# 3. 재테스트 (최대 3회)
```

---

## Phase 2: 시장 데이터 검증 (src/market_data.py)

### 2.1 단위 테스트 (tests/test_market_data.py)
```python
class TestMarketData:

    def test_fetch_single_ticker(self):
        """개별 종목 데이터 수집 검증"""
        # yfinance로 AAPL 데이터 수집
        # 검증: price > 0, ma20 > 0, rsi 0-100 범위, macd 존재

    def test_fetch_macro_indicators(self):
        """매크로 지표 수집 검증"""
        # ^VIX, ^TYX, USDKRW=X 수집
        # 검증: 각 값이 합리적 범위
        #   VIX: 5-80, 30Y yield: 2-8%, USDKRW: 1100-1600

    def test_master_switch_calculation(self):
        """마스터 스위치 상태 계산 검증"""
        # 현재 실제 데이터 기준:
        #   QQQ $587 < MA200 $592 → below
        #   SPY $645 < MA200 $657 → below
        #   → status = "RED"
        # 검증: master_switch.status == "RED"

    def test_technical_indicators_calculation(self):
        """기술지표 계산 정확성"""
        # RSI(14) 범위: 0-100
        # MACD: macd, signal, histogram 3개 값 존재
        # BB: upper > ma20 > lower
        # MA: ma200 < ma50 또는 ma50 < ma20 (추세 확인)

    def test_output_format(self):
        """market_cache.json 출력 포맷 검증"""
        # 필수 키: updated_at, master_switch, macro, tickers
        # master_switch: qqq_price, spy_price, status 등
        # macro: vix, treasury_30y, usdkrw
        # tickers: 각 종목별 price, ma20, rsi, macd 등

    def test_yfinance_error_handling(self):
        """yfinance 실패 시 에러 핸들링"""
        # 존재하지 않는 티커 "XXXXX" 조회
        # 검증: 예외 발생 안 함, 에러 로그 출력, 해당 종목 skip

    def test_cache_fallback(self):
        """네트워크 실패 시 캐시 사용 검증"""
        # 기존 market_cache.json이 있는 상태에서 fetch 실패
        # 검증: 캐시 데이터 반환, 경고 로그 출력
```

### 2.2 Mock 데이터 (네트워크 없는 환경용)
```python
# tests/fixtures/mock_market_data.json
# yfinance 접근이 안 되는 CI/테스트 환경에서 사용
# 2026-03-28 실제 데이터 기반으로 고정값 제공
{
    "master_switch": {
        "qqq_price": 587.82, "qqq_ma200": 592.43, "qqq_above_ma200": false,
        "spy_price": 645.09, "spy_ma200": 657.19, "spy_above_ma200": false,
        "status": "RED"
    },
    "macro": {
        "vix": 30.91, "vix_tier": "high",
        "treasury_30y": 4.982, "usdkrw": 1425.50
    },
    "tickers": {
        "TSLA": {"price": 361.88, "ma20": 378.50, "ma50": 395.20, "ma200": 310.00,
                 "rsi": 38.2, "macd": -3.44, "macd_signal": -1.82, "macd_histogram": -1.62,
                 "bb_upper": 410.50, "bb_lower": 346.50, "volume_ratio": 0.87},
        "NVDA": {"price": 167.55, "ma20": 172.30, "ma50": 180.10, "ma200": 135.00,
                 "rsi": 35.8, "macd": -2.10, "macd_signal": -1.50, "macd_histogram": -0.60,
                 "bb_upper": 195.00, "bb_lower": 155.00, "volume_ratio": 0.92},
        "QQQ":  {"price": 587.82, "ma20": 599.66, "ma50": 608.66, "ma200": 592.43,
                 "rsi": 34.75, "macd": -7.12, "macd_signal": -5.80, "macd_histogram": -1.32,
                 "bb_upper": 635.00, "bb_lower": 565.00, "volume_ratio": 1.05},
        "TLT":  {"price": 85.64, "ma20": 87.20, "ma50": 88.50, "ma200": 90.10,
                 "rsi": 34.0, "macd": -0.80, "macd_signal": -0.60, "macd_histogram": -0.20,
                 "bb_upper": 92.00, "bb_lower": 83.00, "volume_ratio": 1.10},
        "VOO":  {"price": 582.50, "ma20": 595.00, "ma50": 605.00, "ma200": 570.00,
                 "rsi": 36.5, "macd": -5.20, "macd_signal": -4.10, "macd_histogram": -1.10,
                 "bb_upper": 625.00, "bb_lower": 560.00, "volume_ratio": 0.95}
    }
}
```

### 2.3 검증 실행
```bash
pytest tests/test_market_data.py -v --tb=short

# yfinance 접근 불가 시: mock fixture 자동 사용
# 합격 기준: 전체 테스트 PASSED
# 실패 시: yfinance API 변경 대응, 지표 계산 로직 수정
```

---

## Phase 3: 규칙 엔진 검증 (src/rule_engine.py)

### 3.1 시나리오 기반 테스트 (tests/test_rule_engine.py)
```python
class TestMasterSwitch:

    def test_red_both_below(self):
        """QQQ, SPY 모두 MA200 아래 → RED"""
        # 입력: qqq=587, qqq_ma200=592, spy=645, spy_ma200=657
        # 검증: status == "RED", allocation_multiplier == 0.0

    def test_green_both_above(self):
        """QQQ, SPY 모두 MA200 위 → GREEN"""
        # 입력: qqq=620, qqq_ma200=592, spy=670, spy_ma200=657
        # 검증: status == "GREEN", allocation_multiplier == 1.0

    def test_yellow_one_above(self):
        """하나만 MA200 위 → YELLOW"""
        # 입력: qqq=600, qqq_ma200=592, spy=645, spy_ma200=657
        # 검증: status == "YELLOW", allocation_multiplier == 0.5

    def test_vix_override_tier1(self):
        """VIX 25-30 → allocation x0.7"""
        # 입력: vix=27, base_multiplier=1.0
        # 검증: final_multiplier == 0.7

    def test_vix_override_tier2(self):
        """VIX 30-35 → allocation x0.5"""
        # 입력: vix=31, base_multiplier=1.0
        # 검증: final_multiplier == 0.5

    def test_vix_override_tier3(self):
        """VIX > 35 → 전체 Exit L1 트리거"""
        # 입력: vix=38
        # 검증: all positions get L1 warning


class TestGrowthStrategy:

    def test_tranche1_conditions_met(self):
        """성장주 1차 매수 조건 충족"""
        # TSLA: macd_hist_rising_2d=True, rsi=36, adx=22, near_bb_lower=True
        # 검증: signal == "TRANCHE_1_BUY", 3/6 선택조건 + 필수조건 충족

    def test_tranche1_veto_rsi_high(self):
        """RSI > 50이면 1차 매수 거부"""
        # TSLA: 모든 조건 충족이지만 rsi=55
        # 검증: signal != "TRANCHE_1_BUY", veto 사유 표시

    def test_tranche1_blocked_by_master_red(self):
        """마스터 스위치 RED → 모든 주식 매수 차단"""
        # 마스터: RED, TSLA: 1차 조건 충족
        # 검증: signal == "BLOCKED_BY_MASTER", not "TRANCHE_1_BUY"

    def test_tranche2_all_conditions(self):
        """2차 매수: 4개 조건 ALL 충족 필요"""
        # 검증: 4개 중 3개만 충족 → 거부, 4개 모두 충족 → 승인

    def test_tranche_sequence(self):
        """1차 → 2차 → 3차 순서 강제"""
        # 1차 미완료 상태에서 2차 조건 충족 → 거부
        # 검증: 반드시 순차 진행


class TestETFStrategy:

    def test_tranche1_pick3(self):
        """ETF 1차: 5개 중 3개 선택 충족"""
        # QQQ: rsi=34, below_ma20=True, near_bb_lower=True
        # 검증: 3/5 충족 → signal == "TRANCHE_1_BUY"

    def test_tranche1_only2_met(self):
        """2개만 충족 → 매수 안 됨"""
        # QQQ: rsi=34, below_ma20=True (2개만)
        # 검증: signal == "HOLD"


class TestBondStrategy:

    def test_bond_independent_of_master(self):
        """채권 전략은 마스터 스위치 무시"""
        # 마스터: RED, treasury_30y=5.1, tlt_rsi=33
        # 검증: signal == "TRANCHE_1_BUY" (마스터 RED인데도 매수)

    def test_bond_trigger_at_5pct(self):
        """30Y 금리 5.0% 도달 시 1차 매수"""
        # treasury_30y=5.01, tlt_rsi=34
        # 검증: signal == "TRANCHE_1_BUY"

    def test_bond_below_threshold(self):
        """30Y 금리 5.0% 미만 → 대기"""
        # treasury_30y=4.98, tlt_rsi=34
        # 검증: signal == "WATCH" or "HOLD"


class TestExitSystem:

    def test_exit_L1_two_conditions(self):
        """Exit L1: 4개 중 2개 충족 → 경고"""
        # macd_hist_declining_2d + rsi_turned_from_65
        # 검증: exit_level == "L1", action includes "신규 매수 금지"

    def test_exit_L2_triggers_trim(self):
        """Exit L2: 2개 충족 → 30% 트림 권고"""
        # macd_hist_declining_3d + rsi_lower_high
        # 검증: exit_level == "L2", action includes "30% 익절"

    def test_exit_L3_any_one(self):
        """Exit L3: 1개라도 충족 → 전량 매도"""
        # drawdown_8pct_from_peak만 충족
        # 검증: exit_level == "L3", action includes "전량 매도"

    def test_top_signal_rsi75(self):
        """RSI >= 75 → 강제 익절"""
        # rsi=78
        # 검증: top_signal == True

    def test_no_exit_normal_conditions(self):
        """정상 상태 → 퇴출 신호 없음"""
        # rsi=50, macd_hist rising, above ma20
        # 검증: exit_level == None


class TestRebalanceChecker:

    def test_overweight_detection(self):
        """단일 종목 15% 초과 감지"""
        # VOO: $102,110 / $431,847 = 23.6%
        # 검증: alert includes "VOO overweight 23.6% > 15%"

    def test_dividend_limit_warning(self):
        """배당소득 18M KRW 임박 경고"""
        # projected_annual_dividend = 17,500,000 KRW
        # 검증: alert includes "배당소득 한도 임박"
```

### 3.2 현재 실제 포트폴리오 기대 결과
```python
# tests/fixtures/expected_signals_20260328.py
# 2026-03-28 실제 데이터 기준 기대되는 시그널

EXPECTED_MASTER_SWITCH = "RED"  # QQQ, SPY 모두 MA200 아래
EXPECTED_VIX_TIER = "high"     # VIX 30.91

EXPECTED_SIGNALS = {
    # 마스터 RED → 모든 주식 신규 매수 차단
    "VOO":  {"action": "HOLD",       "reason": "master RED, 기존 보유 유지"},
    "BIL":  {"action": "HOLD",       "reason": "단기채, 현금 대용 유지"},
    "QQQ":  {"action": "HOLD",       "reason": "master RED, MA200 아래"},
    "TSLA": {"action": "L1_WARNING", "reason": "MACD hist declining, RSI 하락"},  # 또는 HOLD
    "TLT":  {"action": "WATCH",      "reason": "30Y 4.98%, 5.0% 트리거 임박"},
    "ETHU": {"action": "L2_WARNING", "reason": "22% 손실, MACD 하락 지속"},  # 또는 HOLD

    # 리밸런싱 경고
    "rebalance": [
        "VOO overweight: 23.6% > 15% threshold",
        "BIL overweight: 21.2% > 15% threshold",
    ]
}
```

### 3.3 검증 실행
```bash
pytest tests/test_rule_engine.py -v --tb=short
pytest tests/test_signal_generator.py -v --tb=short

# 합격 기준:
# - 마스터 스위치 RED 정확 판정
# - 성장주/ETF/채권 전략 로직 정상 작동
# - Exit L1/L2/L3 에스컬레이션 정확
# - 리밸런싱 트리거 정상 감지
# - 한국어 템플릿 근거 생성 확인

# 실패 시:
# 1. 조건 판정 로직 확인 → strategy_v3.yaml과 코드 불일치 수정
# 2. 경계값 오류 (>=, >) 확인
# 3. 재테스트
```

---

## Phase 4: 시그널 생성 통합 검증

### 4.1 End-to-End 파이프라인 테스트
```python
# tests/test_integration.py

class TestFullPipeline:

    def test_portfolio_to_signals(self):
        """portfolio.json + market_data → signals.json 전체 흐름"""
        # 1. data/portfolio.json 로드 (실제 23개 종목)
        # 2. data/market_cache.json 로드 (mock 또는 실제)
        # 3. rule_engine 실행
        # 4. signal_generator 실행
        # 5. signals.json 출력 검증

        # 검증:
        # - signals.json 생성됨
        # - signals.date == "2026-03-28"
        # - signals.master_switch == "RED"
        # - signals.signals 리스트에 23개 종목 존재
        # - 각 signal에 ticker, action, confidence, rationale 존재
        # - confidence 범위: 0-100
        # - rationale이 비어있지 않은 한국어 문자열

    def test_confidence_scores_reasonable(self):
        """확신도 점수가 합리적 범위"""
        # RED 마스터 → HOLD 종목의 confidence가 40-70 범위
        # 경고 종목의 confidence가 60-90 범위
        # WATCH 종목의 confidence가 30-60 범위

    def test_signals_json_schema(self):
        """signals.json 스키마 검증"""
        # 필수 키: date, master_switch, vix_tier, signals, macro_alerts
        # signals 배열: ticker, classification, action, confidence, rationale,
        #               conditions_met, conditions_not_met

    def test_history_append(self):
        """history.json에 일별 스냅샷 추가 확인"""
        # 파이프라인 2회 실행
        # 검증: history.json에 2개 항목 존재, 날짜 다름
```

### 4.2 실행
```bash
pytest tests/test_integration.py -v --tb=short

# 합격 기준: 전체 PASSED
# 실패 시: 모듈 간 인터페이스 (JSON 키 이름, 데이터 타입) 불일치 수정
```

---

## Phase 5: 대시보드 검증 (dashboard/)

### 5.1 Streamlit 로컬 실행 + 자동 검증
```bash
# 대시보드를 백그라운드로 실행
cd dashboard
streamlit run app.py --server.port 8501 --server.headless true &
STREAMLIT_PID=$!
sleep 10  # 서버 기동 대기

# 페이지 접근 가능 확인
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
# 검증: 200 OK

# 스크린샷 캡처 (playwright 사용)
pip install playwright
playwright install chromium
python tests/capture_dashboard.py

# 서버 종료
kill $STREAMLIT_PID
```

### 5.2 대시보드 자동 캡처 스크립트
```python
# tests/capture_dashboard.py
"""
Streamlit 대시보드의 각 페이지를 캡처하여 시각적 검증용 스크린샷 저장.
Claude Code가 이 스크린샷을 확인하여 레이아웃, 데이터 표시, 차트 렌더링을 검증.
"""

import asyncio
from playwright.async_api import async_playwright

PAGES = [
    ("http://localhost:8501", "overview"),
    ("http://localhost:8501/Ticker_Detail", "ticker_detail"),
    ("http://localhost:8501/Signals", "signals"),
]

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for url, name in PAGES:
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)  # 차트 렌더링 대기
            await page.screenshot(path=f"tests/screenshots/{name}.png", full_page=True)
            print(f"Captured: {name}.png")
        await browser.close()

asyncio.run(capture())
```

### 5.3 대시보드 시각 검증 체크리스트
```
Claude Code는 캡처된 스크린샷을 직접 확인하여 아래 항목을 검증합니다:

[Overview 페이지]
□ 마스터 스위치 "RED" 배지 표시
□ 총자산 메트릭 카드에 ~$431,847 표시
□ 포트폴리오 트렌드 차트 렌더링 (빈 차트 아님)
□ 보유 종목 테이블에 23개 행 (또는 스크롤 가능)
□ VOO가 최상단 (금액 기준 정렬)
□ 시그널 요약 카드 1개 이상 표시
□ 매크로 지표 (QQQ/SPY/VIX) 표시

[Ticker Detail 페이지]
□ 종목 선택 드롭다운 동작
□ 가격 차트 렌더링 (빈 차트 아님)
□ RSI 패널 표시 (30/70 기준선 포함)
□ MACD 패널 표시 (히스토그램 + 라인)
□ 거래량 패널 표시
□ 전략 단계 프로그레스 표시

[Signals 페이지]
□ 마스터 스위치 배너 표시
□ 요약 카드 (경고/관심/매수/홀드 수)
□ 시그널 카드에 티커, 배지, 확신도 바 표시
□ 한국어 근거 텍스트 정상 렌더링
□ 조건 태그 (충족=녹색, 미충족=회색) 표시
□ HOLD 종목 그리드 축약 표시

검증 방법: Claude Code가 screenshot을 view 도구로 직접 확인하여 체크
```

### 5.4 대시보드 데이터 정합성 테스트
```python
# tests/test_dashboard_data.py

class TestDashboardData:

    def test_overview_total_matches_portfolio(self):
        """Overview 총자산 == portfolio.json 총합"""
        # dashboard에 표시되는 총자산과 portfolio.json의 total_value_usd 비교

    def test_ticker_detail_data_available(self):
        """23개 종목 모두 Ticker Detail에서 선택 가능"""
        # selectbox의 옵션 수 == 23

    def test_signals_count_matches(self):
        """Signals 페이지 표시 수 == signals.json 항목 수"""

    def test_chart_has_data_points(self):
        """트렌드 차트에 데이터 포인트가 1개 이상"""
        # history.json에 항목이 있으면 차트 렌더링
```

---

## Phase 6: GitHub Actions 워크플로우 검증

### 6.1 워크플로우 문법 검증
```bash
# actionlint 설치 및 실행
pip install check-jsonschema
python -c "
import yaml
for f in ['.github/workflows/daily_report.yml', '.github/workflows/telegram_trigger.yml']:
    with open(f) as fh:
        data = yaml.safe_load(fh)
        # 필수 키 확인
        assert 'on' in data, f'{f}: missing on trigger'
        assert 'jobs' in data, f'{f}: missing jobs'
        print(f'{f}: YAML valid')
"

# 검증 기준:
# - YAML 문법 정상
# - daily_report: cron '0 22 * * *' 존재
# - telegram_trigger: repository_dispatch 존재
# - 두 워크플로우 모두 python setup, pip install, git commit 단계 포함
```

### 6.2 텔레그램 봇 로직 검증 (실제 전송 없이)
```python
# tests/test_telegram_bot.py

class TestTelegramBot:

    def test_notification_message_format(self):
        """알림 메시지 포맷 검증"""
        # signals.json 기반으로 메시지 생성
        # 검증: 총자산, 마스터 스위치, 주요 시그널, 대시보드 URL 포함
        # 검증: 메시지 길이 < 4096 (Telegram 제한)

    def test_message_includes_warnings(self):
        """경고 시그널이 메시지에 포함"""
        # L1/L2 경고가 있으면 메시지에 표시

    def test_message_includes_dashboard_url(self):
        """대시보드 URL 포함"""
        # https://*.streamlit.app 형식 URL 존재

    def test_empty_signals_handling(self):
        """시그널 없을 때 메시지 정상 생성"""
        # 모든 종목 HOLD → "특이 시그널 없음" 메시지
```

---

## Phase 7: 전체 통합 테스트

### 7.1 Full Pipeline Smoke Test
```bash
#!/bin/bash
# tests/smoke_test.sh — 전체 파이프라인 1회 실행

set -e  # 에러 시 즉시 중단

echo "=== Step 1: Market Data ==="
python src/market_data.py
cat data/market_cache.json | python -m json.tool | head -20

echo "=== Step 2: Rule Engine ==="
python src/rule_engine.py
echo "Rule engine completed"

echo "=== Step 3: Signal Generator ==="
python src/signal_generator.py
cat data/signals.json | python -m json.tool | head -30

echo "=== Step 4: Dashboard Data Check ==="
python -c "
import json
with open('data/signals.json') as f:
    s = json.load(f)
print(f'Date: {s[\"date\"]}')
print(f'Master: {s[\"master_switch\"]}')
print(f'Signals: {len(s[\"signals\"])} tickers')
for sig in s['signals'][:5]:
    print(f'  {sig[\"ticker\"]:6s} | {sig[\"action\"]:12s} | {sig[\"confidence\"]}% | {sig[\"rationale\"][:50]}...')
"

echo "=== Step 5: Pytest ==="
pytest tests/ -v --tb=short -q

echo "=== ALL SMOKE TESTS PASSED ==="
```

### 7.2 최종 합격 기준
```
전체 시스템 검증 합격 조건:

[필수]
✅ pytest 전체 통과 (0 failures)
✅ 23개 종목 모두 signals.json에 존재
✅ 마스터 스위치 RED 정확 판정
✅ portfolio.json 총자산 오차 < $500
✅ signals.json 스키마 완전
✅ 대시보드 3페이지 모두 200 OK
✅ GitHub Actions YAML 문법 정상
✅ 텔레그램 메시지 포맷 정상

[권장]
☑ 대시보드 스크린샷 시각 검증 통과
☑ 히스토리 append 동작 확인
☑ 에러 핸들링 (yfinance 실패, OCR 실패) 정상
☑ 캐시 fallback 동작 확인
```

---

## 검증 자동 실행 명령 (Claude Code용)

```
이 프로젝트의 VALIDATION_PLAN.md를 읽고 Phase 0부터 Phase 7까지 순서대로 검증을 진행해줘.

각 Phase에서:
1. 테스트를 실행
2. 실패하면 원인을 분석하고 코드를 수정
3. 수정 후 재테스트 (최대 3회)
4. 모든 테스트가 통과하면 다음 Phase로

Phase 5 (대시보드)에서는:
- Streamlit을 로컬로 실행
- playwright로 3페이지 스크린샷 캡처
- 캡처된 이미지를 직접 확인하여 시각 검증 체크리스트 통과 확인

전체 Phase 완료 후 최종 결과 요약을 출력해줘.
```
