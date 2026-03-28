"""
tests/test_market_data.py — 시장 데이터 수집 단위 테스트
yfinance 없이 계산 로직만 테스트
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from market_data import (
    calc_sma,
    calc_rsi,
    calc_macd,
    calc_bollinger,
    calc_adx,
    get_macd_hist_trend,
    safe_float,
)


# ─────────────────────────────────────────────
# 헬퍼: 테스트용 가격 시리즈 생성
# ─────────────────────────────────────────────
def make_series(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


# ─────────────────────────────────────────────
# calc_sma 테스트
# ─────────────────────────────────────────────
class TestCalcSma:
    def test_basic(self):
        s = make_series([10.0, 20.0, 30.0, 40.0, 50.0])
        sma3 = calc_sma(s, 3)
        assert sma3.iloc[-1] == pytest.approx(40.0)

    def test_period_equals_length(self):
        s = make_series([1.0, 2.0, 3.0, 4.0, 5.0])
        sma5 = calc_sma(s, 5)
        assert sma5.iloc[-1] == pytest.approx(3.0)

    def test_short_series_returns_nan(self):
        s = make_series([10.0, 20.0])
        sma5 = calc_sma(s, 5)
        assert np.isnan(sma5.iloc[-1])


# ─────────────────────────────────────────────
# calc_rsi 테스트
# ─────────────────────────────────────────────
class TestCalcRsi:
    def test_rsi_range(self):
        """RSI는 항상 0~100 사이"""
        prices = [100 + i * 0.5 for i in range(50)]
        s = make_series(prices)
        rsi = calc_rsi(s, 14)
        valid = rsi.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_rsi_overbought(self):
        """상승 추세에서 RSI > 70"""
        prices = [100.0 + i * 2.0 for i in range(50)]
        s = make_series(prices)
        rsi = calc_rsi(s, 14)
        assert rsi.dropna().iloc[-1] > 70

    def test_rsi_oversold(self):
        """하락 추세에서 RSI < 30"""
        prices = [100.0 - i * 2.0 for i in range(50)]
        prices = [max(p, 1.0) for p in prices]
        s = make_series(prices)
        rsi = calc_rsi(s, 14)
        assert rsi.dropna().iloc[-1] < 30


# ─────────────────────────────────────────────
# calc_macd 테스트
# ─────────────────────────────────────────────
class TestCalcMacd:
    def test_returns_three_series(self):
        s = make_series([100.0 + i for i in range(100)])
        macd, signal, hist = calc_macd(s)
        assert len(macd) == len(signal) == len(hist) == 100

    def test_histogram_is_diff(self):
        """히스토그램 = MACD - Signal"""
        s = make_series([100.0 + i * 0.1 for i in range(100)])
        macd, signal, hist = calc_macd(s)
        expected_hist = macd - signal
        pd.testing.assert_series_equal(hist, expected_hist)

    def test_uptrend_positive_macd(self):
        """강한 상승 추세에서 MACD > 0"""
        prices = [100.0 + i * 1.0 for i in range(100)]
        s = make_series(prices)
        macd, _, _ = calc_macd(s)
        assert macd.dropna().iloc[-1] > 0


# ─────────────────────────────────────────────
# calc_bollinger 테스트
# ─────────────────────────────────────────────
class TestCalcBollinger:
    def test_upper_gt_lower(self):
        prices = [100.0 + np.sin(i) for i in range(50)]
        s = make_series(prices)
        upper, mid, lower = calc_bollinger(s, 20)
        valid_idx = upper.dropna().index
        assert (upper.loc[valid_idx] >= mid.loc[valid_idx]).all()
        assert (mid.loc[valid_idx] >= lower.loc[valid_idx]).all()

    def test_mid_is_sma(self):
        prices = [100.0 + i * 0.1 for i in range(50)]
        s = make_series(prices)
        upper, mid, lower = calc_bollinger(s, 20)
        expected_mid = calc_sma(s, 20)
        pd.testing.assert_series_equal(mid, expected_mid)

    def test_constant_series_zero_width(self):
        """가격이 일정하면 BB 상단=중앙=하단"""
        prices = [100.0] * 50
        s = make_series(prices)
        upper, mid, lower = calc_bollinger(s, 20)
        assert upper.dropna().iloc[-1] == pytest.approx(100.0)
        assert lower.dropna().iloc[-1] == pytest.approx(100.0)


# ─────────────────────────────────────────────
# get_macd_hist_trend 테스트
# ─────────────────────────────────────────────
class TestGetMacdHistTrend:
    def test_rising_3d(self):
        hist = make_series([-3.0, -2.0, -1.0, 0.0, 1.0])
        result = get_macd_hist_trend(hist, 3)
        assert "rising" in result

    def test_declining_3d(self):
        hist = make_series([1.0, 0.0, -1.0, -2.0, -3.0])
        result = get_macd_hist_trend(hist, 3)
        assert "declining" in result

    def test_mixed(self):
        hist = make_series([1.0, -1.0, 1.0, -1.0, 1.0])
        result = get_macd_hist_trend(hist, 3)
        # 마지막 2일 확인
        assert result in ("rising_2d", "mixed")

    def test_insufficient_data(self):
        hist = make_series([1.0])
        result = get_macd_hist_trend(hist, 3)
        assert result == "unknown"


# ─────────────────────────────────────────────
# safe_float 테스트
# ─────────────────────────────────────────────
class TestSafeFloat:
    def test_normal(self):
        assert safe_float(3.14) == pytest.approx(3.14)

    def test_nan_returns_none(self):
        assert safe_float(float('nan')) is None

    def test_none_returns_none(self):
        assert safe_float(None) is None

    def test_string_number(self):
        assert safe_float("3.14") == pytest.approx(3.14)

    def test_invalid_string(self):
        assert safe_float("abc") is None

    def test_numpy_nan(self):
        assert safe_float(np.nan) is None

    def test_integer(self):
        assert safe_float(42) == 42.0
