"""
tests/test_signal_generator.py — 시그널 생성기 단위 테스트
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rule_engine import RuleResult, MarketContext
from signal_generator import (
    calc_confidence,
    format_conditions_text,
    generate_rationale,
    generate_macro_alerts,
    sort_signals,
    ACTION_PRIORITY,
)


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


def make_result(action: str = "HOLD", **kwargs) -> RuleResult:
    r = RuleResult(ticker="TEST", classification="growth_v22", action=action)
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


# ─────────────────────────────────────────────
# 확신도 점수 테스트
# ─────────────────────────────────────────────

class TestCalcConfidence:
    def test_green_bonus(self):
        """GREEN 마스터 스위치 +20 보너스"""
        ctx = make_ctx(master_switch="GREEN", vix=18.0)
        r = make_result("BUY_T1", conditions_met=["a", "b", "c"], conditions_not_met=["d", "e"])
        conf_green = calc_confidence(r, ctx)
        assert conf_green > 50

    def test_red_penalty(self):
        """RED 마스터 스위치 -20 패널티"""
        ctx_green = make_ctx(master_switch="GREEN", vix=18.0)
        ctx_red = make_ctx(master_switch="RED", vix=18.0)
        r = make_result("HOLD", conditions_met=["a", "b"], conditions_not_met=["c", "d"])
        conf_red = calc_confidence(r, ctx_red)
        conf_green = calc_confidence(r, ctx_green)
        assert conf_green > conf_red

    def test_high_vix_penalty(self):
        """VIX 30+ → -10 패널티"""
        ctx_low = make_ctx(vix=18.0, master_switch="GREEN")
        ctx_high = make_ctx(vix=32.0, master_switch="GREEN")
        r = make_result("BUY_T1", conditions_met=["a", "b", "c"], conditions_not_met=[])
        assert calc_confidence(r, ctx_low) > calc_confidence(r, ctx_high)

    def test_exit_signal_minimum(self):
        """L2/L3 Exit → 최소 70% 확신도"""
        ctx = make_ctx(master_switch="RED", vix=32.0)
        r = make_result("L2_WEAKENING", conditions_met=["a"], conditions_not_met=["b", "c", "d"])
        assert calc_confidence(r, ctx) >= 70

    def test_range_0_100(self):
        """0~100 범위 내"""
        ctx = make_ctx()
        for action in ["HOLD", "BUY_T1", "L3_BREAKDOWN", "WATCH"]:
            r = make_result(action)
            conf = calc_confidence(r, ctx)
            assert 0 <= conf <= 100, f"{action}: {conf}"


# ─────────────────────────────────────────────
# 조건 텍스트 포맷 테스트
# ─────────────────────────────────────────────

class TestFormatConditions:
    def test_known_conditions(self):
        conds = ["rsi <= 38", "price_near_bb_lower"]
        text = format_conditions_text(conds)
        assert "RSI 과매도" in text
        assert "BB 하단" in text

    def test_max_4_conditions(self):
        conds = ["a", "b", "c", "d", "e", "f"]
        text = format_conditions_text(conds)
        assert text.count("+") <= 3  # 최대 4개 = + 3개

    def test_empty_conditions(self):
        text = format_conditions_text([])
        assert text == ""

    def test_unknown_condition_passthrough(self):
        """알 수 없는 조건은 원문 그대로"""
        text = format_conditions_text(["unknown_condition_xyz"])
        assert "unknown_condition_xyz" in text


# ─────────────────────────────────────────────
# 근거 텍스트 생성 테스트
# ─────────────────────────────────────────────

class TestGenerateRationale:
    def test_l1_warning(self):
        ctx = make_ctx()
        r = make_result("L1_WARNING", conditions_met=["macd_hist_declining_1_2d"])
        ind_data = {"rsi": 55.0, "macd": -0.5, "macd_signal": 0.2}
        text = generate_rationale(r, ctx, ind_data)
        assert len(text) > 10
        assert isinstance(text, str)

    def test_buy_t1(self):
        ctx = make_ctx()
        r = make_result("BUY_T1", tranche=1,
                        conditions_met=["rsi <= 38", "price_near_bb_lower"])
        ind_data = {"rsi": 36.0, "macd": 0.5, "macd_signal": 0.3}
        text = generate_rationale(r, ctx, ind_data)
        assert "1차" in text or "T1" in text or "매수" in text

    def test_hold(self):
        ctx = make_ctx()
        r = make_result("HOLD")
        ind_data = {"rsi": 50.0, "macd": 0.1, "macd_signal": -0.1}
        text = generate_rationale(r, ctx, ind_data)
        assert "유지" in text or "HOLD" in text or "RSI" in text


# ─────────────────────────────────────────────
# 매크로 알림 테스트
# ─────────────────────────────────────────────

class TestMacroAlerts:
    def test_red_switch_alert(self):
        ctx = make_ctx(master_switch="RED")
        alerts = generate_macro_alerts(ctx)
        types = [a["type"] for a in alerts]
        assert "master_switch" in types

    def test_vix_panic_alert(self):
        ctx = make_ctx(vix=36.0, vix_tier="panic")
        alerts = generate_macro_alerts(ctx)
        vix_alerts = [a for a in alerts if a["type"] == "vix"]
        assert len(vix_alerts) > 0
        assert vix_alerts[0]["level"] == "danger"

    def test_treasury_5pct_alert(self):
        ctx = make_ctx(treasury_30y=5.05)
        alerts = generate_macro_alerts(ctx)
        tr_alerts = [a for a in alerts if a["type"] == "treasury_yield"]
        assert len(tr_alerts) > 0

    def test_no_alerts_on_normal(self):
        ctx = make_ctx(master_switch="GREEN", vix=18.0, treasury_30y=4.5, usdkrw=1380.0)
        alerts = generate_macro_alerts(ctx)
        # GREEN + 정상 환경 → 경고 없음
        warning_alerts = [a for a in alerts if a["level"] in ("warning", "danger")]
        assert len(warning_alerts) == 0

    def test_high_exchange_rate(self):
        ctx = make_ctx(usdkrw=1460.0)
        alerts = generate_macro_alerts(ctx)
        fx_alerts = [a for a in alerts if a["type"] == "exchange_rate"]
        assert len(fx_alerts) > 0


# ─────────────────────────────────────────────
# 시그널 정렬 테스트
# ─────────────────────────────────────────────

class TestSortSignals:
    def test_exit_before_buy(self):
        signals = [
            {"action": "HOLD", "ticker": "A"},
            {"action": "BUY_T1", "ticker": "B"},
            {"action": "L1_WARNING", "ticker": "C"},
            {"action": "L3_BREAKDOWN", "ticker": "D"},
        ]
        sorted_s = sort_signals(signals)
        actions = [s["action"] for s in sorted_s]
        assert actions.index("L3_BREAKDOWN") < actions.index("L1_WARNING")
        assert actions.index("L1_WARNING") < actions.index("BUY_T1")
        assert actions.index("BUY_T1") < actions.index("HOLD")

    def test_all_actions_have_priority(self):
        for action in ["L3_BREAKDOWN", "TOP_SIGNAL", "L2_WEAKENING", "L1_WARNING",
                       "BUY_T3", "BUY_T2", "BUY_T1", "WATCH", "HOLD"]:
            assert action in ACTION_PRIORITY
