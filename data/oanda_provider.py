import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class OandaProvider:
    """
    OANDA v20 REST API provider for real-time XAUUSD prices.
    Requires OANDA_API_KEY and optional OANDA_ACCOUNT_ID in config.
    Falls back gracefully if not configured.
    """
    BASE_URL = "https://api-fxpractice.oanda.com/v3"
    STREAM_URL = "https://stream-fxpractice.oanda.com/v3"

    def __init__(self, api_key: str = "", account_id: str = ""):
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.account_id = account_id
        self._enabled = bool(api_key)

    def is_enabled(self) -> bool:
        return self._enabled

    async def get_price(self, instrument: str = "XAU_USD") -> Optional[dict]:
        if not self._enabled:
            return None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/accounts/{self.account_id}/pricing",
                    params={"instruments": instrument},
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    prices = data.get("prices", [])
                    if prices:
                        p = prices[0]
                        bid = float(p.get("bids", [{}])[0].get("price", 0))
                        ask = float(p.get("asks", [{}])[0].get("price", 0))
                        mid = (bid + ask) / 2
                        return {"bid": bid, "ask": ask, "price": mid, "source": "oanda", "time": p.get("time", "")}
                elif resp.status_code == 401:
                    self.logger.warning("OANDA API: Invalid or expired API key")
                    self._enabled = False
                else:
                    self.logger.warning(f"OANDA API: HTTP {resp.status_code}")
        except Exception as e:
            self.logger.warning(f"OANDA API error: {e}")
        return None

    async def get_candles(self, instrument: str = "XAU_USD", count: int = 100,
                          granularity: str = "M5") -> Optional[list]:
        if not self._enabled:
            return None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/accounts/{self.account_id}/instruments/{instrument}/candles",
                    params={"count": count, "granularity": granularity, "price": "MBA"},
                    headers=headers,
                )
                if resp.status_code == 200:
                    return resp.json().get("candles", [])
        except Exception as e:
            self.logger.warning(f"OANDA candles error: {e}")
        return None
