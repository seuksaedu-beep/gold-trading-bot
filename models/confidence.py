import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ProConfidenceScorer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _score_technical(self, technical: dict, signal_direction: str = "neutral") -> dict:
        score = 50
        details = []
        if not technical:
            return {"score": 30, "details": ["No technical data"], "pass": False}
        rsi = technical.get("rsi_signal", "neutral")
        if rsi in ["oversold", "overbought"]:
            score += 20
            details.append(f"RSI extreme ({rsi})")
        elif rsi in ["bullish", "bearish"]:
            score += 10
            details.append(f"RSI trending ({rsi})")
        else:
            score -= 2
            details.append("RSI neutral")
        macd = technical.get("macd", {})
        crossover = macd.get("crossover", "none")
        if crossover in ["bullish", "bearish"]:
            aligned = (signal_direction == "buy" and crossover == "bullish") or (signal_direction == "sell" and crossover == "bearish")
            score += 20 if aligned else 8
            details.append(f"MACD crossover ({crossover})")
        elif macd.get("macd") and macd.get("signal"):
            macd_val = macd.get("macd", 0)
            signal_val = macd.get("signal", 0)
            macd_bullish = macd_val > signal_val
            aligned = (signal_direction == "buy" and macd_bullish) or (signal_direction == "sell" and not macd_bullish)
            if aligned:
                score += 8
                details.append("MACD aligned with direction")
            else:
                score -= 2
                details.append("MACD misaligned")
        trend = technical.get("trend", "ranging")
        if trend in ["strong_bullish", "strong_bearish"]:
            score += 20
            details.append(f"Strong trend ({trend})")
        elif trend in ["bullish", "bearish"]:
            score += 10
            details.append(f"Trend ({trend})")
        else:
            score -= 3
            details.append("Ranging market")
        bb = technical.get("bollinger_bands", {})
        bb_pos = bb.get("position", "middle")
        if bb_pos in ["below_lower", "above_upper"]:
            score += 12
            details.append(f"BB extreme ({bb_pos})")
        ema_check = technical.get("price_above_ema_20")
        if ema_check is not None:
            score += 5
            if ema_check:
                details.append("Price above EMA20")
            else:
                details.append("Price below EMA20")
        atr = technical.get("atr")
        current_price = technical.get("current_price", 0)
        if atr and current_price > 0:
            atr_pct = (atr / current_price) * 100
            if atr_pct < 0.15:
                score += 5
                details.append(f"Low volatility ({atr_pct:.2f}%)")
            elif atr_pct > 0.5:
                score -= 8
                details.append(f"High volatility ({atr_pct:.2f}%)")
        return {
            "score": max(0, min(100, score)),
            "details": details,
            "pass": score >= 75,
        }

    def _score_fundamental(self, fundamental: dict) -> dict:
        score = 50
        details = []
        if not fundamental:
            return {"score": 40, "details": ["No fundamental data"], "pass": True}
        vix = fundamental.get("vix", {})
        vix_level = vix.get("level", "normal")
        if vix_level == "low":
            score += 15
            details.append("VIX low - stable market")
        elif vix_level == "normal":
            score += 5
            details.append("VIX normal")
        elif vix_level == "elevated":
            score -= 10
            details.append("VIX elevated - caution")
        else:
            score -= 20
            details.append("VIX extreme - no trading")
        dollar = fundamental.get("dollar", {})
        d_strength = dollar.get("strength", "neutral")
        if d_strength in ["bullish", "bearish"]:
            score += 5
            details.append(f"Dollar trending ({d_strength})")
        if fundamental.get("is_suitable_for_trading", False) is False:
            score -= 15
            details.append("Market not suitable")
        risk_factors = fundamental.get("risk_factors", [])
        score -= min(len(risk_factors) * 5, 20)
        for rf in risk_factors[:2]:
            details.append(f"Risk: {rf}")
        fed = fundamental.get("fed", {})
        fed_stance = fed.get("fed_stance", "neutral")
        if fed_stance == "neutral":
            score += 5
            details.append("Fed neutral")
        elif fed_stance in ["hawkish", "dovish"]:
            score -= 3
            details.append(f"Fed {fed_stance}")
        return {
            "score": max(0, min(100, score)),
            "details": details,
            "pass": score >= 40,
        }

    def _score_smc(self, smc: dict) -> dict:
        score = 40
        details = []
        if not smc:
            return {"score": 30, "details": ["No SMC data"], "pass": False}
        bos_choch = smc.get("bos_choch", {})
        bos = bos_choch.get("bos", "none")
        choch = bos_choch.get("choch", "none")
        smc_trend = bos_choch.get("trend", "ranging")
        if bos != "none":
            score += 18
            details.append(f"BOS detected ({bos})")
        if choch != "none":
            score += 15
            details.append(f"CHOCH detected ({choch})")
        if smc_trend != "ranging":
            score += 8
            details.append(f"SMC trend: {smc_trend}")
        liquidity_sweeps = smc.get("liquidity_sweeps", [])
        ls_count = len(liquidity_sweeps)
        if ls_count >= 2:
            score += 18
            details.append(f"{ls_count} liquidity sweeps")
        elif ls_count == 1:
            score += 10
            details.append("1 liquidity sweep")
        fvgs = smc.get("fair_value_gaps", [])
        if len(fvgs) >= 1:
            score += 12
            details.append(f"{len(fvgs)} FVGs")
        demand_supply = smc.get("demand_supply_zones", {})
        demand_count = len(demand_supply.get("demand_zones", []))
        supply_count = len(demand_supply.get("supply_zones", []))
        if demand_count > 0 or supply_count > 0:
            score += 5
            details.append(f"Zones: {demand_count}D/{supply_count}S")
        order_blocks = smc.get("order_blocks", {})
        ob_count = len(order_blocks.get("bullish_blocks", [])) + len(order_blocks.get("bearish_blocks", []))
        if ob_count > 0:
            score += 8
            details.append(f"{ob_count} order blocks")
        nearest_demand = smc.get("nearest_demand")
        nearest_supply = smc.get("nearest_supply")
        current_price = smc.get("current_price", 0)
        if nearest_demand and current_price > 0:
            dist = abs(current_price - nearest_demand.get("bottom", current_price))
            if dist / current_price < 0.003:
                score += 5
                details.append("Near demand zone")
        if nearest_supply and current_price > 0:
            dist = abs(current_price - nearest_supply.get("top", current_price))
            if dist / current_price < 0.003:
                score += 5
                details.append("Near supply zone")
        return {
            "score": max(0, min(100, score)),
            "details": details,
            "pass": score >= 75,
        }

    def _check_multi_timeframe_alignment(self, timeframe_analysis: dict) -> dict:
        if not timeframe_analysis:
            return {"aligned": False, "score": 0, "details": ["No multi-TF data"]}
        directions = []
        alignment_score = 0
        details = []
        for tf, data in timeframe_analysis.items():
            dir = data.get("signal_direction", "neutral")
            directions.append(dir)
        if not directions:
            return {"aligned": False, "score": 0, "details": ["No timeframe data"]}
        non_neutral = [d for d in directions if d != "neutral"]
        if len(non_neutral) >= 3:
            all_same = all(d == non_neutral[0] for d in non_neutral)
            if all_same:
                alignment_score = 100
                details.append(f"All {len(non_neutral)} TFs aligned: {non_neutral[0]}")
                return {"aligned": True, "score": alignment_score, "details": details}
            else:
                alignment_score = 40
                details.append("Mixed signals across timeframes")
                return {"aligned": False, "score": alignment_score, "details": details}
        elif len(non_neutral) >= 2 and len(non_neutral) == len([d for d in non_neutral if d == non_neutral[0]]):
            alignment_score = 75
            details.append(f"2 TFs aligned: {non_neutral[0]}")
            return {"aligned": True, "score": alignment_score, "details": details}
        else:
            alignment_score = 25
            details.append("Insufficient TF alignment")
            return {"aligned": False, "score": alignment_score, "details": details}

    def calculate_pro(
        self,
        technical: dict,
        fundamental: dict,
        smc: dict,
        signals: dict,
        timeframe_analysis: Optional[dict] = None,
        capital: float = 50.0,
    ) -> dict:
        direction = signals.get("direction", "neutral")
        tech = self._score_technical(technical, direction)
        fund = self._score_fundamental(fundamental)
        smc_result = self._score_smc(smc)
        tf_alignment = self._check_multi_timeframe_alignment(timeframe_analysis or {})
        weights = {
            "technical": 0.25,
            "fundamental": 0.10,
            "smc": 0.35,
            "timeframe_alignment": 0.30,
        }
        base_confidence = (
            tech["score"] * weights["technical"]
            + fund["score"] * weights["fundamental"]
            + smc_result["score"] * weights["smc"]
            + tf_alignment["score"] * weights["timeframe_alignment"]
        )
        if direction == "neutral":
            base_confidence *= 0.4
        if capital < 100:
            base_confidence *= 0.98
        penalties = 0
        if tech["score"] < 65:
            penalties += 5
        if smc_result["score"] < 65:
            penalties += 8
        if not tf_alignment["aligned"]:
            penalties += 15
        if not fund["pass"]:
            penalties += 5
        final = base_confidence - penalties
        final = max(0, min(100, final))
        details = {
            "technical": tech,
            "fundamental": fund,
            "smc": smc_result,
            "timeframe_alignment": tf_alignment,
            "direction": direction,
        }
        is_super_signal = (
            final >= 90
            and tech["pass"]
            and smc_result["pass"]
            and tf_alignment["aligned"]
            and direction != "neutral"
        )
        is_strong_signal = (
            final >= 80
            and direction != "neutral"
        )
        return {
            "confidence": round(final, 1),
            "grade": self._get_grade(final),
            "is_super_signal": is_super_signal,
            "is_strong_signal": is_strong_signal,
            "should_trade": is_strong_signal,
            "should_trade_super": is_super_signal,
            "details": details,
            "penalties": round(penalties, 1),
        }

    def _get_grade(self, confidence: float) -> str:
        if confidence >= 95:
            return "SUPER SIGNAL"
        elif confidence >= 90:
            return "EXCELLENT"
        elif confidence >= 85:
            return "VERY HIGH"
        elif confidence >= 80:
            return "HIGH"
        elif confidence >= 70:
            return "GOOD"
        elif confidence >= 60:
            return "MODERATE"
        else:
            return "WEAK - NO TRADE"


class ConfidenceScorer(ProConfidenceScorer):
    pass
