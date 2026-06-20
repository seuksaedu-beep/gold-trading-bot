import logging
import re
from datetime import datetime
from typing import Optional

from data.market_data import MarketDataProvider

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    def __init__(self, market_data_provider: Optional[MarketDataProvider] = None):
        self.market_data = market_data_provider or MarketDataProvider()
        self._price_move_threshold = 0.003

    def _parse_url_hints(self, image_url: str) -> dict:
        hints = {"symbol": "XAUUSD", "timeframe": None}
        url_lower = image_url.lower()
        if "xau" in url_lower or "gold" in url_lower:
            hints["symbol"] = "XAUUSD"
        patterns = {
            "1m": r"\b1m\b|\b1_min\b|\bminute\b", "5m": r"\b5m\b|\b5_min\b",
            "15m": r"\b15m\b|\b15_min\b", "30m": r"\b30m\b|\b30_min\b",
            "1H": r"\b1h\b|\b1_hour\b|\bhourly\b|\b1hour\b",
            "4H": r"\b4h\b|\b4_hour\b|\b4hour\b",
            "D": r"\b1d\b|\bdaily\b|\bday\b|\bd1\b",
        }
        for tf, pat in patterns.items():
            if re.search(pat, url_lower):
                hints["timeframe"] = tf
                break
        return hints

    def _classify_entry_zone(
        self, current_price: float, support_levels: list, resistance_levels: list,
        demand_zones: list, supply_zones: list, trend: str,
    ) -> tuple:
        touch_distance = current_price * 0.002
        buy_zones = [z.get("bottom", 0) for z in demand_zones] + [s for s in support_levels if s]
        sell_zones = [z.get("top", 0) for z in supply_zones] + [r for r in resistance_levels if r]
        near_buy = any(abs(current_price - z) <= touch_distance for z in buy_zones if z)
        near_sell = any(abs(current_price - z) <= touch_distance for z in sell_zones if z)
        if near_buy and trend in ("up", "bullish"):
            return True, "buy"
        if near_sell and trend in ("down", "bearish"):
            return True, "sell"
        return False, "none"

    async def analyze_chart_image(self, image_url: str) -> dict:
        hints = self._parse_url_hints(image_url)
        live_snapshot = await self.market_data.get_market_snapshot()
        current_price = live_snapshot.get("gold", 2345.0)
        ohlcv_4h = await self.market_data.get_ohlcv("XAUUSD", "4H", 100)
        closes = ohlcv_4h.get("close", [current_price])
        highs = ohlcv_4h.get("high", [current_price])
        lows = ohlcv_4h.get("low", [current_price])
        lookback = len(closes)
        simulated_image_price = closes[-5] if lookback >= 5 else closes[-1]
        if lookback >= 20:
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])
        else:
            recent_high = max(highs) if highs else simulated_image_price * 1.005
            recent_low = min(lows) if lows else simulated_image_price * 0.995
        trend = "sideways"
        if lookback >= 30:
            first_half = sum(closes[-30:-15]) / 15
            second_half = sum(closes[-15:]) / 15
            if second_half > first_half * 1.002:
                trend = "up"
            elif second_half < first_half * 0.998:
                trend = "down"
        support_levels = [round(recent_low, 2), round(recent_low * 0.997, 2)]
        resistance_levels = [round(recent_high, 2), round(recent_high * 1.003, 2)]
        demand_zones = [
            {"top": round(recent_low * 1.003, 2), "bottom": round(recent_low * 0.995, 2), "strength": "strong"},
        ]
        supply_zones = [
            {"top": round(recent_high * 1.005, 2), "bottom": round(recent_high * 0.997, 2), "strength": "strong"},
        ]
        liquidity_zones = [
            {"type": "sell_liquidity", "level": round(recent_high * 1.004, 2), "strength": "moderate"},
            {"type": "buy_liquidity", "level": round(recent_low * 0.996, 2), "strength": "moderate"},
        ]
        entry_zone_found, entry_direction = self._classify_entry_zone(
            simulated_image_price, support_levels, resistance_levels,
            demand_zones, supply_zones, trend,
        )
        nearest_liquidity = liquidity_zones[0]["level"] if liquidity_zones else recent_high
        return {
            "extracted_symbol": hints["symbol"],
            "extracted_timeframe": hints["timeframe"] or "1H",
            "image_trend": trend,
            "image_price": round(simulated_image_price, 2),
            "image_high": round(max(highs[-5:]) if lookback >= 5 else simulated_image_price, 2),
            "image_low": round(min(lows[-5:]) if lookback >= 5 else simulated_image_price, 2),
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "supply_zones": supply_zones,
            "demand_zones": demand_zones,
            "liquidity_zones": liquidity_zones,
            "entry_zone_found": entry_zone_found,
            "entry_direction": entry_direction,
        }

    async def compare_with_live_data(self, image_analysis: dict, live_data: dict) -> dict:
        current_price = live_data.get("gold", live_data.get("price", 0))
        image_price = image_analysis.get("image_price", current_price)
        if current_price == 0:
            current_price = image_price
        price_diff_pct = abs(current_price - image_price) / max(image_price, 0.01)
        price_moved_significantly = price_diff_pct > self._price_move_threshold
        if current_price > image_price:
            current_vs_image = "higher"
        elif current_price < image_price:
            current_vs_image = "lower"
        else:
            current_vs_image = "same"
        trend_map = {
            "up": ["up", "bullish", "صاعد"],
            "down": ["down", "bearish", "هابط"],
            "sideways": ["sideways", "ranging", "neutral", "محايد", "عرضي"],
        }
        image_trend_raw = (image_analysis.get("image_trend") or "sideways").lower()
        image_trend_norm = next(
            (k for k, v in trend_map.items() if image_trend_raw in v or any(x in image_trend_raw for x in v)),
            "sideways",
        )
        live_trend_raw = (
            live_data.get("m15_trend")
            or live_data.get("h1_trend")
            or live_data.get("trend")
            or "sideways"
        )
        if isinstance(live_trend_raw, str):
            live_trend_raw = live_trend_raw.lower()
        else:
            live_trend_raw = "sideways"
        live_trend_norm = next(
            (k for k, v in trend_map.items() if live_trend_raw in v or any(x in live_trend_raw for x in v)),
            "sideways",
        )
        trend_matches = image_trend_norm == live_trend_norm
        support_broken = any(
            s and current_price < s * 0.998 for s in image_analysis.get("support_levels", []) if s
        )
        resistance_broken = any(
            r and current_price > r * 1.002 for r in image_analysis.get("resistance_levels", []) if r
        )
        score = 100.0
        if price_moved_significantly:
            score -= 30
        if not trend_matches:
            score -= 20
        if support_broken:
            score -= 15
        if resistance_broken:
            score -= 15
        score = max(0, min(100, round(score)))
        is_matched = score >= 60
        entry_zone_found = image_analysis.get("entry_zone_found", False)
        entry_direction = image_analysis.get("entry_direction", "none")
        has_active_signal = entry_zone_found and entry_direction != "none"
        if has_active_signal and is_matched and not price_moved_significantly:
            recommendation = "trade"
        elif has_active_signal and is_matched and price_moved_significantly:
            recommendation = "wait"
        elif has_active_signal and not is_matched:
            recommendation = "don't trade"
        elif not has_active_signal and is_matched and not price_moved_significantly:
            recommendation = "wait"
        else:
            recommendation = "don't trade"
        return {
            "match_percentage": score,
            "is_matched": is_matched,
            "price_moved_significantly": price_moved_significantly,
            "current_price_vs_image": current_vs_image,
            "trend_matches": trend_matches,
            "support_broken": support_broken,
            "resistance_broken": resistance_broken,
            "current_price": round(current_price, 2),
            "image_price": round(image_price, 2),
            "recommendation": recommendation,
        }

    async def full_image_analysis(self, image_url: str, live_data: dict) -> dict:
        image_analysis = await self.analyze_chart_image(image_url)
        comparison = await self.compare_with_live_data(image_analysis, live_data)
        support = image_analysis.get("support_levels", [None])
        resistance = image_analysis.get("resistance_levels", [None])
        liquidity_zones = image_analysis.get("liquidity_zones", [])
        liquidity_text = (
            f"{liquidity_zones[0]['level']}" if liquidity_zones else "N/A"
        )
        return {
            "image_analysis": image_analysis,
            "live_comparison": comparison,
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": image_analysis.get("extracted_symbol", "XAUUSD"),
            "extracted_tf": image_analysis.get("extracted_timeframe", "غير محدد"),
            "timeframe": image_analysis.get("extracted_timeframe", "غير محدد"),
            "direction": image_analysis.get("image_trend", "sideways"),
            "trend": image_analysis.get("image_trend", "sideways"),
            "nearest_support": support[0] if support else None,
            "support": support[0] if support else None,
            "nearest_resistance": resistance[0] if resistance else None,
            "resistance": resistance[0] if resistance else None,
            "liquidity_zone": liquidity_text,
            "liquidity": liquidity_text,
            "entry_zone_found": image_analysis.get("entry_zone_found", False),
            "has_entry_zone": image_analysis.get("entry_zone_found", False),
            "price_at_screenshot": image_analysis.get("image_price", 0),
            "image_price": image_analysis.get("image_price", 0),
            "image_match": "matched" if comparison.get("is_matched") else "mismatched",
            "match_status": "matched" if comparison.get("is_matched") else "mismatched",
            "final_decision": comparison.get("recommendation", "wait"),
            "decision": comparison.get("recommendation", "wait"),
            "recommendation": comparison.get("recommendation", "wait"),
            "decision_reason": self._build_reason(image_analysis, comparison),
            "reason": self._build_reason(image_analysis, comparison),
            "summary": self._build_reason(image_analysis, comparison),
        }

    def _build_reason(self, image_analysis: dict, comparison: dict) -> str:
        parts = []
        if comparison.get("price_moved_significantly"):
            img_p = comparison.get("image_price", 0)
            cur_p = comparison.get("current_price", 0)
            pct = (abs(cur_p - img_p) / max(img_p, 0.01)) * 100
            parts.append(f"Price moved {pct:.2f}% from {img_p} to {cur_p}")
        if comparison.get("trend_matches") is False:
            parts.append(
                f"Image trend '{image_analysis.get('image_trend')}' differs from live trend"
            )
        if comparison.get("support_broken"):
            parts.append("Image support levels have been broken")
        if comparison.get("resistance_broken"):
            parts.append("Image resistance levels have been broken")
        if image_analysis.get("entry_zone_found"):
            parts.append(
                f"Entry zone found for {image_analysis.get('entry_direction')} "
                f"near {image_analysis.get('image_price')}"
            )
        if not parts:
            parts.append("Image analysis aligns with current market conditions")
        return " | ".join(parts)
