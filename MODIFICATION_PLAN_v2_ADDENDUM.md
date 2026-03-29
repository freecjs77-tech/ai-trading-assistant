# MODIFICATION_PLAN_v2 — 추가 수정 사항 (Addendum)

> MODIFICATION_PLAN_v2.md와 함께 읽어주세요.
> 이 파일의 내용을 v2.md 수정 작업에 함께 반영합니다.

---

## M8: 사이드바 정리 + 페이지 이름 변경

### 삭제할 파일
```bash
# 기존 Signals 페이지 삭제 (Market Signals와 중복)
rm dashboard/pages/2_Signals.py
# 또는 파일명에 따라:
rm dashboard/pages/*Signals.py  # 이전 단일 Signals 페이지만 삭제
```

### 최종 페이지 구조
```
dashboard/
├── app.py                          # Overview (메인 페이지)
├── pages/
│   ├── 1_Ticker_Detail.py          # 종목별 상세
│   ├── 2_Market_Signals.py         # 시장 시그널 (마스터 스위치 반영)
│   └── 3_Technical_Signals.py      # 기술 시그널 (마스터 스위치 무시)
└── .streamlit/
    └── config.toml
```

### 사이드바 표시 이름 설정

Streamlit은 파일명의 숫자 접두사와 언더스코어를 자동 변환합니다.
`1_Ticker_Detail.py` → "Ticker Detail"로 표시.

메인 페이지(app.py)의 이름은 `st.set_page_config()`에서 설정:
```python
# dashboard/app.py 상단
st.set_page_config(
    page_title="Overview | AI Trading Assistant",
    page_icon="📊",
    layout="wide"
)
```

### 사이드바 설정 섹션 제거

기존 사이드바에 있던 설정 위젯들을 모두 삭제:
```python
# ❌ 삭제할 코드 (기존에 있던 것들)
# st.sidebar.toggle("테스트 모드 (mock 데이터)")
# st.sidebar.toggle("HOLD 종목 표시")
# st.sidebar.selectbox("분류 필터", ["전체 표시", ...])

# ✅ 사이드바는 페이지 메뉴만 남김 (Streamlit이 자동 생성)
# 추가 위젯 없음
```

### 사이드바 최종 모습
```
┌─────────────────┐
│ Overview        │  ← app.py (현재 페이지면 하이라이트)
│ Ticker Detail   │  ← pages/1_Ticker_Detail.py
│ Market Signals  │  ← pages/2_Market_Signals.py
│ Technical Signals│ ← pages/3_Technical_Signals.py
│                 │
│ (설정 섹션 없음) │
└─────────────────┘
```

### 테스트 모드 대체 방안
기존 사이드바의 "테스트 모드" 토글은 삭제하되, 기능은 환경변수로 대체:
```python
# 코드 내부에서 테스트 모드 판단
import os
USE_MOCK = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

# 실행 시:
# 실데이터: streamlit run app.py
# 테스트:   USE_MOCK_DATA=true streamlit run app.py
```

---

## 실행 명령 (Claude Code용 — v2.md 실행 시 함께 적용)

```
MODIFICATION_PLAN_v2.md와 MODIFICATION_PLAN_v2_ADDENDUM.md를 함께 읽고,
M1~M8을 순서대로 진행해줘.

M8 작업:
- 기존 Signals 단일 페이지 파일 삭제
- app.py의 page_title을 "Overview"로 변경
- 사이드바에서 설정 위젯(토글, 셀렉트박스) 모두 제거
- 테스트 모드는 환경변수 USE_MOCK_DATA로 전환
- 최종 사이드바: Overview / Ticker Detail / Market Signals / Technical Signals 4개만
```
