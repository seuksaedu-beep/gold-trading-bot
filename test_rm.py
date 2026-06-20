import sys
sys.path.insert(0, "C:\\Users\\Windows 10\\Downloads\\ai_trading_bot")
from database.db import get_or_create_user_settings
from analysis.risk_manager import MicroRiskManager

s = get_or_create_user_settings(12345)
print("UserSettings:")
print(f"  Capital: ${s.capital}")
print(f"  Risk: {s.risk_percent}%")
print(f"  Confidence: {s.min_confidence}%")
print(f"  Type: {s.trading_type}")

rm = MicroRiskManager(12345)
print(f"\nRiskManager:")
print(f"  Capital: ${rm.capital}")
print(f"  Small Capital: {rm.is_small_capital}")
print(f"  Risk%: {rm.risk_percent}%")
print(f"  Max Daily: {rm.max_daily}")

pos = rm.calculate_scalp_position(2345.0, 2330.0)
print(f"\nPosition for BUY at 2345, SL at 2330:")
print(f"  Lot: {pos['lot']}")
print(f"  Risk Amount: ${pos['risk_amount']}")
print(f"  Risk%: {pos['risk_percent']}%")
print(f"  Can Afford: {pos['can_afford']}")
print(f"  Stop Pips: {pos['stop_pips']}")
print(f"  Leverage: {pos['implied_leverage']}:1")
print(f"  Warnings: {pos['warnings']}")
print(f"  Recommendation: {pos['recommendation']}")

print(f"\nCan Trade: {rm.can_trade()}")

filters = rm.get_scalp_filters()
print(f"\nScalp Filters: {filters}")
