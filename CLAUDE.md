# CLAUDE.md — AI Trading Assistant 프로젝트 지시서

> 이 파일은 Claude Code가 프로젝트를 이해하고 자율적으로 구현을 진행하기 위한 지시서입니다.
> 전체 기획서: `AI_TRADING_ASSISTANT_SPEC.md` 참조

---

## 프로젝트 개요

토스증권 포트폴리오를 자동 분석하여 매일 매수/매도/대기 시그널을 생성하는 **$0/월 완전 자동화 시스템**.

핵심 구성:
1. **Telegram bot** → 토스 스크린샷 수신 → Tesseract OCR 파싱
2. **yfinance** → 시장 데이터 + 기술지표 수집
3. **Rule engine (v3.0)** → 전략 규칙 기반 시그널 생성 (Claude API 미사용)
4. **Streamlit dashboard** → 포트폴리오 + 트렌드 차트 + 시그널 표시
5. **GitHub Actions** → 매일 7AM KST 자동 실행 + 텔레그램 알림

## 구현 순서

**반드시 Sprint 순서대로 진행. 각 Sprint 완료 후 테스트 확인.**

### Sprint 1: Foundation
1. 프로젝트 디렉토리 구조 생성 (`src/`, `dashboard/`, `config/`, `data/`, `tests/`, `.github/workflows/`)
2. `requirements.txt` 작성
3. `config/tickers.yaml` — 한글 → 티커 매핑 + 종목 분류
4. `config/strategy_v3.yaml` — 전체 전략 규칙 (SPEC.md 섹션 5 참조)
5. `config/thresholds.yaml` — 매크로 임계값
6. `src/ocr_parser.py` — Tesseract OCR 파서 (SPEC.md 섹션 3 참조, 100% 검증된 로직)
7. `src/market_data.py` — yfinance 래퍼 (SPEC.md 섹션 4 참조)
8. `data/portfolio.json` — 현재 23개 종목 초기 데이터 생성
9. 테스트: `tests/test_ocr_parser.py`, `tests/test_market_data.py`

### Sprint 2: Brain
1. `src/rule_engine.py` — 마스터 스위치 + 4개 전략(v2.2/v2.3/v2.4/v2.6) + Exit v2.5
2. `src/signal_generator.py` — 규칙 통합 + 확신도 점수 + 한국어 템플릿 근거
3. `src/rebalance_checker.py` — 4개 리밸런싱 트리거
4. 테스트: `tests/test_rule_engine.py`, `tests/test_signal_generator.py`

### Sprint 3: Dashboard
1. `dashboard/app.py` — Overview (메트릭 카드 + 포트폴리오 트렌드 차트 + 보유 테이블 + 시그널 요약)
2. `dashboard/pages/1_Ticker_Detail.py` — 멀티패널 기술 차트 (가격+BB, RSI, MACD, 거래량) + 전략 단계
3. `dashboard/pages/2_Signals.py` — 시그널 카드 (경고/관심/매수/홀드)
4. Streamlit Community Cloud 배포 설정

### Sprint 4: Automation
1. `src/telegram_bot.py` — 텔레그램 봇 (수신: 이미지, 발신: URL + 요약)
2. `.github/workflows/daily_report.yml` — cron 0 22 * * * UTC
3. `.github/workflows/telegram_trigger.yml` — repository_dispatch
4. End-to-end 테스트

## 기술 규칙

- Python 3.11+
- 한국어 주석/로그 사용
- type hints 필수
- 에러 핸들링: yfinance 실패 시 캐시 사용, OCR 실패 시 텔레그램 에러 알림
- 데이터 파일은 `data/` 디렉토리에 JSON으로 저장
- 설정 파일은 `config/` 디렉토리에 YAML로 관리
- git commit 메시지: `feat:`, `fix:`, `data:` 접두사 사용

## 차트 스펙 (Streamlit + Plotly)

### 포트폴리오 트렌드 차트
- 메인 라인: 총자산 area fill (teal)
- 보조 라인: 원가 기준선 (점선, light blue)
- 우측 Y축: 배당금 bar (amber)
- 이벤트 마커: 매수(삼각형), 매도(다이아몬드)
- 기간 선택: 1M/3M/6M/1Y
- 호버 툴팁: 날짜, 총가치, 원가, 손익(금액+%), 배당금

### 종목 기술 차트 (Plotly subplots, shared_xaxes=True, 4행)
- Row 1 (60%): 가격 + MA20 + MA50 + 볼린저 밴드 음영 + 매수 마커
- Row 2 (15%): RSI(14) + 70/30 기준선
- Row 3 (15%): MACD 히스토그램(초록/빨강) + MACD/Signal 라인
- Row 4 (10%): 거래량 바

## 현재 보유 종목 (23개, 실제 데이터 2026-03-28)

| Ticker | 한글명 | 금액($) | 분류 |
|--------|--------|---------|------|
| VOO | Vanguard S&P 500 | 102,110 | etf_v24 |
| BIL | SPDR 1-3 Month | 91,630 | bond_gold_v26 |
| QQQ | Invesco QQQ | 76,310 | etf_v24 |
| SCHD | Schwab Dividend | 46,025 | etf_v24 |
| AAPL | 애플 | 19,742 | growth_v22 |
| O | 리얼티 인컴 | 17,056 | energy_v23 |
| JEPI | JPMorgan Premium | 14,113 | etf_v24 |
| SOXX | iShares Semi | 9,992 | etf_v24 |
| TSLA | 테슬라 | 9,745 | growth_v22 |
| TLT | iShares 20+ Year | 8,564 | bond_gold_v26 |
| NVDA | 엔비디아 | 8,158 | growth_v22 |
| PLTR | 팔란티어 | 8,130 | growth_v22 |
| SPY | SPDR S&P 500 | 5,635 | etf_v24 |
| UNH | 유나이티드헬스 | 4,662 | energy_v23 |
| MSFT | 마이크로소프트 | 4,281 | growth_v22 |
| GOOGL | 알파벳 | 2,929 | growth_v22 |
| AMZN | 아마존 | 1,166 | growth_v22 |
| SLV | iShares Silver | 761 | bond_gold_v26 |
| TQQQ | ProShares 2x QQQ | 290 | speculative |
| SOXL | Direxion 3x Semi | 233 | speculative |
| ETHU | 이더리움 2X | 202 | speculative |
| CRCL | 써클 인터넷 | 94 | speculative |
| BTDR | 비트마인 | 18 | speculative |

## 현재 시장 상태 (테스트용 실제 데이터)
- QQQ: $587.82, MA200: $592.43 → MA200 아래
- SPY: $645.09, MA200: $657.19 → MA200 아래
- 마스터 스위치: RED
- VIX: 30.91
- 30Y 국채: 4.982%
- 총자산: ~$431,847
