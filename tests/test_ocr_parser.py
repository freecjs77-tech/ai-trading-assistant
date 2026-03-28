"""
tests/test_ocr_parser.py — OCR 파서 단위 테스트
Tesseract 없이 순수 로직만 테스트
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ocr_parser import (
    clean_dollar,
    extract_dollar_amount,
    extract_pnl,
    extract_shares,
    find_ticker_in_line,
    update_portfolio,
)


# ─────────────────────────────────────────────
# clean_dollar 테스트
# ─────────────────────────────────────────────
class TestCleanDollar:
    def test_basic_space_removal(self):
        """$1 7,055 → $17,055"""
        assert clean_dollar("$1 7,055") == "$17,055"

    def test_large_amount(self):
        """$1 02,110 → $102,110"""
        assert clean_dollar("$1 02,110") == "$102,110"

    def test_no_space(self):
        """공백 없는 금액은 그대로"""
        assert clean_dollar("$17,055") == "$17,055"

    def test_multiple_occurrences(self):
        """여러 금액 동시 보정"""
        text = "평가금액 $9 1,630 손익 $4 30"
        result = clean_dollar(text)
        assert "$91,630" in result

    def test_no_dollar(self):
        """달러 기호 없는 텍스트는 그대로"""
        assert clean_dollar("테슬라") == "테슬라"


# ─────────────────────────────────────────────
# extract_dollar_amount 테스트
# ─────────────────────────────────────────────
class TestExtractDollarAmount:
    def test_basic(self):
        assert extract_dollar_amount("$17,055") == 17055.0

    def test_with_decimal(self):
        assert extract_dollar_amount("$102,109.73") == 102109.73

    def test_multiple_pick_max(self):
        """여러 금액 중 최대값 반환"""
        # 평가금액이 손익보다 크므로 최대값 반환
        text = "$9,745 (+$3,280 (25.19%))"
        result = extract_dollar_amount(text)
        assert result == 9745.0

    def test_none_on_missing(self):
        assert extract_dollar_amount("테슬라 주식") is None

    def test_small_amount(self):
        assert extract_dollar_amount("$18") == 18.0


# ─────────────────────────────────────────────
# extract_pnl 테스트
# ─────────────────────────────────────────────
class TestExtractPnl:
    def test_positive_pnl(self):
        pnl_usd, pnl_pct = extract_pnl("+$12,079 (13.42%)")
        assert pnl_usd == 12079.0
        assert pnl_pct == 13.42

    def test_negative_pnl(self):
        pnl_usd, pnl_pct = extract_pnl("-$3,280 (25.19%)")
        assert pnl_usd == -3280.0
        assert pnl_pct == -25.19

    def test_no_pnl(self):
        pnl_usd, pnl_pct = extract_pnl("테슬라")
        assert pnl_usd is None
        assert pnl_pct is None

    def test_small_pnl(self):
        pnl_usd, pnl_pct = extract_pnl("+$430.50 (0.47%)")
        assert pnl_usd == 430.50
        assert pnl_pct == 0.47


# ─────────────────────────────────────────────
# extract_shares 테스트
# ─────────────────────────────────────────────
class TestExtractShares:
    def test_decimal_shares(self):
        assert extract_shares("175.157486주") == 175.157486

    def test_integer_shares(self):
        assert extract_shares("100주") == 100.0

    def test_small_shares(self):
        assert extract_shares("0.034주") == 0.034

    def test_no_shares(self):
        assert extract_shares("테슬라 주식") is None

    def test_with_comma(self):
        assert extract_shares("1,019주") == 1019.0


# ─────────────────────────────────────────────
# find_ticker_in_line 테스트
# ─────────────────────────────────────────────
class TestFindTickerInLine:
    @pytest.fixture
    def ticker_map(self):
        return {
            "테슬라": "TSLA",
            "엔비디아": "NVDA",
            "iShares 2 ETF": "SLV",
            "iShares 은": "SLV",
            "iShares 20": "TLT",
            "SPDR 1-3": "BIL",
            "Vanguard S&P": "VOO",
            "리얼티 인컴": "O",
        }

    def test_korean_growth(self, ticker_map):
        assert find_ticker_in_line("테슬라 361.88", ticker_map) == "TSLA"

    def test_ocr_silver_correction(self, ticker_map):
        """OCR 보정: '은' → '2'"""
        assert find_ticker_in_line("iShares 2 ETF $761", ticker_map) == "SLV"

    def test_tlt(self, ticker_map):
        assert find_ticker_in_line("iShares 20+ Year Treasury", ticker_map) == "TLT"

    def test_bil(self, ticker_map):
        assert find_ticker_in_line("SPDR 1-3 Month Treasury", ticker_map) == "BIL"

    def test_voo(self, ticker_map):
        assert find_ticker_in_line("Vanguard S&P 500 ETF", ticker_map) == "VOO"

    def test_reit(self, ticker_map):
        assert find_ticker_in_line("리얼티 인컴", ticker_map) == "O"

    def test_no_match(self, ticker_map):
        assert find_ticker_in_line("알 수 없는 종목", ticker_map) is None

    def test_longer_key_priority(self, ticker_map):
        """긴 키가 우선 매핑되어야 함 (iShares 2 ETF > iShares 2)"""
        assert find_ticker_in_line("iShares 2 ETF $761", ticker_map) == "SLV"


# ─────────────────────────────────────────────
# update_portfolio 테스트
# ─────────────────────────────────────────────
class TestUpdatePortfolio:
    def test_basic_structure(self):
        parsed = [
            {"ticker": "TSLA", "value_usd": 9745.0, "pnl_usd": -3280.0, "pnl_pct": -25.19, "shares": 26.93},
            {"ticker": "NVDA", "value_usd": 8158.0, "pnl_usd": -2140.0, "pnl_pct": -20.77, "shares": 62.12},
        ]
        portfolio = update_portfolio(parsed)
        assert "updated_at" in portfolio
        assert "total_value_usd" in portfolio
        assert portfolio["total_value_usd"] == 17903.0
        assert len(portfolio["holdings"]) == 2
        assert portfolio["source"] == "toss_securities_ocr"

    def test_total_value_sum(self):
        parsed = [
            {"ticker": "VOO", "value_usd": 100000.0, "pnl_usd": None, "pnl_pct": None, "shares": None},
            {"ticker": "BIL", "value_usd": 50000.0, "pnl_usd": None, "pnl_pct": None, "shares": None},
        ]
        portfolio = update_portfolio(parsed)
        assert portfolio["total_value_usd"] == 150000.0

    def test_all_23_tickers(self):
        """23개 종목 구조 검증"""
        tickers = ["VOO", "BIL", "QQQ", "SCHD", "AAPL", "O", "JEPI", "SOXX",
                   "TSLA", "TLT", "NVDA", "PLTR", "SPY", "UNH", "MSFT",
                   "GOOGL", "AMZN", "SLV", "TQQQ", "SOXL", "ETHU", "CRCL", "BTDR"]
        parsed = [
            {"ticker": t, "value_usd": 1000.0, "pnl_usd": 0.0, "pnl_pct": 0.0, "shares": 10.0}
            for t in tickers
        ]
        portfolio = update_portfolio(parsed)
        assert len(portfolio["holdings"]) == 23
