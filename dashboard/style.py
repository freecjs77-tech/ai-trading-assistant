"""
dashboard/style.py — 대시보드 공통 CSS 및 스타일 시스템
모든 페이지 상단에서 inject_css() 호출
"""

import streamlit as st

CUSTOM_CSS = """
<style>
/* 전체 레이아웃 */
.main .block-container { max-width: 960px; padding: 1rem 1rem; }

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
.signal-card-warn { border-left: 3px solid #A32D2D; border-radius: 0 12px 12px 0; }
.signal-card-watch { border-left: 3px solid #BA7517; border-radius: 0 12px 12px 0; }
.signal-card-buy { border-left: 3px solid #0F6E56; border-radius: 0 12px 12px 0; }
.signal-card-hold { border-left: 3px solid #888780; border-radius: 0 12px 12px 0; }

/* 배지(pill) */
.pill {
    display: inline-block;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 8px;
    margin-left: 4px;
}
.pill-sell { background: #FCEBEB; color: #791F1F; }
.pill-buy  { background: #EAF3DE; color: #27500A; }
.pill-hold { background: #F1EFE8; color: #5F5E5A; }
.pill-wait { background: #FAEEDA; color: #633806; }
.pill-bond { background: #E1F5EE; color: #085041; }

/* 마스터 스위치 배지 */
.switch-badge {
    display: inline-block;
    font-size: 12px;
    padding: 4px 12px;
    border-radius: 8px;
    font-weight: 500;
}
.switch-red    { background: #FCEBEB; color: #791F1F; }
.switch-green  { background: #EAF3DE; color: #27500A; }
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

/* 보유 테이블 */
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
.step-done { background: #EAF3DE; color: #27500A; border-radius: 4px; padding: 3px 8px; font-size: 12px; display: inline-block; margin: 2px; }
.step-cur  { background: #FAEEDA; color: #633806; border-radius: 4px; padding: 3px 8px; font-size: 12px; display: inline-block; margin: 2px; }
.step-lock { background: #f0f0f0; color: #999;    border-radius: 4px; padding: 3px 8px; font-size: 12px; display: inline-block; margin: 2px; }
</style>
"""


def inject_css():
    """모든 페이지 상단에서 호출"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
