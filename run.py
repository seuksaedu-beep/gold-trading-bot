#!/usr/bin/env python3
"""
Deployment startup script for Gold XAUUSD Trading Bot.
Handles MT5 gracefully when not available in cloud environments.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DEPLOY_NO_MT5"] = "1"

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DEPLOY")

try:
    from config import settings
    logger.info(f"Config loaded | Capital: ${settings.DEFAULT_CAPITAL} | Type: {settings.DEFAULT_TRADING_TYPE}")

    from bot.telegram_bot import TradingBot
    bot = TradingBot(token=settings.TELEGRAM_TOKEN)
    logger.info("Starting bot polling...")
    bot.run()
except Exception as e:
    logger.error(f"Fatal: {e}")
    sys.exit(1)
