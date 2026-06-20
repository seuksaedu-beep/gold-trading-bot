import pytest
import random
from analysis.backtester import WalkForwardBacktester


def _uid():
    return random.randint(1000, 99999)


@pytest.mark.asyncio
async def test_backtester_initializes():
    bt = WalkForwardBacktester(user_id=_uid())
    assert bt is not None
    assert bt.risk is not None


@pytest.mark.asyncio
async def test_backtest_1h_defaults():
    bt = WalkForwardBacktester(user_id=_uid())
    result = await bt.run_backtest(capital=50.0, timeframe="1H", days=30, min_confidence=85)
    assert "total_trades" in result
    assert "timeframe" in result
    assert result["total_trades"] >= 0


@pytest.mark.asyncio
async def test_backtest_5m():
    bt = WalkForwardBacktester(user_id=_uid())
    result = await bt.run_backtest(capital=100.0, timeframe="5m", days=7, min_confidence=80)
    assert result is not None
    if result.get("total_trades", 0) > 0:
        assert "win_rate" in result
        assert result["avg_confidence"] > 0
        assert result["max_drawdown"] >= 0


@pytest.mark.asyncio
async def test_backtest_big_capital():
    bt = WalkForwardBacktester(user_id=_uid())
    result = await bt.run_backtest(capital=10000.0, timeframe="1H", days=30, min_confidence=70)
    assert result is not None


@pytest.mark.asyncio
async def test_backtest_full_multi_tf():
    bt = WalkForwardBacktester(user_id=_uid())
    full = await bt.run_full_backtest(capital=50.0, days=14, min_confidence=85)
    assert "results" in full
    assert "best_timeframe" in full
    assert len(full["results"]) >= 5


@pytest.mark.asyncio
async def test_format_backtest_summary():
    bt = WalkForwardBacktester(user_id=_uid())
    result = await bt.run_backtest(capital=50.0, timeframe="1H", days=7, min_confidence=85)
    text = bt.format_backtest_summary(result)
    assert isinstance(text, str)
    assert len(text) > 50
