import sys
sys.path.insert(0, "C:\\Users\\Windows 10\\Downloads\\ai_trading_bot")

print("=" * 50)
print("GOLD AI TRADER - Import Verification")
print("=" * 50)

modules = {
    "Config": "from config import settings",
    "Database": "from database.db import get_or_create_user_settings, save_trade",
    "Models/Trade": "from database.models import Trade, UserSettings",
    "Technical Analysis": "from analysis.technical import TechnicalAnalyzer",
    "Smart Money": "from analysis.smart_money import SmartMoneyAnalyzer",
    "Fundamental": "from analysis.fundamentals import FundamentalAnalyzer",
    "Risk Manager": "from analysis.risk_manager import MicroRiskManager",
    "Market Analyzer": "from analysis.market_analyzer import MarketAnalyzer",
    "Session Detector": "from analysis.session_detector import SessionDetector",
    "Spread Monitor": "from analysis.spread_monitor import SpreadMonitor",
    "Price Fetcher": "from data.price_fetcher import RealPriceFetcher",
    "MT5 Provider": "from data.mt5_provider import get_mt5",
    "Market Data": "from data.market_data import MarketDataProvider",
    "News Collector": "from data.news_collector import NewsCollector",
    "Econ Calendar": "from data.economic_calendar import EconomicCalendar",
    "AI Model": "from models.ai_model import AIModel",
    "Confidence": "from models.confidence import ProConfidenceScorer",
    "Signal Generator": "from models.signal_generator import SignalGenerator",
    "Scalping Signal": "from models.scalping_signal import ScalpingProSignal",
    "Telegram Bot": "from bot.telegram_bot import TradingBot",
    "Keyboards": "from bot.keyboards import main_menu_keyboard, timeframe_keyboard, settings_keyboard",
    "Messages": "from bot.messages import WELCOME_MESSAGE, format_current_price",
    "Image Analyzer": "from bot.image_analyzer import ImageAnalyzer",
    "Helpers": "from utils.helpers import safe_float, format_number",
    "Dashboard": "from dashboard.control_panel import app",
}

ok, fail = 0, 0
for name, imp in modules.items():
    try:
        exec(imp)
        print(f"  ✅ {name:25s}")
        ok += 1
    except Exception as e:
        print(f"  ❌ {name:25s} - {str(e)[:60]}")
        fail += 1

print(f"\n{'='*50}")
print(f"RESULT: {ok} OK, {fail} FAILED out of {len(modules)}")
print(f"{'='*50}")

if ok == len(modules):
    print("\nChecking config...")
    print(f"  Capital: ${settings.DEFAULT_CAPITAL}")
    print(f"  Risk: {settings.DEFAULT_RISK_PERCENT}%")
    print(f"  Min Confidence: {settings.DEFAULT_MIN_CONFIDENCE}%")
    print(f"  Trading Type: {settings.DEFAULT_TRADING_TYPE}")
    print(f"  Small Capital Mode: {settings.SMALL_CAPITAL_MODE}")
    print(f"  Quick Scalp Min: {settings.QUICK_SCALP_MIN_CONFIDENCE}%")
    print(f"  Max Spread Scalp: {settings.MAX_SPREAD_SCALP}")
    print(f"  Min RR: {settings.MIN_ENTRY_RISK_REWARD}")

    print("\nTesting RiskManager...")
    rm = MicroRiskManager(12345)
    print(f"  Capital: ${rm.capital}")
    print(f"  Risk%: {rm.risk_percent}%")
    print(f"  Small Capital: {rm.is_small_capital}")
    pos = rm.calculate_scalp_position(2345.0, 2330.0)
    print(f"  Position: lot={pos['lot']}, risk=${pos['risk_amount']}, can_afford={pos['can_afford']}")
    print(f"  Warnings: {pos['warnings']}")

    print("\nTesting SessionDetector...")
    sd = SessionDetector()
    s = sd.get_current_session()
    print(f"  Session: {s.get('session_name')}")
    print(f"  Major: {s.get('is_major')}")
    print(f"  Quality: {s.get('quality')}")
    print(f"  Time remaining: {s.get('time_remaining_minutes')}m")

    print("\nTesting SpreadMonitor...")
    sm = SpreadMonitor()
    ss = sm.get_spread_status()
    print(f"  Spread: {ss.get('spread')}")
    print(f"  Status: {ss.get('status')}")
    print(f"  Tradeable: {ss.get('spread', 999) <= 30}")

    print("\nTesting ImageAnalyzer...")
    ia = ImageAnalyzer()
    img_result = ia.analyze_chart_image("simulated")
    print(f"  Direction: {img_result.get('direction')}")
    print(f"  Entry zone: {img_result.get('entry_zone_found')}")
    live_data = {"gold": 2345.0, "dxy": 100.5, "vix": 16.0}
    comp = ia.compare_with_live_data(img_result, live_data)
    print(f"  Match: {comp.get('match_percentage')}%")
    print(f"  Recommendation: {comp.get('recommendation')}")

    print("\n✅ ALL SYSTEMS OPERATIONAL")
else:
    print(f"\n❌ {fail} MODULES FAILED TO IMPORT")