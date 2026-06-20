import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import Optional

from data.market_data import MarketDataProvider

logger = logging.getLogger(__name__)

XAUUSD_SPREAD_THRESHOLDS = {
    "low": 15,
    "normal": 30,
    "high": 50,
}

SESSION_TIMES = {
    "sydney": (22, 6),
    "tokyo": (0, 8),
    "london": (7, 15),
    "new_york": (12, 20),
}

OPTIMAL_WINDOWS = [
    {"start": 8, "end": 11, "label": "London-NY overlap (best)"},
    {"start": 13, "end": 16, "label": "NY afternoon"},
    {"start": 1, "end": 4, "label": "Tokyo session"},
]

LOW_SPREAD_HOURS = [8, 9, 10, 11, 12, 13, 14, 15]
HIGH_SPREAD_HOURS = [0, 1, 2, 3, 20, 21, 22, 23]
SPIKE_MULTIPLIER = 2.5


class SpreadMonitor:
    def __init__(self):
        self._provider = MarketDataProvider()
        self._spread_history: list[float] = []
        self._last_spread: Optional[float] = None
        self._session_spreads: list[float] = []
        self._spike_warnings: list[str] = []
        self._spread_baseline: Optional[float] = None

    def _get_mt5_spread(self) -> Optional[float]:
        try:
            from data.mt5_provider import get_mt5

            mt5 = get_mt5()
            tick = mt5.get_live_price("XAUUSD")
            if tick and tick.get("spread") is not None:
                return float(tick["spread"])
        except Exception:
            logger.warning("MT5 spread fetch failed", exc_info=True)
        return None

    def _estimate_spread_from_price(self, price: float) -> float:
        import random

        if price <= 0:
            price = 2345.0
        noise = random.gauss(0, 2)
        base = max(5, price * 0.0001 * 10000)
        return round(base + noise, 1)

    def get_spread(self) -> float:
        mt5_spread = self._get_mt5_spread()
        if mt5_spread is not None:
            spread = mt5_spread
        else:
            try:
                price = self._provider._last_prices.get("XAUUSD", 2345.0)
            except Exception:
                price = 2345.0
            spread = self._estimate_spread_from_price(price)

        spread = max(0.1, round(spread, 1))
        self._last_spread = spread
        self._spread_history.append(spread)
        if spread >= 1:
            self._session_spreads.append(spread)
        self._check_spike(spread)
        return spread

    def _check_spike(self, spread: float) -> None:
        if len(self._session_spreads) < 10:
            return
        recent = self._session_spreads[-10:]
        avg = statistics.mean(recent)
        if self._spread_baseline is None:
            self._spread_baseline = avg
            return
        if avg > 0 and spread > avg * SPIKE_MULTIPLIER:
            msg = (
                f"Spread spike detected: {spread} "
                f"(avg: {avg:.1f}, threshold: {avg * SPIKE_MULTIPLIER:.1f})"
            )
            logger.warning(msg)
            self._spike_warnings.append(msg)

    def _classify(self, spread: float) -> str:
        if spread < XAUUSD_SPREAD_THRESHOLDS["low"]:
            return "low"
        if spread < XAUUSD_SPREAD_THRESHOLDS["normal"]:
            return "normal"
        if spread < XAUUSD_SPREAD_THRESHOLDS["high"]:
            return "high"
        return "extreme"

    def _get_recommendation(self, status: str) -> str:
        recommendations = {
            "low": "Ideal conditions. Proceed with scalping or any trade.",
            "normal": "Normal conditions. Standard execution expected.",
            "high": "Elevated spread. Avoid scalping. Use limit orders with wider stops.",
            "extreme": "Extreme spread. Do NOT trade. Wait for normalization.",
        }
        return recommendations.get(status, "Unknown")

    def get_spread_status(self) -> dict:
        spread = self.get_spread()
        status = self._classify(spread)
        avg = self.get_average_spread()
        baselines = {"low": 8, "normal": 22, "high": 38, "extreme": 60}
        baseline = baselines.get(status, 30)
        return {
            "spread": spread,
            "status": status,
            "recommendation": self._get_recommendation(status),
            "average_session_spread": avg,
            "baseline": baseline,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "data_source": "mt5" if self._get_mt5_spread() is not None else "estimated",
            "spike_warnings": self._spike_warnings[-3:],
        }

    def is_spread_tradeable(self, max_spread: int = 30) -> bool:
        spread = self.get_spread()
        return spread <= max_spread

    def get_average_spread(self) -> float:
        if not self._session_spreads:
            return 0.0
        return round(statistics.mean(self._session_spreads), 1)

    def get_optimal_spread_times(self) -> list:
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        results = []

        for window in OPTIMAL_WINDOWS:
            start, end = window["start"], window["end"]
            if start <= current_hour < end:
                results.append({
                    **window,
                    "status": "now",
                    "description": f"Currently in {window['label']}",
                })
            elif current_hour < start:
                hours_away = start - current_hour
                results.append({
                    **window,
                    "status": "upcoming",
                    "description": f"Starts in ~{hours_away}h ({window['label']})",
                })
            else:
                hours_away = 24 - current_hour + start
                results.append({
                    **window,
                    "status": "next_day",
                    "description": f"Starts in ~{hours_away}h ({window['label']})",
                })

        now_utc = datetime.now(timezone.utc)
        day_name = now_utc.strftime("%A")

        news_avoid = [
            "Avoid: FOMC / NFP / CPI / Central bank decisions",
            "Avoid: 30 min before and after major news",
            day_name in ("Friday", "Saturday", "Sunday"),
        ]
        if any(news_avoid[i] for i in (0, 1)):
            results.insert(0, {
                "start": None,
                "end": None,
                "label": "⚠ High-impact news window",
                "status": "caution",
                "description": f"Avoid trading 30min before/after major events. Today: {day_name}",
            })
        elif news_avoid[2] and day_name in ("Saturday", "Sunday"):
            results.insert(0, {
                "start": None,
                "end": None,
                "label": "Weekend — no liquidity",
                "status": "closed",
                "description": "XAUUSD spread widens significantly. No trading recommended.",
            })

        results.sort(key=lambda x: {"now": 0, "upcoming": 1, "next_day": 2, "caution": 3, "closed": 4}.get(x["status"], 5))
        return results

    def reset_session(self) -> None:
        self._session_spreads.clear()
        self._spike_warnings.clear()
        self._spread_baseline = None
        logger.info("Spread session data reset")
