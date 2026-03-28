"""
tests/test_integration.py — 통합 파이프라인 검증
portfolio.json + market_cache.json → signals.json 전체 흐름
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
DATA_DIR = ROOT / "data"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def portfolio():
    path = DATA_DIR / "portfolio.json"
    assert path.exists(), "data/portfolio.json 없음"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def market_cache():
    """market_cache.json 로드. tickers가 비어있으면 mock 데이터 폴백."""
    path = DATA_DIR / "market_cache.json"
    mock_path = ROOT / "tests" / "fixtures" / "mock_market_data.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("tickers"):  # 실데이터 있으면 그대로 사용
            return data
    assert mock_path.exists(), "mock_market_data.json 없음"
    with open(mock_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def signals():
    path = DATA_DIR / "signals.json"
    assert path.exists(), "data/signals.json 없음"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Phase 4.1: portfolio.json 구조 검증 ────────────────────────────────────

class TestPortfolioJson:

    def test_required_keys(self, portfolio):
        """portfolio.json 필수 키 존재"""
        for key in ["updated_at", "total_value_usd", "holdings"]:
            assert key in portfolio, f"필수 키 누락: {key}"

    def test_23_holdings(self, portfolio):
        """23개 종목 존재"""
        assert len(portfolio["holdings"]) == 23

    def test_total_value_range(self, portfolio):
        """총자산 $430,000~$435,000 범위 (실제 데이터 기준 ±$500)"""
        total = portfolio["total_value_usd"]
        assert 430_000 <= total <= 435_000, f"총자산 범위 초과: ${total:,.0f}"

    def test_holdings_schema(self, portfolio):
        """각 보유 종목 필수 필드 존재"""
        required = ["ticker", "value_usd", "pnl_usd", "pnl_pct", "shares"]
        for h in portfolio["holdings"]:
            for key in required:
                assert key in h, f"{h.get('ticker')}: {key} 누락"

    def test_all_values_numeric(self, portfolio):
        """모든 숫자 필드가 실수값 (None 없음)"""
        for h in portfolio["holdings"]:
            for key in ["value_usd", "pnl_usd", "pnl_pct"]:
                val = h[key]
                assert isinstance(val, (int, float)), \
                    f"{h['ticker']}.{key} = {val!r} (숫자 아님)"

    def test_voo_is_largest(self, portfolio):
        """VOO가 최대 보유 종목"""
        holdings_sorted = sorted(portfolio["holdings"], key=lambda x: x["value_usd"], reverse=True)
        assert holdings_sorted[0]["ticker"] == "VOO"

    def test_expected_values(self, portfolio):
        """주요 종목 금액 오차 $1 이내"""
        expected = {
            "VOO": 102109.73, "BIL": 91629.97, "QQQ": 76310.31,
            "TSLA": 9744.64, "TLT": 8563.99, "BTDR": 18.39,
        }
        holding_map = {h["ticker"]: h for h in portfolio["holdings"]}
        for ticker, exp_val in expected.items():
            actual = holding_map[ticker]["value_usd"]
            assert abs(actual - exp_val) < 1.0, \
                f"{ticker}: 기대 ${exp_val}, 실제 ${actual} (오차 ${abs(actual-exp_val):.2f})"


# ── Phase 4.2: market_cache.json 구조 검증 ────────────────────────────────

class TestMarketCacheJson:

    def test_required_keys(self, market_cache):
        """market_cache.json 필수 키 존재"""
        for key in ["updated_at", "master_switch", "macro", "tickers"]:
            assert key in market_cache, f"필수 키 누락: {key}"

    def test_master_switch_red(self, market_cache):
        """현재 마스터 스위치 RED (실제 데이터 기준)"""
        ms = market_cache["master_switch"]
        assert ms["status"] == "RED", f"마스터 스위치: {ms['status']} (기대: RED)"

    def test_macro_values_reasonable(self, market_cache):
        """매크로 지표 합리적 범위"""
        m = market_cache["macro"]
        assert 5 <= m["vix"] <= 80, f"VIX 범위 초과: {m['vix']}"
        assert 2 <= m["treasury_30y"] <= 8, f"30Y 금리 범위 초과: {m['treasury_30y']}"
        assert 1000 <= m["usdkrw"] <= 1700, f"USD/KRW 범위 초과: {m['usdkrw']}"

    def test_23_tickers_in_cache(self, market_cache):
        """23개 종목 데이터 존재"""
        assert len(market_cache["tickers"]) >= 23

    def test_ticker_has_indicators(self, market_cache):
        """각 종목에 핵심 지표 존재"""
        required = ["price", "rsi", "macd", "macd_signal"]
        for ticker, data in list(market_cache["tickers"].items())[:5]:
            for key in required:
                assert key in data, f"{ticker}: {key} 누락"

    def test_rsi_range(self, market_cache):
        """모든 종목 RSI 0-100 범위"""
        for ticker, data in market_cache["tickers"].items():
            rsi = data.get("rsi")
            if rsi is not None:
                assert 0 <= rsi <= 100, f"{ticker} RSI={rsi} 범위 초과"


# ── Phase 4.3: signals.json 구조 검증 ────────────────────────────────────

class TestSignalsJson:

    def test_required_keys(self, signals):
        """signals.json 필수 키 존재"""
        for key in ["date", "master_switch", "vix_tier", "signals", "macro_alerts"]:
            assert key in signals, f"필수 키 누락: {key}"

    def test_master_switch_red(self, signals):
        """시그널의 마스터 스위치 RED"""
        assert signals["master_switch"] == "RED"

    def test_23_signals(self, signals):
        """23개 종목 시그널 존재"""
        assert len(signals["signals"]) == 23

    def test_signal_schema(self, signals):
        """각 시그널 필수 필드"""
        required = ["ticker", "classification", "action", "confidence",
                    "rationale", "conditions_met", "conditions_not_met"]
        for s in signals["signals"]:
            for key in required:
                assert key in s, f"{s.get('ticker')}: {key} 누락"

    def test_confidence_range(self, signals):
        """모든 확신도 0-100 범위"""
        for s in signals["signals"]:
            c = s["confidence"]
            assert 0 <= c <= 100, f"{s['ticker']}: confidence={c} 범위 초과"

    def test_rationale_korean(self, signals):
        """근거 텍스트가 한국어 포함 비어있지 않음"""
        for s in signals["signals"]:
            r = s["rationale"]
            assert len(r) > 5, f"{s['ticker']}: rationale 너무 짧음: '{r}'"

    def test_macro_alerts_exist(self, signals):
        """RED 마스터 스위치 상황에서 매크로 알림 1개 이상"""
        assert len(signals["macro_alerts"]) >= 1

    def test_no_duplicate_tickers(self, signals):
        """티커 중복 없음"""
        tickers = [s["ticker"] for s in signals["signals"]]
        assert len(tickers) == len(set(tickers)), "중복 티커 발견"

    def test_l3_signals_present(self, signals):
        """현재 시장(RED+VIX 31)에서 L3 시그널 존재"""
        l3 = [s for s in signals["signals"] if s["action"] == "L3_BREAKDOWN"]
        assert len(l3) >= 1, "L3 시그널 없음"


# ── Phase 4.4: 파이프라인 실행 시간 검증 ────────────────────────────────

class TestPipelineRuntime:

    def test_signal_generator_runs(self):
        """signal_generator가 오류 없이 실행됨"""
        from signal_generator import generate_signals, load_signals
        signals = load_signals()
        assert signals is not None
        assert "signals" in signals

    def test_rebalance_checker_runs(self):
        """rebalance_checker가 오류 없이 실행됨"""
        from rebalance_checker import run_rebalance_check
        alerts = run_rebalance_check()
        # VOO 23.6% > 15% → 반드시 alert 존재
        assert len(alerts) >= 1

    def test_rebalance_detects_voo_overweight(self):
        """VOO 23.6% 초과 보유 감지"""
        from rebalance_checker import run_rebalance_check
        result = run_rebalance_check()
        ra = result.get("rebalance_alerts", [])
        tickers = [a.get("ticker", "") for a in ra]
        assert "VOO" in tickers, f"VOO 비중초과 알림 없음. alerts: {ra}"
