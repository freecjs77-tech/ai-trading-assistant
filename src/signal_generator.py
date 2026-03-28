"""
src/signal_generator.py — 규칙 통합 + 확신도 점수 + 한국어 템플릿 시그널 생성
rule_engine.py 결과를 signals.json 포맷으로 변환
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from rule_engine import (
    RuleResult, MarketContext,
    build_context, build_indicators, evaluate_ticker,
    get_vix_allocation_modifier,
    load_market_data, load_portfolio,
)

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"


# ─────────────────────────────────────────────
# 확신도 점수 계산
# ─────────────────────────────────────────────

def calc_confidence(result: RuleResult, ctx: MarketContext) -> int:
    """
    확신도 점수 0~100 계산
    base = (충족 조건 / 전체 조건) * 100
    가중치:
      마스터 스위치 GREEN +20 / YELLOW +0 / RED -20
      VIX < 20 +10 / VIX 25-30 +0 / VIX > 30 -10
    """
    total_conditions = len(result.conditions_met) + len(result.conditions_not_met)
    if total_conditions == 0:
        base = 50
    else:
        base = int(len(result.conditions_met) / total_conditions * 100)

    # 마스터 스위치 가중치
    if ctx.master_switch == "GREEN":
        base += 20
    elif ctx.master_switch == "RED":
        base -= 20

    # VIX 가중치
    vix = ctx.vix or 0
    if vix < 20:
        base += 10
    elif vix > 30:
        base -= 10

    # Exit 시그널은 확신도 높게 (위험 상황이므로)
    if result.action in ("L2_WEAKENING", "L3_BREAKDOWN", "TOP_SIGNAL"):
        base = max(base, 70)

    return max(0, min(100, base))


# ─────────────────────────────────────────────
# 한국어 템플릿 근거 생성
# ─────────────────────────────────────────────

TEMPLATES = {
    "L1_WARNING": (
        "MACD 히스토그램 하락 전환 감지. "
        "{conditions_text}. "
        "신규 매수 중단, L2 발동 시 30% 트림 준비."
    ),
    "L2_WEAKENING": (
        "추세 약화 신호 {cond_count}개 발동. "
        "{conditions_text}. "
        "보유 30% 익절 권장."
    ),
    "L3_BREAKDOWN": (
        "붕괴 시그널 발동. "
        "{conditions_text}. "
        "전량 매도 검토."
    ),
    "TOP_SIGNAL": (
        "과매수 신호. "
        "{conditions_text}. "
        "일부 강제 익절 권장."
    ),
    "BUY_T1": (
        "{strategy_desc} 1차 매수(20%) 조건 충족. "
        "{conditions_text}."
    ),
    "BUY_T2": (
        "{strategy_desc} 2차 추가매수(30%) 조건 충족. "
        "{conditions_text}."
    ),
    "BUY_T3": (
        "{strategy_desc} 3차 풀포지션(50%) 조건 충족. "
        "{conditions_text}."
    ),
    "WATCH": (
        "진입 조건 접근 중. "
        "{conditions_text}. "
        "나머지 조건 확인 후 진입 결정."
    ),
    "HOLD": (
        "특이 신호 없음. RSI {rsi_text}. "
        "MACD {macd_text}. 현재 포지션 유지."
    ),
}

STRATEGY_DESC = {
    "growth_v22": "성장주(v2.2)",
    "etf_v24": "ETF(v2.4)",
    "energy_v23": "에너지/가치(v2.3)",
    "bond_gold_v26": "채권/금(v2.6)",
    "speculative": "투기종목",
}


def format_conditions_text(conditions: list[str]) -> str:
    """조건 리스트 → 한국어 요약"""
    ko_map = {
        "rsi <= 38": "RSI 과매도(38↓)",
        "rsi <= 40": "RSI 과매도(40↓)",
        "rsi <= 35": "RSI 극과매도(35↓)",
        "rsi > 42": "RSI 회복(42↑)",
        "rsi > 48": "RSI 중립 상향(48↑)",
        "rsi >= 75": "RSI 과매수(75↑)",
        "adx <= 25": "ADX 약세(25↓)",
        "price_near_bb_lower": "BB 하단 근접",
        "price_below_ma20": "가격 MA20 하향",
        "price_above_ma20": "가격 MA20 상향",
        "price_above_bb_upper": "BB 상단 돌파",
        "price_inside_bb_from_upper": "BB 상단에서 내부 진입",
        "macd_histogram_rising_2d": "MACD 히스토그램 2일 상승",
        "macd_hist_declining_1_2d": "MACD 히스토그램 하락 전환",
        "macd_hist_declining_3d": "MACD 히스토그램 3일 하락",
        "macd_golden_cross OR hist_rising_3d": "MACD 골든크로스/히스토그램 상승",
        "macd > macd_signal": "MACD > Signal",
        "macd_above_zero": "MACD 제로선 상향",
        "volume_ratio >= 1.2": "거래량 20% 증가",
        "volume_ratio >= 1.3": "거래량 30% 증가",
        "volume_divergence_negative": "거래량 감소 다이버전스",
        "double_bottom": "이중 바닥 패턴",
        "double_bottom_3pct": "이중 바닥(3%)",
        "higher_low": "상승 저점",
        "pullback_5pct": "5% 풀백",
        "momentum_declining_slowing": "모멘텀 둔화",
        "drawdown_8pct": "8% 하락",
        "drawdown_20pct_from_entry": "20% 손절 기준 도달",
        "rsi_65_turning_down": "RSI 65에서 하락 전환",
        "rsi_lower_high_divergence": "RSI 하락 다이버전스",
        "rsi > 35 AND rsi_rising": "RSI 35↑ + 상승 중",
        "double_top_or_head_shoulder": "더블탑/헤드앤숄더",
        "treasury_30y >= 5.0": "30Y 금리 5.0% 돌파",
        "treasury_30y >= 5.2": "30Y 금리 5.2% 돌파",
        "tlt_rsi <= 35": "TLT RSI 과매도",
        "tlt_macd_golden_cross": "TLT MACD 골든크로스",
        "tlt_above_ma20": "TLT MA20 상향",
        "slv_rsi <= 40": "SLV RSI 과매도",
        "slv_below_ma20": "SLV MA20 하향",
        "vix > 25": "VIX 25 이상(공포)",
        "vix_panic >= 35": "VIX 패닉(35↑)",
        "bounce_2pct": "2% 반등",
        "3day_low_hold": "3일 저점 유지",
        "price_below_ma20_2d": "MA20 아래 2일",
        "higher_low_broken": "상승 저점 붕괴",
        "macd_death_cross": "MACD 데스 크로스",
        "gain_10pct_in_3d": "3일 10% 급등",
    }
    parts = [ko_map.get(c, c) for c in conditions[:4]]  # 최대 4개
    return " + ".join(parts)


def generate_rationale(result: RuleResult, ctx: MarketContext, ind_data: dict) -> str:
    """한국어 근거 텍스트 생성"""
    template = TEMPLATES.get(result.action, TEMPLATES["HOLD"])

    rsi_val = ind_data.get("rsi")
    macd_val = ind_data.get("macd")
    macd_sig = ind_data.get("macd_signal")

    rsi_text = f"{rsi_val:.1f}" if rsi_val is not None else "N/A"
    macd_text = ("상승" if (macd_val and macd_sig and macd_val > macd_sig) else "하락")

    cond_text = format_conditions_text(result.conditions_met) if result.conditions_met else "조건 미충족"
    strategy_desc = STRATEGY_DESC.get(result.classification, result.classification)

    return template.format(
        conditions_text=cond_text,
        cond_count=len(result.conditions_met),
        strategy_desc=strategy_desc,
        rsi_text=rsi_text,
        macd_text=macd_text,
        hist_days=2,
        rsi_level=rsi_text,
    )


# ─────────────────────────────────────────────
# 매크로 알림 생성
# ─────────────────────────────────────────────

def generate_macro_alerts(ctx: MarketContext) -> list[dict]:
    """매크로 상황 알림 리스트 생성"""
    alerts = []

    # 마스터 스위치
    if ctx.master_switch == "RED":
        alerts.append({
            "type": "master_switch",
            "level": "warning",
            "message": f"마스터 스위치 RED — QQQ/SPY 모두 MA200 아래. 신규 주식 매수 없음."
        })
    elif ctx.master_switch == "YELLOW":
        alerts.append({
            "type": "master_switch",
            "level": "caution",
            "message": f"마스터 스위치 YELLOW — 1차 트랜치만 허용 (배분 50%)."
        })

    # VIX
    if ctx.vix is not None:
        if ctx.vix >= 35:
            alerts.append({
                "type": "vix",
                "level": "danger",
                "message": f"VIX 패닉 {ctx.vix:.1f} — 전 포지션 L1 경고 발동. 진입 없음."
            })
        elif ctx.vix >= 30:
            alerts.append({
                "type": "vix",
                "level": "warning",
                "message": f"VIX 극공포 {ctx.vix:.1f} — 배분 50% 축소."
            })
        elif ctx.vix >= 25:
            alerts.append({
                "type": "vix",
                "level": "caution",
                "message": f"VIX 고공포 {ctx.vix:.1f} — 배분 30% 축소."
            })

    # 30Y 금리
    if ctx.treasury_30y is not None:
        if ctx.treasury_30y >= 5.2:
            alerts.append({
                "type": "treasury_yield",
                "level": "warning",
                "message": f"30Y 금리 {ctx.treasury_30y:.3f}% — 주식 진입 urgency 하향. TLT 2차 트리거 임박."
            })
        elif ctx.treasury_30y >= 5.0:
            alerts.append({
                "type": "treasury_yield",
                "level": "info",
                "message": f"30Y 금리 {ctx.treasury_30y:.3f}% — TLT/BIL 전략 활성화."
            })
        elif ctx.treasury_30y >= 4.8:
            alerts.append({
                "type": "treasury_yield",
                "level": "info",
                "message": f"30Y 금리 {ctx.treasury_30y:.3f}% — 5.0% 진입 트리거 임박."
            })

    # 환율
    if ctx.usdkrw is not None:
        if ctx.usdkrw > 1450:
            alerts.append({
                "type": "exchange_rate",
                "level": "caution",
                "message": f"원달러 {ctx.usdkrw:.0f}원 — 환율 고점. 미국 주식 신규 매수 지연 권장."
            })
        elif ctx.usdkrw < 1300:
            alerts.append({
                "type": "exchange_rate",
                "level": "info",
                "message": f"원달러 {ctx.usdkrw:.0f}원 — 환율 저점. 미국 주식 매수 가속화 기회."
            })

    return alerts


# ─────────────────────────────────────────────
# 시그널 우선순위 정렬
# ─────────────────────────────────────────────

ACTION_PRIORITY = {
    "L3_BREAKDOWN": 0,
    "TOP_SIGNAL": 1,
    "L2_WEAKENING": 2,
    "L1_WARNING": 3,
    "BUY_T3": 4,
    "BUY_T2": 5,
    "BUY_T1": 6,
    "WATCH": 7,
    "HOLD": 8,
}


def sort_signals(signals: list[dict]) -> list[dict]:
    return sorted(signals, key=lambda s: ACTION_PRIORITY.get(s["action"], 99))


# ─────────────────────────────────────────────
# 메인 생성 함수
# ─────────────────────────────────────────────

def _make_technical_context(ctx: MarketContext) -> MarketContext:
    """technical_only 모드: 마스터 스위치/VIX/매크로 무시한 중립 컨텍스트"""
    from dataclasses import replace
    return replace(
        ctx,
        master_switch="GREEN",
        qqq_above_ma200=True,
        spy_above_ma200=True,
        vix=15.0,
        vix_tier="normal",
        treasury_30y=None,
        usdkrw=None,
    )


def generate_signals(
    mode: str = "full",
    portfolio_data: Optional[dict] = None,
    market_data: Optional[dict] = None,
) -> dict:
    """전체 시그널 생성 → signals.json 저장

    Parameters
    ----------
    mode : "full" | "technical_only"
        full: 마스터 스위치 + 매크로 + 기술지표 모두 반영
        technical_only: 기술지표만 반영, 마스터 스위치/매크로 무시
    portfolio_data : 직접 전달할 포트폴리오 데이터 (None이면 파일 로드)
    market_data : 직접 전달할 시장 데이터 (None이면 파일 로드)
    """
    cache = market_data if market_data is not None else load_market_data()
    portfolio = portfolio_data if portfolio_data is not None else load_portfolio()

    if not cache or not portfolio:
        logger.error("데이터 없음")
        return {}

    ctx = build_context(cache)
    if mode == "technical_only":
        ctx = _make_technical_context(ctx)

    today = datetime.now(KST).strftime("%Y-%m-%d")

    signals_list = []
    for holding in portfolio.get("holdings", []):
        ticker = holding["ticker"]
        ind = build_indicators(ticker, cache, portfolio)
        result = evaluate_ticker(ind, ctx)
        confidence = calc_confidence(result, ctx)
        ind_data = cache.get("tickers", {}).get(ticker, {})
        rationale = generate_rationale(result, ctx, ind_data)

        signal = {
            "ticker": ticker,
            "classification": result.classification,
            "action": result.action,
            "tranche": result.tranche,
            "confidence": confidence,
            "rationale": rationale,
            "conditions_met": result.conditions_met,
            "conditions_not_met": result.conditions_not_met,
            "exit_level": result.exit_level,
            "notes": result.notes,
            "strategy_stage": result.strategy_stage,
        }
        signals_list.append(signal)

    signals_list = sort_signals(signals_list)
    macro_alerts = generate_macro_alerts(ctx)

    # VIX allocation modifier
    vix_modifier = get_vix_allocation_modifier(ctx.vix)
    allocation_note = ""
    if vix_modifier < 1.0:
        allocation_note = f"VIX {ctx.vix:.1f} — 모든 진입 규모 x{vix_modifier:.1f} 적용"

    result_doc = {
        "date": today,
        "master_switch": ctx.master_switch,
        "vix_tier": f"{ctx.vix_tier} ({ctx.vix:.1f})" if ctx.vix else ctx.vix_tier,
        "treasury_30y": ctx.treasury_30y,
        "usdkrw": ctx.usdkrw,
        "allocation_modifier": vix_modifier,
        "allocation_note": allocation_note,
        "signals": signals_list,
        "macro_alerts": macro_alerts,
        "summary": {
            "l3_breakdown": sum(1 for s in signals_list if s["action"] == "L3_BREAKDOWN"),
            "l2_weakening": sum(1 for s in signals_list if s["action"] == "L2_WEAKENING"),
            "l1_warning": sum(1 for s in signals_list if s["action"] == "L1_WARNING"),
            "top_signal": sum(1 for s in signals_list if s["action"] == "TOP_SIGNAL"),
            "buy": sum(1 for s in signals_list if s["action"].startswith("BUY")),
            "watch": sum(1 for s in signals_list if s["action"] == "WATCH"),
            "hold": sum(1 for s in signals_list if s["action"] == "HOLD"),
        }
    }

    # 모드 기록
    result_doc["mode"] = mode

    # 저장 (technical_only는 별도 파일)
    DATA_DIR.mkdir(exist_ok=True)
    filename = "signals_technical.json" if mode == "technical_only" else "signals.json"
    signals_path = DATA_DIR / filename
    with open(signals_path, "w", encoding="utf-8") as f:
        json.dump(result_doc, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 시그널 생성 완료 [{mode}]: {signals_path}")
    s = result_doc["summary"]
    logger.info(
        f"   L3:{s['l3_breakdown']} L2:{s['l2_weakening']} L1:{s['l1_warning']} "
        f"TOP:{s['top_signal']} BUY:{s['buy']} WATCH:{s['watch']} HOLD:{s['hold']}"
    )
    return result_doc


def load_signals() -> Optional[dict]:
    """signals.json 로드"""
    path = DATA_DIR / "signals.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_signals_technical() -> Optional[dict]:
    """signals_technical.json 로드"""
    path = DATA_DIR / "signals_technical.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "technical_only", "both"], default="full")
    args = parser.parse_args()

    modes = ["full", "technical_only"] if args.mode == "both" else [args.mode]
    for m in modes:
        result = generate_signals(mode=m)
        if result:
            print(f"\n[{m}] 마스터 스위치: {result['master_switch']}")
            for sig in result["signals"][:5]:
                print(f"  {sig['ticker']:6s} → {sig['action']:15s} ({sig['confidence']}%) {sig['rationale'][:60]}")
