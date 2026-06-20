import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_TOKEN: str = ""
    ALLOWED_USER_IDS: list[int] = [0]

    DATABASE_URL: str = "sqlite:///./trading_bot.db"
    DEFAULT_CAPITAL: float = 50.0
    DEFAULT_RISK_PERCENT: float = 0.5
    DEFAULT_MIN_CONFIDENCE: float = 85.0
    DEFAULT_MAX_LEVERAGE: int = 10
    DEFAULT_MAX_TRADES_PER_DAY: int = 3
    DEFAULT_TRADING_TYPE: str = "scalping"
    MAX_CONSECUTIVE_LOSSES: int = 2

    SMALL_CAPITAL_MODE: bool = True
    SMALL_CAPITAL_THRESHOLD: float = 200.0
    MICRO_LOT: float = 0.01
    MAX_RISK_PER_TRADE_SMALL: float = 1.0
    MAX_SPREAD_SCALP: int = 30
    QUICK_SCALP_MIN_CONFIDENCE: float = 90.0
    REGULAR_SCALP_MIN_CONFIDENCE: float = 85.0
    MIN_ENTRY_RISK_REWARD: float = 1.5

    ALPHA_VANTAGE_KEY: str = ""
    NEWS_API_KEY: str = ""
    FRED_API_KEY: str = ""
    OANDA_API_KEY: str = ""
    OANDA_ACCOUNT_ID: str = ""
    OANDA_INSTRUMENT: str = "XAU_USD"

    ANALYSIS_INTERVAL_MINUTES: int = 15
    ENABLE_AUTO_ANALYSIS: bool = True
    SYMBOL: str = "XAUUSD"
    LOG_LEVEL: str = "INFO"

    MT5_ENABLED: bool = True
    MT5_SYMBOL: str = "XAUUSD"
    MT5_TIMEOUT_SECONDS: int = 30

    WEBHOOK_URL: str = ""
    WEBHOOK_PORT: int = 8080

    @field_validator("ALLOWED_USER_IDS", mode="before")
    @classmethod
    def parse_user_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip().lstrip("-").isdigit()]
        if isinstance(v, int):
            return [v]
        if isinstance(v, list):
            return v
        return [0]

    @field_validator("WEBHOOK_PORT", mode="before")
    @classmethod
    def parse_port(cls, v):
        if isinstance(v, str):
            return int(v)
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
