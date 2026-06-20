import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SmartMoneyAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def find_order_blocks(
        self, highs: list[float], lows: list[float], closes: list[float], lookback: int = 100
    ) -> dict:
        if len(highs) < lookback or len(lows) < lookback:
            return {"bullish_blocks": [], "bearish_blocks": []}
        highs_ = highs[-lookback:]
        lows_ = lows[-lookback:]
        closes_ = closes[-lookback:]
        bullish_blocks = []
        bearish_blocks = []
        for i in range(2, len(highs_) - 2):
            if highs_[i] > highs_[i + 1] and highs_[i] > highs_[i + 2] and \
               lows_[i] > lows_[i + 1] and lows_[i] > lows_[i + 2]:
                bearish_blocks.append({
                    "type": "bearish",
                    "high": round(highs_[i], 2),
                    "low": round(lows_[i], 2),
                    "strength": "strong" if closes_[i] < highs_[i] - (highs_[i] - lows_[i]) * 0.3 else "moderate",
                })
            if lows_[i] < lows_[i + 1] and lows_[i] < lows_[i + 2] and \
               highs_[i] < highs_[i + 1] and highs_[i] < highs_[i + 2]:
                bullish_blocks.append({
                    "type": "bullish",
                    "high": round(highs_[i], 2),
                    "low": round(lows_[i], 2),
                    "strength": "strong" if closes_[i] > lows_[i] + (highs_[i] - lows_[i]) * 0.7 else "moderate",
                })
        return {
            "bullish_blocks": bullish_blocks[-5:],
            "bearish_blocks": bearish_blocks[-5:],
        }

    def find_fair_value_gaps(
        self, highs: list[float], lows: list[float], lookback: int = 100
    ) -> list[dict]:
        if len(highs) < 3:
            return []
        highs_ = highs[-lookback:]
        lows_ = lows[-lookback:]
        fvgs = []
        for i in range(2, len(highs_)):
            prev_high, prev_low = highs_[i - 2], lows_[i - 2]
            curr_high, curr_low = highs_[i - 1], lows_[i - 1]
            next_open = highs_[i]
            if curr_low > prev_high:
                gap_top = curr_low
                gap_bottom = prev_high
                if next_open < gap_top:
                    fvgs.append({
                        "type": "bullish",
                        "top": round(gap_top, 2),
                        "bottom": round(gap_bottom, 2),
                        "size": round(gap_top - gap_bottom, 2),
                        "status": "unfilled",
                    })
            if curr_high < prev_low:
                gap_top = prev_low
                gap_bottom = curr_high
                if next_open > gap_bottom:
                    fvgs.append({
                        "type": "bearish",
                        "top": round(gap_top, 2),
                        "bottom": round(gap_bottom, 2),
                        "size": round(gap_top - gap_bottom, 2),
                        "status": "unfilled",
                    })
        return fvgs[-5:]

    def detect_liquidity_sweeps(
        self, highs: list[float], lows: list[float], lookback: int = 50
    ) -> list[dict]:
        if len(highs) < lookback:
            return []
        highs_ = highs[-lookback:]
        lows_ = lows[-lookback:]
        sweeps = []
        for i in range(5, len(highs_) - 1):
            recent_highs = highs_[i - 5:i]
            if highs_[i] > max(recent_highs) and highs_[i + 1] < highs_[i]:
                sweeps.append({
                    "type": "sell_liquidity_sweep",
                    "level": round(highs_[i], 2),
                    "strength": "strong" if (highs_[i] - highs_[i + 1]) > (max(recent_highs) - min(recent_highs)) * 0.5 else "moderate",
                })
            recent_lows = lows_[i - 5:i]
            if lows_[i] < min(recent_lows) and lows_[i + 1] > lows_[i]:
                sweeps.append({
                    "type": "buy_liquidity_sweep",
                    "level": round(lows_[i], 2),
                    "strength": "strong" if (lows_[i + 1] - lows_[i]) > (max(recent_lows) - min(recent_lows)) * 0.5 else "moderate",
                })
        return sweeps[-5:]

    def detect_bos_choch(
        self, highs: list[float], lows: list[float], lookback: int = 60
    ) -> dict:
        if len(highs) < lookback:
            return {"bos": "none", "choch": "none"}
        highs_ = highs[-lookback:]
        lows_ = lows[-lookback:]
        trend = "ranging"
        bos = "none"
        choch = "none"
        mid = len(highs_) // 2
        first_half_high = max(highs_[:mid])
        first_half_low = min(lows_[:mid])
        second_half_high = max(highs_[mid:])
        second_half_low = min(lows_[mid:])
        if second_half_high > first_half_high and second_half_low > first_half_low:
            trend = "bullish"
        elif second_half_high < first_half_high and second_half_low < first_half_low:
            trend = "bearish"
        if trend == "bullish":
            low_idx = lows_.index(min(lows_[-20:])) if lows_[-20:] else -1
            if low_idx > 0 and low_idx < len(highs_) - 1:
                if max(highs_[low_idx:]) > highs_[low_idx]:
                    bos = "bullish_bos"
            last_high = max(highs_[-10:]) if len(highs_) >= 10 else max(highs_)
            if lows_[-1] < lows_[-3] and highs_[-1] > highs_[-3]:
                choch = "bullish_choch"
        elif trend == "bearish":
            high_idx = highs_.index(max(highs_[-20:])) if highs_[-20:] else -1
            if high_idx > 0 and high_idx < len(lows_) - 1:
                if min(lows_[high_idx:]) < lows_[high_idx]:
                    bos = "bearish_bos"
            last_low = min(lows_[-10:]) if len(lows_) >= 10 else min(lows_)
            if highs_[-1] > highs_[-3] and lows_[-1] < lows_[-3]:
                choch = "bearish_choch"
        return {"bos": bos, "choch": choch, "trend": trend}

    def find_demand_supply_zones(
        self, highs: list[float], lows: list[float], lookback: int = 100
    ) -> dict:
        if len(highs) < lookback:
            return {"demand_zones": [], "supply_zones": []}
        highs_ = highs[-lookback:]
        lows_ = lows[-lookback:]
        demand_zones = []
        supply_zones = []
        for i in range(3, len(highs_) - 3):
            if lows_[i] < lows_[i - 1] and lows_[i] < lows_[i - 2] and lows_[i] < lows_[i - 3]:
                if highs_[i + 1] > highs_[i] and highs_[i + 2] > highs_[i]:
                    zone_base = lows_[i]
                    zone_top = min(highs_[i], highs_[i + 1])
                    demand_zones.append({
                        "top": round(zone_top, 2),
                        "bottom": round(zone_base, 2),
                        "strength": "strong",
                    })
            if highs_[i] > highs_[i - 1] and highs_[i] > highs_[i - 2] and highs_[i] > highs_[i - 3]:
                if lows_[i + 1] < lows_[i] and lows_[i + 2] < lows_[i]:
                    zone_base = highs_[i]
                    zone_bottom = max(highs_[i + 1], lows_[i])
                    supply_zones.append({
                        "top": round(zone_base, 2),
                        "bottom": round(zone_bottom, 2),
                        "strength": "strong",
                    })
        return {
            "demand_zones": demand_zones[-3:],
            "supply_zones": supply_zones[-3:],
        }

    def full_smc_analysis(self, ohlcv: dict) -> dict:
        highs = ohlcv.get("high", [])
        lows = ohlcv.get("low", [])
        closes = ohlcv.get("close", [])
        if not highs or not lows or not closes:
            return {"error": "No price data"}
        order_blocks = self.find_order_blocks(highs, lows, closes)
        fvgs = self.find_fair_value_gaps(highs, lows)
        liquidity_sweeps = self.detect_liquidity_sweeps(highs, lows)
        bos_choch = self.detect_bos_choch(highs, lows)
        demand_supply = self.find_demand_supply_zones(highs, lows)
        current_price = closes[-1] if closes else 0
        nearest_demand = None
        nearest_supply = None
        if demand_supply["demand_zones"]:
            for zone in sorted(demand_supply["demand_zones"], key=lambda z: z["bottom"], reverse=True):
                if zone["bottom"] < current_price:
                    nearest_demand = zone
                    break
            if not nearest_demand and demand_supply["demand_zones"]:
                nearest_demand = max(demand_supply["demand_zones"], key=lambda z: z["bottom"])
        if demand_supply["supply_zones"]:
            for zone in sorted(demand_supply["supply_zones"], key=lambda z: z["top"]):
                if zone["top"] > current_price:
                    nearest_supply = zone
                    break
            if not nearest_supply and demand_supply["supply_zones"]:
                nearest_supply = min(demand_supply["supply_zones"], key=lambda z: z["top"])
        return {
            "order_blocks": order_blocks,
            "fair_value_gaps": fvgs,
            "liquidity_sweeps": liquidity_sweeps,
            "bos_choch": bos_choch,
            "demand_supply_zones": demand_supply,
            "nearest_demand": nearest_demand,
            "nearest_supply": nearest_supply,
            "current_price": current_price,
        }
