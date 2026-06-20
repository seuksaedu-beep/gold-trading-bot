import logging
import asyncio
from datetime import datetime
from typing import Optional

from config import settings
from data.market_data import MarketDataProvider
from data.news_collector import NewsCollector
from data.economic_calendar import EconomicCalendar
from analysis.technical import TechnicalAnalyzer
from analysis.smart_money import SmartMoneyAnalyzer
from analysis.fundamentals import FundamentalAnalyzer
from models.ai_model import AIModel
from models.confidence import ConfidenceScorer
from models.signal_generator import SignalGenerator
from database.db import save_market_analysis, get_latest_market_analysis

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    def __init__(self):
        self.market_data = MarketDataProvider()
        self.news_collector = NewsCollector()
        self.econ_calendar = EconomicCalendar()
        self.tech_analyzer = TechnicalAnalyzer()
        self.smc_analyzer = SmartMoneyAnalyzer()
        self.fund_analyzer = FundamentalAnalyzer()
        self.ai_model = AIModel()
        self.confidence_scorer = ConfidenceScorer()
        self._last_analysis = None
        self._is_running = False

    async def analyze_market_full(self) -> dict:
        try:
            snapshot = await self.market_data.get_market_snapshot()
            ohlcv_4h = await self.market_data.get_ohlcv("XAUUSD", "4H", 100)
            ohlcv_daily = await self.market_data.get_ohlcv("XAUUSD", "D", 50)
            ohlcv_1h = await self.market_data.get_ohlcv("XAUUSD", "1H", 100)
            news = await self.news_collector.get_latest_news(10)
            news_impact = await self.news_collector.analyze_news_impact(news)
            fed_news = await self.news_collector.get_fed_news()
            upcoming_events = await self.econ_calendar.get_upcoming_events(14)
            fund_analysis = self.fund_analyzer.full_fundamental_analysis(
                dxy=snapshot["dxy"], vix=snapshot["vix"], oil=snapshot["oil"],
                sp500=snapshot["sp500"], us10y=snapshot["us10y"], us2y=snapshot["us2y"],
            )
            smc_4h = self.smc_analyzer.full_smc_analysis(ohlcv_4h)
            smc_daily = self.smc_analyzer.full_smc_analysis(ohlcv_daily)
            tech_4h = self.tech_analyzer.full_technical_analysis(ohlcv_4h)
            tech_daily = self.tech_analyzer.full_technical_analysis(ohlcv_daily)
            tech_1h = self.tech_analyzer.full_technical_analysis(ohlcv_1h)
            signals_4h = self.ai_model.combine_technical_signals(
                tech_4h.get("rsi_signal", "neutral"),
                tech_4h.get("macd", {}).get("crossover", "none"),
                tech_4h.get("trend", "ranging"),
                tech_4h.get("bollinger_bands", {}).get("position", "middle"),
                smc_4h.get("bos_choch", {}),
                smc_4h.get("liquidity_sweeps", []),
            )
            signals_daily = self.ai_model.combine_technical_signals(
                tech_daily.get("rsi_signal", "neutral"),
                tech_daily.get("macd", {}).get("crossover", "none"),
                tech_daily.get("trend", "ranging"),
                tech_daily.get("bollinger_bands", {}).get("position", "middle"),
                smc_daily.get("bos_choch", {}),
                smc_daily.get("liquidity_sweeps", []),
            )
            confidence_4h = self.confidence_scorer.calculate_pro(tech_4h, fund_analysis, smc_4h, signals_4h).get("confidence", 0)
            confidence_daily = self.confidence_scorer.calculate_pro(tech_daily, fund_analysis, smc_daily, signals_daily).get("confidence", 0)
            market_quality = self.ai_model.evaluate_market_quality(
                tech_4h.get("trend", "ranging"),
                fund_analysis.get("vix", {}).get("level", "normal"),
                tech_4h.get("atr", 0) or 0,
                fund_analysis.get("dollar", {}).get("strength", "neutral"),
                fund_analysis.get("risk_factors", []),
            )
            timeframe_summary = {}
            for tf in ["1m", "5m", "15m", "30m", "1H", "4H", "D"]:
                ohlcv_tf = await self.market_data.get_ohlcv("XAUUSD", tf, 50)
                tech_tf = self.tech_analyzer.full_technical_analysis(ohlcv_tf)
                smc_tf = self.smc_analyzer.full_smc_analysis(ohlcv_tf)
                timeframe_summary[tf] = {
                    "trend": tech_tf.get("trend", "ranging"),
                    "rsi": tech_tf.get("rsi"),
                    "atr": tech_tf.get("atr"),
                    "bos": smc_tf.get("bos_choch", {}).get("bos", "none"),
                    "choch": smc_tf.get("bos_choch", {}).get("choch", "none"),
                }
            bias = "محايد"
            if signals_4h.get("direction") == signals_daily.get("direction"):
                bias = "صاعد بقوة" if signals_4h.get("direction") == "buy" else "هابط بقوة"
            elif signals_4h.get("direction") != "neutral" or signals_daily.get("direction") != "neutral":
                bias = "مائل للصعود" if signals_4h.get("direction") == "buy" or signals_daily.get("direction") == "buy" else "مائل للهبوط"
            analysis = {
                "gold_price": snapshot["gold"],
                "dxy_price": snapshot["dxy"],
                "vix_price": snapshot["vix"],
                "oil_price": snapshot["oil"],
                "sp500_price": snapshot["sp500"],
                "us_bond_yield": snapshot["us10y"],
                "trend": tech_4h.get("trend", "ranging"),
                "volatility": "مرتفع" if (tech_4h.get("atr", 0) or 0) > snapshot["gold"] * 0.01 else "منخفض",
                "sentiment": fund_analysis.get("vix", {}).get("market_state", "محايد"),
                "ai_summary": (
                    f"تحليل شامل للذهب: {bias} | "
                    f"الثقة (4H): {confidence_4h}% | "
                    f"جودة السوق: {market_quality['quality']} | "
                    f"الدولار: {fund_analysis['dollar']['signal']} | "
                    f"VIX: {fund_analysis['vix']['signal']}"
                ),
                "bias": bias,
                "confidence_4h": confidence_4h,
                "confidence_daily": confidence_daily,
                "timeframe_summary": timeframe_summary,
                "market_quality": market_quality,
                "signals_4h": signals_4h,
                "signals_daily": signals_daily,
                "fundamental": fund_analysis,
                "news_impact": news_impact,
                "upcoming_events": upcoming_events[:5],
                "sms_support": {
                    "bos_choch_4h": smc_4h.get("bos_choch", {}),
                    "demand_supply": smc_4h.get("demand_supply_zones", {}),
                    "liquidity_sweeps": smc_4h.get("liquidity_sweeps", [])[-3:],
                    "fvgs": smc_4h.get("fair_value_gaps", [])[-3:],
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
            save_market_analysis({
                "symbol": "XAUUSD",
                "gold_price": snapshot["gold"],
                "dxy_price": snapshot["dxy"],
                "vix_price": snapshot["vix"],
                "oil_price": snapshot["oil"],
                "sp500_price": snapshot["sp500"],
                "us_bond_yield": snapshot["us10y"],
                "trend": tech_4h.get("trend", "ranging"),
                "volatility": analysis["volatility"],
                "sentiment": analysis["sentiment"],
                "ai_summary": analysis["ai_summary"],
            })
            self._last_analysis = analysis
            return analysis
        except Exception as e:
            logger.error(f"Full market analysis error: {e}", exc_info=True)
            return {"error": str(e)}

    async def auto_analyze_loop(self):
        self._is_running = True
        while self._is_running:
            if settings.ENABLE_AUTO_ANALYSIS:
                await self.analyze_market_full()
                logger.info("Auto market analysis completed")
            await asyncio.sleep(settings.ANALYSIS_INTERVAL_MINUTES * 60)

    def stop(self):
        self._is_running = False

    def get_last_analysis(self) -> Optional[dict]:
        return self._last_analysis
