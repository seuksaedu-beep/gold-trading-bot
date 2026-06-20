import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from database.db import (
    get_or_create_user_settings,
    update_user_settings,
    get_trades,
    get_trade_by_id,
    get_trade_stats,
    get_latest_market_analysis,
    get_backtest_results,
)
from models.signal_generator import SignalGenerator
from analysis.market_analyzer import MarketAnalyzer

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Trading Assistant - Dashboard", version="1.0.0")
market_analyzer = MarketAnalyzer()


class SettingsUpdate(BaseModel):
    capital: Optional[float] = None
    risk_percent: Optional[float] = None
    min_confidence: Optional[float] = None
    max_leverage: Optional[int] = None
    trading_type: Optional[str] = None
    max_trades_per_day: Optional[int] = None
    is_active: Optional[bool] = None
    is_paused: Optional[bool] = None


class BacktestRequest(BaseModel):
    start_date: str
    end_date: str
    initial_capital: float = 10000.0
    risk_percent: float = 1.5


@app.get("/")
async def root():
    return {"status": "online", "service": "AI Trading Assistant", "symbol": "XAUUSD"}


@app.get("/api/v1/status")
async def get_status():
    analysis = market_analyzer.get_last_analysis()
    return {
        "status": "running",
        "last_analysis": analysis.get("timestamp") if analysis else None,
        "last_gold_price": analysis.get("gold_price") if analysis else None,
        "market_trend": analysis.get("trend") if analysis else None,
    }


@app.get("/api/v1/settings/{user_id}")
async def get_settings(user_id: int):
    settings = get_or_create_user_settings(user_id)
    return {
        "user_id": settings.user_id,
        "is_active": settings.is_active,
        "is_paused": settings.is_paused,
        "capital": settings.capital,
        "risk_percent": settings.risk_percent,
        "min_confidence": settings.min_confidence,
        "max_leverage": settings.max_leverage,
        "trading_type": settings.trading_type,
        "max_trades_per_day": settings.max_trades_per_day,
        "consecutive_losses": settings.consecutive_losses,
    }


@app.put("/api/v1/settings/{user_id}")
async def update_settings(user_id: int, data: SettingsUpdate):
    kwargs = {k: v for k, v in data.dict(exclude_none=True).items()}
    if kwargs:
        update_user_settings(user_id, **kwargs)
    settings = get_or_create_user_settings(user_id)
    return {"status": "updated", "settings": settings}


@app.get("/api/v1/analysis")
async def get_analysis():
    analysis = market_analyzer.get_last_analysis()
    if not analysis:
        analysis = await market_analyzer.analyze_market_full()
    return analysis


@app.post("/api/v1/refresh-analysis")
async def refresh_analysis():
    analysis = await market_analyzer.analyze_market_full()
    return analysis


@app.get("/api/v1/signal/{user_id}")
async def get_signal(user_id: int):
    generator = SignalGenerator(user_id)
    result = await generator.generate_signal()
    return result


@app.get("/api/v1/trades")
async def list_trades(limit: int = 20):
    trades = get_trades(limit)
    return [
        {
            "id": t.id,
            "type": t.trade_type,
            "style": t.trading_style,
            "entry": t.entry_price,
            "sl": t.stop_loss,
            "tp1": t.take_profit_1,
            "status": t.status,
            "result": t.result,
            "pnl": t.pnl,
            "confidence": t.confidence,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in trades
    ]


@app.get("/api/v1/trades/{trade_id}")
async def get_trade(trade_id: int):
    trade = get_trade_by_id(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "type": trade.trade_type,
        "style": trade.trading_style,
        "entry": trade.entry_price,
        "sl": trade.stop_loss,
        "tp1": trade.take_profit_1,
        "tp2": trade.take_profit_2,
        "tp3": trade.take_profit_3,
        "confidence": trade.confidence,
        "risk_level": trade.risk_level,
        "status": trade.status,
        "result": trade.result,
        "pnl": trade.pnl,
        "entry_reason": trade.entry_reason,
        "news_analysis": trade.news_analysis,
        "dollar_analysis": trade.dollar_analysis,
        "bonds_analysis": trade.bonds_analysis,
        "liquidity_analysis": trade.liquidity_analysis,
        "whales_analysis": trade.whales_analysis,
        "ai_decision": trade.ai_decision,
        "created_at": trade.created_at.isoformat() if trade.created_at else None,
    }


@app.get("/api/v1/stats/{user_id}")
async def get_stats(user_id: int):
    return get_trade_stats(user_id)


@app.get("/api/v1/backtest/results")
async def list_backtests():
    results = get_backtest_results(10)
    return [
        {
            "id": r.id,
            "start": r.start_date.isoformat() if r.start_date else None,
            "end": r.end_date.isoformat() if r.end_date else None,
            "total_trades": r.total_trades,
            "win_rate": r.win_rate,
            "total_pnl": r.total_pnl,
            "max_drawdown": r.max_drawdown,
            "avg_confidence": r.avg_confidence,
        }
        for r in results
    ]


@app.post("/api/v1/backtest/run")
async def run_backtest(request: BacktestRequest):
    return {
        "status": "not_implemented",
        "message": "Backtesting will be available in a future update. Please use the Telegram bot interface.",
    }
