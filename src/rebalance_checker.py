"""
src/rebalance_checker.py — 리밸런싱 트리거 체크
4개 트리거: 단일 종목 과중, 자산군 편차, 배당 한도, 세금 계좌
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))
ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"

# 세전 배당률 (연간 추정, 종목별)
DIVIDEND_YIELD_MAP = {
    "SCHD": 0.035,   # 3.5%
    "JEPI": 0.074,   # 7.4%
    "O":    0.060,   # 6.0%
    "TLT":  0.040,   # 4.0%
    "BIL":  0.052,   # 5.2%
    "VOO":  0.013,   # 1.3%
    "SPY":  0.013,   # 1.3%
    "QQQ":  0.006,   # 0.6%
    "SOXX": 0.008,   # 0.8%
    "AAPL": 0.005,   # 0.5%
    "MSFT": 0.008,   # 0.8%
    "NVDA": 0.001,   # 0.1%
    "TSLA": 0.000,
    "PLTR": 0.000,
    "GOOGL":0.005,   # 0.5%
    "AMZN": 0.000,
    "UNH":  0.016,   # 1.6%
    "SLV":  0.000,
    "TQQQ": 0.000,
    "SOXL": 0.000,
    "ETHU": 0.000,
    "CRCL": 0.000,
    "BTDR": 0.000,
}

# 자산군 분류 (리밸런싱용)
ASSET_CLASS_MAP = {
    "equity": ["VOO", "QQQ", "SCHD", "AAPL", "JEPI", "SOXX", "TSLA",
               "NVDA", "PLTR", "SPY", "UNH", "MSFT", "GOOGL", "AMZN", "O",
               "TQQQ", "SOXL", "ETHU", "CRCL", "BTDR"],
    "bond": ["TLT", "BIL"],
    "commodity": ["SLV"],
}


def load_thresholds() -> dict:
    """config/thresholds.yaml에서 리밸런싱 임계값 로드"""
    with open(CONFIG_DIR / "thresholds.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("rebalancing", {})


def load_portfolio() -> Optional[dict]:
    path = DATA_DIR / "portfolio.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def calc_portfolio_weights(holdings: list[dict]) -> dict[str, float]:
    """종목별 비중 계산"""
    total = sum(h["value_usd"] for h in holdings)
    if total == 0:
        return {}
    return {h["ticker"]: h["value_usd"] / total for h in holdings}


def calc_asset_class_weights(holdings: list[dict]) -> dict[str, float]:
    """자산군별 비중 계산"""
    total = sum(h["value_usd"] for h in holdings)
    class_totals = {"equity": 0.0, "bond": 0.0, "commodity": 0.0, "other": 0.0}

    for h in holdings:
        ticker = h["ticker"]
        classified = False
        for cls, tickers in ASSET_CLASS_MAP.items():
            if ticker in tickers:
                class_totals[cls] += h["value_usd"]
                classified = True
                break
        if not classified:
            class_totals["other"] += h["value_usd"]

    if total == 0:
        return {k: 0.0 for k in class_totals}
    return {k: v / total for k, v in class_totals.items()}


def calc_annual_dividend_krw(holdings: list[dict], usdkrw: float = 1425.0) -> float:
    """연간 예상 배당금 계산 (KRW)"""
    total_dividend_usd = 0.0
    for h in holdings:
        yield_rate = DIVIDEND_YIELD_MAP.get(h["ticker"], 0.0)
        total_dividend_usd += h["value_usd"] * yield_rate
    return total_dividend_usd * usdkrw


# ─────────────────────────────────────────────
# 4개 리밸런싱 트리거
# ─────────────────────────────────────────────

def check_single_position_overweight(weights: dict[str, float], thresh: dict) -> list[dict]:
    """트리거 1: 단일 종목 15% 초과"""
    max_pct = thresh.get("single_position_max_pct", 0.15)
    trim_target = thresh.get("single_position_trim_target", 0.12)
    alerts = []
    for ticker, weight in weights.items():
        if weight > max_pct:
            alerts.append({
                "trigger": "single_position_overweight",
                "ticker": ticker,
                "current_pct": round(weight * 100, 2),
                "max_pct": round(max_pct * 100, 2),
                "action": f"다음 L1/L2 시그널 시 {round(trim_target * 100, 1)}%까지 트림",
                "message": (
                    f"{ticker} 비중 {weight*100:.1f}% — "
                    f"최대 {max_pct*100:.0f}% 초과. "
                    f"L1/L2 시그널 발생 시 {trim_target*100:.0f}%까지 트림 권장."
                ),
                "severity": "warning" if weight > max_pct * 1.2 else "caution",
            })
    return alerts


def check_asset_class_drift(class_weights: dict[str, float], thresh: dict) -> list[dict]:
    """트리거 2: 자산군 비중 편차 (주식 75% 초과 OR 채권 15% 미만)"""
    equity_max = thresh.get("equity_max_pct", 0.75)
    bond_min = thresh.get("bond_min_pct", 0.15)
    alerts = []

    equity_pct = class_weights.get("equity", 0)
    bond_pct = class_weights.get("bond", 0)

    if equity_pct > equity_max:
        alerts.append({
            "trigger": "asset_class_drift",
            "asset_class": "equity",
            "current_pct": round(equity_pct * 100, 2),
            "threshold_pct": round(equity_max * 100, 2),
            "action": "신규 자금을 채권/금으로 배분",
            "message": (
                f"주식 비중 {equity_pct*100:.1f}% — "
                f"상한 {equity_max*100:.0f}% 초과. "
                f"신규 자금을 채권/금으로 리다이렉트 권장."
            ),
            "severity": "caution",
        })

    if bond_pct < bond_min:
        alerts.append({
            "trigger": "asset_class_drift",
            "asset_class": "bond",
            "current_pct": round(bond_pct * 100, 2),
            "threshold_pct": round(bond_min * 100, 2),
            "action": "TLT/BIL 비중 확대 검토",
            "message": (
                f"채권 비중 {bond_pct*100:.1f}% — "
                f"하한 {bond_min*100:.0f}% 미달. "
                f"TLT/BIL 추가 매수 검토."
            ),
            "severity": "info",
        })

    return alerts


def check_dividend_income_limit(
    holdings: list[dict],
    thresh: dict,
    usdkrw: float = 1425.0
) -> list[dict]:
    """트리거 3: 연간 배당 18M KRW 한도"""
    limit_krw = thresh.get("dividend_annual_limit_krw", 18_000_000)
    buffer_krw = thresh.get("dividend_safety_buffer_krw", 2_000_000)
    warn_threshold = limit_krw - buffer_krw  # 16M KRW에서 경고

    annual_div_krw = calc_annual_dividend_krw(holdings, usdkrw)
    alerts = []

    if annual_div_krw >= limit_krw:
        alerts.append({
            "trigger": "dividend_income_limit",
            "annual_dividend_krw": round(annual_div_krw),
            "limit_krw": limit_krw,
            "action": "고배당에서 성장주/채권으로 회전",
            "message": (
                f"연간 배당 예상 {annual_div_krw/1e6:.1f}M KRW — "
                f"한도 {limit_krw/1e6:.0f}M KRW 초과. "
                f"SCHD/JEPI/O → 성장주 또는 채권으로 회전 검토."
            ),
            "severity": "warning",
        })
    elif annual_div_krw >= warn_threshold:
        alerts.append({
            "trigger": "dividend_income_limit",
            "annual_dividend_krw": round(annual_div_krw),
            "limit_krw": limit_krw,
            "action": "배당 비중 모니터링",
            "message": (
                f"연간 배당 예상 {annual_div_krw/1e6:.1f}M KRW — "
                f"한도 {limit_krw/1e6:.0f}M KRW의 {annual_div_krw/limit_krw*100:.0f}%. "
                f"추가 고배당 종목 매수 자제."
            ),
            "severity": "info",
        })

    return alerts


def check_tax_account_priority() -> list[dict]:
    """트리거 4: ISA/연금 계좌 우선 활용 안내"""
    # 실제 계좌 잔여 용량은 외부 정보가 필요하므로 정적 안내
    return [{
        "trigger": "tax_account_priority",
        "action": "ISA/연금 계좌 신규 매수 우선 배분",
        "message": "ISA/연금 계좌 연간 납입 한도 활용 여부 확인. 세제 혜택 활용 우선.",
        "severity": "info",
    }]


# ─────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────

def run_rebalance_check(usdkrw: float = 1425.0) -> dict:
    """리밸런싱 체크 실행 → signals.json의 rebalance_alerts 업데이트"""
    portfolio = load_portfolio()
    if not portfolio:
        logger.error("portfolio.json 없음")
        return {}

    holdings = portfolio.get("holdings", [])
    thresh = load_thresholds()

    weights = calc_portfolio_weights(holdings)
    class_weights = calc_asset_class_weights(holdings)

    # 4개 트리거 실행
    alerts = []
    alerts.extend(check_single_position_overweight(weights, thresh))
    alerts.extend(check_asset_class_drift(class_weights, thresh))
    alerts.extend(check_dividend_income_limit(holdings, thresh, usdkrw))
    alerts.extend(check_tax_account_priority())

    today = datetime.now(KST).strftime("%Y-%m-%d")

    result = {
        "date": today,
        "portfolio_stats": {
            "total_value_usd": portfolio.get("total_value_usd", 0),
            "asset_class_weights": {k: round(v * 100, 2) for k, v in class_weights.items()},
            "top5_by_weight": sorted(
                [(t, round(w * 100, 2)) for t, w in weights.items()],
                key=lambda x: x[1], reverse=True
            )[:5],
        },
        "rebalance_alerts": alerts,
        "alert_count": len([a for a in alerts if a.get("severity") in ("warning", "caution")]),
    }

    # signals.json에 병합
    signals_path = DATA_DIR / "signals.json"
    if signals_path.exists():
        with open(signals_path, encoding="utf-8") as f:
            signals_doc = json.load(f)
        signals_doc["rebalance_alerts"] = alerts
        signals_doc["portfolio_stats"] = result["portfolio_stats"]
        with open(signals_path, "w", encoding="utf-8") as f:
            json.dump(signals_doc, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ signals.json 리밸런싱 알림 업데이트")

    for a in alerts:
        level = a.get("severity", "info")
        logger.info(f"  [{level.upper()}] {a['message'][:80]}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_rebalance_check()
    if result:
        print(f"\n[완료] 리밸런싱 체크 완료")
        print(f"   경고/주의: {result['alert_count']}건")
        for a in result["rebalance_alerts"]:
            print(f"   [{a.get('severity','info').upper()}] {a['message'][:80]}")
