import pytest
from data.oanda_provider import OandaProvider


@pytest.mark.asyncio
async def test_oanda_disabled_by_default():
    provider = OandaProvider()
    assert provider.is_enabled() is False
    result = await provider.get_price()
    assert result is None


@pytest.mark.asyncio
async def test_oanda_enabled_with_key():
    provider = OandaProvider(api_key="fake_key", account_id="123")
    assert provider.is_enabled() is True


@pytest.mark.asyncio
async def test_oanda_get_price_bad_key():
    provider = OandaProvider(api_key="invalid_key_xxx", account_id="123")
    assert provider.is_enabled() is True
    result = await provider.get_price()
    assert result is None
