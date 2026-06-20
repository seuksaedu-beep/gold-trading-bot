import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AIModel:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def evaluate_market_quality(
        self,
        trend: str,
        vix_level: str,
        volatility: float,
        dxy_strength: str,
        risk_factors: list,
    ) -> dict:
        score = 100
        deductions = []
        if vix_level in ["extreme", "high"]:
            score -= 30
            deductions.append("تقلبات سوق عالية جداً")
        if trend == "ranging":
            score -= 10
            deductions.append("سوق عرضي بدون اتجاه واضح")
        if dxy_strength in ["strong_bullish", "strong_bearish"]:
            score -= 15
            deductions.append("حركة حادة في الدولار")
        if volatility > 2.5:
            score -= 10
            deductions.append("تقلبات سعرية عالية")
        score = max(10, min(100, score))
        quality = "ممتاز" if score >= 85 else "جيد" if score >= 70 else "متوسط" if score >= 50 else "ضعيف"
        is_tradeable = score >= 50
        return {
            "score": score,
            "quality": quality,
            "is_tradeable": is_tradeable,
            "deductions": deductions,
        }

    def combine_technical_signals(
        self,
        rsi_signal: str,
        macd_crossover: str,
        trend: str,
        bb_position: str,
        bos_choch: dict,
        liquidity_sweeps: list,
    ) -> dict:
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0
        if rsi_signal == "oversold":
            bullish_signals += 2
            total_signals += 2
        elif rsi_signal == "bullish":
            bullish_signals += 1
            total_signals += 1
        elif rsi_signal == "overbought":
            bearish_signals += 2
            total_signals += 2
        elif rsi_signal == "bearish":
            bearish_signals += 1
            total_signals += 1
        if macd_crossover == "bullish":
            bullish_signals += 2
            total_signals += 2
        elif macd_crossover == "bearish":
            bearish_signals += 2
            total_signals += 2
        if trend in ["strong_bullish", "bullish"]:
            bullish_signals += 1
            total_signals += 1
        elif trend in ["strong_bearish", "bearish"]:
            bearish_signals += 1
            total_signals += 1
        if bb_position == "below_lower":
            bullish_signals += 1
            total_signals += 1
        elif bb_position == "above_upper":
            bearish_signals += 1
            total_signals += 1
        if bos_choch.get("trend") == "bullish":
            bullish_signals += 1
            total_signals += 1
        elif bos_choch.get("trend") == "bearish":
            bearish_signals += 1
            total_signals += 1
        for sweep in liquidity_sweeps:
            if sweep.get("type") == "buy_liquidity_sweep":
                bullish_signals += 1
            elif sweep.get("type") == "sell_liquidity_sweep":
                bearish_signals += 1
            total_signals += 1
        if total_signals == 0:
            return {"direction": "neutral", "bullish_signals": 0, "bearish_signals": 0, "ratio": 0}
        bull_ratio = bullish_signals / total_signals * 100
        bear_ratio = bearish_signals / total_signals * 100
        if bull_ratio > 65:
            direction = "buy"
        elif bear_ratio > 65:
            direction = "sell"
        else:
            direction = "neutral"
        return {
            "direction": direction,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "bullish_ratio": round(bull_ratio, 1),
            "bearish_ratio": round(bear_ratio, 1),
        }

    def calculate_confidence(
        self,
        technical_alignment: float,
        fundamental_alignment: float,
        smc_alignment: float,
        market_quality_score: float,
        trend_clarity: float,
        volume_confirmation: float,
    ) -> float:
        weights = {
            "technical": 0.25,
            "fundamental": 0.20,
            "smc": 0.20,
            "market_quality": 0.15,
            "trend_clarity": 0.10,
            "volume": 0.10,
        }
        score = (
            technical_alignment * weights["technical"]
            + fundamental_alignment * weights["fundamental"]
            + smc_alignment * weights["smc"]
            + market_quality_score * weights["market_quality"]
            + trend_clarity * weights["trend_clarity"]
            + volume_confirmation * weights["volume"]
        )
        return round(max(0, min(100, score)), 1)

    def get_ai_reasoning(
        self,
        technical: dict,
        fundamental: dict,
        smc: dict,
        signals: dict,
        market_quality: dict,
    ) -> str:
        reasons = []
        if signals.get("direction") == "buy":
            reasons.append("الإشارات الفنية إيجابية")
            if technical.get("trend") in ["bullish", "strong_bullish"]:
                reasons.append("اتجاه صاعد واضح")
            if technical.get("rsi_signal") == "oversold":
                reasons.append("مؤشر RSI في منطقة ذروة البيع")
            if smc.get("bos_choch", {}).get("bos") == "bullish_bos":
                reasons.append("كسر هيكلي صاعد BOS")
            if smc.get("liquidity_sweeps"):
                buy_sweeps = [s for s in smc.get("liquidity_sweeps", []) if s.get("type") == "buy_liquidity_sweep"]
                if buy_sweeps:
                    reasons.append("تم كسح سيولة شراء")
            if smc.get("fair_value_gaps"):
                bullish_fvgs = [f for f in smc.get("fair_value_gaps", []) if f.get("type") == "bullish"]
                if bullish_fvgs:
                    reasons.append("وجود فجوات سعرية صاعدة FVG")
        elif signals.get("direction") == "sell":
            reasons.append("الإشارات الفنية سلبية")
            if technical.get("trend") in ["bearish", "strong_bearish"]:
                reasons.append("اتجاه هابط واضح")
            if technical.get("rsi_signal") == "overbought":
                reasons.append("مؤشر RSI في منطقة ذروة الشراء")
            if smc.get("bos_choch", {}).get("bos") == "bearish_bos":
                reasons.append("كسر هيكلي هابط BOS")
            if smc.get("liquidity_sweeps"):
                sell_sweeps = [s for s in smc.get("liquidity_sweeps", []) if s.get("type") == "sell_liquidity_sweep"]
                if sell_sweeps:
                    reasons.append("تم كسح سيولة بيع")
        if not market_quality.get("is_tradeable", True):
            reasons.append("⚠️ تحذير: جودة السوق ضعيفة")
        if fundamental:
            if fundamental.get("vix", {}).get("trading_risk") in ["خطير", "خطير جداً"]:
                reasons.append("⚠️ تقلبات VIX خطيرة")
            if fundamental.get("dollar", {}).get("strength") in ["strong_bullish", "strong_bearish"]:
                reasons.append("⚠️ الدولار في حركة حادة")
        return " | ".join(reasons) if reasons else "تحليل متكامل - فرصة تداول متوسطة"
