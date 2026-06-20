import logging
import random
import math
from datetime import datetime, timedelta
from typing import Optional, List

from config import settings
from analysis.technical import TechnicalAnalyzer
from analysis.smart_money import SmartMoneyAnalyzer
from analysis.fundamentals import FundamentalAnalyzer
from analysis.risk_manager import MicroRiskManager
from data.market_data import MarketDataProvider
from data.price_fetcher import RealPriceFetcher
from data.oanda_provider import OandaProvider
from database.db import save_backtest_result, get_trades
from database.models import BacktestResult

logger = logging.getLogger(__name__)

TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1H": 60, "4H": 240, "D": 1440}
MIN_BARS = 200
SUPPORTED_TFS = ["1m", "5m", "15m", "30m", "1H", "4H", "D"]

ALPHA = 0.9
BETA = 1.1
SMALL_CAP = 50.0
LARGE_CAP = 10000.0


class WalkForwardBacktester:
    def __init__(self, user_id: int = 0):
        self.user_id = user_id
        self.market_data = MarketDataProvider()
        self.fetcher = RealPriceFetcher()
        self.oanda = OandaProvider(
            api_key=settings.OANDA_API_KEY,
            account_id=settings.OANDA_ACCOUNT_ID,
        )
        self.tech = TechnicalAnalyzer()
        self.smc = SmartMoneyAnalyzer()
        self.fund = FundamentalAnalyzer()
        self.risk = MicroRiskManager(user_id)

    async def fetch_historical_data(self, timeframe: str, count: int = 1000) -> Optional[dict]:
        if self.oanda.is_enabled():
            try:
                candles = await self.oanda.get_candles("XAU_USD", count, timeframe)
                if candles and len(candles) > 50:
                    return self._oanda_candles_to_ohlcv(candles)
            except Exception:
                pass
        return await self.market_data.get_ohlcv("XAUUSD", timeframe, count)

    def _oanda_candles_to_ohlcv(self, candles: list) -> dict:
        closes, highs, lows, volumes = [], [], [], []
        for c in candles:
            mid = c.get("mid", {})
            vol = c.get("volume", 0)
            closes.append(float(mid.get("c", 0)))
            highs.append(float(mid.get("h", 0)))
            lows.append(float(mid.get("l", 0)))
            volumes.append(int(vol))
        closes.reverse()
        highs.reverse()
        lows.reverse()
        volumes.reverse()
        return {"close": closes, "high": highs, "low": lows, "volume": volumes}

    def _compute_volatility(self, closes: List[float], window: int = 20) -> float:
        if len(closes) < window + 1:
            return 0.5
        logs = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                logs.append(math.log(closes[i] / closes[i - 1]))
        if len(logs) < window:
            return 0.5
        recent = logs[-window:]
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        return math.sqrt(variance) * 100

    def _compute_sma(self, closes: List[float], period: int) -> float:
        if len(closes) < period:
            return closes[-1] if closes else 0
        return sum(closes[-period:]) / period

    def _compute_rsi(self, closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains, losses = [], []
        for i in range(len(closes) - period, len(closes)):
            if i == 0:
                continue
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _compute_macd(self, closes: List[float]) -> dict:
        if len(closes) < 26:
            return {"signal": "neutral", "histogram": 0}
        ema12 = self._compute_sma(closes, 12)
        ema26 = self._compute_sma(closes, 26)
        macd_line = ema12 - ema26
        signal = self._compute_sma(closes[-9:], 9) if len(closes) >= 9 else 0
        hist = macd_line - signal
        crossover = "bullish" if hist > 0 and len(closes) > 1 and (closes[-1] > closes[-2]) else "bearish" if hist < 0 else "neutral"
        return {"signal": crossover, "histogram": hist}

    def _detect_trend(self, closes: List[float]) -> str:
        if len(closes) < 50:
            return "ranging"
        sma20 = self._compute_sma(closes, 20)
        sma50 = self._compute_sma(closes, 50)
        price = closes[-1]
        if price > sma20 > sma50:
            return "bullish"
        elif price < sma20 < sma50:
            return "bearish"
        return "ranging"

    def _simulate_signal(self, closes: List[float], highs: List[float], lows: List[float],
                         capital: float, small_mode: bool) -> Optional[dict]:
        if len(closes) < MIN_BARS:
            return None
        price = closes[-1]
        rsi = self._compute_rsi(closes)
        macd = self._compute_macd(closes)
        trend = self._detect_trend(closes)
        atr_val = self._compute_volatility(closes)
        volatility = atr_val / price * 100 if price > 0 else 0

        if small_mode:
            min_conf = 85
            if capital < 50:
                min_conf = 90
        else:
            min_conf = 75

        direction, confidence, reasons = "neutral", 0, []
        rsi_signal = "neutral"
        if rsi < 30:
            rsi_signal = "oversold"
        elif rsi > 70:
            rsi_signal = "overbought"
        elif rsi < 45:
            rsi_signal = "bearish"
        elif rsi > 55:
            rsi_signal = "bullish"

        trend_conf = 10 if "bull" in trend else 15 if "bear" in trend else 0
        rsi_conf = 25 if rsi_signal in ("oversold", "overbought") else 15 if rsi_signal in ("bullish", "bearish") else 0
        macd_conf = 20 if macd["signal"] in ("bullish", "bearish") else 0
        vol_conf = -15 if volatility > 2.5 else 0

        if rsi_signal in ("oversold", "bullish") and trend in ("bullish", "ranging"):
            direction = "buy"
            confidence = 50 + trend_conf + rsi_conf + macd_conf + vol_conf
            reasons.append("bullish")
        elif rsi_signal in ("overbought", "bearish") and trend in ("bearish", "ranging"):
            direction = "sell"
            confidence = 50 + trend_conf + rsi_conf + macd_conf + vol_conf
            reasons.append("bearish")

        if macd["signal"] != "neutral":
            reasons.append(f"macd_{macd['signal']}")
        if rsi_signal:
            reasons.append(f"rsi_{rsi_signal}")
        reasons.append(f"trend_{trend}")

        alignment_bonus = 0
        if len(closes) > 100:
            sma50 = self._compute_sma(closes, 50)
            sma200 = self._compute_sma(closes, 200) if len(closes) >= 200 else sma50
            htf_trend = "bullish" if sma50 > sma200 else "bearish" if sma50 < sma200 else "ranging"
            if direction == htf_trend:
                alignment_bonus = 15
            elif htf_trend != "ranging" and direction != "neutral":
                alignment_bonus = -10
        confidence += alignment_bonus
        confidence = max(5, min(99, confidence))

        if direction == "neutral" or confidence < min_conf:
            return None

        sl_pips = max(5, min(25, atr_val * 15 / price * 100 if price > 0 else 15))
        rr = 2.0 if confidence >= 90 else 1.8 if confidence >= 85 else 1.5
        tp_pips = sl_pips * rr

        sl_dist = sl_pips * price / 10000 if price > 0 else sl_pips * 0.1
        tp_dist = tp_pips * price / 10000 if price > 0 else tp_pips * 0.1

        if direction == "buy":
            entry = price
            sl = price - sl_dist
            tp = price + tp_dist
        else:
            entry = price
            sl = price + sl_dist
            tp = price - tp_dist

        risk_amount = capital * (self.risk.risk_percent / 100.0)
        risk_amount = min(risk_amount, capital * 0.02)
        stop_pips = abs(entry - sl) * 10000 / price if price > 0 else abs(entry - sl) * 100
        pip_value = 0.10
        raw_lot = risk_amount / (stop_pips * pip_value) if stop_pips > 0 else 0.01
        lot = max(0.01, min(raw_lot, 0.10))
        lot = round(lot / 0.01) * 0.01

        return {
            "direction": direction,
            "confidence": round(confidence, 1),
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "lot": lot,
            "risk_amount": round(risk_amount, 2),
            "is_super": confidence >= 92,
            "reasons": reasons,
        }

    def _simulate_trade(self, signal: dict, closes: List[float], highs: List[float],
                        lows: List[float], entry_idx: int) -> dict:
        direction = signal["direction"]
        entry = signal["entry"]
        sl = signal["sl"]
        tp = signal["tp"]
        lot = signal["lot"]

        hit_sl, hit_tp = False, False
        hit_price_sl, hit_price_tp = None, None
        hit_idx_sl, hit_idx_tp = None, None

        for i in range(entry_idx, len(closes)):
            hi = highs[i]
            lo = lows[i]
            if direction == "buy":
                if lo <= sl:
                    hit_sl = True
                    hit_price_sl = sl
                    hit_idx_sl = i
                    break
                if hi >= tp:
                    hit_tp = True
                    hit_price_tp = tp
                    hit_idx_tp = i
                    break
            else:
                if hi >= sl:
                    hit_sl = True
                    hit_price_sl = sl
                    hit_idx_sl = i
                    break
                if lo <= tp:
                    hit_tp = True
                    hit_price_tp = tp
                    hit_idx_tp = i
                    break

        if hit_tp:
            result = "win"
            pnl = abs(entry - tp) * lot * 1000
        elif hit_sl:
            result = "loss"
            pnl = -abs(entry - sl) * lot * 1000
        else:
            last_price = closes[-1]
            if direction == "buy":
                pnl = (last_price - entry) * lot * 1000
            else:
                pnl = (entry - last_price) * lot * 1000
            result = "win" if pnl > 0 else "loss"

        bars_held = (hit_idx_tp if hit_tp else hit_idx_sl if hit_sl else len(closes) - entry_idx)

        return {
            "result": result,
            "pnl": round(pnl, 2),
            "bars_held": bars_held,
            "entry_idx": entry_idx,
            "exit_type": "tp" if hit_tp else "sl" if hit_sl else "end",
        }

    def _compute_max_drawdown(self, equity_curve: List[float]) -> float:
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return round(max_dd, 2)

    def _compute_sharpe(self, returns: List[float], rf: float = 0.05) -> float:
        if len(returns) < 2:
            return 0.0
        avg_r = sum(returns) / len(returns)
        if all(r == 0 for r in returns):
            return 0.0
        variance = sum((r - avg_r) ** 2 for r in returns) / (len(returns) - 1)
        if variance <= 0:
            return 0.0
        std = math.sqrt(variance)
        daily_rf = rf / 365
        excess = (avg_r - daily_rf)
        sharpe = excess / std if std > 0 else 0
        return round(sharpe * math.sqrt(365), 2)

    async def run_backtest(self, capital: float = 50.0, timeframe: str = "1H",
                           days: int = 30, min_confidence: float = 85) -> dict:
        small_mode = capital < 200
        num_bars = max(MIN_BARS * 2, int(days * 24 * 60 / TF_MINUTES.get(timeframe, 60)))
        num_bars = min(num_bars, 5000)
        ohlcv = await self.fetch_historical_data(timeframe, num_bars)
        closes = ohlcv.get("close", [])
        highs = ohlcv.get("high", [])
        lows = ohlcv.get("low", [])
        volumes = ohlcv.get("volume", [])

        if len(closes) < MIN_BARS:
            logger.warning(f"Not enough bars for {timeframe}: {len(closes)}")
            test_tf = {"1m": 3, "5m": 10, "15m": 20, "30m": 30, "1H": 60, "4H": 200, "D": 500}
            min_req = max(100, days * 24 * 60 // TF_MINUTES.get(timeframe, 60))
            count = max(min_req, 500)
            ohlcv = await self.market_data.get_ohlcv("XAUUSD", timeframe, count)
            closes = ohlcv.get("close", [])
            highs = ohlcv.get("high", [])
            lows = ohlcv.get("low", [])

        trades = []
        equity = [capital]
        balance = capital
        wins, losses = 0, 0
        consec_losses = 0
        trade_count = 0
        daily_trades = 0
        last_trade_day = -1

        lookback = MIN_BARS
        step = max(1, TF_MINUTES.get(timeframe, 60) // 5)
        step = min(step, 12)

        for idx in range(lookback, len(closes) - 1, step):
            if trade_count >= 100:
                break
            bar_day = idx // (24 * 60 // TF_MINUTES.get(timeframe, 60))
            if bar_day != last_trade_day:
                daily_trades = 0
                last_trade_day = bar_day
            if daily_trades >= 3:
                continue
            if consec_losses >= 2:
                last_trade_day += 1
                consec_losses = 0
                continue

            sub_close = closes[:idx + 1]
            sub_high = highs[:idx + 1]
            sub_low = lows[:idx + 1]

            signal = self._simulate_signal(sub_close, sub_high, sub_low, balance, small_mode)
            if signal is None:
                continue
            if signal["confidence"] < min_confidence:
                continue
            if signal["confidence"] < 90 and small_mode:
                continue

            result = self._simulate_trade(signal, closes, highs, lows, idx + 1)
            pnl = result["pnl"]
            balance += pnl
            trade_count += 1
            daily_trades += 1

            if result["result"] == "win":
                wins += 1
                consec_losses = 0
            else:
                losses += 1
                consec_losses += 1

            trades.append({
                "idx": idx,
                "direction": signal["direction"],
                "entry": signal["entry"],
                "sl": signal["sl"],
                "tp": signal["tp"],
                "confidence": signal["confidence"],
                "result": result["result"],
                "pnl": pnl,
                "bars_held": result["bars_held"],
                "lot": signal["lot"],
                "exit_type": result["exit_type"],
            })
            equity.append(balance)

        total = len(trades)
        if total == 0:
            return {
                "timeframe": timeframe,
                "days": days,
                "capital": capital,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "final_balance": capital,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "avg_confidence": 0,
                "avg_bars_held": 0,
                "best_trade": 0,
                "worst_trade": 0,
                "avg_pnl": 0,
                "profit_factor": 0,
                "message": "لم يتم العثور على صفقات - اختر فريم زمني أصغر أو فترة أطول",
            }

        win_rate = (wins / total * 100) if total > 0 else 0
        max_dd = self._compute_max_drawdown(equity)
        returns = [t["pnl"] / capital for t in trades] if capital > 0 else []
        sharpe = self._compute_sharpe(returns)
        avg_conf = sum(t["confidence"] for t in trades) / total
        avg_bars = sum(t["bars_held"] for t in trades) / total
        best_pnl = max(t["pnl"] for t in trades)
        worst_pnl = min(t["pnl"] for t in trades)
        avg_pnl_val = sum(t["pnl"] for t in trades) / total

        gross_wins = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        gross_losses = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else gross_wins if gross_wins > 0 else 0

        timeframe_map = {"1m": "دقيقة", "5m": "5 دقائق", "15m": "15 دقيقة", "30m": "30 دقيقة", "1H": "ساعة", "4H": "4 ساعات", "D": "يومي"}
        time_label = timeframe_map.get(timeframe, timeframe)

        result_data = {
            "timeframe": timeframe,
            "timeframe_label": time_label,
            "days": days,
            "capital": capital,
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": losses,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(balance - capital, 2),
            "final_balance": round(balance, 2),
            "return_pct": round((balance - capital) / capital * 100, 2) if capital > 0 else 0,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe,
            "avg_confidence": round(avg_conf, 1),
            "avg_bars_held": round(avg_bars, 1),
            "best_trade": round(best_pnl, 2),
            "worst_trade": round(worst_pnl, 2),
            "avg_pnl": round(avg_pnl_val, 2),
            "profit_factor": round(profit_factor, 2),
            "is_small_capital": small_mode,
            "trades": trades[:20],
            "total_trades_count": total,
        }
        return result_data

    async def run_full_backtest(self, capital: float = 50.0, days: int = 30,
                                min_confidence: float = 85) -> dict:
        results = {}
        for tf in SUPPORTED_TFS:
            try:
                result = await self.run_backtest(capital, tf, days, min_confidence)
                results[tf] = result
            except Exception as e:
                logger.error(f"Backtest error for {tf}: {e}")
                results[tf] = {"error": str(e), "timeframe": tf}
        best_tf = None
        best_sharpe = -999
        for tf, r in results.items():
            if "sharpe_ratio" in r and r["sharpe_ratio"] is not None and r.get("total_trades", 0) >= 10:
                if r["sharpe_ratio"] > best_sharpe:
                    best_sharpe = r["sharpe_ratio"]
                    best_tf = tf
        return {
            "results": results,
            "best_timeframe": best_tf,
            "best_sharpe": best_sharpe if best_sharpe > -999 else 0,
            "capital": capital,
            "days": days,
            "min_confidence": min_confidence,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def save_backtest(self, capital: float = 50.0, days: int = 30,
                            min_confidence: float = 85, timeframe: str = "1H") -> BacktestResult:
        result = await self.run_backtest(capital, timeframe, days, min_confidence)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        bt_data = {
            "start_date": start_date,
            "end_date": end_date,
            "total_trades": result.get("total_trades", 0),
            "winning_trades": result.get("winning_trades", 0),
            "losing_trades": result.get("losing_trades", 0),
            "win_rate": result.get("win_rate", 0),
            "total_pnl": result.get("total_pnl", 0),
            "max_drawdown": result.get("max_drawdown", 0),
            "sharpe_ratio": result.get("sharpe_ratio", 0),
            "avg_confidence": result.get("avg_confidence", 0),
        }
        return save_backtest_result(bt_data)

    def format_backtest_summary(self, result: dict) -> str:
        if result.get("total_trades", 0) == 0:
            return f"⚠️ *نتيجة الاختبار الخلفي*\n\nلم يتم العثور على صفقات لـ {result.get('timeframe', 'N/A')} / {result.get('days', 30)} يوم\n\nجرب:\n• فريم زمني أصغر (5m, 15m)\n• فترة أطول (60-90 يوم)\n• خفض أقل نسبة ثقة (80)"

        emoji = "🟢" if result.get("total_pnl", 0) > 0 else "🔴"
        text = (
            f"{emoji} *نتيجة الاختبار الخلفي*\n\n"
            f"📊 الفريم: {result.get('timeframe_label', result.get('timeframe', 'N/A'))}\n"
            f"📅 الفترة: {result.get('days', 30)} يوم\n"
            f"💰 رأس المال: ${result.get('capital', 0):.2f}\n\n"
            f"*الإحصائيات:*\n"
            f"📋 إجمالي الصفقات: {result.get('total_trades', 0)}\n"
            f"✅ الصفقات الرابحة: {result.get('winning_trades', 0)}\n"
            f"❌ الصفقات الخاسرة: {result.get('losing_trades', 0)}\n"
            f"📈 نسبة الربح: {result.get('win_rate', 0)}%\n"
            f"💵 إجمالي الربح/الخسارة: ${result.get('total_pnl', 0):.2f}\n"
            f"💰 الرصيد النهائي: ${result.get('final_balance', 0):.2f}\n"
            f"📊 العائد: {result.get('return_pct', 0)}%\n"
            f"📉 أقصى انخفاض: {result.get('max_drawdown', 0)}%\n"
            f"⚡ Sharpe Ratio: {result.get('sharpe_ratio', 0)}\n"
            f"🎯 متوسط الثقة: {result.get('avg_confidence', 0)}%\n"
            f"⏱ متوسط الحجز (بار): {result.get('avg_bars_held', 0)}\n"
            f"🏆 أفضل صفقة: ${result.get('best_trade', 0):.2f}\n"
            f"💔 أسوأ صفقة: ${result.get('worst_trade', 0):.2f}\n"
            f"📐 Profit Factor: {result.get('profit_factor', 0):.2f}\n"
        )

        if result.get("win_rate", 0) >= 60 and result.get("profit_factor", 0) >= 1.5:
            text += "\n*⭐ توصية: استراتيجية مناسبة لهذا الفريم*"
        elif result.get("win_rate", 0) < 40:
            text += "\n*⚠️ توصية: تجنب هذا الفريم حالياً*"
        else:
            text += "\n*📌 توصية: استراتيجية متوسطة - راقب الأداء*"

        return text
