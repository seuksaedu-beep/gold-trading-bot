import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_number(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def calculate_lot_size(
    capital: float,
    risk_percent: float,
    stop_loss_pips: float,
    pip_value_per_lot: float = 10.0,
) -> float:
    if stop_loss_pips <= 0:
        return 0.01
    risk_amount = capital * (risk_percent / 100.0)
    lot_size = risk_amount / (stop_loss_pips * pip_value_per_lot)
    return round(max(0.01, min(lot_size, 100.0)), 2)


def calculate_pip_value(
    capital: float, lot_size: float, stop_loss_points: float
) -> float:
    if lot_size <= 0 or stop_loss_points <= 0:
        return 0.0
    return capital * (lot_size / 100000) * stop_loss_points


def is_trading_hours() -> bool:
    now = datetime.utcnow()
    market_open = now.replace(hour=0, minute=5, second=0)
    market_close = now.replace(hour=23, minute=55, second=0)
    if now.weekday() >= 5:
        return False
    return market_open <= now <= market_close


def calculate_risk_score(
    atr: float, current_price: float, stop_loss_distance: float
) -> str:
    if current_price <= 0:
        return "unknown"
    ratio = stop_loss_distance / current_price
    if ratio < 0.005:
        return "منخفض"
    elif ratio < 0.015:
        return "متوسط"
    elif ratio < 0.03:
        return "مرتفع"
    else:
        return "خطير جداً"


def get_trade_duration(trade_type: str) -> str:
    durations = {
        "scalping": "دقائق - ساعة",
        "intraday": "ساعات - يوم",
        "swing": "أيام - أسبوع",
    }
    return durations.get(trade_type, "غير محدد")


def get_recommended_leverage(risk_level: str, trade_type: str) -> str:
    if risk_level == "خطير جداً":
        return "غير موصى به"
    if trade_type == "scalping":
        return "1:5 إلى 1:10"
    elif trade_type == "intraday":
        return "1:3 إلى 1:5"
    else:
        return "1:2 إلى 1:3"


def serialize_datetime(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def create_backup_state(data: dict) -> str:
    try:
        return json.dumps(data, default=serialize_datetime, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to serialize state: {e}")
        return "{}"
