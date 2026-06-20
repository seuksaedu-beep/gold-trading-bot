import logging
import random
import asyncio
from datetime import datetime
from typing import Optional

from data.price_fetcher import RealPriceFetcher
from data.mt5_provider import get_mt5
from data.oanda_provider import OandaProvider
from config import settings

logger = logging.getLogger(__name__)


class MarketDataProvider:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fetcher = RealPriceFetcher()
        self.oanda = OandaProvider(
            api_key=settings.OANDA_API_KEY,
            account_id=settings.OANDA_ACCOUNT_ID,
        )
        self._last_prices = {
            "XAUUSD": 2345.50, "DXY": 104.35, "VIX": 15.2,
            "USOIL": 78.45, "SP500": 4830.50, "US10Y": 4.48, "US2Y": 4.82,
        }
        self._data_source = "api"
        if self.oanda.is_enabled():
            self._data_source = "oanda"

    def _is_valid_gold(self, price: float) -> bool:
        return 1800 <= price <= 3500

    def _try_mt5_price(self, symbol: str) -> Optional[float]:
        try:
            mt5 = get_mt5()
            tick = mt5.get_live_price(symbol)
            if tick:
                price = tick["last"]
                if symbol == "XAUUSD" and self._is_valid_gold(price):
                    self._data_source = "mt5"
                    return price
                elif symbol != "XAUUSD":
                    self._data_source = "mt5"
                    return price
        except:
            pass
        return None

    async def _try_oanda_price(self) -> Optional[float]:
        if not self.oanda.is_enabled():
            return None
        try:
            price_data = await self.oanda.get_price(settings.OANDA_INSTRUMENT)
            if price_data and self._is_valid_gold(price_data["price"]):
                self._data_source = "oanda"
                return price_data["price"]
        except:
            pass
        return None

    def _generate_ohlcv(self, base_price: float, count: int = 100, volatility: float = 0.002) -> dict:
        prices, highs, lows, closes, volumes = [], [], [], [], []
        price = base_price
        for i in range(count):
            change = price * volatility * random.gauss(0, 1)
            new_price = price + change
            high = max(price, new_price) + abs(change) * random.random()
            low = min(price, new_price) - abs(change) * random.random()
            volume = random.randint(1000, 100000)
            prices.append(round(new_price, 2))
            highs.append(round(high, 2))
            lows.append(round(low, 2))
            closes.append(round(new_price, 2))
            volumes.append(volume)
            price = new_price
        return {"close": closes, "high": highs, "low": lows, "volume": volumes}

    async def get_gold_price(self) -> float:
        mt5_price = self._try_mt5_price("XAUUSD")
        if mt5_price:
            self._last_prices["XAUUSD"] = mt5_price
            return mt5_price
        oanda_price = await self._try_oanda_price()
        if oanda_price:
            self._last_prices["XAUUSD"] = oanda_price
            return oanda_price
        real = await self.fetcher.fetch_gold_price()
        self._last_prices["XAUUSD"] = real
        self._data_source = "api"
        return real

    async def get_dxy(self) -> float:
        mt5_price = self._try_mt5_price("DXY")
        if mt5_price:
            self._last_prices["DXY"] = mt5_price
            return mt5_price
        real = await self.fetcher.fetch_dxy()
        self._last_prices["DXY"] = real
        return real

    async def get_vix(self) -> float:
        real = await self.fetcher.fetch_vix()
        self._last_prices["VIX"] = real
        return real

    async def get_oil_price(self) -> float:
        real = await self.fetcher.fetch_oil()
        self._last_prices["USOIL"] = real
        return real

    async def get_sp500(self) -> float:
        real = await self.fetcher.fetch_sp500()
        self._last_prices["SP500"] = real
        return real

    async def get_us_bond_yield(self) -> float:
        real = await self.fetcher.fetch_bond_yield()
        self._last_prices["US10Y"] = real
        return real

    async def get_us_2y_yield(self) -> float:
        real = await self.fetcher.fetch_us_2y_yield()
        self._last_prices["US2Y"] = real
        return real

    def get_ohlcv_from_mt5(self, symbol: str = "XAUUSD", timeframe: str = "1H", count: int = 100) -> Optional[dict]:
        try:
            mt5 = get_mt5()
            if mt5.connect():
                rates = mt5.get_live_rates(symbol, timeframe, count)
                if rates:
                    return rates
        except:
            pass
        return None

    async def get_ohlcv(self, symbol: str = "XAUUSD", timeframe: str = "1H", count: int = 100) -> dict:
        mt5_data = self.get_ohlcv_from_mt5(symbol, timeframe, count)
        if mt5_data:
            close = mt5_data.get("close", [])
            high = mt5_data.get("high", [])
            low = mt5_data.get("low", [])
            volume = mt5_data.get("volume", [])
            if close and len(close) >= 30:
                if symbol == "XAUUSD" and not self._is_valid_gold(close[-1]):
                    real_price = self._last_prices.get("XAUUSD", 2345.0)
                    if not self._is_valid_gold(real_price):
                        real_price = await self.get_gold_price()
                    factor = real_price / close[-1]
                    close = [round(c * factor, 2) for c in close]
                    high = [round(h * factor, 2) for h in high]
                    low = [round(l * factor, 2) for l in low]
                return {"close": close, "high": high, "low": low, "volume": volume}
        base = self._last_prices.get(symbol, 2345.0)
        volatility_map = {
            "1m": 0.0005, "5m": 0.001, "15m": 0.0015,
            "30m": 0.002, "1H": 0.003, "4H": 0.005, "D": 0.008,
        }
        vol = volatility_map.get(timeframe, 0.002)
        return self._generate_ohlcv(base, count, vol)

    async def get_market_snapshot(self) -> dict:
        gold, dxy, vix, oil, sp500, us10y, us2y = await asyncio.gather(
            self.get_gold_price(), self.get_dxy(), self.get_vix(),
            self.get_oil_price(), self.get_sp500(), self.get_us_bond_yield(),
            self.get_us_2y_yield(), return_exceptions=True,
        )
        return {
            "gold": gold if isinstance(gold, float) else 2345.0,
            "dxy": dxy if isinstance(dxy, float) else 104.35,
            "vix": vix if isinstance(vix, float) else 15.2,
            "oil": oil if isinstance(oil, float) else 78.45,
            "sp500": sp500 if isinstance(sp500, float) else 4830.0,
            "us10y": us10y if isinstance(us10y, float) else 4.48,
            "us2y": us2y if isinstance(us2y, float) else 4.82,
            "timestamp": datetime.utcnow().isoformat(),
            "data_source": self._data_source,
        }

    async def get_all_timeframes(self, symbol: str = "XAUUSD") -> dict:
        result = {}
        mt5_data = None
        try:
            mt5 = get_mt5()
            if mt5.connect():
                mt5_data = mt5.get_live_data_all_timeframes(symbol)
        except:
            pass
        if mt5_data:
            for tf in ["1m", "5m", "15m", "30m", "1H", "4H", "D"]:
                if tf in mt5_data:
                    result[tf] = mt5_data[tf]
        for tf in ["1m", "5m", "15m", "30m", "1H", "4H", "D"]:
            if tf not in result:
                result[tf] = await self.get_ohlcv(symbol, tf, 100)
        return result
