import numpy as np
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def calculate_ema(prices: list[float], period: int = 14) -> list[float]:
    if len(prices) < period:
        return []
    multiplier = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema


def calculate_sma(prices: list[float], period: int = 14) -> list[float]:
    if len(prices) < period:
        return []
    sma = []
    for i in range(len(prices) - period + 1):
        sma.append(sum(prices[i : i + period]) / period)
    return sma


def calculate_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        return 100.0
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def calculate_macd(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict:
    if len(prices) < slow + signal:
        return {"macd": None, "signal": None, "histogram": None, "crossover": "none"}
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    if not ema_fast or not ema_slow:
        return {"macd": None, "signal": None, "histogram": None, "crossover": "none"}
    min_len = min(len(ema_fast), len(ema_slow))
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(min_len)]
    signal_line = calculate_ema(macd_line, signal)
    if not signal_line:
        return {"macd": None, "signal": None, "histogram": None, "crossover": "none"}
    histogram = [macd_line[-(len(signal_line)) + i] - signal_line[i] for i in range(len(signal_line))]
    macd_val = macd_line[-1] if macd_line else None
    signal_val = signal_line[-1] if signal_line else None
    hist_val = histogram[-1] if histogram else None
    crossover = "none"
    if len(macd_line) >= 2 and len(signal_line) >= 2:
        if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
            crossover = "bullish"
        elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
            crossover = "bearish"
    return {
        "macd": round(macd_val, 2) if macd_val else None,
        "signal": round(signal_val, 2) if signal_val else None,
        "histogram": round(hist_val, 2) if hist_val else None,
        "crossover": crossover,
    }


def calculate_atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> Optional[float]:
    if len(highs) < period + 1:
        return None
    tr_values = []
    for i in range(1, len(highs)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr_values.append(max(hl, hc, lc))
    if len(tr_values) < period:
        return None
    atr = sum(tr_values[:period]) / period
    for val in tr_values[period:]:
        atr = (atr * (period - 1) + val) / period
    return round(atr, 2)


def calculate_bollinger_bands(
    prices: list[float], period: int = 20, std_dev: float = 2
) -> dict:
    if len(prices) < period:
        return {"upper": None, "middle": None, "lower": None, "bandwidth": None}
    sma = calculate_sma(prices, period)
    if not sma:
        return {"upper": None, "middle": None, "lower": None, "bandwidth": None}
    middle = sma[-1]
    variance = sum((p - middle) ** 2 for p in prices[-period:]) / period
    std = variance ** 0.5
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    bandwidth = ((upper - lower) / middle * 100) if middle != 0 else 0
    position = "middle"
    current = prices[-1]
    if current >= upper:
        position = "above_upper"
    elif current <= lower:
        position = "below_lower"
    elif current > middle:
        position = "above_middle"
    else:
        position = "below_middle"
    return {
        "upper": round(upper, 2),
        "middle": round(middle, 2),
        "lower": round(lower, 2),
        "bandwidth": round(bandwidth, 2),
        "position": position,
    }


def calculate_volume_profile(
    prices: list[float], volumes: list[float], zones: int = 10
) -> dict:
    if not prices or not volumes or len(prices) != len(volumes):
        return {"poc": None, "high_volume_nodes": [], "low_volume_nodes": []}
    price_min, price_max = min(prices), max(prices)
    if price_max == price_min:
        return {"poc": price_min, "high_volume_nodes": [], "low_volume_nodes": []}
    zone_size = (price_max - price_min) / zones
    zones_data = {}
    for price, vol in zip(prices, volumes):
        zone_idx = min(int((price - price_min) / zone_size), zones - 1)
        zone_low = price_min + zone_idx * zone_size
        zone_high = zone_low + zone_size
        zone_label = f"{zone_low:.2f}-{zone_high:.2f}"
        if zone_label not in zones_data:
            zones_data[zone_label] = {"volume": 0, "count": 0, "mid": (zone_low + zone_high) / 2}
        zones_data[zone_label]["volume"] += vol
        zones_data[zone_label]["count"] += 1
    if not zones_data:
        return {"poc": None, "high_volume_nodes": [], "low_volume_nodes": []}
    sorted_zones = sorted(zones_data.items(), key=lambda x: x[1]["volume"], reverse=True)
    avg_volume = sum(z["volume"] for _, z in sorted_zones) / len(sorted_zones)
    poc_zone = sorted_zones[0]
    high_vol = [{"price": z["mid"], "volume": z["volume"]} for _, z in sorted_zones if z["volume"] > avg_volume * 1.2]
    low_vol = [{"price": z["mid"], "volume": z["volume"]} for _, z in sorted_zones if z["volume"] < avg_volume * 0.5]
    return {
        "poc": round(poc_zone[1]["mid"], 2),
        "high_volume_nodes": high_vol,
        "low_volume_nodes": low_vol,
    }


class TechnicalAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze_trend(self, prices: list[float]) -> str:
        if len(prices) < 50:
            return "ranging"
        ema_20 = calculate_ema(prices, 20)
        ema_50 = calculate_ema(prices, 50)
        if not ema_20 or not ema_50:
            return "ranging"
        if len(ema_20) < 2 or len(ema_50) < 2:
            return "ranging"
        price_above_20 = prices[-1] > ema_20[-1]
        price_above_50 = prices[-1] > ema_50[-1]
        ema_20_above_50 = ema_20[-1] > ema_50[-1]
        recent_highs = prices[-20:]
        recent_lows = prices[-20:]
        higher_highs = all(recent_highs[i] >= recent_highs[i - 1] for i in range(1, len(recent_highs))) if len(recent_highs) > 1 else False
        higher_lows = all(recent_lows[i] >= recent_lows[i - 1] for i in range(1, len(recent_lows))) if len(recent_lows) > 1 else False
        lower_highs = all(recent_highs[i] <= recent_highs[i - 1] for i in range(1, len(recent_highs))) if len(recent_highs) > 1 else False
        lower_lows = all(recent_lows[i] <= recent_lows[i - 1] for i in range(1, len(recent_lows))) if len(recent_lows) > 1 else False
        if price_above_20 and price_above_50 and ema_20_above_50:
            if higher_highs and higher_lows:
                return "strong_bullish"
            return "bullish"
        elif not price_above_20 and not price_above_50 and not ema_20_above_50:
            if lower_highs and lower_lows:
                return "strong_bearish"
            return "bearish"
        else:
            return "ranging"

    def find_support_resistance(
        self, highs: list[float], lows: list[float], lookback: int = 50
    ) -> dict:
        if len(highs) < lookback or len(lows) < lookback:
            return {"support": min(lows) if lows else None, "resistance": max(highs) if highs else None}
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        resistance = max(recent_highs)
        support = min(recent_lows)
        pivot_highs = []
        pivot_lows = []
        for i in range(2, len(recent_highs) - 2):
            if recent_highs[i] > recent_highs[i - 1] and recent_highs[i] > recent_highs[i - 2] and \
               recent_highs[i] > recent_highs[i + 1] and recent_highs[i] > recent_highs[i + 2]:
                pivot_highs.append(recent_highs[i])
            if recent_lows[i] < recent_lows[i - 1] and recent_lows[i] < recent_lows[i - 2] and \
               recent_lows[i] < recent_lows[i + 1] and recent_lows[i] < recent_lows[i + 2]:
                pivot_lows.append(recent_lows[i])
        key_resistance = max(pivot_highs) if pivot_highs else resistance
        key_support = min(pivot_lows) if pivot_lows else support
        return {
            "support": round(key_support, 2),
            "resistance": round(key_resistance, 2),
            "all_pivot_highs": [round(p, 2) for p in pivot_highs[-5:]],
            "all_pivot_lows": [round(p, 2) for p in pivot_lows[-5:]],
        }

    def get_rsi_signal(self, rsi: Optional[float]) -> str:
        if rsi is None:
            return "neutral"
        if rsi > 70:
            return "overbought"
        elif rsi < 30:
            return "oversold"
        elif rsi > 60:
            return "bullish"
        elif rsi < 40:
            return "bearish"
        return "neutral"

    def full_technical_analysis(self, ohlcv: dict) -> dict:
        prices = ohlcv.get("close", [])
        highs = ohlcv.get("high", [])
        lows = ohlcv.get("low", [])
        volumes = ohlcv.get("volume", [])
        if not prices:
            return {"error": "No price data"}
        rsi = calculate_rsi(prices)
        macd = calculate_macd(prices)
        atr = calculate_atr(highs, lows, prices)
        bb = calculate_bollinger_bands(prices)
        trend = self.analyze_trend(prices)
        sr = self.find_support_resistance(highs, lows)
        vp = calculate_volume_profile(prices, volumes) if volumes else {"poc": None, "high_volume_nodes": [], "low_volume_nodes": []}
        return {
            "current_price": prices[-1] if prices else None,
            "rsi": rsi,
            "rsi_signal": self.get_rsi_signal(rsi),
            "macd": macd,
            "atr": atr,
            "bollinger_bands": bb,
            "trend": trend,
            "support_resistance": sr,
            "volume_profile": vp,
            "ema_20": calculate_ema(prices, 20)[-1] if calculate_ema(prices, 20) else None,
            "ema_50": calculate_ema(prices, 50)[-1] if calculate_ema(prices, 50) else None,
            "ema_200": calculate_ema(prices, 200)[-1] if calculate_ema(prices, 200) else None,
            "price_above_ema_20": prices[-1] > calculate_ema(prices, 20)[-1] if calculate_ema(prices, 20) else None,
            "price_above_ema_50": prices[-1] > calculate_ema(prices, 50)[-1] if calculate_ema(prices, 50) else None,
            "price_above_ema_200": prices[-1] > calculate_ema(prices, 200)[-1] if calculate_ema(prices, 200) else None,
        }
