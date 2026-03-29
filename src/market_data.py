"""
src/market_data.py — yfinance 시장 데이터 수집 래퍼
보유 종목별 기술 지표 + 매크로 데이터 수집
캐시 실패 시 기존 캐시 사용
"""

import json
import logging
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

KST = timezone(timedelta(hours=9))
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"


# ─────────────────────────────────────────────
# 기술 지표 계산 함수
# ─────────────────────────────────────────────

def calc_sma(series: pd.Series, period: int) -> pd.Series:
    """단순 이동평균"""
    return series.rolling(window=period).mean()


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI(14) 계산"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    # loss가 0인 구간(순수 상승) → RSI=100 처리
    rs = avg_gain / avg_loss.where(avg_loss != 0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    return rsi


def calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD(12,26,9) → (macd, signal, histogram)"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - sig
    return macd, sig, hist


def calc_bollinger(series: pd.Series, period: int = 20, std: int = 2) -> tuple[pd.Series, pd.Series, pd.Series]:
    """볼린저 밴드 → (upper, middle, lower)"""
    mid = calc_sma(series, period)
    std_dev = series.rolling(window=period).std()
    upper = mid + std * std_dev
    lower = mid - std * std_dev
    return upper, mid, lower


def calc_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ADX(14) 계산"""
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr = tr.ewm(com=period - 1, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(com=period - 1, min_periods=period).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(com=period - 1, min_periods=period).mean() / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(com=period - 1, min_periods=period).mean()
    return adx


def get_macd_hist_trend(hist_series: pd.Series, days: int = 3) -> str:
    """
    MACD 히스토그램 추세 분석
    반환: 'rising_Nd' | 'declining_Nd' | 'mixed'
    """
    recent = hist_series.dropna().tail(days)
    if len(recent) < 2:
        return "unknown"
    diffs = recent.diff().dropna()
    if (diffs > 0).all():
        return f"rising_{days}d"
    elif (diffs < 0).all():
        return f"declining_{days}d"
    elif (diffs.tail(2) > 0).all():
        return "rising_2d"
    elif (diffs.tail(2) < 0).all():
        return "declining_2d"
    return "mixed"


def safe_float(val) -> Optional[float]:
    """NaN/None → None 변환"""
    if val is None:
        return None
    try:
        f = float(val)
        return None if np.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────
# 종목 데이터 수집
# ─────────────────────────────────────────────

def fetch_ticker_data(ticker: str, period: str = "1y") -> Optional[dict]:
    """
    단일 종목의 기술 지표 수집
    실패 시 None 반환
    """
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=period, auto_adjust=True)

        if hist.empty or len(hist) < 30:
            logger.warning(f"  {ticker}: 데이터 부족 ({len(hist)}일)")
            return None

        close = hist["Close"]
        high = hist["High"]
        low = hist["Low"]
        volume = hist["Volume"]

        # 이동평균
        ma20 = calc_sma(close, 20)
        ma50 = calc_sma(close, 50)
        ma200 = calc_sma(close, 200)

        # RSI
        rsi = calc_rsi(close, 14)

        # MACD
        macd, macd_sig, macd_hist = calc_macd(close)

        # 볼린저 밴드
        bb_upper, bb_mid, bb_lower = calc_bollinger(close)

        # ADX
        adx = calc_adx(high, low, close)

        # 거래량
        vol_avg20 = calc_sma(volume, 20)

        # 현재값 (마지막 행)
        cur_price = safe_float(close.iloc[-1])
        cur_ma20 = safe_float(ma20.iloc[-1])
        cur_ma50 = safe_float(ma50.iloc[-1])
        cur_ma200 = safe_float(ma200.iloc[-1])
        cur_rsi = safe_float(rsi.iloc[-1])
        cur_macd = safe_float(macd.iloc[-1])
        cur_macd_sig = safe_float(macd_sig.iloc[-1])
        cur_macd_hist = safe_float(macd_hist.iloc[-1])
        cur_bb_upper = safe_float(bb_upper.iloc[-1])
        cur_bb_lower = safe_float(bb_lower.iloc[-1])
        cur_adx = safe_float(adx.iloc[-1])
        cur_vol = safe_float(volume.iloc[-1])
        cur_vol_avg = safe_float(vol_avg20.iloc[-1])

        # 거래량 비율
        vol_ratio = None
        if cur_vol and cur_vol_avg and cur_vol_avg > 0:
            vol_ratio = round(cur_vol / cur_vol_avg, 3)

        # MACD 히스토그램 추세
        macd_hist_trend = get_macd_hist_trend(macd_hist, 3)

        # ── 히스토리 기반 지표 ──────────────────────────────────
        # MA20 기울기: 최근 5거래일 변화율 (양수=상승)
        ma20_slope: Optional[float] = None
        ma20_clean = ma20.dropna()
        if len(ma20_clean) >= 6:
            ma20_slope = safe_float(
                (ma20_clean.iloc[-1] - ma20_clean.iloc[-6]) / ma20_clean.iloc[-6]
            )

        # MA20 위 연속일수
        consecutive_above_ma20 = 0
        n = min(len(close), len(ma20_clean))
        for i in range(1, n + 1):
            if close.iloc[-i] > ma20_clean.iloc[-i]:
                consecutive_above_ma20 += 1
            else:
                break

        # BB상단 위 연속일수
        consecutive_above_bb_upper = 0
        bb_upper_clean = bb_upper.dropna()
        nb = min(len(close), len(bb_upper_clean))
        for i in range(1, nb + 1):
            if close.iloc[-i] > bb_upper_clean.iloc[-i]:
                consecutive_above_bb_upper += 1
            else:
                break

        # 당일 등락률 (%)
        day_change_pct: Optional[float] = None
        if len(close) >= 2:
            day_change_pct = safe_float((close.iloc[-1] / close.iloc[-2] - 1) * 100)

        # 최근 3거래일 누적 등락률 (%)
        gain_3day_pct: Optional[float] = None
        if len(close) >= 4:
            gain_3day_pct = safe_float((close.iloc[-1] / close.iloc[-4] - 1) * 100)

        # 이번 캔들 MA20 아래로 이탈 (L2 ③)
        price_crossed_below_ma20 = False
        if len(close) >= 2 and len(ma20_clean) >= 2:
            price_crossed_below_ma20 = bool(
                close.iloc[-2] >= ma20_clean.iloc[-2]
                and close.iloc[-1] < ma20_clean.iloc[-1]
            )

        # 직전 캔들 BB상단 위에 있었음 (L1 ③)
        price_was_above_bb_upper = False
        if len(close) >= 2 and len(bb_upper_clean) >= 2:
            price_was_above_bb_upper = bool(close.iloc[-2] > bb_upper_clean.iloc[-2])

        return {
            "price": cur_price,
            "ma20": cur_ma20,
            "ma50": cur_ma50,
            "ma200": cur_ma200,
            "above_ma200": bool(cur_price and cur_ma200 and cur_price > cur_ma200),
            "rsi": cur_rsi,
            "macd": cur_macd,
            "macd_signal": cur_macd_sig,
            "macd_histogram": cur_macd_hist,
            "macd_hist_trend": macd_hist_trend,
            "bb_upper": cur_bb_upper,
            "bb_lower": cur_bb_lower,
            "adx": cur_adx,
            "volume": int(cur_vol) if cur_vol else None,
            "volume_avg20": int(cur_vol_avg) if cur_vol_avg else None,
            "volume_ratio": vol_ratio,
            # 히스토리 기반 지표
            "ma20_slope": ma20_slope,
            "consecutive_above_ma20": consecutive_above_ma20,
            "consecutive_above_bb_upper": consecutive_above_bb_upper,
            "day_change_pct": day_change_pct,
            "gain_3day_pct": gain_3day_pct,
            "price_crossed_below_ma20": price_crossed_below_ma20,
            "price_was_above_bb_upper": price_was_above_bb_upper,
        }

    except Exception as e:
        logger.error(f"  {ticker} 데이터 수집 실패: {e}")
        return None


# ─────────────────────────────────────────────
# 매크로 데이터 수집
# ─────────────────────────────────────────────

def fetch_macro_data() -> dict:
    """
    매크로 지표 수집
    - VIX (^VIX)
    - 30Y 국채 (^TYX)
    - 원달러 환율 (USDKRW=X)
    - QQQ, SPY MA200
    """
    macro = {}

    # VIX
    try:
        vix_data = yf.Ticker("^VIX").history(period="5d")
        if not vix_data.empty:
            vix = float(vix_data["Close"].iloc[-1])
            macro["vix"] = round(vix, 2)
            # VIX 구간 분류
            if vix < 20:
                macro["vix_tier"] = "normal"
            elif vix < 25:
                macro["vix_tier"] = "elevated"
            elif vix < 30:
                macro["vix_tier"] = "high"
            elif vix < 35:
                macro["vix_tier"] = "extreme"
            else:
                macro["vix_tier"] = "panic"
            logger.info(f"  VIX: {vix:.2f} ({macro['vix_tier']})")
    except Exception as e:
        logger.warning(f"  VIX 수집 실패: {e}")

    # 30Y 국채 금리
    # ^TYX: yfinance가 % 단위 그대로 반환 (예: 4.982)
    try:
        tyx_data = yf.Ticker("^TYX").history(period="5d")
        if not tyx_data.empty:
            tyx = float(tyx_data["Close"].iloc[-1])
            # ^TYX는 % 단위 직접 반환. 단 간혹 10배 스케일(49.82)로 오는 경우 보정
            treasury = tyx if tyx < 20 else tyx / 10
            macro["treasury_30y"] = round(treasury, 3)
            logger.info(f"  30Y 국채: {macro['treasury_30y']:.3f}%")
    except Exception as e:
        logger.warning(f"  30Y 국채 수집 실패: {e}")

    # 원달러 환율
    try:
        fx_data = yf.Ticker("USDKRW=X").history(period="5d")
        if not fx_data.empty:
            macro["usdkrw"] = round(float(fx_data["Close"].iloc[-1]), 2)
            logger.info(f"  USD/KRW: {macro['usdkrw']:.2f}")
    except Exception as e:
        logger.warning(f"  환율 수집 실패: {e}")

    return macro


def fetch_master_switch_data() -> dict:
    """
    마스터 스위치 계산용 QQQ, SPY MA200 수집
    """
    result = {}
    for ticker in ["QQQ", "SPY"]:
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(period="1y", auto_adjust=True)
            if hist.empty:
                continue
            close = hist["Close"]
            ma200 = calc_sma(close, 200)
            price = float(close.iloc[-1])
            ma200_val = float(ma200.iloc[-1]) if not np.isnan(ma200.iloc[-1]) else None

            result[ticker.lower()] = {
                "price": round(price, 2),
                "ma200": round(ma200_val, 2) if ma200_val else None,
                "above_ma200": bool(ma200_val and price > ma200_val),
            }
            status = "위" if (ma200_val and price > ma200_val) else "아래"
            logger.info(f"  {ticker}: ${price:.2f} (MA200 {status}: ${ma200_val:.2f})")
        except Exception as e:
            logger.error(f"  {ticker} 마스터 스위치 데이터 실패: {e}")

    # 마스터 스위치 상태 결정
    qqq_above = result.get("qqq", {}).get("above_ma200", False)
    spy_above = result.get("spy", {}).get("above_ma200", False)

    if qqq_above and spy_above:
        status = "GREEN"
    elif qqq_above or spy_above:
        status = "YELLOW"
    else:
        status = "RED"

    return {
        "qqq_price": result.get("qqq", {}).get("price"),
        "qqq_ma200": result.get("qqq", {}).get("ma200"),
        "qqq_above_ma200": qqq_above,
        "spy_price": result.get("spy", {}).get("price"),
        "spy_ma200": result.get("spy", {}).get("ma200"),
        "spy_above_ma200": spy_above,
        "status": status,
    }


# ─────────────────────────────────────────────
# 메인 수집 함수
# ─────────────────────────────────────────────

def collect_all(use_cache_on_fail: bool = True) -> dict:
    """
    전체 시장 데이터 수집 → market_cache.json 저장
    """
    logger.info("=" * 50)
    logger.info("시장 데이터 수집 시작")

    # 포트폴리오에서 종목 목록 로드
    portfolio_path = DATA_DIR / "portfolio.json"
    tickers: list[str] = []
    if portfolio_path.exists():
        with open(portfolio_path, encoding="utf-8") as f:
            portfolio = json.load(f)
        tickers = [h["ticker"] for h in portfolio.get("holdings", [])]
    else:
        # 기본 종목 목록 (portfolio.json 없을 때 fallback)
        with open(CONFIG_DIR / "tickers.yaml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        for cls in cfg.get("classifications", {}).values():
            tickers.extend(cls.get("tickers", []))
        tickers = list(dict.fromkeys(tickers))  # 중복 제거

    logger.info(f"대상 종목: {tickers}")

    # 기존 캐시 로드 (수집 실패 시 fallback)
    old_cache = load_cache() if use_cache_on_fail else None
    old_tickers = (old_cache or {}).get("tickers", {})
    old_macro = (old_cache or {}).get("macro", {})
    old_master = (old_cache or {}).get("master_switch", {})

    # 매크로 데이터
    logger.info("\n[매크로 데이터]")
    master_switch = fetch_master_switch_data()
    # FIX: 가격 데이터가 null이면 기존 캐시로 폴백 (status만 체크하면 안 됨)
    if master_switch.get("qqq_price") is None and old_master and old_master.get("qqq_price") is not None:
        master_switch = old_master
        logger.warning("  마스터 스위치 가격 데이터 없음 → 기존 캐시 사용")

    macro = fetch_macro_data()
    if not macro and old_macro:
        macro = old_macro
        logger.warning("  매크로 데이터 수집 실패 → 기존 캐시 사용")

    logger.info(f"  마스터 스위치: {master_switch['status']}")

    # 종목별 데이터
    logger.info("\n[종목 데이터]")
    ticker_data: dict[str, dict] = {}
    for ticker in tickers:
        logger.info(f"  {ticker} 수집 중...")
        data = fetch_ticker_data(ticker)
        if data:
            ticker_data[ticker] = data
        elif use_cache_on_fail and ticker in old_tickers:
            ticker_data[ticker] = old_tickers[ticker]
            logger.warning(f"  {ticker}: 수집 실패 → 기존 캐시 사용")
        else:
            logger.warning(f"  {ticker}: 수집 실패 (캐시 없음)")

    # FIX: 모든 종목 수집 실패 시 기존 캐시 전체 사용
    if not ticker_data and old_tickers:
        ticker_data = old_tickers
        logger.warning(f"  전체 종목 수집 실패 → 기존 캐시 전체 사용 ({len(old_tickers)}개)")

    now_kst = datetime.now(KST).isoformat()
    result = {
        "updated_at": now_kst,
        "master_switch": master_switch,
        "macro": macro,
        "tickers": ticker_data,
    }

    # FIX: 빈 데이터로 유효한 캐시를 덮어쓰지 않음
    if old_cache and not ticker_data and not macro:
        logger.warning("❌ 수집 데이터 없음 — 기존 캐시 유지, 덮어쓰기 안 함")
        return old_cache

    # 저장
    DATA_DIR.mkdir(exist_ok=True)
    cache_path = DATA_DIR / "market_cache.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 시장 데이터 저장 완료: {cache_path}")
    logger.info(f"   종목: {len(ticker_data)}/{len(tickers)}개 성공")
    logger.info(f"   마스터 스위치: {master_switch['status']}")
    logger.info("=" * 50)

    return result


def load_cache() -> Optional[dict]:
    """market_cache.json 로드 (실패 시 None)"""
    cache_path = DATA_DIR / "market_cache.json"
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


if __name__ == "__main__":
    collect_all()
