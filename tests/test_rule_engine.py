"""
tests/test_rule_engine.py — 규칙 엔진 단위 테스트
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rule_engine import (
    TickerIndicators, MarketContext, RuleResult,
    check_rsi_le, check_rsi_ge, check_price_near_bb_lower,
    check_price_below_ma20, check_price_above_ma20,
    check_macd_hist_rising, check_macd_hist_declining,
    check_macd_golden_cross, check_macd_above_zero,
    check_volume_ratio_ge, check_drawdown_from_peak,
    check_higher_low, check_double_bottom,
    get_vix_allocation_modifier, check_vix_panic,
    evaluate_exit, evaluate_growth_v22, evaluate_etf_v24,
    evaluate_bond_v26,
)


# ─────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────

def make_ind(**kwargs) -> TickerIndicators:
    defaults = {
        "ticker": "TEST",
        "price": 100.0,
        "ma20": 95.0,
        "ma50": 90.0,
        "ma200": 85.0,
        "rsi": 45.0,
        "macd": 0.5,
        "macd_signal": 0.3,
        "macd_histogram": 0.2,
        "macd_hist_trend": "rising_2d",
        "bb_upper": 110.0,
        "bb_lower": 90.0,
        "adx": 20.0,
        "volume": 1000000,
        "volume_avg20": 1000000,
        "volume_ratio": 1.0,
        "pnl_pct": 5.0,
    }
    defaults.update(kwargs)
    return TickerIndicators(**defaults)


def make_ctx(**kwargs) -> MarketContext:
    defaults = {
        "master_switch": "GREEN",
        "qqq_above_ma200": True,
        "spy_above_ma200": True,
        "vix": 18.0,
        "vix_tier": "normal",
        "treasury_30y": 4.5,
        "usdkrw": 1380.0,
    }
    defaults.update(kwargs)
    return MarketContext(**defaults)


# ─────────────────────────────────────────────
# 조건 함수 테스트
# ─────────────────────────────────────────────

class TestConditions:
    def test_rsi_le(self):
        ind = make_ind(rsi=35.0)
        assert check_rsi_le(ind, 38) is True
        assert check_rsi_le(ind, 30) is False

    def test_rsi_ge(self):
        ind = make_ind(rsi=75.0)
        assert check_rsi_ge(ind, 75) is True
        assert check_rsi_ge(ind, 80) is False

    def test_price_near_bb_lower(self):
        ind = make_ind(price=91.0, bb_lower=90.0)
        assert check_price_near_bb_lower(ind, 0.02) is True

        ind2 = make_ind(price=100.0, bb_lower=90.0)
        assert check_price_near_bb_lower(ind2, 0.02) is False

    def test_price_below_ma20(self):
        ind = make_ind(price=90.0, ma20=95.0)
        assert check_price_below_ma20(ind) is True

        ind2 = make_ind(price=100.0, ma20=95.0)
        assert check_price_below_ma20(ind2) is False

    def test_macd_hist_rising(self):
        ind = make_ind(macd_hist_trend="rising_2d")
        assert check_macd_hist_rising(ind, 2) is True

        ind2 = make_ind(macd_hist_trend="declining_2d")
        assert check_macd_hist_rising(ind2, 2) is False

    def test_macd_hist_declining(self):
        ind = make_ind(macd_hist_trend="declining_3d")
        assert check_macd_hist_declining(ind, 3) is True

    def test_macd_golden_cross(self):
        ind = make_ind(macd=1.0, macd_signal=0.5)
        assert check_macd_golden_cross(ind) is True

        ind2 = make_ind(macd=0.5, macd_signal=1.0)
        assert check_macd_golden_cross(ind2) is False

    def test_volume_ratio(self):
        ind = make_ind(volume_ratio=1.3)
        assert check_volume_ratio_ge(ind, 1.2) is True
        assert check_volume_ratio_ge(ind, 1.5) is False

    def test_drawdown_from_peak(self):
        ind = make_ind(pnl_pct=-10.0)
        assert check_drawdown_from_peak(ind, 0.08) is True

        ind2 = make_ind(pnl_pct=-5.0)
        assert check_drawdown_from_peak(ind2, 0.08) is False

    def test_none_safety(self):
        """None 값 안전 처리"""
        ind = make_ind(rsi=None, price=None, macd=None)
        assert check_rsi_le(ind, 38) is False
        assert check_price_below_ma20(ind) is False
        assert check_macd_golden_cross(ind) is False


# ─────────────────────────────────────────────
# VIX 오버레이 테스트
# ─────────────────────────────────────────────

class TestVixOverlay:
    def test_normal(self):
        assert get_vix_allocation_modifier(18.0) == 1.0

    def test_elevated(self):
        assert get_vix_allocation_modifier(22.0) == 1.0

    def test_high(self):
        assert get_vix_allocation_modifier(27.0) == 0.7

    def test_extreme(self):
        assert get_vix_allocation_modifier(32.0) == 0.5

    def test_panic(self):
        assert get_vix_allocation_modifier(36.0) == 0.0

    def test_none(self):
        assert get_vix_allocation_modifier(None) == 1.0

    def test_vix_panic_flag(self):
        assert check_vix_panic(35.0) is True
        assert check_vix_panic(34.9) is False


# ─────────────────────────────────────────────
# Exit 시스템 테스트
# ─────────────────────────────────────────────

class TestExitSystem:
    def test_no_exit_on_healthy(self):
        """건강한 종목 — Exit 없음"""
        ind = make_ind(rsi=50.0, macd_hist_trend="rising_2d", pnl_pct=5.0)
        ctx = make_ctx(vix=18.0)
        level, met, _ = evaluate_exit(ind, ctx)
        assert level is None

    def test_top_signal_rsi(self):
        """RSI 75 이상 → TOP 시그널"""
        ind = make_ind(rsi=78.0)
        ctx = make_ctx()
        level, met, _ = evaluate_exit(ind, ctx)
        assert level == 99
        assert "rsi >= 75" in met

    def test_l3_drawdown(self):
        """8% 하락 → L3"""
        ind = make_ind(rsi=30.0, pnl_pct=-15.0,
                       macd=0.5, macd_signal=1.0,
                       macd_hist_trend="declining_3d")
        ctx = make_ctx(vix=20.0)
        level, met, _ = evaluate_exit(ind, ctx)
        assert level == 3
        assert "drawdown_8pct" in met

    def test_l1_two_conditions(self):
        """L1 — 2개 조건 충족"""
        ind = make_ind(
            rsi=65.0,
            macd_hist_trend="declining_2d",
            volume_ratio=0.6,   # 음의 거래량 다이버전스
        )
        ctx = make_ctx()
        level, met, _ = evaluate_exit(ind, ctx)
        assert level == 1

    def test_vix_panic_triggers_l1(self):
        """VIX 35 이상 → L1 자동 발동"""
        ind = make_ind()
        ctx = make_ctx(vix=36.0)
        level, met, _ = evaluate_exit(ind, ctx)
        assert level == 1
        assert "vix_panic >= 35" in met


# ─────────────────────────────────────────────
# 마스터 스위치 테스트
# ─────────────────────────────────────────────

class TestMasterSwitch:
    def test_red_blocks_growth_entry(self):
        """마스터 스위치 RED → 성장주 진입 차단"""
        ind = make_ind(
            ticker="TSLA", rsi=30.0,
            macd_hist_trend="rising_2d",
            bb_lower=85.0, price=88.0,
        )
        ctx = make_ctx(master_switch="RED")
        result = evaluate_growth_v22(ind, ctx)
        assert result.action == "HOLD"
        assert any("RED" in n for n in result.notes)

    def test_red_blocks_etf_entry(self):
        """마스터 스위치 RED → ETF 진입 차단"""
        ind = make_ind(ticker="QQQ", rsi=35.0, price=85.0, ma20=95.0)
        ctx = make_ctx(master_switch="RED")
        result = evaluate_etf_v24(ind, ctx)
        assert result.action == "HOLD"

    def test_green_allows_growth_entry(self):
        """마스터 스위치 GREEN → 조건 충족 시 진입 허용"""
        ind = make_ind(
            ticker="TSLA",
            rsi=35.0,
            adx=20.0,
            price=88.0,
            ma20=95.0,
            bb_lower=87.0,
            macd_hist_trend="rising_2d",
        )
        ctx = make_ctx(master_switch="GREEN")
        result = evaluate_growth_v22(ind, ctx)
        # 조건 3개 충족 시 BUY_T1 또는 WATCH
        assert result.action in ("BUY_T1", "WATCH")


# ─────────────────────────────────────────────
# Bond v2.6 테스트
# ─────────────────────────────────────────────

class TestBondV26:
    def test_bond_t1_trigger(self):
        """30Y >= 5.0% AND RSI <= 35 → BUY_T1"""
        ind = make_ind(ticker="TLT", rsi=33.0)
        ctx = make_ctx(master_switch="RED", treasury_30y=5.05)
        result = evaluate_bond_v26(ind, ctx)
        assert result.action == "BUY_T1"
        assert result.tranche == 1

    def test_bond_master_switch_exempt(self):
        """Bond는 마스터 스위치 RED여도 진입 가능"""
        ind = make_ind(ticker="TLT", rsi=30.0)
        ctx = make_ctx(master_switch="RED", treasury_30y=5.1)
        result = evaluate_bond_v26(ind, ctx)
        # RED임에도 T1 조건 충족이면 BUY
        assert result.action == "BUY_T1"

    def test_bond_watch_below_trigger(self):
        """30Y 4.8~4.99% → WATCH"""
        ind = make_ind(ticker="TLT", rsi=40.0)
        ctx = make_ctx(master_switch="RED", treasury_30y=4.85)
        result = evaluate_bond_v26(ind, ctx)
        assert result.action in ("WATCH", "HOLD")
