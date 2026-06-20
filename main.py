#!/usr/bin/env python3
"""
AI Trading Assistant - Professional XAU/USD Trading Bot
Main entry point that starts both Telegram bot and FastAPI web server.
"""

import asyncio
import logging
import sys
from typing import NoReturn

import uvicorn

from config import settings
from bot.telegram_bot import TradingBot
from dashboard.control_panel import app as fastapi_app

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/trading_bot.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


async def run_telegram_bot():
    bot = TradingBot()
    app = bot.build_app()
    logger.info("Starting Telegram bot...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("Telegram bot is running!")
    try:
        await bot.market_analyzer.auto_analyze_loop()
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def run_fastapi():
    logger.info(f"Starting FastAPI dashboard on port {settings.WEBHOOK_PORT}...")
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=settings.WEBHOOK_PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )


async def main() -> NoReturn:
    logger.info("=" * 60)
    logger.info("GOLD AI TRADER - Professional XAU/USD")
    logger.info("=" * 60)
    logger.info(f"Capital: ${settings.DEFAULT_CAPITAL} | Risk: {settings.DEFAULT_RISK_PERCENT}%")
    logger.info(f"Min Confidence: {settings.DEFAULT_MIN_CONFIDENCE}% | Type: {settings.DEFAULT_TRADING_TYPE}")
    logger.info(f"Small Capital Protection: {'ON' if settings.SMALL_CAPITAL_MODE else 'OFF'}")
    logger.info(f"Max Daily Trades: {settings.DEFAULT_MAX_TRADES_PER_DAY}")
    logger.info(f"Analysis Interval: {settings.ANALYSIS_INTERVAL_MINUTES} min")
    logger.info(f"MT5: {'Enabled' if settings.MT5_ENABLED else 'Disabled'}")
    logger.info("=" * 60)
    if settings.TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("=" * 60)
        logger.error("ERROR: You must set TELEGRAM_TOKEN in .env file!")
        logger.error("1. Copy .env.example to .env")
        logger.error("2. Set your Telegram Bot Token from @BotFather")
        logger.error("3. Set your Telegram User ID")
        logger.error("=" * 60)
        sys.exit(1)
    telegram_task = asyncio.create_task(run_telegram_bot())
    loop = asyncio.get_event_loop()
    await asyncio.gather(
        telegram_task,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
