# 대시보드 디자인 수정 지시서 (Visual Fix Guide)

> Claude Code가 이 문서를 읽고, docs/design_reference/ 폴더의 이미지와 HTML을 참조하여 대시보드를 수정합니다.
> 목표: overview_target.png(또는 overview_target.html)과 **완전히 동일한** 화면을 Streamlit에서 구현

---

## 사용법

```bash
# 1. 이 파일들을 프로젝트에 복사
cp overview_target.html docs/design_reference/
cp overview_target.png docs/design_reference/
cp VISUAL_FIX_GUIDE.md docs/

# 2. Claude Code에서 실행
claude "docs/VISUAL_FIX_GUIDE.md를 읽고, docs/design_reference/overview_target.html을 열어서
       이 HTML과 완전히 동일한 화면을 Streamlit에서 구현해줘.
       현재 대시보드와 차이가 있는 부분을 모두 수정해."
```

---

## 핵심 원칙

1. **overview_target.html이 정답**: 이 HTML 파일의 모든 색상, 간격, 폰트, 레이아웃을 Streamlit에서 그대로 재현
2. **모든 UI는 st.markdown(unsafe_allow_html=True)로**: st.metric(), st.dataframe() 등 Streamlit 기본 위젯 사용 금지
3. **Plotly만 예외**: 차트만 st.plotly_chart() 사용 허용
4. **라이트 모드 고정**: .streamlit/config.toml에 base="light" 필수

---

## 수정 체크리스트 (12개 항목)

### Critical — 시그널 로직 수정 (가장 먼저)

#### FIX-1: 시그널 판정 로직 수정
- **문제**: 거의 모든 종목이 "L3 BREAKDOWN" 또는 "TOP SIGNAL"로 표시됨
- **원인**: exit 조건이 너무 공격적이거나, mock 데이터 해석이 잘못됨
- **정답 기준** (overview_target.html의 Market 컬럼):
  - VOO: HOLD, BIL: CASH, QQQ: HOLD, SCHD: HOLD
  - TSLA: L1 WARN (MACD hist declining 2d)
  - TLT: BOND WATCH (30Y 금리 4.98%, 5.0% 미도달)
  - NVDA: HOLD, ETHU: L2 WEAK
  - 나머지 대부분: HOLD (마스터 RED → 주식 매수 전면 차단)
- **수정**: rule_engine.py의 exit 조건 임계값 검토. mock_market_data.json의 값으로 테스트 시 위 결과가 나와야 함

#### FIX-2: Market vs Technical 분리 작동
- **문제**: 두 컬럼이 완전히 동일한 값
- **정답 기준** (overview_target.html 참조):
  - Market: 마스터 RED 반영 → 대부분 HOLD
  - Technical: 마스터 무시 → TLT=1st BUY, SLV=1st BUY, NVDA=WATCH, QQQ=BLOCKED
- **수정**: signal_generator.py에서 mode="full" vs mode="technical_only" 분기 확인
  - full 모드: 마스터 스위치 RED면 bond/gold 외 모든 주식 → HOLD
  - technical_only 모드: 마스터 스위치 무시, 순수 기술지표로만 판단

### Critical — 누락 섹션 추가

#### FIX-3: 듀얼 시그널 카드 섹션 추가
- **문제**: 테이블 아래에 Market/Technical 시그널 카드가 없음
- **정답**: overview_target.html의 하단 "Market signals / Technical signals" 2열 섹션
- **구현**: st.columns(2) + st.markdown(signal_card HTML)

#### FIX-4: Signal reference 인덱스 추가
- **문제**: 페이지 최하단에 시그널 설명 인덱스가 없음
- **정답**: overview_target.html의 최하단 "Signal reference" 패널
- **구현**: components.py의 signal_index_html() 함수 호출

### Styling — 카드 스타일

#### FIX-5: 메트릭 카드 배경
- **현재**: 흰색 배경 + 눈에 띄는 테두리
- **정답**: background: #F8F9FA, border: none, border-radius: 8px
- **수정**: HTML에서 style="background:#F8F9FA;border:none;border-radius:8px"

#### FIX-6: 매크로 지표 카드 동일
- **현재**: 흰색 + 테두리
- **정답**: background: #F8F9FA, border: none, text-align: center

### Styling — 테이블

#### FIX-7: 종목명 서브타이틀 추가
- **현재**: "VOO" 한 줄만 표시
- **정답**: "VOO" (bold 12px) + 줄바꿈 + "Vanguard S&P 500" (gray 10px)
- **수정**: `<span class="tk">VOO</span><br><span class="nm">Vanguard S&P 500</span>`

#### FIX-8: Weight 바 높이
- **현재**: 약간 두꺼운 바
- **정답**: height: 5px, border-radius: 3px

### Styling — 헤더

#### FIX-9: 사이드바 페이지명 "app" → "Overview"
- **수정방법**: app.py 파일명을 변경하거나, Streamlit의 page config 활용
  - 가장 확실한 방법: `dashboard/app.py` → `dashboard/0_Overview.py`로 변경하고 메인 엔트리로 설정
  - 또는 `.streamlit/config.toml`에 추가하거나 st.set_page_config() 활용

#### FIX-10: 날짜 포맷
- **현재**: "2026-03-28T07:00:00+09:00"
- **정답**: "2026-03-28 07:00 KST"
- **수정**: datetime 파싱 후 strftime("%Y-%m-%d %H:%M KST")

#### FIX-11: USD/KRW 토글 스타일
- **현재**: Streamlit 기본 radio button
- **정답**: 커스텀 pill 토글 (overview_target.html의 `.tg` 클래스 참조)
- **수정**: st.radio를 유지하되, label_visibility="collapsed" + CSS 오버라이드
  또는 st.markdown + JavaScript로 토글 구현 (Streamlit에서 JS 제한적이므로 st.radio + CSS가 현실적)

#### FIX-12: 기존 Signals 페이지 삭제
- dashboard/pages/ 에서 이전 단일 Signals 페이지 파일 삭제
- 최종 페이지: Overview, Ticker Detail, Market Signals, Technical Signals (4개만)
- 사이드바 설정 섹션(테스트 모드, HOLD 토글, 분류 필터) 모두 제거

---

## 참조 파일

| 파일 | 용도 |
|------|------|
| docs/design_reference/overview_target.html | **정답 HTML** — 브라우저에서 열어서 비교용 |
| docs/design_reference/overview_target.png | **정답 스크린샷** — 시각적 비교용 |

Claude Code는 overview_target.html을 직접 열어서 구조, CSS, 색상 코드를 확인하고
현재 dashboard/app.py를 이 HTML과 동일하게 수정합니다.

---

## 수정 순서 (권장)

1. FIX-1, FIX-2: 시그널 로직 수정 (rule_engine.py, signal_generator.py)
2. FIX-12: 불필요 페이지 삭제, 사이드바 정리
3. FIX-5, FIX-6: 카드 배경색 수정
4. FIX-7, FIX-8: 테이블 스타일 수정
5. FIX-9, FIX-10, FIX-11: 헤더/사이드바 수정
6. FIX-3, FIX-4: 듀얼 시그널 섹션 + 인덱스 추가
7. Streamlit 로컬 실행 → 스크린샷 → overview_target.png와 비교 → 차이 수정

---

## 검증 방법

```bash
# Streamlit 실행
USE_MOCK_DATA=true streamlit run dashboard/app.py --server.port 8501

# playwright로 캡처
python3 -c "
import asyncio
from playwright.async_api import async_playwright
async def cap():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':960,'height':2400})
        await pg.goto('http://localhost:8501')
        await pg.wait_for_timeout(5000)
        await pg.screenshot(path='docs/design_reference/current_overview.png', full_page=True)
        await b.close()
asyncio.run(cap())
"

# Claude Code가 두 이미지를 비교:
# view docs/design_reference/overview_target.png
# view docs/design_reference/current_overview.png
# 차이가 있으면 수정 반복
```
