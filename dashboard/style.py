"""
dashboard/style.py â ê³µíµ CSS (overview_target.html ê¸°ì¤)
"""

CUSTOM_CSS = """
<style>
/* ââ Streamlit ê¸°ë³¸ ì¤ë²ë¼ì´ë ââ */
.main .block-container { max-width: 900px; padding: 1rem 1rem 2rem 1rem; }
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
* { box-sizing: border-box; }

/* ââ í¤ë ââ */
.hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.hdr h1 { font-size: 22px; font-weight: 500; color: #1A1A1A; }
.meta { font-size: 11px; color: #888780; }
.ctrls { display: flex; align-items: center; gap: 8px; }

/* ââ ë§ì¤í° ì¤ìì¹ ë°°ì§ ââ */
.sw { display: inline-block; font-size: 11px; padding: 3px 10px; border-radius: 8px; font-weight: 500; }
.sw-r { background: #FCEBEB; color: #791F1F; }
.sw-y { background: #FAEEDA; color: #633806; }
.sw-g { background: #EAF3DE; color: #27500A; }

/* ââ USD/KRW í ê¸ ââ */
.tg { display: inline-flex; background: #F8F9FA; border-radius: 8px; padding: 2px; font-size: 11px; }
.tg span { padding: 4px 12px; border-radius: 6px; cursor: pointer; color: #888; }
.tg .on { background: #fff; color: #1A1A1A; font-weight: 500; }

/* ââ íì¨ íì ââ */
.rate { font-size: 10px; color: #888; text-align: right; margin-bottom: 10px; }

/* ââ ë©í¸ë¦­ ì¹´ë ââ */
.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px; }
.mc { background: #F8F9FA; border-radius: 8px; padding: 10px 12px; }
.mc .lb { font-size: 10px; color: #888; }
.mc .vl { font-size: 18px; font-weight: 500; margin-top: 1px; color: #1A1A1A; }
.mc .ch { font-size: 10px; margin-top: 1px; }

/* ââ ìì ââ */
.up { color: #0F6E56; }
.dn { color: #A32D2D; }
.warn { color: #BA7517; }

/* ââ ë§¤í¬ë¡ ì¹´ë ââ */
.macro { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 16px; }
.ma { background: #F8F9FA; border-radius: 8px; padding: 8px; text-align: center; }
.ma .lb { font-size: 10px; color: #888; }
.ma .vl { font-size: 13px; font-weight: 500; margin: 1px 0; }
.ma .st { font-size: 10px; }

/* ââ ë§ì¤í° ì¤ìì¹ ë°°ë ââ */
.ms-banner { background: #fff; border: 0.5px solid #E0E0E0; border-left: 3px solid #A32D2D; padding: 10px 12px; margin-bottom: 16px; }
.ms-banner-y { border-left-color: #BA7517; }
.ms-banner-g { border-left-color: #0F6E56; }
.ms-banner .title { font-weight: 500; font-size: 14px; margin-bottom: 4px; }
.ms-banner .detail { font-size: 12px; color: #666; }

/* ââ ì¹ì í¤ë ââ */
.sh { font-size: 16px; font-weight: 500; margin-bottom: 10px; color: #1A1A1A; }
.section-hdr { font-size: 16px; font-weight: 500; margin-bottom: 10px; color: #1A1A1A; }

/* ââ ë³´ì  íì´ë¸ ââ */
.tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
.tbl th { text-align: left; padding: 7px 5px; color: #888; font-weight: 400; border-bottom: 0.5px solid #E0E0E0; font-size: 10px; }
.tbl td { padding: 7px 5px; border-bottom: 0.5px solid #E0E0E0; color: #1A1A1A; }
.tk { font-weight: 500; font-size: 12px; color: #1A1A1A; }
.nm { color: #888; font-size: 10px; }

/* ââ ì¨ì´í¸ ë° ââ */
.bar-bg { height: 5px; border-radius: 3px; background: #E0E0E0; width: 60px; display: inline-block; vertical-align: middle; }
.bar-f { height: 5px; border-radius: 3px; display: block; }

/* ââ êµ¬ë¶ì  ââ */
.sep { border: none; border-top: 0.5px solid #E0E0E0; margin: 14px 0; }

/* ââ ìê·¸ë ë°°ì§ (pill) ââ */
.pill { display: inline-block; font-size: 9px; padding: 2px 6px; border-radius: 6px; font-weight: 500; white-space: nowrap; }
.pill-sell  { background: #FCEBEB; color: #791F1F; }
.pill-buy   { background: #EAF3DE; color: #27500A; }
.pill-hold  { background: #F1EFE8; color: #5F5E5A; }
.pill-wait  { background: #FAEEDA; color: #633806; }
.pill-bond  { background: #E1F5EE; color: #085041; }
.pill-block { background: #EEEDFE; color: #3C3489; }
.pill-top   { background: #FCEBEB; color: #791F1F; border: 0.5px solid #F09595; }
.pill-tech  { display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 6px; background: #E6F1FB; color: #0C447C; }

/* ââ ìê·¸ë ì¹ì ââ */
.sig-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.sig-col h3 { font-size: 13px; font-weight: 500; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; color: #1A1A1A; }
.sig-sm { display: flex; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }
.cnt { background: #F8F9FA; border-radius: 6px; padding: 2px 8px; font-size: 10px; color: #888; }

/* ââ ìê·¸ë ì¹´ë ââ */
.sig-card { background: #fff; border: 0.5px solid #E0E0E0; border-radius: 10px; padding: 10px; margin-bottom: 6px; }
.sig-card-warn  { border-left: 3px solid #A32D2D; border-radius: 0; }
.sig-card-watch { border-left: 3px solid #BA7517; border-radius: 0; }
.sig-card-buy   { border-left: 3px solid #0F6E56; border-radius: 0; }
.sig-h { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.sig-tk { font-weight: 500; font-size: 13px; color: #1A1A1A; }
.conf { font-size: 10px; color: #888; display: flex; align-items: center; gap: 4px; }
.conf-bar { height: 4px; border-radius: 2px; background: #E0E0E0; display: inline-block; width: 50px; vertical-align: middle; }
.conf-fill { height: 4px; border-radius: 2px; display: block; }
.sig-body { font-size: 11px; color: #666; line-height: 1.5; }

/* ââ ì¸ë±ì¤ ââ */
.idx { padding-top: 14px; border-top: 0.5px solid #E0E0E0; margin-top: 14px; }
.idx-hdr { font-size: 14px; font-weight: 500; margin-bottom: 10px; color: #1A1A1A; }
.idx-sub { font-size: 12px; font-weight: 500; color: #888; margin: 10px 0 6px; }
.idx-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.idx-item { display: flex; gap: 8px; padding: 8px 10px; border-radius: 8px; background: #F8F9FA; align-items: flex-start; }
.idx-name { font-size: 11px; font-weight: 500; color: #1A1A1A; }
.idx-desc { font-size: 10px; color: #888; line-height: 1.4; margin-top: 1px; }

/* ââ ë§ì¤í° ì¤ìì¹ ìí ì¹´ë í ââ */
.sw-row { display: flex; gap: 6px; margin-bottom: 8px; }
.sw-card { flex: 1; padding: 6px 8px; border-radius: 8px; text-align: center; }
.sw-gg { background: #EAF3DE; } .sw-yy { background: #FAEEDA; } .sw-rr { background: #FCEBEB; }
.sw-card .sl { font-size: 10px; font-weight: 500; }
.sw-gg .sl { color: #27500A; } .sw-yy .sl { color: #633806; } .sw-rr .sl { color: #791F1F; }
.sw-card .sd { font-size: 9px; }
.sw-gg .sd { color: #3B6D11; } .sw-yy .sd { color: #854F0B; } .sw-rr .sd { color: #A32D2D; }

/* ââ íì ë ë° ââ */
.rate-label { font-size: 10px; color: #888; display: flex; align-items: center; gap: 5px; margin: 3px 0; }
/* sidebar "app" -> "Overview" */
[data-testid="stSidebarNavItems"] li:first-child span {font-size:0}
[data-testid="stSidebarNavItems"] li:first-child span::after {content:"Overview";font-size:14px}
</style>
"""


def inject_css() -> str:
    return CUSTOM_CSS


SIDEBAR_CSS = """<style>
[data-testid="stSidebarNav"] ul { padding-top: 0.5rem; }
[data-testid="stSidebarNav"] li { padding: 0.15rem 0; }
[data-testid="stSidebarNav"] a { font-size: 0.9rem; }
</style>"""


def inject_sidebar_css() -> str:
    return SIDEBAR_CSS
