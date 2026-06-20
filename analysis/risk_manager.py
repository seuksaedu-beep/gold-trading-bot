import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import settings
from database.db import get_or_create_user_settings, update_user_settings, get_trades_count_today

logger = logging.getLogger(__name__)

SMALL_CAPITAL_THRESHOLD = 200.0
MAX_CONSECUTIVE_LOSSES = 2
MAX_DAILY_TRADES_SMALL = 3
MAX_RISK_PERCENT_SMALL = 1.0
DEFAULT_RISK_PERCENT = 0.5
MIN_STOP_PIPS = 5
MAX_STOP_PIPS_SMALL = 25
MIN_RISK_REWARD = 1.5
MICRO_LOT = 0.01
LOT_STEP = 0.01
PIP_VALUE_USD = 0.10

LOT_TABLE = {
    50: {"max_lot": 0.02, "max_leverage": 10, "label": "micro"},
    100: {"max_lot": 0.03, "max_leverage": 15, "label": "micro"},
    200: {"max_lot": 0.05, "max_leverage": 20, "label": "nano"},
    500: {"max_lot": 0.10, "max_leverage": 30, "label": "mini"},
    1000: {"max_lot": 0.20, "max_leverage": 50, "label": "mini"},
}


class MicroRiskManager:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.settings = get_or_create_user_settings(user_id)
        self.capital = self.settings.capital or settings.DEFAULT_CAPITAL
        self.risk_percent = min(self.settings.risk_percent or DEFAULT_RISK_PERCENT, MAX_RISK_PERCENT_SMALL)
        self.is_small_capital = self.capital < SMALL_CAPITAL_THRESHOLD
        self.max_daily = min(self.settings.max_trades_per_day or MAX_DAILY_TRADES_SMALL, MAX_DAILY_TRADES_SMALL)

    def get_lot_limits(self) -> dict:
        caps = sorted(LOT_TABLE.keys())
        selected = LOT_TABLE[caps[0]]
        for cap in caps:
            if self.capital <= cap:
                selected = LOT_TABLE[cap]
                break
            selected = LOT_TABLE[cap]
        return selected

    def can_trade(self) -> tuple:
        if self.settings.is_paused:
            return False, "البوت متوقف مؤقتاً", "pause"
        if not self.settings.is_active:
            return False, "البوت غير نشط", "inactive"
        if self.capital < 10:
            return False, f"رأس المال (${self.capital:.2f}) غير كافٍ. الحد الأدنى $10", "low_capital"
        if self.settings.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
            return False, f"تم الوصول للحد الأقصى من الخسائر المتتالية ({MAX_CONSECUTIVE_LOSSES}). توقف حتى الغد", "max_losses"
        today = get_trades_count_today()
        if today >= self.max_daily:
            return False, f"الحد الأقصى اليومي ({self.max_daily} صفقات) تم الوصول إليه", "max_daily"
        return True, "OK", "ok"

    def calculate_scalp_position(self, entry: float, stop_loss: float) -> dict:
        stop_pips = abs(entry - stop_loss)
        lot_limits = self.get_lot_limits()
        max_lot = lot_limits["max_lot"]
        risk_amount = self.capital * (self.risk_percent / 100.0)
        max_risk_one_pct = self.capital * (MAX_RISK_PERCENT_SMALL / 100.0)
        risk_amount = min(risk_amount, max_risk_one_pct, self.capital * 0.02)
        warnings = []
        if stop_pips <= 0:
            return {"lot": MICRO_LOT, "risk_amount": 0.0, "risk_percent": 0.0, "capital": self.capital, "warnings": ["مسافة الوقف غير صالحة"], "recommendation": "لا يمكن حساب اللوت"}
        pip_value = PIP_VALUE_USD
        raw_lot = risk_amount / (stop_pips * pip_value) if stop_pips > 0 else MICRO_LOT
        lot = max(MICRO_LOT, min(raw_lot, max_lot))
        lot = round(lot / LOT_STEP) * LOT_STEP
        actual_risk = lot * stop_pips * pip_value
        risk_pct = (actual_risk / self.capital * 100) if self.capital > 0 else 0
        can_afford = risk_pct <= MAX_RISK_PERCENT_SMALL
        if not can_afford:
            warnings.append(f"⚠️ المخاطرة (${actual_risk:.2f}) تتجاوز 1% من رأس المال (${max_risk_one_pct:.2f})")
        if self.is_small_capital:
            if lot > 0.03:
                warnings.append(f"⚠️ لوت كبير ({lot}) لحساب ${self.capital}. استخدم 0.01-0.02")
            if stop_pips > MAX_STOP_PIPS_SMALL:
                old_sl = stop_loss
                max_pips = MAX_STOP_PIPS_SMALL
                if entry > 0:
                    if stop_loss < entry:
                        stop_loss = entry - max_pips
                    else:
                        stop_loss = entry + max_pips
                stop_pips = abs(entry - stop_loss)
                warnings.append(f"⚠️ تم تقليص الوقف من {old_sl:.2f} إلى {stop_loss:.2f} ({MAX_STOP_PIPS_SMALL} نقطة حد أقصى)")
        implied_leverage = (lot * 100000) / self.capital if self.capital > 0 else 0
        max_lever = lot_limits["max_leverage"]
        if implied_leverage > max_lever:
            warnings.append(f"⚠️ رافعة عالية ({implied_leverage:.1f}:1). الحد الأقصى {max_lever}:1")
        return {
            "lot": lot,
            "risk_amount": round(actual_risk, 2),
            "risk_percent": round(risk_pct, 2),
            "capital": self.capital,
            "can_afford": can_afford,
            "stop_pips": round(stop_pips, 1),
            "implied_leverage": round(implied_leverage, 1),
            "max_leverage": max_lever,
            "max_lot": max_lot,
            "warnings": warnings,
            "recommendation": self._get_recommendation(),
            "is_small_capital": self.is_small_capital,
        }

    def _get_recommendation(self) -> str:
        if self.capital <= 50:
            return "✅ استخدم 0.01 لوت فقط. رافعة 1:10 كحد أقصى. اهدف لربح $0.5-$1 لكل صفقة. وقف 10-20 نقطة"
        elif self.capital <= 100:
            return "✅ استخدم 0.01-0.02 لوت. رافعة 1:15. اهدف لربح $1-$2"
        elif self.capital <= 200:
            return "✅ استخدم 0.02-0.05 لوت. رافعة 1:20"
        elif self.capital <= 500:
            return "✅ استخدم 0.05-0.10 لوت. رافعة 1:30"
        return "✅ استخدم 0.10-0.20 لوت. رافعة 1:50"

    def validate_trade(self, entry: float, stop_loss: float, confidence: float, is_quick_scalp: bool = False) -> dict:
        errors = []
        if self.is_small_capital and confidence < 85:
            errors.append(f"نسبة الثقة ({confidence}%) أقل من الحد الأدنى لحماية رأس المال (85%)")
        if is_quick_scalp and confidence < 90:
            errors.append(f"نسبة الثقة للـ Quick Scalp ({confidence}%) أقل من 90%")
        stop_pips = abs(entry - stop_loss)
        if stop_pips <= 0:
            errors.append("مسافة الوقف غير صالحة")
        if self.is_small_capital and stop_pips > MAX_STOP_PIPS_SMALL:
            errors.append(f"وقف الخسارة ({stop_pips:.0f} نقطة) بعيد جداً. الحد الأقصى {MAX_STOP_PIPS_SMALL} نقطة لحساب صغير")
        can, reason, _ = self.can_trade()
        if not can:
            errors.append(reason)
        pos = self.calculate_scalp_position(entry, stop_loss)
        if not pos.get("can_afford", True):
            errors.append(f"رأس المال لا يتحمل هذه المخاطرة (${pos['risk_amount']:.2f})")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "position": pos,
        }

    def record_result(self, result: str):
        if result == "loss":
            self.settings.consecutive_losses += 1
        elif result == "win":
            self.settings.consecutive_losses = 0
        update_user_settings(self.user_id, consecutive_losses=self.settings.consecutive_losses)

    def get_scalp_filters(self) -> dict:
        return {
            "min_confidence": 90 if self.is_small_capital else 85,
            "max_spread": settings.MAX_SPREAD_SCALP,
            "min_rr": MIN_RISK_REWARD,
            "max_stop_pips": MAX_STOP_PIPS_SMALL if self.is_small_capital else 40,
            "max_daily_trades": self.max_daily,
            "capital": self.capital,
            "is_small_capital": self.is_small_capital,
        }

    def get_small_capital_report(self) -> str:
        today = get_trades_count_today()
        daily_left = max(0, self.max_daily - today)
        pos = self.calculate_scalp_position(2345.0, 2330.0)
        return (
            f"💰 رأس المال: ${self.capital:.2f}\n"
            f"🛡️ وضع حماية رأس المال: {'مفعل' if self.is_small_capital else 'غير مفعل'}\n"
            f"⚠️ المخاطرة القصوى: {MAX_RISK_PERCENT_SMALL}%\n"
            f"📊 أقصى لوت: {pos['max_lot']}\n"
            f"🔒 أقصى رافعة: 1:{pos['max_leverage']}\n"
            f"📋 صفقات اليوم: {today}/{self.max_daily}\n"
            f"✅ متبقي: {daily_left} صفقة\n"
            f"❌ خسائر متتالية: {self.settings.consecutive_losses}/{MAX_CONSECUTIVE_LOSSES}"
        )
