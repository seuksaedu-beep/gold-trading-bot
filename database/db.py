import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from database.models import (
    Trade,
    UserSettings,
    MarketAnalysis,
    BacktestResult,
    init_db,
)
from config import settings

logger = logging.getLogger(__name__)

engine, SessionLocal = init_db(settings.DATABASE_URL)


def get_session() -> Session:
    return SessionLocal()


def get_or_create_user_settings(user_id: int) -> UserSettings:
    with get_session() as session:
        user_settings = (
            session.query(UserSettings)
            .filter(UserSettings.user_id == user_id)
            .first()
        )
        if not user_settings:
            user_settings = UserSettings(
                user_id=user_id,
                capital=settings.DEFAULT_CAPITAL,
                risk_percent=settings.DEFAULT_RISK_PERCENT,
                min_confidence=settings.DEFAULT_MIN_CONFIDENCE,
                max_leverage=settings.DEFAULT_MAX_LEVERAGE,
                trading_type=settings.DEFAULT_TRADING_TYPE,
                max_trades_per_day=settings.DEFAULT_MAX_TRADES_PER_DAY,
            )
            session.add(user_settings)
            session.commit()
            session.refresh(user_settings)
        return user_settings


def update_user_settings(user_id: int, **kwargs) -> UserSettings:
    with get_session() as session:
        user_settings = (
            session.query(UserSettings)
            .filter(UserSettings.user_id == user_id)
            .first()
        )
        if not user_settings:
            user_settings = get_or_create_user_settings(user_id)
            session.add(user_settings)
        for key, value in kwargs.items():
            if hasattr(user_settings, key):
                setattr(user_settings, key, value)
        user_settings.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(user_settings)
        return user_settings


def save_trade(trade_data: dict) -> Trade:
    with get_session() as session:
        trade = Trade(**trade_data)
        session.add(trade)
        session.commit()
        session.refresh(trade)
        return trade


def get_trades(limit: int = 20, offset: int = 0):
    with get_session() as session:
        return (
            session.query(Trade)
            .order_by(Trade.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )


def get_trade_by_id(trade_id: int) -> Optional[Trade]:
    with get_session() as session:
        return session.query(Trade).filter(Trade.id == trade_id).first()


def get_trades_count_today() -> int:
    with get_session() as session:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            session.query(Trade)
            .filter(Trade.created_at >= today_start)
            .count()
        )


def get_recent_trades(days: int = 7):
    with get_session() as session:
        since = datetime.utcnow() - timedelta(days=days)
        return (
            session.query(Trade)
            .filter(Trade.created_at >= since)
            .order_by(Trade.created_at.desc())
            .all()
        )


def get_trade_stats(user_id: int) -> dict:
    with get_session() as session:
        trades = (
            session.query(Trade)
            .order_by(Trade.created_at.desc())
            .limit(100)
            .all()
        )
        total = len(trades)
        wins = sum(1 for t in trades if t.result == "win")
        losses = sum(1 for t in trades if t.result == "loss")
        pending = sum(1 for t in trades if t.status == "pending")
        win_rate = (wins / total * 100) if total > 0 else 0
        total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
        }


def save_market_analysis(data: dict) -> MarketAnalysis:
    with get_session() as session:
        analysis = MarketAnalysis(**data)
        session.add(analysis)
        session.commit()
        session.refresh(analysis)
        return analysis


def get_latest_market_analysis():
    with get_session() as session:
        return (
            session.query(MarketAnalysis)
            .order_by(MarketAnalysis.created_at.desc())
            .first()
        )


def save_backtest_result(data: dict) -> BacktestResult:
    with get_session() as session:
        result = BacktestResult(**data)
        session.add(result)
        session.commit()
        session.refresh(result)
        return result


def get_backtest_results(limit: int = 10):
    with get_session() as session:
        return (
            session.query(BacktestResult)
            .order_by(BacktestResult.created_at.desc())
            .limit(limit)
            .all()
        )
