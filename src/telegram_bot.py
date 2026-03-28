"""
src/telegram_bot.py — 텔레그램 봇
수신: 토스증권 스크린샷 → OCR → 포트폴리오 업데이트
발신: 분석 완료 → 요약 + 대시보드 URL 알림
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
sys.path.insert(0, str(ROOT_DIR / "src"))

# 환경 변수
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "https://your-app.streamlit.app")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # "owner/repo"


# ─────────────────────────────────────────────
# 텔레그램 발신 함수 (봇 없이 HTTP 직접 호출)
# ─────────────────────────────────────────────

def send_telegram_message(text: str, token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
    """텔레그램 메시지 직접 발송 (HTTP API)"""
    token = token or TELEGRAM_BOT_TOKEN
    chat_id = chat_id or TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 미설정")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("텔레그램 메시지 발송 완료")
        return True
    except requests.RequestException as e:
        logger.error(f"텔레그램 발송 실패: {e}")
        return False


def format_notify_message(signals_path: Optional[str] = None) -> str:
    """
    signals.json → 텔레그램 알림 메시지 포맷
    """
    sig_path = Path(signals_path) if signals_path else DATA_DIR / "signals.json"
    portfolio_path = DATA_DIR / "portfolio.json"

    # 포트폴리오 총자산
    total_value = 0
    if portfolio_path.exists():
        with open(portfolio_path, encoding="utf-8") as f:
            portfolio = json.load(f)
        total_value = portfolio.get("total_value_usd", 0)

    # 시그널
    if not sig_path.exists():
        return f"📊 포트폴리오 업데이트 완료\n총자산: ${total_value:,.0f}\n\n🔗 대시보드: {DASHBOARD_URL}"

    with open(sig_path, encoding="utf-8") as f:
        signals_doc = json.load(f)

    ms = signals_doc.get("master_switch", "N/A")
    ms_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(ms, "⚫")
    vix_tier = signals_doc.get("vix_tier", "")
    treasury = signals_doc.get("treasury_30y")
    date = signals_doc.get("date", "")

    signals = signals_doc.get("signals", [])
    summary = signals_doc.get("summary", {})

    # 주요 시그널 추출
    important_sigs = [s for s in signals if s["action"] not in ("HOLD",)]
    exit_sigs = [s for s in important_sigs if "WARNING" in s["action"] or "WEAKENING" in s["action"] or "BREAKDOWN" in s["action"]]
    buy_sigs = [s for s in important_sigs if s["action"].startswith("BUY")]
    watch_sigs = [s for s in important_sigs if s["action"] == "WATCH"]
    top_sigs = [s for s in important_sigs if s["action"] == "TOP_SIGNAL"]

    lines = [
        f"📊 <b>포트폴리오 일일 리포트 {date}</b>",
        f"총자산: ${total_value:,.0f}",
        f"마스터 스위치: {ms_emoji} <b>{ms}</b>",
        f"VIX: {vix_tier}" + (f" | 30Y 금리: {treasury:.3f}%" if treasury else ""),
        "",
    ]

    if top_sigs:
        for s in top_sigs[:3]:
            lines.append(f"🔥 <b>{s['ticker']}</b>: 상단 시그널 ({s['confidence']}%)")

    if exit_sigs:
        for s in exit_sigs[:4]:
            emoji = "🚨" if "L3" in s["action"] or "L2" in s["action"] else "⚠️"
            action_ko = {"L3_BREAKDOWN": "L3 붕괴", "L2_WEAKENING": "L2 약화",
                         "L1_WARNING": "L1 경고"}.get(s["action"], s["action"])
            lines.append(f"{emoji} <b>{s['ticker']}</b>: {action_ko} ({s['confidence']}%)")

    if buy_sigs:
        for s in buy_sigs[:3]:
            t = s.get("tranche", "?")
            lines.append(f"💚 <b>{s['ticker']}</b>: {t}차 매수 신호 ({s['confidence']}%)")

    if watch_sigs:
        watch_list = ", ".join(f"<b>{s['ticker']}</b>" for s in watch_sigs[:4])
        lines.append(f"👀 주시: {watch_list}")

    # 매크로 알림
    macro_alerts = signals_doc.get("macro_alerts", [])
    warning_alerts = [a for a in macro_alerts if a.get("level") in ("warning", "danger")]
    if warning_alerts:
        lines.append("")
        for alert in warning_alerts[:2]:
            lines.append(f"⚡ {alert['message'][:60]}")

    lines.extend([
        "",
        f"🔗 <a href='{DASHBOARD_URL}'>대시보드 보기</a>",
    ])

    return "\n".join(lines)


def trigger_github_action(image_url: str) -> bool:
    """GitHub Actions repository_dispatch 트리거"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.warning("GITHUB_TOKEN 또는 GITHUB_REPO 미설정")
        return False

    url = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}",
    }
    payload = {
        "event_type": "portfolio_update",
        "client_payload": {"image_url": image_url},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 204:
            logger.info("GitHub Actions 트리거 완료")
            return True
        else:
            logger.error(f"GitHub Actions 트리거 실패: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"GitHub Actions 트리거 오류: {e}")
        return False


# ─────────────────────────────────────────────
# 텔레그램 봇 핸들러 (수신 모드)
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """'/start' 명령어"""
    await update.message.reply_text(
        "📊 <b>AI Trading Assistant Bot</b>\n\n"
        "사용법:\n"
        "• 토스증권 스크린샷을 이미지로 전송 → 자동 분석\n"
        "• /status — 현재 포트폴리오 상태\n"
        "• /signals — 오늘의 시그널\n"
        "• /dashboard — 대시보드 링크",
        parse_mode="HTML",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status — 포트폴리오 현황"""
    portfolio_path = DATA_DIR / "portfolio.json"
    if not portfolio_path.exists():
        await update.message.reply_text("portfolio.json 없음. 스크린샷을 전송해주세요.")
        return

    with open(portfolio_path, encoding="utf-8") as f:
        portfolio = json.load(f)

    total = portfolio.get("total_value_usd", 0)
    holdings = portfolio.get("holdings", [])
    updated = portfolio.get("updated_at", "N/A")

    text = f"📊 <b>포트폴리오 현황</b>\n총자산: ${total:,.0f}\n종목 수: {len(holdings)}개\n업데이트: {updated}"
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_signals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/signals — 오늘의 시그널 요약"""
    msg = format_notify_message()
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/dashboard — 대시보드 링크"""
    await update.message.reply_text(
        f"🔗 <a href='{DASHBOARD_URL}'>대시보드 열기</a>",
        parse_mode="HTML",
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """이미지 수신 핸들러 — OCR 파싱 → GitHub Actions 트리거"""
    await update.message.reply_text("⏳ 스크린샷 수신. OCR 파싱 중...")

    # 가장 큰 해상도 사진 다운로드
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    # 임시 파일로 저장
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    await file.download_to_drive(tmp_path)
    logger.info(f"이미지 저장: {tmp_path}")

    # 로컬 OCR 파싱 시도
    try:
        from ocr_parser import parse_screenshot, update_portfolio, save_portfolio

        holdings = parse_screenshot(tmp_path)
        if holdings:
            portfolio = update_portfolio(holdings, str(DATA_DIR / "portfolio.json"))
            save_portfolio(portfolio)
            count = len(holdings)
            total = portfolio["total_value_usd"]
            await update.message.reply_text(
                f"✅ OCR 완료: {count}개 종목 파싱\n총자산: ${total:,.0f}\n"
                f"⏳ 시장 데이터 수집 및 분석 중...\n"
                f"(GitHub Actions에서 계속 처리됩니다)"
            )
        else:
            await update.message.reply_text("⚠️ OCR 파싱 실패. 이미지를 확인해주세요.")
    except ImportError:
        await update.message.reply_text("ℹ️ 로컬 OCR 미지원. GitHub Actions에서 처리합니다.")

    # GitHub Actions 트리거
    file_url = file.file_path  # Telegram 파일 URL
    if trigger_github_action(file_url):
        await update.message.reply_text("🚀 GitHub Actions 트리거 완료. 잠시 후 결과를 전송합니다.")
    else:
        await update.message.reply_text(
            "⚠️ GitHub Actions 트리거 실패.\n"
            "GITHUB_TOKEN, GITHUB_REPO 환경변수를 확인해주세요."
        )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """에러 핸들러"""
    logger.error(f"봇 오류: {context.error}")
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("⚠️ 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


# ─────────────────────────────────────────────
# 실행 진입점
# ─────────────────────────────────────────────

def run_notify() -> None:
    """GitHub Actions에서 호출: 분석 완료 후 알림 발송"""
    msg = format_notify_message()
    success = send_telegram_message(msg)
    if success:
        print("✅ 텔레그램 알림 발송 완료")
    else:
        print("❌ 텔레그램 알림 발송 실패")
        sys.exit(1)


def run_bot() -> None:
    """텔레그램 봇 실행 (수신 모드)"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN 미설정")
        sys.exit(1)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 핸들러 등록
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("signals", cmd_signals))
    app.add_handler(CommandHandler("dashboard", cmd_dashboard))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(handle_error)

    logger.info("텔레그램 봇 시작")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "bot"

    if mode == "notify":
        # GitHub Actions: python src/telegram_bot.py notify
        run_notify()
    elif mode == "bot":
        # 로컬 봇 실행: python src/telegram_bot.py bot
        run_bot()
    else:
        print(f"알 수 없는 모드: {mode}")
        print("사용법: python src/telegram_bot.py [notify|bot]")
        sys.exit(1)
