"""
src/rule_engine.py — 전략 규칙 엔진 v3.0
마스터 스위치 + 4개 진입 전략(v2.2/v2.3/v2.4/v2.6) + Exit v2.5
Claude API 미사용 — 순수 규칙 기반
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"


# ─────────────────────────────────────────────
# 데이터 클래스
# ─────────────────────────────────────────────

@dataclass
class TickerIndicators:
    """단일 종목의 기술 지표"""
    ticker: str
    price: Optional[float] = None
    ma20: Optional[float] = None
    ma50: Optional[float] = None
    ma200: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_hist_trend: str = "unknown"
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    adx: Optional[float] = None
    volume: Optional[int] = None
    volume_avg20: Optional[int] = None
    volume_ratio: Optional[float] = None
    pnl_pct: Optional[float] = None          # 보유 수익률 (portfolio.json)
    # ── 히스토리 기반 지표 (market_data.py 수집 필요, 기본값=미수집) ──
    ma20_slope: Optional[float] = None       # MA20 기울기 (양수=상승)
    consecutive_above_ma20: int = 0          # MA20 위 연속일수
    consecutive_above_bb_upper: int = 0      # BB상단 위 연속일수
    day_change_pct: Optional[float] = None   # 당일 등락률(%)
    gain_3day_pct: Optional[float] = None    # 최근 3거래일 누적 등락률(%)
    price_crossed_below_ma20: bool = False   # 이번 캔들 MA20 아래로 이탈 (L2 ③)
    price_was_above_bb_upper: bool = False   # 직전 캔들 BB상단 위에 있었음 (L1 ③)


@dataclass
class MarketContext:
    """매크로 시장 상태"""
    master_switch: str = "RED"         # GREEN / YELLOW / RED
    qqq_above_ma200: bool = False
    spy_above_ma200: bool = False
    vix: Optional[float] = None
    vix_tier: str = "unknown"
    treasury_30y: Optional[float] = None
    usdkrw: Optional[float] = None
    mode: str = "full"                 # "full" | "technical_only"


@dataclass
class RuleResult:
    """단일 종목 규칙 평가 결과"""
    ticker: str
    classification: str
    action: str = "HOLD"              # L1_WARNING / L2_WEAKENING / L3_BREAKDOWN / TOP_SIGNAL / BUY_T1 / BUY_T2 / BUY_T3 / WATCH / HOLD
    tranche: Optional[int] = None     # 1, 2, 3
    conditions_met: list[str] = field(default_factory=list)
    conditions_not_met: list[str] = field(default_factory=list)
    exit_level: Optional[int] = None
    strategy_stage: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────
# 조건 평가 함수들
# ─────────────────────────────────────────────

def _v(val: Optional[float]) -> float:
    """None → 0.0 안전 변환"""
    return val if val is not None else 0.0


def check_rsi_le(ind: TickerIndicators, threshold: float) -> bool:
    return ind.rsi is not None and ind.rsi <= threshold


def check_rsi_ge(ind: TickerIndicators, threshold: float) -> bool:
    return ind.rsi is not None and ind.rsi >= threshold


def check_rsi_range(ind: TickerIndicators, lo: float, hi: float) -> bool:
    return ind.rsi is not None and lo <= ind.rsi <= hi


def check_adx_le(ind: TickerIndicators, threshold: float) -> bool:
    return ind.adx is not None and ind.adx <= threshold


def check_price_near_bb_lower(ind: TickerIndicators, proximity: float = 0.02) -> bool:
    """현재가가 BB 하단에서 proximity% 이내"""
    if ind.price is None or ind.bb_lower is None:
        return False
    return abs(ind.price - ind.bb_lower) / ind.bb_lower <= proximity


def check_price_below_ma20(ind: TickerIndicators) -> bool:
    return ind.price is not None and ind.ma20 is not None and ind.price < ind.ma20


def check_price_above_ma20(ind: TickerIndicators) -> bool:
    return ind.price is not None and ind.ma20 is not None and ind.price > ind.ma20


def check_price_above_bb_upper(ind: TickerIndicators) -> bool:
    return ind.price is not None and ind.bb_upper is not None and ind.price > ind.bb_upper


def check_price_inside_bb_from_upper(ind: TickerIndicators) -> bool:
    """가격이 BB 상단에서 내려와 밴드 안으로 진입"""
    if ind.price is None or ind.bb_upper is None or ind.bb_lower is None:
        return False
    return ind.bb_lower < ind.price < ind.bb_upper


def check_macd_hist_rising(ind: TickerIndicators, days: int = 2) -> bool:
    """MACD 히스토그램 N일 연속 상승"""
    trend = ind.macd_hist_trend
    if days >= 3:
        return "rising_3d" in trend
    elif days == 2:
        return "rising_2d" in trend or "rising_3d" in trend
    else:  # days == 1
        return "rising" in trend


def check_macd_hist_declining(ind: TickerIndicators, days: int = 2) -> bool:
    """MACD 히스토그램 N일 연속 하락 (최소 days일 이상 하락 시 True)"""
    trend = ind.macd_hist_trend
    if days >= 3:
        return "declining_3d" in trend
    elif days == 2:
        return "declining_2d" in trend or "declining_3d" in trend
    else:  # days == 1
        return "declining" in trend


def check_macd_above_zero(ind: TickerIndicators) -> bool:
    return ind.macd is not None and ind.macd > 0


def check_macd_golden_cross(ind: TickerIndicators) -> bool:
    """MACD > Signal (골든 크로스 상태)"""
    return ind.macd is not None and ind.macd_signal is not None and ind.macd > ind.macd_signal


def check_volume_ratio_ge(ind: TickerIndicators, threshold: float) -> bool:
    return ind.volume_ratio is not None and ind.volume_ratio >= threshold


def check_pullback_5pct(ind: TickerIndicators) -> bool:
    """MA50 대비 5% 이상 하락 (풀백 기회)"""
    if ind.price is None or ind.ma50 is None:
        return False
    return ind.price <= ind.ma50 * 0.95


def check_momentum_declining_slowing(ind: TickerIndicators) -> bool:
    """모멘텀 감소 둔화 (MACD 히스토그램이 음수지만 감소세가 약해짐)"""
    if ind.macd_histogram is None:
        return False
    # 히스토그램이 음수이면서 rising_2d인 경우
    return ind.macd_histogram < 0 and check_macd_hist_rising(ind, 2)


def check_rsi_65_turning_down(ind: TickerIndicators) -> bool:
    """RSI가 65 이상에서 하락 전환 (근사: RSI 55~75 이면서 MACD 히스토그램 감소)"""
    if ind.rsi is None:
        return False
    return 55 <= ind.rsi <= 75 and check_macd_hist_declining(ind, 1)


def check_volume_divergence_negative(ind: TickerIndicators) -> bool:
    """음의 거래량 다이버전스: 가격 상승에 거래량 감소"""
    if ind.volume_ratio is None:
        return False
    return ind.volume_ratio < 0.8  # 평균 대비 20% 미만


def check_drawdown_from_peak(ind: TickerIndicators, threshold: float = 0.08) -> bool:
    """보유 수익률 기준 8% 이상 하락 (음수 pnl_pct)"""
    if ind.pnl_pct is None:
        return False
    return ind.pnl_pct <= -(threshold * 100)


def check_higher_low(ind: TickerIndicators) -> bool:
    """상승 저점 패턴 (RSI 상승 + 가격 MA20 근접)"""
    if ind.rsi is None or ind.price is None or ind.ma20 is None:
        return False
    # RSI > 40이고 가격이 MA20 위
    return ind.rsi > 40 and ind.price > ind.ma20


def check_double_bottom(ind: TickerIndicators) -> bool:
    """이중 바닥 근사: RSI < 40이면서 MACD 히스토그램 상승 전환"""
    return (ind.rsi is not None and ind.rsi < 40
            and check_macd_hist_rising(ind, 2))


def check_rsi_lower_high_divergence(ind: TickerIndicators) -> bool:
    """RSI 하락 다이버전스 근사: RSI > 60이면서 MACD 감소"""
    if ind.rsi is None:
        return False
    return ind.rsi > 60 and check_macd_hist_declining(ind, 3)


def check_ma20_slope_rising(ind: TickerIndicators) -> bool:
    """MA20 기울기 상승 전환 (market_data에서 수집 필요, 기본=False)"""
    return ind.ma20_slope is not None and ind.ma20_slope > 0


def check_consecutive_above_ma20(ind: TickerIndicators, days: int = 2) -> bool:
    """MA20 위 연속일수 (market_data에서 수집 필요, 기본=0)"""
    return ind.consecutive_above_ma20 >= days


def check_consecutive_above_bb_upper(ind: TickerIndicators, days: int = 2) -> bool:
    """BB상단 위 연속일수 (market_data에서 수집 필요, 기본=0)"""
    return ind.consecutive_above_bb_upper >= days


def check_panic_drop(ind: TickerIndicators, pct: float = 5.0) -> bool:
    """당일 -pct% 이상 급락 (패닉 바이 방지)"""
    return ind.day_change_pct is not None and ind.day_change_pct <= -pct


def check_gain_3day(ind: TickerIndicators, pct: float = 10.0) -> bool:
    """최근 3거래일 누적 +pct% 이상 급등"""
    return ind.gain_3day_pct is not None and ind.gain_3day_pct >= pct


def check_bb_upper_pullback(ind: TickerIndicators) -> bool:
    """BB상단 터치 후 밴드 안으로 밀림 (직전 캔들 BB상단 위 → 현재 안쪽)
    market_data에서 price_was_above_bb_upper 수집 필요, 기본=False"""
    if not ind.price_was_above_bb_upper:
        return False
    return check_price_inside_bb_from_upper(ind)


def check_ma20_fresh_breakdown(ind: TickerIndicators) -> bool:
    """이번 캔들 MA20 아래로 이탈 (market_data 수집 필요, 기본=False)"""
    return ind.price_crossed_below_ma20


def check_ma20_flat(ind: TickerIndicators) -> bool:
    """MA20 평탄화: 기울기 절댓값이 임계치 이하 (market_data 수집 필요)"""
    return ind.ma20_slope is not None and abs(ind.ma20_slope) <= 0.001


# ─────────────────────────────────────────────
# VIX 오버레이
# ─────────────────────────────────────────────

def get_vix_allocation_modifier(vix: Optional[float]) -> float:
    """VIX 기반 allocation 조정 배율"""
    if vix is None:
        return 1.0
    if vix >= 35:
        return 0.0  # 패닉 — 진입 없음
    elif vix >= 30:
        return 0.5
    elif vix >= 25:
        return 0.7
    return 1.0


def check_vix_panic(vix: Optional[float]) -> bool:
    return vix is not None and vix >= 35


# ─────────────────────────────────────────────
# Exit 시스템 v2.5
# ─────────────────────────────────────────────

def evaluate_exit(ind: TickerIndicators, ctx: MarketContext) -> tuple[Optional[int], list[str], list[str]]:
    """
    Exit v2.5 평가 (수정: 단일 스냅샷 기반 — L3 비활성화)
    Returns: (exit_level, conditions_met, conditions_not_met)
    exit_level: None | 1 | 2 | 99(TOP)

    L3는 히스토리 없이 단일 시점 데이터만으로 판정 불가 → HOLD 처리.
    L2: macd_hist_declining_3d 필수 + price_below_ma20 충족 시 발동.
    L1: macd_hist_declining_2d 필수 + RSI > 35(과매도 아님) + 추가 조건 1개 이상.
    """
    # TOP 시그널 (단일 스냅샷으로 확인 가능한 조건만)
    top_conds = {
        "rsi >= 75": check_rsi_ge(ind, 75),
        "price_above_bb_upper": check_price_above_bb_upper(ind),
        "consecutive_above_bb_upper_2d": check_consecutive_above_bb_upper(ind, 2),
        "gain_3day_10pct": check_gain_3day(ind, 10.0),
    }
    if any(top_conds.values()):
        return 99, [k for k, v in top_conds.items() if v], [k for k, v in top_conds.items() if not v]

    # VIX 패닉 — 전체 L1
    if check_vix_panic(ctx.vix):
        return 1, ["vix_panic >= 35"], []

    # L2 약화: macd_hist_declining_3d 필수 + 의미 있는 손실(-15%~-30%) 또는 기타 조건 1개 이상
    l2_required = check_macd_hist_declining(ind, 3)
    l2_optionals = {
        "drawdown_15_30pct": (ind.pnl_pct is not None and -30.0 <= ind.pnl_pct <= -15.0),
        "rsi_lower_high_divergence": check_rsi_lower_high_divergence(ind),
        "ma20_fresh_breakdown": check_ma20_fresh_breakdown(ind),
    }
    l2_opt_met = [k for k, v in l2_optionals.items() if v]
    if l2_required and len(l2_opt_met) >= 1:
        return 2, ["macd_hist_declining_3d"] + l2_opt_met, [k for k, v in l2_optionals.items() if not v]

    # L1 조기 경고: macd_hist_declining_2d 필수 + RSI > 35 + 추가 조건 1개 이상
    # (RSI ≤ 35 이미 과매도 → exit 경고 불필요)
    l1_required = (check_macd_hist_declining(ind, 2)
                   and ind.rsi is not None and ind.rsi > 35)
    l1_optional = {
        "rsi_65_turning_down": check_rsi_65_turning_down(ind),
        "volume_divergence_negative": (ind.volume_ratio is not None
                                       and ind.volume_ratio < 0.88),
        "bb_upper_pullback": check_bb_upper_pullback(ind),
    }
    l1_opt_met = [k for k, v in l1_optional.items() if v]
    l1_opt_not = [k for k, v in l1_optional.items() if not v]
    if l1_required and len(l1_opt_met) >= 1:
        return 1, ["macd_hist_declining_1_2d"] + l1_opt_met, l1_opt_not

    return None, [], []


# ─────────────────────────────────────────────
# 진입 전략 평가
# ─────────────────────────────────────────────

def evaluate_growth_v22(ind: TickerIndicators, ctx: MarketContext) -> RuleResult:
    """Growth v2.2 — NVDA, TSLA, PLTR, MSFT, GOOGL, AMZN, AAPL"""
    result = RuleResult(ticker=ind.ticker, classification="growth_v22")

    # 마스터 스위치 RED면 진입 없음
    if ctx.master_switch == "RED":
        result.action = "HOLD"
        result.notes.append("마스터 스위치 RED — 신규 진입 없음")
        return result

    # 당일 -5% 이상 급락 → 패닉 바이 방지
    if check_panic_drop(ind):
        result.action = "HOLD"
        result.notes.append(f"패닉 바이 방지 — 당일 {ind.day_change_pct:.1f}% 급락")
        return result

    # Tranche 1 조건 (YELLOW: T1만 허용)
    yellow_mode = (ctx.master_switch == "YELLOW")
    required_t1 = check_macd_hist_rising(ind, 2)
    pick_conditions = {
        "rsi <= 38": check_rsi_le(ind, 38),
        "adx <= 25": check_adx_le(ind, 25),
        "price_near_bb_lower": check_price_near_bb_lower(ind),
        "price_below_ma20": check_price_below_ma20(ind),
        "bounce_2pct": (ind.price is not None and ind.ma20 is not None
                        and ind.price >= ind.ma20 * 0.98 and ind.price <= ind.ma20),
        "3day_low_hold": check_rsi_le(ind, 42) and not check_macd_hist_declining(ind, 3),
    }
    veto_t1 = check_rsi_ge(ind, 50)

    t1_met = [k for k, v in pick_conditions.items() if v]
    t1_not = [k for k, v in pick_conditions.items() if not v]

    if required_t1 and len(t1_met) >= 3 and not veto_t1:
        result.action = "BUY_T1"
        result.tranche = 1
        result.conditions_met = ["macd_histogram_rising_2d"] + t1_met
        result.conditions_not_met = t1_not
        result.strategy_stage = {
            "current": 1,
            "next_conditions": "double_bottom + RSI>35 rising 3d + MACD golden cross + vol 1.2x"
        }
        return result

    # YELLOW 모드: T1만 허용, T2/T3 미진입
    if yellow_mode:
        result.action = "WATCH" if (required_t1 and len(t1_met) >= 2) else "HOLD"
        result.notes.append("마스터 스위치 YELLOW — T1(20%)만 허용, T2/T3 진입 없음")
        result.conditions_met = (["macd_histogram_rising_2d"] + t1_met) if required_t1 else t1_met
        result.conditions_not_met = t1_not
        return result

    # Tranche 2 조건
    t2_conds = {
        "double_bottom": check_double_bottom(ind),
        "rsi > 35 AND rsi_rising": check_rsi_ge(ind, 35) and check_macd_hist_rising(ind, 2),
        "macd_golden_cross OR hist_rising_3d": (check_macd_golden_cross(ind)
                                                 or check_macd_hist_rising(ind, 3)),
        "volume_ratio >= 1.2": check_volume_ratio_ge(ind, 1.2),
    }
    t2_met = [k for k, v in t2_conds.items() if v]
    t2_not = [k for k, v in t2_conds.items() if not v]

    if len(t2_met) == len(t2_conds):
        result.action = "BUY_T2"
        result.tranche = 2
        result.conditions_met = t2_met
        result.conditions_not_met = []
        return result

    # Tranche 3 조건
    veto_t3 = check_rsi_ge(ind, 75)
    t3_conds = {
        "price_above_ma20": check_price_above_ma20(ind),
        "macd_above_zero": check_macd_above_zero(ind),
        "volume_ratio >= 1.3": check_volume_ratio_ge(ind, 1.3),
        "ma20_slope_rising": check_ma20_slope_rising(ind),
        "consecutive_above_ma20_2d": check_consecutive_above_ma20(ind, 2),
    }
    t3_met = [k for k, v in t3_conds.items() if v]
    t3_not = [k for k, v in t3_conds.items() if not v]

    if len(t3_met) >= 3 and not veto_t3:
        result.action = "BUY_T3"
        result.tranche = 3
        result.conditions_met = t3_met
        return result

    # WATCH — 조건 일부 충족
    if required_t1 and len(t1_met) >= 2:
        result.action = "WATCH"
        result.conditions_met = ["macd_histogram_rising_2d"] + t1_met
        result.conditions_not_met = t1_not
        result.notes.append(f"T1 조건 {len(t1_met)}/3 충족 ({', '.join(t1_met)})")
    else:
        result.action = "HOLD"
        result.conditions_not_met = (["macd_histogram_rising_2d"] if not required_t1 else []) + t1_not

    return result


def evaluate_etf_v24(ind: TickerIndicators, ctx: MarketContext) -> RuleResult:
    """ETF v2.4 — QQQ, VOO, SPY, SCHD, SOXX, JEPI"""
    result = RuleResult(ticker=ind.ticker, classification="etf_v24")

    if ctx.master_switch == "RED":
        result.action = "HOLD"
        result.notes.append("마스터 스위치 RED — 신규 진입 없음")
        return result

    # 당일 -5% 이상 급락 → 패닉 바이 방지
    if check_panic_drop(ind):
        result.action = "HOLD"
        result.notes.append(f"패닉 바이 방지 — 당일 {ind.day_change_pct:.1f}% 급락")
        return result

    yellow_mode = (ctx.master_switch == "YELLOW")
    veto = check_rsi_ge(ind, 70)

    # Tranche 1
    t1_pool = {
        "rsi <= 40": check_rsi_le(ind, 40),
        "price_below_ma20": check_price_below_ma20(ind),
        "price_near_bb_lower": check_price_near_bb_lower(ind),
        "momentum_declining_slowing": check_momentum_declining_slowing(ind),
        "pullback_5pct": check_pullback_5pct(ind),
    }
    t1_met = [k for k, v in t1_pool.items() if v]
    t1_not = [k for k, v in t1_pool.items() if not v]

    if len(t1_met) >= 3 and not veto:
        result.action = "BUY_T1"
        result.tranche = 1
        result.conditions_met = t1_met
        result.conditions_not_met = t1_not
        return result

    # YELLOW 모드: T1만 허용
    if yellow_mode:
        result.action = "WATCH" if len(t1_met) >= 2 else "HOLD"
        result.notes.append("마스터 스위치 YELLOW — T1(20%)만 허용, T2/T3 진입 없음")
        result.conditions_met = t1_met
        result.conditions_not_met = t1_not
        return result

    # Tranche 2
    t2_pool = {
        "rsi > 42": check_rsi_ge(ind, 42),
        "macd > macd_signal": check_macd_golden_cross(ind),
        "price_above_ma20": check_price_above_ma20(ind),
        "higher_low": check_higher_low(ind),
    }
    t2_met = [k for k, v in t2_pool.items() if v]
    t2_not = [k for k, v in t2_pool.items() if not v]

    if len(t2_met) >= 3 and not veto:
        result.action = "BUY_T2"
        result.tranche = 2
        result.conditions_met = t2_met
        result.conditions_not_met = t2_not
        return result

    # Tranche 3
    t3_pool = {
        "price_above_ma20": check_price_above_ma20(ind),
        "rsi > 48": check_rsi_ge(ind, 48),
        "macd_above_zero": check_macd_above_zero(ind),
        "ma20_slope_rising": check_ma20_slope_rising(ind),
    }
    t3_met = [k for k, v in t3_pool.items() if v]
    t3_not = [k for k, v in t3_pool.items() if not v]

    if len(t3_met) >= 3 and not veto:
        result.action = "BUY_T3"
        result.tranche = 3
        result.conditions_met = t3_met
        return result

    if len(t1_met) >= 2:
        result.action = "WATCH"
        result.conditions_met = t1_met
        result.conditions_not_met = t1_not
        result.notes.append(f"T1 조건 {len(t1_met)}/3 충족")
    else:
        result.action = "HOLD"
        result.conditions_not_met = t1_not

    return result


def evaluate_energy_v23(ind: TickerIndicators, ctx: MarketContext) -> RuleResult:
    """Energy/Value v2.3 — UNH, O"""
    result = RuleResult(ticker=ind.ticker, classification="energy_v23")

    if ctx.master_switch == "RED":
        result.action = "HOLD"
        result.notes.append("마스터 스위치 RED — 신규 진입 없음")
        return result

    # 당일 -5% 이상 급락 → 패닉 바이 방지
    if check_panic_drop(ind):
        result.action = "HOLD"
        result.notes.append(f"패닉 바이 방지 — 당일 {ind.day_change_pct:.1f}% 급락")
        return result

    yellow_mode = (ctx.master_switch == "YELLOW")

    # T1 (growth_v22와 동일, veto RSI>70으로 수정)
    required_t1 = check_macd_hist_rising(ind, 2)
    pick_conditions = {
        "rsi <= 38": check_rsi_le(ind, 38),
        "adx <= 25": check_adx_le(ind, 25),
        "price_near_bb_lower": check_price_near_bb_lower(ind),
        "price_below_ma20": check_price_below_ma20(ind),
        "3day_low_hold": check_rsi_le(ind, 42),
        "bounce_2pct": ind.price is not None and ind.ma20 is not None and ind.price >= ind.ma20 * 0.98,
    }
    veto_t1 = check_rsi_ge(ind, 70)  # spec: RSI>70 veto (v2.2와 다름)
    t1_met = [k for k, v in pick_conditions.items() if v]
    t1_not = [k for k, v in pick_conditions.items() if not v]

    if required_t1 and len(t1_met) >= 3 and not veto_t1:
        result.action = "BUY_T1"
        result.tranche = 1
        result.conditions_met = ["macd_histogram_rising_2d"] + t1_met
        result.conditions_not_met = t1_not
        return result

    # YELLOW 모드: T1만 허용
    if yellow_mode:
        result.action = "WATCH" if (required_t1 and len(t1_met) >= 2) else "HOLD"
        result.notes.append("마스터 스위치 YELLOW — T1(20%)만 허용, T2/T3 진입 없음")
        result.conditions_met = (["macd_histogram_rising_2d"] + t1_met) if required_t1 else t1_met
        result.conditions_not_met = t1_not
        return result

    veto = check_rsi_ge(ind, 70)

    # T2
    t2_pool = {
        "double_bottom_3pct": check_double_bottom(ind),
        "rsi > 40": check_rsi_ge(ind, 40),
        "macd > macd_signal": check_macd_golden_cross(ind),
        "price_above_ma20": check_price_above_ma20(ind),
    }
    t2_met = [k for k, v in t2_pool.items() if v]
    t2_not = [k for k, v in t2_pool.items() if not v]

    if len(t2_met) >= 3 and not veto:
        result.action = "BUY_T2"
        result.tranche = 2
        result.conditions_met = t2_met
        return result

    # T3
    t3_pool = {
        "price_above_ma20": check_price_above_ma20(ind),
        "macd > macd_signal": check_macd_golden_cross(ind),
        "rsi > 45": check_rsi_ge(ind, 45),
        "ma20_slope_rising": check_ma20_slope_rising(ind),
        "consecutive_above_ma20_2d": check_consecutive_above_ma20(ind, 2),
    }
    t3_met = [k for k, v in t3_pool.items() if v]

    if len(t3_met) >= 3 and not veto:
        result.action = "BUY_T3"
        result.tranche = 3
        result.conditions_met = t3_met
        return result

    if required_t1 and len(t1_met) >= 2:
        result.action = "WATCH"
        result.conditions_met = ["macd_histogram_rising_2d"] + t1_met
        result.conditions_not_met = t1_not
    else:
        result.action = "HOLD"
        result.conditions_not_met = (["macd_histogram_rising_2d"] if not required_t1 else []) + t1_not

    return result


def evaluate_bond_v26(ind: TickerIndicators, ctx: MarketContext) -> RuleResult:
    """Bond v2.6 — TLT (마스터 스위치 무시)"""
    result = RuleResult(ticker=ind.ticker, classification="bond_gold_v26")
    treasury = ctx.treasury_30y  # technical_only 모드에서는 None

    # technical_only 모드 (treasury=None): 순수 기술지표로 BUY 판단
    if treasury is None:
        tech_t1 = {
            "tlt_rsi <= 35": check_rsi_le(ind, 35),
            "price_near_bb_lower": check_price_near_bb_lower(ind, 0.05),
        }
        tech_met = [k for k, v in tech_t1.items() if v]
        if check_rsi_le(ind, 35):  # RSI ≤ 35는 필수
            result.action = "BUY_T1"
            result.tranche = 1
            result.conditions_met = tech_met
            return result
        result.action = "WATCH"
        result.conditions_met = tech_met
        return result

    treasury_val = treasury or 0.0

    # T1
    t1_conds = {
        "treasury_30y >= 5.0": treasury_val >= 5.0,
        "tlt_rsi <= 35": check_rsi_le(ind, 35),
    }
    t1_met = [k for k, v in t1_conds.items() if v]
    t1_not = [k for k, v in t1_conds.items() if not v]

    if len(t1_met) == 2:
        result.action = "BUY_T1"
        result.tranche = 1
        result.conditions_met = t1_met
        return result

    # T2
    t2_conds = {
        "treasury_30y >= 5.2": treasury >= 5.2,
        "tlt_macd_golden_cross": check_macd_golden_cross(ind),
    }
    t2_met = [k for k, v in t2_conds.items() if v]

    if t2_met:
        result.action = "BUY_T2"
        result.tranche = 2
        result.conditions_met = t2_met
        return result

    # T3
    t3_conds = {
        "tlt_above_ma20": check_price_above_ma20(ind),
        "treasury_30y_declining": treasury > 0 and treasury < 5.5,  # 피크 하락 근사
    }
    t3_met = [k for k, v in t3_conds.items() if v]

    if len(t3_met) == 2:
        result.action = "BUY_T3"
        result.tranche = 3
        result.conditions_met = t3_met
        return result

    # BOND_WATCH — 금리 4.8% 이상이면 주시
    if treasury_val >= 4.8:
        result.action = "BOND_WATCH"
        result.conditions_met = t1_met
        result.conditions_not_met = t1_not
        result.notes.append(f"30Y 금리 {treasury_val:.3f}% — 5.0% 트리거 임박" if treasury_val < 5.0
                            else f"30Y 금리 {treasury_val:.3f}% — RSI {ind.rsi:.1f} (35 이하 필요)")
    else:
        result.action = "HOLD"
        result.conditions_not_met = t1_not

    return result


def evaluate_gold_v26(ind: TickerIndicators, ctx: MarketContext) -> RuleResult:
    """Gold/Silver v2.6 — SLV
    full 모드에서 master=RED면 진입 없음.
    technical_only 모드(master=GREEN 강제)에서는 기술지표로 판단.
    """
    result = RuleResult(ticker=ind.ticker, classification="bond_gold_v26")

    # full 모드에서 master=RED면 HOLD
    if ctx.master_switch == "RED":
        result.action = "HOLD"
        result.notes.append("마스터 스위치 RED — SLV 신규 진입 없음")
        return result

    # RSI > 80 → TOP_SIGNAL (과매수 경고)
    if check_rsi_ge(ind, 80):
        result.action = "TOP_SIGNAL"
        result.exit_level = 99
        result.conditions_met = ["rsi >= 80"]
        result.notes.append("SLV RSI 과매수(≥80) — TOP_SIGNAL")
        return result

    # T1
    t1_pool = {
        "slv_rsi <= 40": check_rsi_le(ind, 40),
        "slv_below_ma20": check_price_below_ma20(ind),
        "vix > 25": ctx.vix is not None and ctx.vix > 25,
    }
    t1_met = [k for k, v in t1_pool.items() if v]
    t1_not = [k for k, v in t1_pool.items() if not v]

    if len(t1_met) >= 2:
        result.action = "BUY_T1"
        result.tranche = 1
        result.conditions_met = t1_met
        result.conditions_not_met = t1_not
        return result

    # T2
    t2_pool = {
        "slv_macd > signal": check_macd_golden_cross(ind),
        "slv_rsi > 42": check_rsi_ge(ind, 42),
        "slv_higher_low": check_higher_low(ind),
        "slv_ma20_flat": check_ma20_flat(ind),
    }
    t2_met = [k for k, v in t2_pool.items() if v]

    if len(t2_met) >= 2:
        result.action = "BUY_T2"
        result.tranche = 2
        result.conditions_met = t2_met
        return result

    # T3
    t3_pool = {
        "slv_above_ma20": check_price_above_ma20(ind),
        "slv_macd_above_zero": check_macd_above_zero(ind),
    }
    t3_met = [k for k, v in t3_pool.items() if v]

    if len(t3_met) >= 2:
        result.action = "BUY_T3"
        result.tranche = 3
        result.conditions_met = t3_met
        return result

    if t1_met:
        result.action = "WATCH"
        result.conditions_met = t1_met
        result.conditions_not_met = t1_not
    else:
        result.action = "HOLD"
        result.conditions_not_met = t1_not

    return result


def evaluate_speculative(ind: TickerIndicators, ctx: MarketContext) -> RuleResult:
    """투기 종목 — TQQQ, SOXL, ETHU, CRCL, BTDR
    신규 매수 없음. Exit는 evaluate_exit에서 처리.
    """
    result = RuleResult(ticker=ind.ticker, classification="speculative")
    result.action = "HOLD"
    result.notes.append("투기 종목 — 신규 매수 없음.")
    return result


# ─────────────────────────────────────────────
# 분류별 전략 라우팅
# ─────────────────────────────────────────────

CLASSIFICATION_MAP = {
    "growth_v22": evaluate_growth_v22,
    "etf_v24": evaluate_etf_v24,
    "energy_v23": evaluate_energy_v23,
    "bond_gold_v26_tlt": evaluate_bond_v26,
    "bond_gold_v26_slv": evaluate_gold_v26,
    "speculative": evaluate_speculative,
}


def get_classification(ticker: str) -> str:
    """티커 → 전략 분류"""
    with open(CONFIG_DIR / "tickers.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for cls_name, cls_data in cfg.get("classifications", {}).items():
        if ticker in cls_data.get("tickers", []):
            if cls_name == "bond_gold_v26":
                if ticker == "TLT":
                    return "bond_gold_v26_tlt"
                elif ticker == "SLV":
                    return "bond_gold_v26_slv"
                else:
                    return "bond_gold_v26_tlt"  # BIL — HOLD
            return cls_name
    return "speculative"  # 기본값


def evaluate_ticker(ind: TickerIndicators, ctx: MarketContext) -> RuleResult:
    """
    종목 하나에 대해 전략 평가 실행
    1. Exit 체크
    2. 진입 전략 평가
    """
    classification = get_classification(ind.ticker)

    # BIL은 CASH (현금성 자산)
    if ind.ticker == "BIL":
        result = RuleResult(ticker=ind.ticker, classification="bond_gold_v26")
        result.action = "CASH"
        result.notes.append("단기채 현금성 자산 — 현재 포지션 유지")
        return result

    # ETF는 exit 생략 (분산투자 특성상 개별 종목 exit 시그널 불필요)
    if classification == "etf_v24":
        evaluator = CLASSIFICATION_MAP.get(classification)
        if evaluator:
            return evaluator(ind, ctx)
        return RuleResult(ticker=ind.ticker, classification=classification, action="HOLD")

    # technical_only 모드에서는 투기 종목 exit 생략 (pnl_pct=None이므로 오탐 방지)
    if classification == "speculative" and ctx.mode == "technical_only":
        return evaluate_speculative(ind, ctx)

    # Exit 평가 (growth, energy, bond_gold, speculative)
    exit_level, exit_met, exit_not_met = evaluate_exit(ind, ctx)

    if exit_level is not None:
        action_map = {1: "L1_WARNING", 2: "L2_WEAKENING", 3: "L3_BREAKDOWN", 99: "TOP_SIGNAL"}
        result = RuleResult(ticker=ind.ticker, classification=classification)
        result.action = action_map.get(exit_level, "HOLD")
        result.exit_level = exit_level
        result.conditions_met = exit_met
        result.conditions_not_met = exit_not_met
        return result

    # 진입 전략
    evaluator = CLASSIFICATION_MAP.get(classification)
    if evaluator:
        return evaluator(ind, ctx)

    # 기본 HOLD
    return RuleResult(ticker=ind.ticker, classification=classification, action="HOLD")


# ─────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────

def load_market_data() -> Optional[dict]:
    """market_cache.json 로드"""
    cache_path = DATA_DIR / "market_cache.json"
    if not cache_path.exists():
        logger.error("market_cache.json 없음. market_data.py를 먼저 실행하세요.")
        return None
    with open(cache_path, encoding="utf-8") as f:
        return json.load(f)


def load_portfolio() -> Optional[dict]:
    """portfolio.json 로드"""
    portfolio_path = DATA_DIR / "portfolio.json"
    if not portfolio_path.exists():
        return None
    with open(portfolio_path, encoding="utf-8") as f:
        return json.load(f)


def build_context(cache: dict) -> MarketContext:
    """market_cache → MarketContext"""
    ms = cache.get("master_switch", {})
    macro = cache.get("macro", {})
    return MarketContext(
        master_switch=ms.get("status", "RED"),
        qqq_above_ma200=ms.get("qqq_above_ma200", False),
        spy_above_ma200=ms.get("spy_above_ma200", False),
        vix=macro.get("vix"),
        vix_tier=macro.get("vix_tier", "unknown"),
        treasury_30y=macro.get("treasury_30y"),
        usdkrw=macro.get("usdkrw"),
    )


def build_indicators(ticker: str, cache: dict, portfolio: dict) -> TickerIndicators:
    """market_cache + portfolio → TickerIndicators"""
    t_data = cache.get("tickers", {}).get(ticker, {})
    holdings = {h["ticker"]: h for h in portfolio.get("holdings", [])}
    holding = holdings.get(ticker, {})

    return TickerIndicators(
        ticker=ticker,
        price=t_data.get("price"),
        ma20=t_data.get("ma20"),
        ma50=t_data.get("ma50"),
        ma200=t_data.get("ma200"),
        rsi=t_data.get("rsi"),
        macd=t_data.get("macd"),
        macd_signal=t_data.get("macd_signal"),
        macd_histogram=t_data.get("macd_histogram"),
        macd_hist_trend=t_data.get("macd_hist_trend", "unknown"),
        bb_upper=t_data.get("bb_upper"),
        bb_lower=t_data.get("bb_lower"),
        adx=t_data.get("adx"),
        volume=t_data.get("volume"),
        volume_avg20=t_data.get("volume_avg20"),
        volume_ratio=t_data.get("volume_ratio"),
        pnl_pct=holding.get("pnl_pct"),
        # 히스토리 기반 지표 (market_data.py 확장 시 수집, 기본=미수집)
        ma20_slope=t_data.get("ma20_slope"),
        consecutive_above_ma20=t_data.get("consecutive_above_ma20", 0),
        consecutive_above_bb_upper=t_data.get("consecutive_above_bb_upper", 0),
        day_change_pct=t_data.get("day_change_pct"),
        gain_3day_pct=t_data.get("gain_3day_pct"),
        price_crossed_below_ma20=t_data.get("price_crossed_below_ma20", False),
        price_was_above_bb_upper=t_data.get("price_was_above_bb_upper", False),
    )


def run_all() -> list[RuleResult]:
    """전체 종목 규칙 엔진 실행"""
    cache = load_market_data()
    portfolio = load_portfolio()
    if not cache or not portfolio:
        logger.error("데이터 로드 실패")
        return []

    ctx = build_context(cache)
    logger.info(f"마스터 스위치: {ctx.master_switch} | VIX: {ctx.vix} | 30Y: {ctx.treasury_30y}%")

    results: list[RuleResult] = []
    for holding in portfolio.get("holdings", []):
        ticker = holding["ticker"]
        ind = build_indicators(ticker, cache, portfolio)
        result = evaluate_ticker(ind, ctx)
        results.append(result)
        logger.info(f"  {ticker}: {result.action}" + (f" (T{result.tranche})" if result.tranche else ""))

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run_all()
    print(f"\n✅ 규칙 엔진 완료: {len(results)}개 종목")
    for r in results:
        print(f"  {r.ticker:6s} → {r.action}")
