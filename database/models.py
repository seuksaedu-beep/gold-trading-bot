from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Text, Boolean, JSON, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), default="XAUUSD")
    trade_type = Column(String(20))  # buy / sell
    trading_style = Column(String(20))  # scalping / intraday / swing
    timeframe = Column(String(10))
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float, nullable=True)
    take_profit_2 = Column(Float, nullable=True)
    take_profit_3 = Column(Float, nullable=True)
    confidence = Column(Float)
    risk_level = Column(String(30))
    leverage = Column(String(20))
    capital_at_risk = Column(Float, default=0.0)
    lot_size = Column(Float, default=0.0)
    status = Column(String(20), default="pending")  # pending / open / closed / cancelled
    result = Column(String(20), nullable=True)  # win / loss / breakeven
    pnl = Column(Float, nullable=True)
    entry_reason = Column(Text)
    news_analysis = Column(Text)
    dollar_analysis = Column(Text)
    bonds_analysis = Column(Text)
    liquidity_analysis = Column(Text)
    whales_analysis = Column(Text)
    ai_decision = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    opened_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True)
    is_active = Column(Boolean, default=True)
    capital = Column(Float, default=50.0)
    risk_percent = Column(Float, default=0.5)
    min_confidence = Column(Float, default=85.0)
    max_leverage = Column(Integer, default=10)
    trading_type = Column(String(20), default="scalping")
    max_trades_per_day = Column(Integer, default=3)
    consecutive_losses = Column(Integer, default=0)
    is_paused = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketAnalysis(Base):
    __tablename__ = "market_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), default="XAUUSD")
    gold_price = Column(Float)
    dxy_price = Column(Float)
    vix_price = Column(Float)
    oil_price = Column(Float)
    us_bond_yield = Column(Float)
    sp500_price = Column(Float)
    trend = Column(String(20))  # bullish / bearish / ranging
    volatility = Column(String(20))
    sentiment = Column(String(30))
    ai_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)
    total_pnl = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float, nullable=True)
    avg_confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db(db_url: str = "sqlite:///./trading_bot.db"):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal
