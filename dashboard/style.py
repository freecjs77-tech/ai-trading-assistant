"""
dashboard/style.py — 공통 CSS (라이트 모드 전용)
모든 페이지 상단에서 inject_css() 호출
"""
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
.signal-card-warn  { border-left: 3px solid #A32D2D; border-radius: 0; }
.signal-card-watch { border-left: 3px solid #BA7517; border-radius: 0; }
.signal-card-buy   { border-left: 3px solid #0F6E56; border-radius: 0; }
.signal-card-hold  { border-left: 3px solid #888780; border-radius: 0; }

/* ── Badges / Pills ── */
.pill {
    display: inline-block; font-size: 9px; padding: 2px 6px;
    border-radius: 6px; font-weight: 500; margin-left: 4px;
}
.pill-sell  { background: #FCEBEB; color: #791F1F; }
.pill-buy   { background: #EAF3DE; color: #27500A; }
.pill-hold  { background: #F1EFE8; color: #5F5E5A; }
.pill-wait  { background: #FAEEDA; color: #633806; }
.pill-bond  { background: #E1F5EE; color: #085041; }
.pill-block { background: #EEEDFE; color: #3C3489; }
.pill-top   { background: #FCEBEB; color: #791F1F; border: 0.5px solid #F09595; }

/* ── Master switch badges ── */
.switch-badge {
    display: inline-block; font-size: 11px; padding: 3px 10px; border-radius: 8px;
}
.switch-red    { background: #FCEBEB; color: #791F1F; }
.switch-green  { background: #EAF3DE; color: #27500A; }
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

/* ── Strategy progress ── */
.step-done { background: #EAF3DE; color: #27500A; border-radius: 4px; padding: 3px 8px; font-size: 12px; display: inline-block; margin: 2px; }
.step-cur  { background: #FAEEDA; color: #633806; border-radius: 4px; padding: 3px 8px; font-size: 12px; display: inline-block; margin: 2px; }
.step-lock { background: #F0F0F0; color: #999;    border-radius: 4px; padding: 3px 8px; font-size: 12px; display: inline-block; margin: 2px; }

/* ── Colors ── */
.up { color: #0F6E56; }
.dn { color: #A32D2D; }

/* ── Rate label ── */
.rate-label { font-size: 10px; color: #888780; text-align: right; margin-bottom: 10px; }

/* ── Section header ── */
.section-hdr { font-size: 16px; font-weight: 500; margin-bottom: 10px; color: #1A1A1A; }

/* ── Separator ── */
.sep { border: none; border-top: 0.5px solid #E0E0E0; margin: 14px 0; }

/* ── Index grid ── */
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
    """모든 페이지 상단에서 호출"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
