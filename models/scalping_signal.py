import logging
from datetime import datetime
from typing import Optional

from config import settings
from analysis.technical import TechnicalAnalyzer
from analysis.smart_money import SmartMoneyAnalyzer
from analysis.fundamentals import FundamentalAnalyzer
from analysis.risk_manager import MicroRiskManager
from models.confidence import ProConfidenceScorer
from models.ai_model import AIModel
from data.market_data import MarketDataProvider
from data.price_fetcher import RealPriceFetcher
from data.news_collector import NewsCollector
from data.economic_calendar import EconomicCalendar
from database.db import save_trade

logger = logging.getLogger(__name__)


class ScalpingProSignal:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.tech = TechnicalAnalyzer()
        self.smc = SmartMoneyAnalyzer()
        self.fund = FundamentalAnalyzer()
        self.data = MarketDataProvider()
        self.fetcher = RealPriceFetcher()
        self.news = NewsCollector()
        self.econ = EconomicCalendar()
        self.ai = AIModel()
        self.scorer = ProConfidenceScorer()
        self.risk = MicroRiskManager(user_id)

    async def analyze_scalp_timeframe(self, timeframe: str = "1m") -> dict:
        try:
            ohlcv = await self.data.get_ohlcv("XAUUSD", timeframe, 100)
            if timeframe == "1m":
                ohlcv_htf = await self.data.get_ohlcv("XAUUSD", "5m", 100)
            elif timeframe == "5m":
                ohlcv_htf = await self.data.get_ohlcv("XAUUSD", "15m", 100)
            else:
                ohlcv_htf = await self.data.get_ohlcv("XAUUSD", "1H", 100)
            tech_result = self.tech.full_technical_analysis(ohlcv)
            tech_htf = self.tech.full_technical_analysis(ohlcv_htf)
            smc_result = self.smc.full_smc_analysis(ohlcv)
            signals = self.ai.combine_technical_signals(
                tech_result.get("rsi_signal", "neutral"),
                tech_result.get("macd", {}).get("crossover", "none"),
                tech_result.get("trend", "ranging"),
                tech_result.get("bollinger_bands", {}).get("position", "middle"),
                smc_result.get("bos_choch", {}),
                smc_result.get("liquidity_sweeps", []),
            )
            htf_direction = "neutral"
            signals_htf = self.ai.combine_technical_signals(
                tech_htf.get("rsi_signal", "neutral"),
                tech_htf.get("macd", {}).get("crossover", "none"),
                tech_htf.get("trend", "ranging"),
                tech_htf.get("bollinger_bands", {}).get("position", "middle"),
                smc_result.get("bos_choch", {}),
                [],
            )
            htf_direction = signals_htf.get("direction", "neutral")
            snapshot = await self.fetcher.fetch_all_snapshot()
            fund_analysis = self.fund.full_fundamental_analysis(
                dxy=snapshot["dxy"], vix=snapshot["vix"], oil=snapshot["oil"],
                sp500=snapshot["sp500"], us10y=snapshot["us10y"], us2y=snapshot["us2y"],
            )
            news_list = await self.news.get_latest_news(5)
            news_impact = await self.news.analyze_news_impact(news_list)
            tf_analysis = {
                timeframe: {"signal_direction": signals.get("direction", "neutral"), "trend": tech_result.get("trend", "ranging")},
                "htf": {"signal_direction": htf_direction, "trend": tech_htf.get("trend", "ranging")},
            }
            confidence_result = self.scorer.calculate_pro(
                technical=tech_result,
                fundamental=fund_analysis,
                smc=smc_result,
                signals=signals,
                timeframe_analysis=tf_analysis,
                capital=self.risk.settings.capital,
            )
            current_price = tech_result.get("current_price", snapshot["gold"])
            atr = tech_result.get("atr", current_price * 0.002) or (current_price * 0.002)
            direction = signals.get("direction", "neutral")
            result = {
                "timeframe": timeframe,
                "current_price": current_price,
                "direction": direction,
                "confidence": confidence_result,
                "technical": tech_result,
                "smc": smc_result,
                "signals": signals,
                "fundamental": fund_analysis,
                "news_impact": news_impact,
                "htf_trend": htf_direction,
                "htf_aligned": direction == htf_direction,
                "atr": atr,
                "trend": tech_result.get("trend", "ranging"),
                "timestamp": datetime.utcnow().isoformat(),
            }
            return result
        except Exception as e:
            logger.error(f"Scalp analysis error: {e}", exc_info=True)
            return {"error": str(e), "timeframe": timeframe, "direction": "neutral"}

    async def generate_scalp_signal(self, timeframe: str = "1m") -> dict:
        analysis = await self.analyze_scalp_timeframe(timeframe)
        if "error" in analysis:
            return {"no_trade": True, "reason": f"خطأ: {analysis['error']}"}
        confidence_data = analysis.get("confidence", {})
        current_price = analysis.get("current_price", 0)
        direction = analysis.get("direction", "neutral")
        htf_aligned = analysis.get("htf_aligned", False)
        confidence = confidence_data.get("confidence", 0)
        is_super = confidence_data.get("is_super_signal", False)
        is_strong = confidence_data.get("is_strong_signal", False)
        min_conf = max(85, self.risk.settings.min_confidence)
        if direction == "neutral":
            return {
                "no_trade": True,
                "reason": "لا توجد إشارة واضحة. السوق متعادل",
                "confidence": confidence,
                "analysis": analysis,
            }
        if not is_strong:
            return {
                "no_trade": True,
                "reason": f"نسبة الثقة ({confidence}%) أقل من المطلوب ({min_conf}%)",
                "confidence": confidence,
                "analysis": analysis,
                "direction": direction,
            }
        if not htf_aligned:
            return {
                "no_trade": True,
                "reason": "الفريم الأعلى لا يدعم اتجاه الفريم الحالي",
                "confidence": confidence,
                "analysis": analysis,
                "direction": direction,
            }
        can_trade, reason, _ = self.risk.can_trade()
        if not can_trade:
            return {"no_trade": True, "reason": reason, "analysis": analysis}
        atr = analysis.get("atr", current_price * 0.002)
        if direction == "buy":
            entry = round(current_price, 2)
            sl = round(current_price - atr * 1.5, 2)
            tp1 = round(current_price + atr * 1.5, 2)
            tp2 = round(current_price + atr * 2.5, 2)
            tp3 = round(current_price + atr * 4.0, 2)
        else:
            entry = round(current_price, 2)
            sl = round(current_price + atr * 1.5, 2)
            tp1 = round(current_price - atr * 1.5, 2)
            tp2 = round(current_price - atr * 2.5, 2)
            tp3 = round(current_price - atr * 4.0, 2)
        stop_points = abs(entry - sl)
        if stop_points > 30:
            sl = round(entry - atr * 1.0, 2) if direction == "buy" else round(entry + atr * 1.0, 2)
            stop_points = abs(entry - sl)
        position = self.risk.calculate_scalp_position(entry, sl)
        trade_data = {
            "symbol": "XAUUSD",
            "trade_type": direction,
            "trading_style": "scalping",
            "timeframe": timeframe,
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "take_profit_3": tp3,
            "confidence": confidence,
            "risk_level": "منخفض" if confidence >= 90 else "متوسط",
            "leverage": "1:5 إلى 1:10 (لوت 0.01)",
            "capital_at_risk": position.get("risk_amount", 0),
            "lot_size": position.get("lot", 0.01),
            "status": "pending",
            "entry_reason": self._build_reason(analysis, direction),
            "news_analysis": f"تأثير: {analysis.get('news_impact', {}).get('overall_impact', 'محايد')}",
            "dollar_analysis": analysis.get("fundamental", {}).get("dollar", {}).get("signal", "محايد"),
            "bonds_analysis": analysis.get("fundamental", {}).get("bonds", {}).get("gold_impact", "محايد"),
            "liquidity_analysis": f"سيولة: {len(analysis.get('smc', {}).get('liquidity_sweeps', []))} | مناطق: {len(analysis.get('smc', {}).get('demand_supply_zones', {}).get('demand_zones', []))}D/{len(analysis.get('smc', {}).get('demand_supply_zones', {}).get('supply_zones', []))}S",
            "whales_analysis": f"BOS: {analysis.get('smc', {}).get('bos_choch', {}).get('bos', 'none')} | CHOCH: {analysis.get('smc', {}).get('bos_choch', {}).get('choch', 'none')} | FVG: {len(analysis.get('smc', {}).get('fair_value_gaps', []))}",
            "ai_decision": self._build_ai_decision(analysis, confidence_data, direction),
        }
        saved = save_trade(trade_data)
        return {
            "no_trade": False,
            "trade_id": saved.id,
            "trade": {
                **trade_data,
                "trading_style_name": "سكالبينج",
                "expected_duration": "دقائق - 30 دقيقة",
                "stop_points": stop_points,
                "warnings": position.get("warnings", []),
                "recommendation": position.get("recommendation", ""),
                "current_price": current_price,
                "grade": confidence_data.get("grade", ""),
                "is_super": is_super,
                "details": confidence_data.get("details", {}),
                "atr": atr,
            },
        }

    def _build_reason(self, analysis: dict, direction: str) -> str:
        parts = []
        tech = analysis.get("technical", {})
        smc_data = analysis.get("smc", {})
        if direction == "buy":
            parts.append("إشارات شراء قوية")
            rsi = tech.get("rsi_signal", "")
            if rsi == "oversold":
                parts.append("RSI في ذروة البيع")
            elif rsi == "bullish":
                parts.append("RSI صاعد")
            macd = tech.get("macd", {}).get("crossover", "")
            if macd == "bullish":
                parts.append("MACD تقاطع صاعد")
            bos = smc_data.get("bos_choch", {}).get("bos", "")
            if "bullish" in str(bos):
                parts.append("BOS صاعد")
            ls = [s for s in smc_data.get("liquidity_sweeps", []) if s.get("type") == "buy_liquidity_sweep"]
            if ls:
                parts.append("كسح سيولة شراء")
            fvgs = [f for f in smc_data.get("fair_value_gaps", []) if f.get("type") == "bullish"]
            if fvgs:
                parts.append("FVG صاعد")
        else:
            parts.append("إشارات بيع قوية")
            rsi = tech.get("rsi_signal", "")
            if rsi == "overbought":
                parts.append("RSI في ذروة الشراء")
            elif rsi == "bearish":
                parts.append("RSI هابط")
            macd = tech.get("macd", {}).get("crossover", "")
            if macd == "bearish":
                parts.append("MACD تقاطع هابط")
            bos = smc_data.get("bos_choch", {}).get("bos", "")
            if "bearish" in str(bos):
                parts.append("BOS هابط")
            ls = [s for s in smc_data.get("liquidity_sweeps", []) if s.get("type") == "sell_liquidity_sweep"]
            if ls:
                parts.append("كسح سيولة بيع")
            fvgs = [f for f in smc_data.get("fair_value_gaps", []) if f.get("type") == "bearish"]
            if fvgs:
                parts.append("FVG هابط")
        htf = analysis.get("htf_trend", "")
        if htf:
            parts.append(f"الفريم الأعلى: {htf}")
        parts.append(f"ATR: {analysis.get('atr', 0):.2f}")
        return " | ".join(parts)

    def _build_ai_decision(self, analysis: dict, confidence: dict, direction: str) -> str:
        grade = confidence.get("grade", "تحليل")
        details = confidence.get("details", {})
        tech = details.get("technical", {})
        smc_d = details.get("smc", {})
        tf = details.get("timeframe_alignment", {})
        parts = [f"التقييم: {grade}"]
        if tech.get("details"):
            parts.append("فني: " + " | ".join(tech["details"][-3:]))
        if smc_d.get("details"):
            parts.append("SMC: " + " | ".join(smc_d["details"][-3:]))
        if tf.get("details"):
            parts.append("TF: " + " | ".join(tf["details"][-2:]))
        parts.append(f"الاتجاه: {'صاعد 📈' if direction == 'buy' else 'هابط 📉'}")
        htf = analysis.get("htf_trend", "")
        if htf:
            parts.append(f"HTF: {htf}")
        if confidence.get("is_super_signal"):
            parts.append("🔥 SIGNAL فائق القوة - جميع العوامل متوافقة")
        return " | ".join(parts)
