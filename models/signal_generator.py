import logging
import random
from datetime import datetime
from typing import Optional

from config import settings
from models.confidence import ConfidenceScorer
from models.ai_model import AIModel
from analysis.technical import TechnicalAnalyzer
from analysis.smart_money import SmartMoneyAnalyzer
from analysis.fundamentals import FundamentalAnalyzer
from analysis.risk_manager import MicroRiskManager as RiskManager
from data.market_data import MarketDataProvider
from data.price_fetcher import RealPriceFetcher
from data.news_collector import NewsCollector
from data.economic_calendar import EconomicCalendar
from database.db import save_trade, get_trades_count_today

logger = logging.getLogger(__name__)


class SignalGenerator:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.tech_analyzer = TechnicalAnalyzer()
        self.smc_analyzer = SmartMoneyAnalyzer()
        self.fund_analyzer = FundamentalAnalyzer()
        self.market_data = MarketDataProvider()
        self.price_fetcher = RealPriceFetcher()
        self.news_collector = NewsCollector()
        self.econ_calendar = EconomicCalendar()
        self.ai_model = AIModel()
        self.confidence_scorer = ConfidenceScorer()
        self.risk_manager = RiskManager(user_id)

    def _determine_trading_style(self, technical: dict, signal_direction: str) -> str:
        target_styles = {
            "scalping": "سكالبينج",
            "intraday": "يومي",
            "swing": "سوينغ",
        }
        atr = technical.get("atr", 0)
        current_price = technical.get("current_price", 0)
        if current_price and atr and current_price > 0:
            atr_percent = (atr / current_price) * 100
            if atr_percent < 0.3:
                return "scalping"
            elif atr_percent < 0.7:
                return "intraday"
            else:
                return "swing"
        if technical.get("trend") in ["strong_bullish", "strong_bearish"]:
            return "swing"
        return "intraday"

    def _calculate_trade_levels(
        self, direction: str, current_price: float, atr: float, market_data: dict
    ) -> dict:
        if direction == "buy":
            if current_price > 100:
                entry = round(current_price + atr * 0.1, 2)
                sl = round(current_price - atr * 1.5, 2)
                tp1 = round(current_price + atr * 1.5, 2)
                tp2 = round(current_price + atr * 2.5, 2)
                tp3 = round(current_price + atr * 4.0, 2)
            else:
                entry = round(current_price + atr * 0.1, 2)
                sl = round(current_price - atr * 1.5, 2)
                tp1 = round(current_price + atr * 1.5, 2)
                tp2 = round(current_price + atr * 2.5, 2)
                tp3 = round(current_price + atr * 4.0, 2)
        else:
            if current_price > 100:
                entry = round(current_price - atr * 0.1, 2)
                sl = round(current_price + atr * 1.5, 2)
                tp1 = round(current_price - atr * 1.5, 2)
                tp2 = round(current_price - atr * 2.5, 2)
                tp3 = round(current_price - atr * 4.0, 2)
            else:
                entry = round(current_price - atr * 0.1, 2)
                sl = round(current_price + atr * 1.5, 2)
                tp1 = round(current_price - atr * 1.5, 2)
                tp2 = round(current_price - atr * 2.5, 2)
                tp3 = round(current_price - atr * 4.0, 2)
        return {"entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3}

    def _get_timeframe_focus(self, trading_style: str) -> str:
        timeframes = {
            "scalping": "1m / 5m / 15m",
            "intraday": "30m / 1H / 4H",
            "swing": "4H / Daily",
        }
        return timeframes.get(trading_style, "1H / 4H")

    def _get_expected_duration(self, trading_style: str) -> str:
        durations = {
            "scalping": "دقائق - ساعة",
            "intraday": "ساعات - يوم تداول",
            "swing": "أيام - أسبوع",
        }
        return durations.get(trading_style, "غير محدد")

    def _get_success_rate(self, confidence: float, trading_style: str) -> str:
        base = confidence * 0.85
        style_modifier = {"scalping": 0.9, "intraday": 1.0, "swing": 1.05}
        mod = style_modifier.get(trading_style, 1.0)
        rate = base * mod
        rate = max(50, min(95, rate))
        return f"{rate:.0f}%"

    def _get_risk_level(self, vix_risk: str, volatility: float, technical: dict) -> str:
        if vix_risk in ["خطير جداً", "خطير"]:
            return "خطير جداً"
        if volatility > 2.0:
            return "مرتفع"
        if technical.get("trend") in ["strong_bullish", "strong_bearish"]:
            return "متوسط"
        return "منخفض"

    def _get_recommended_leverage(self, risk_level: str, trading_style: str) -> str:
        if risk_level in ["خطير جداً", "مرتفع"]:
            return "1:2 أو بدون رافعة"
        if trading_style == "scalping":
            return "1:5 إلى 1:10"
        elif trading_style == "intraday":
            return "1:3 إلى 1:5"
        else:
            return "1:2 إلى 1:3"

    async def generate_signal(self) -> Optional[dict]:
        can, reason = self.risk_manager.can_trade()
        if not can:
            logger.info(f"Cannot trade: {reason}")
            return {"no_trade": True, "reason": reason}
        try:
            snapshot = await self.market_data.get_market_snapshot()
            all_timeframes = await self.market_data.get_all_timeframes("XAUUSD")
            news = await self.news_collector.get_latest_news(5)
            news_impact = await self.news_collector.analyze_news_impact(news)
            upcoming_events = await self.econ_calendar.get_high_impact_events(7)
            fund_analysis = self.fund_analyzer.full_fundamental_analysis(
                dxy=snapshot["dxy"],
                vix=snapshot["vix"],
                oil=snapshot["oil"],
                sp500=snapshot["sp500"],
                us10y=snapshot["us10y"],
                us2y=snapshot["us2y"],
            )
            primary_tf = "4H"
            ohlcv = all_timeframes.get(primary_tf, await self.market_data.get_ohlcv("XAUUSD", "4H", 100))
            technical = self.tech_analyzer.full_technical_analysis(ohlcv)
            smc = self.smc_analyzer.full_smc_analysis(ohlcv)
            signals = self.ai_model.combine_technical_signals(
                technical.get("rsi_signal", "neutral"),
                technical.get("macd", {}).get("crossover", "none"),
                technical.get("trend", "ranging"),
                technical.get("bollinger_bands", {}).get("position", "middle"),
                smc.get("bos_choch", {}),
                smc.get("liquidity_sweeps", []),
            )
            market_quality = self.ai_model.evaluate_market_quality(
                technical.get("trend", "ranging"),
                fund_analysis.get("vix", {}).get("level", "normal"),
                technical.get("atr", 0) or 0,
                fund_analysis.get("dollar", {}).get("strength", "neutral"),
                fund_analysis.get("risk_factors", []),
            )
            confidence_result = self.confidence_scorer.calculate_pro(technical, fund_analysis, smc, signals, capital=self.risk_manager.settings.capital)
            confidence = confidence_result.get("confidence", 0)
            min_confidence = self.risk_manager.settings.min_confidence or settings.DEFAULT_MIN_CONFIDENCE
            if not self.confidence_scorer.should_trade(confidence, min_confidence):
                ai_reasoning = self.ai_model.get_ai_reasoning(technical, fund_analysis, smc, signals, market_quality)
                return {
                    "no_trade": True,
                    "reason": "لم تصل نسبة الثقة إلى الحد الأدنى المطلوب",
                    "confidence": confidence,
                    "min_required": min_confidence,
                    "direction": signals.get("direction", "neutral"),
                    "technical_trend": technical.get("trend"),
                    "ai_reasoning": ai_reasoning,
                    "market_quality": market_quality,
                    "news_impact": news_impact,
                    "fundamental_summary": fund_analysis.get("summary"),
                }
            if signals.get("direction") == "neutral":
                return {
                    "no_trade": True,
                    "reason": "لا توجد إشارة واضحة - السوق متعادل",
                    "confidence": confidence,
                    "ai_reasoning": "الإشارات الفنية غير حاسمة بين الشراء والبيع",
                }
            direction = signals.get("direction")
            trading_style = self._determine_trading_style(technical, direction)
            current_price = technical.get("current_price", snapshot["gold"])
            atr = technical.get("atr", technical.get("current_price", 2000) * 0.005) or 10
            levels = self._calculate_trade_levels(direction, current_price, atr, snapshot)
            position_info = self.risk_manager.calculate_position_size(
                levels["entry"], levels["sl"], trading_style
            )
            vix_risk = fund_analysis.get("vix", {}).get("trading_risk", "متوسط")
            risk_level = self._get_risk_level(
                vix_risk,
                (atr / current_price * 100) if current_price > 0 else 1,
                technical,
            )
            ai_reasoning = self.ai_model.get_ai_reasoning(technical, fund_analysis, smc, signals, market_quality)
            trade_data = {
                "symbol": "XAUUSD",
                "trade_type": direction,
                "trading_style": trading_style,
                "timeframe": primary_tf,
                "entry_price": levels["entry"],
                "stop_loss": levels["sl"],
                "take_profit_1": levels["tp1"],
                "take_profit_2": levels["tp2"],
                "take_profit_3": levels["tp3"],
                "confidence": confidence,
                "risk_level": risk_level,
                "leverage": self._get_recommended_leverage(risk_level, trading_style),
                "capital_at_risk": position_info.get("capital_at_risk", 0),
                "lot_size": position_info.get("lot_size", 0.01),
                "status": "pending",
                "entry_reason": f"{'شراء' if direction == 'buy' else 'بيع'} {trading_style} - {ai_reasoning}",
                "news_analysis": f"تأثير الأخبار: {news_impact.get('overall_impact', 'محايد')} | تحذير: {news_impact.get('volatility_warning', 'لا يوجد')}",
                "dollar_analysis": fund_analysis.get("dollar", {}).get("signal", "محايد"),
                "bonds_analysis": fund_analysis.get("bonds", {}).get("gold_impact", "محايد"),
                "liquidity_analysis": f"تم كسح {len(smc.get('liquidity_sweeps', []))} منطقة سيولة. مناطق العرض والطلب: {len(smc.get('demand_supply_zones', {}).get('demand_zones', []))} طلب, {len(smc.get('demand_supply_zones', {}).get('supply_zones', []))} عرض.",
                "whales_analysis": f"BOS: {smc.get('bos_choch', {}).get('bos', 'none')} | CHOCH: {smc.get('bos_choch', {}).get('choch', 'none')} | FVGs: {len(smc.get('fair_value_gaps', []))}",
                "ai_decision": ai_reasoning,
            }
            saved_trade = save_trade(trade_data)
            return {
                "no_trade": False,
                "trade_id": saved_trade.id,
                "trade": {
                    **trade_data,
                    "trading_style_name": "سكالبينج" if trading_style == "scalping" else "يومي" if trading_style == "intraday" else "سوينغ",
                    "timeframe_focus": self._get_timeframe_focus(trading_style),
                    "expected_duration": self._get_expected_duration(trading_style),
                    "success_rate": self._get_success_rate(confidence, trading_style),
                    "warnings": position_info.get("warnings", []),
                    "risk_warnings": self.risk_manager.get_risk_warnings(),
                    "fundamental_summary": fund_analysis.get("summary"),
                    "market_quality": market_quality,
                    "upcoming_events": upcoming_events[:3],
                },
            }
        except Exception as e:
            logger.error(f"Error generating signal: {e}", exc_info=True)
            return {"no_trade": True, "reason": f"حدث خطأ أثناء التحليل: {str(e)}"}

    async def generate_signal_for_timeframe(self, timeframe: str = "1H") -> Optional[dict]:
        can, reason = self.risk_manager.can_trade()
        if not can:
            return {"no_trade": True, "reason": reason}
        try:
            snapshot = await self.price_fetcher.fetch_all_snapshot()
            ohlcv = await self.market_data.get_ohlcv("XAUUSD", timeframe, 100)
            if timeframe == "1m":
                ohlcv_htf = await self.market_data.get_ohlcv("XAUUSD", "5m", 100)
            elif timeframe in ["5m", "15m"]:
                ohlcv_htf = await self.market_data.get_ohlcv("XAUUSD", "1H", 100)
            elif timeframe == "30m":
                ohlcv_htf = await self.market_data.get_ohlcv("XAUUSD", "4H", 100)
            elif timeframe == "1H":
                ohlcv_htf = await self.market_data.get_ohlcv("XAUUSD", "4H", 100)
            else:
                ohlcv_htf = await self.market_data.get_ohlcv("XAUUSD", "D", 100)
            news = await self.news_collector.get_latest_news(5)
            news_impact = await self.news_collector.analyze_news_impact(news)
            upcoming_events = await self.econ_calendar.get_high_impact_events(7)
            fund_analysis = self.fund_analyzer.full_fundamental_analysis(
                dxy=snapshot["dxy"], vix=snapshot["vix"], oil=snapshot["oil"],
                sp500=snapshot["sp500"], us10y=snapshot["us10y"], us2y=snapshot["us2y"],
            )
            technical = self.tech_analyzer.full_technical_analysis(ohlcv)
            technical_htf = self.tech_analyzer.full_technical_analysis(ohlcv_htf)
            smc = self.smc_analyzer.full_smc_analysis(ohlcv)
            signals = self.ai_model.combine_technical_signals(
                technical.get("rsi_signal", "neutral"),
                technical.get("macd", {}).get("crossover", "none"),
                technical.get("trend", "ranging"),
                technical.get("bollinger_bands", {}).get("position", "middle"),
                smc.get("bos_choch", {}),
                smc.get("liquidity_sweeps", []),
            )
            htf_trend = technical_htf.get("trend", "ranging")
            tf_alignment = "aligned" if technical.get("trend") == htf_trend else "mixed"
            market_quality = self.ai_model.evaluate_market_quality(
                technical.get("trend", "ranging"),
                fund_analysis.get("vix", {}).get("level", "normal"),
                technical.get("atr", 0) or 0,
                fund_analysis.get("dollar", {}).get("strength", "neutral"),
                fund_analysis.get("risk_factors", []),
            )
            confidence = self.confidence_scorer.calculate_pro(technical, fund_analysis, smc, signals).get("confidence", 0)
            if tf_alignment == "aligned":
                confidence = min(100, confidence * 1.1)
            elif tf_alignment == "mixed":
                confidence = confidence * 0.9
            min_confidence = self.risk_manager.settings.min_confidence or settings.DEFAULT_MIN_CONFIDENCE
            current_price = technical.get("current_price", snapshot["gold"])
            if signals.get("direction") == "neutral":
                return {
                    "no_trade": True, "reason": "لا توجد إشارة واضحة على هذا الفريم",
                    "confidence": confidence, "direction": "neutral",
                    "technical_trend": technical.get("trend"),
                    "ai_reasoning": "الإشارات الفنية غير حاسمة",
                    "market_quality": market_quality,
                    "fundamental_summary": fund_analysis.get("summary"),
                }
            if not self.confidence_scorer.should_trade(confidence, min_confidence):
                return {
                    "no_trade": True, "reason": f"نسبة الثقة {confidence}% أقل من الحد الأدنى {min_confidence}%",
                    "confidence": confidence, "min_required": min_confidence,
                    "direction": signals.get("direction"),
                    "technical_trend": technical.get("trend"),
                    "ai_reasoning": "لم تصل الإشارات إلى مستوى القوة المطلوب",
                    "market_quality": market_quality,
                    "news_impact": news_impact,
                    "fundamental_summary": fund_analysis.get("summary"),
                }
            direction = signals.get("direction")
            trading_style_map = {"1m": "scalping", "5m": "scalping", "15m": "scalping",
                                 "30m": "intraday", "1H": "intraday", "4H": "swing", "D": "swing"}
            trading_style = trading_style_map.get(timeframe, "intraday")
            atr_val = technical.get("atr") or (current_price * 0.005)
            levels = self._calculate_trade_levels(direction, current_price, atr_val, snapshot)
            position_info = self.risk_manager.calculate_position_size(levels["entry"], levels["sl"], trading_style)
            vix_risk = fund_analysis.get("vix", {}).get("trading_risk", "متوسط")
            risk_level = self._get_risk_level(vix_risk, (atr_val / current_price * 100) if current_price > 0 else 1, technical)
            ai_reasoning = self.ai_model.get_ai_reasoning(technical, fund_analysis, smc, signals, market_quality)
            trade_data = {
                "symbol": "XAUUSD", "trade_type": direction, "trading_style": trading_style,
                "timeframe": timeframe, "entry_price": levels["entry"], "stop_loss": levels["sl"],
                "take_profit_1": levels["tp1"], "take_profit_2": levels["tp2"], "take_profit_3": levels["tp3"],
                "confidence": confidence, "risk_level": risk_level,
                "leverage": self._get_recommended_leverage(risk_level, trading_style),
                "capital_at_risk": position_info.get("capital_at_risk", 0),
                "lot_size": position_info.get("lot_size", 0.01), "status": "pending",
                "entry_reason": f"{'شراء' if direction == 'buy' else 'بيع'} على فريم {timeframe} - {ai_reasoning}",
                "news_analysis": f"تأثير الأخبار: {news_impact.get('overall_impact', 'محايد')} | {news_impact.get('volatility_warning', '')}",
                "dollar_analysis": fund_analysis.get("dollar", {}).get("signal", "محايد"),
                "bonds_analysis": fund_analysis.get("bonds", {}).get("gold_impact", "محايد"),
                "liquidity_analysis": f"كسح {len(smc.get('liquidity_sweeps', []))} سيولة | طلب {len(smc.get('demand_supply_zones', {}).get('demand_zones', []))} / عرض {len(smc.get('demand_supply_zones', {}).get('supply_zones', []))}",
                "whales_analysis": f"BOS: {smc.get('bos_choch', {}).get('bos', 'none')} | CHOCH: {smc.get('bos_choch', {}).get('choch', 'none')} | FVG: {len(smc.get('fair_value_gaps', []))}",
                "ai_decision": ai_reasoning,
            }
            saved_trade = save_trade(trade_data)
            return {
                "no_trade": False, "trade_id": saved_trade.id,
                "trade": {
                    **trade_data,
                    "trading_style_name": "سكالبينج" if trading_style == "scalping" else "يومي" if trading_style == "intraday" else "سوينغ",
                    "expected_duration": self._get_expected_duration(trading_style),
                    "warnings": position_info.get("warnings", []),
                    "risk_warnings": self.risk_manager.get_risk_warnings(),
                    "market_quality": market_quality,
                    "upcoming_events": upcoming_events[:3],
                    "current_price": current_price,
                },
            }
        except Exception as e:
            logger.error(f"Error generating signal for {timeframe}: {e}", exc_info=True)
            return {"no_trade": True, "reason": f"خطأ في التحليل: {str(e)}"}
