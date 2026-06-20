import pytest
from data.market_data import MarketDataProvider


@pytest.mark.asyncio
async def test_market_data_fallback_chain():
    """Without MT5 or OANDA, falls back to API/simulated data."""
    provider = MarketDataProvider()
    price = await provider.get_gold_price()
    assert isinstance(price, float)
    assert 1800 <= price <= 3500


@pytest.mark.asyncio
async def test_market_snapshot_default():
    provider = MarketDataProvider()
    snap = await provider.get_market_snapshot()
    assert "gold" in snap
    assert "dxy" in snap
    assert "vix" in snap
    assert snap["gold"] is not None
    assert isinstance(snap["data_source"], str)


@pytest.mark.asyncio
async def test_get_ohlcv_generates_valid():
    provider = MarketDataProvider()
    ohlcv = await provider.get_ohlcv("XAUUSD", "1H", 50)
    assert len(ohlcv["close"]) == 50
    assert len(ohlcv["high"]) == 50
    assert len(ohlcv["low"]) == 50
    assert len(ohlcv["volume"]) == 50
