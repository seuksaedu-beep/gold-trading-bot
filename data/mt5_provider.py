import logging
import platform
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class MT5Provider:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._connected = False
        self._mt5 = None

    def _import_mt5(self):
        if self._mt5 is not None:
            return self._mt5 is not None
        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5
            return True
        except ImportError:
            self.logger.warning("MetaTrader5 package not installed")
            return False
        except Exception as e:
            self.logger.warning(f"MetaTrader5 import error: {e}")
            return False

    def connect(self) -> bool:
        if not self._import_mt5():
            return False
        if self._connected:
            return True
        try:
            initialized = self._mt5.initialize()
            if initialized:
                self._connected = True
                self.logger.info("Connected to MetaTrader 5")
                terminal_info = self._mt5.terminal_info()
                if terminal_info:
                    self.logger.info(f"MT5: {terminal_info.name}, Build: {terminal_info.build}")
                return True
            else:
                self.logger.warning(f"MT5 initialize failed: {self._mt5.last_error()}")
                return False
        except Exception as e:
            self.logger.warning(f"MT5 connection error: {e}")
            return False

    def disconnect(self):
        if self._connected and self._mt5:
            try:
                self._mt5.shutdown()
            except:
                pass
            self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_live_price(self, symbol: str = "XAUUSD") -> Optional[dict]:
        if not self.connect():
            return None
        mt5_symbol = symbol
        try:
            tick = self._mt5.symbol_info_tick(mt5_symbol)
            if tick is None:
                alt_symbols = ["XAUUSD.c", "GOLD", "XAUUSDm", "XAUUSD.pro"]
                for alt in alt_symbols:
                    tick = self._mt5.symbol_info_tick(alt)
                    if tick is not None:
                        mt5_symbol = alt
                        break
            if tick is None:
                self.logger.warning(f"Cannot get tick for {symbol}")
                return None
            return {
                "bid": tick.bid,
                "ask": tick.ask,
                "spread": tick.ask - tick.bid,
                "last": (tick.bid + tick.ask) / 2,
                "time": datetime.fromtimestamp(tick.time),
                "symbol": mt5_symbol,
            }
        except Exception as e:
            self.logger.error(f"MT5 get_live_price error: {e}")
            return None

    def _to_mtf(self, timeframe: str):
        mapping = {
            "1m": self._mt5.TIMEFRAME_M1,
            "5m": self._mt5.TIMEFRAME_M5,
            "15m": self._mt5.TIMEFRAME_M15,
            "30m": self._mt5.TIMEFRAME_M30,
            "1H": self._mt5.TIMEFRAME_H1,
            "4H": self._mt5.TIMEFRAME_H4,
            "D": self._mt5.TIMEFRAME_D1,
        }
        return mapping.get(timeframe, self._mt5.TIMEFRAME_M1)

    def get_live_rates(self, symbol: str = "XAUUSD", timeframe: str = "1H", count: int = 100) -> Optional[dict]:
        if not self.connect():
            return None
        mt5_symbol = symbol
        try:
            tick = self._mt5.symbol_info_tick(mt5_symbol)
            if tick is None:
                alt_symbols = ["XAUUSD.c", "GOLD", "XAUUSDm", "XAUUSD.pro"]
                for alt in alt_symbols:
                    tick = self._mt5.symbol_info_tick(alt)
                    if tick is not None:
                        mt5_symbol = alt
                        break
            tf = self._to_mtf(timeframe)
            rates = self._mt5.copy_rates_from_pos(mt5_symbol, tf, 0, count)
            if rates is None:
                return None
            if isinstance(rates, (list, tuple)):
                return {
                    "close": [r.close for r in rates],
                    "high": [r.high for r in rates],
                    "low": [r.low for r in rates],
                    "open": [r.open for r in rates],
                    "volume": [r.tick_volume for r in rates],
                    "time": [datetime.fromtimestamp(r.time) for r in rates],
                    "symbol": mt5_symbol,
                }
            import numpy as np
            if isinstance(rates, np.ndarray):
                return {
                    "close": [float(r["close"]) for r in rates],
                    "high": [float(r["high"]) for r in rates],
                    "low": [float(r["low"]) for r in rates],
                    "open": [float(r["open"]) for r in rates],
                    "volume": [int(r["tick_volume"]) for r in rates],
                    "time": [datetime.fromtimestamp(r["time"]) for r in rates],
                    "symbol": mt5_symbol,
                }
            return None
        except Exception as e:
            self.logger.error(f"MT5 get_live_rates error: {e}")
            return None

    def get_live_data_all_timeframes(self, symbol: str = "XAUUSD") -> dict:
        result = {}
        if not self.connect():
            return result
        mtf_map = {
            "1m": self._mt5.TIMEFRAME_M1,
            "5m": self._mt5.TIMEFRAME_M5,
            "15m": self._mt5.TIMEFRAME_M15,
            "30m": self._mt5.TIMEFRAME_M30,
            "1H": self._mt5.TIMEFRAME_H1,
            "4H": self._mt5.TIMEFRAME_H4,
            "D": self._mt5.TIMEFRAME_D1,
        }
        for tf_name, tf_const in mtf_map.items():
            try:
                rates = self._mt5.copy_rates_from_pos(symbol, tf_const, 0, 100)
                if rates is not None and len(rates) > 0:
                    import numpy as np
                    if isinstance(rates, np.ndarray):
                        result[tf_name] = {
                            "close": [float(r["close"]) for r in rates],
                            "high": [float(r["high"]) for r in rates],
                            "low": [float(r["low"]) for r in rates],
                            "open": [float(r["open"]) for r in rates],
                            "volume": [int(r["tick_volume"]) for r in rates],
                        }
                    else:
                        result[tf_name] = {
                            "close": [r.close for r in rates],
                            "high": [r.high for r in rates],
                            "low": [r.low for r in rates],
                            "open": [r.open for r in rates],
                            "volume": [r.tick_volume for r in rates],
                        }
            except:
                continue
        return result

    def get_live_snapshot(self) -> dict:
        snapshot = {}
        tick = self.get_live_price("XAUUSD")
        snapshot["gold"] = tick["last"] if tick else 0

        tick2 = self.get_live_price("DXY")
        if tick2 is None:
            tick2 = self.get_live_price("USDX")
        snapshot["dxy"] = tick2["last"] if tick2 else 0

        return snapshot


_mt5_instance = None


def get_mt5() -> MT5Provider:
    global _mt5_instance
    if _mt5_instance is None:
        _mt5_instance = MT5Provider()
    return _mt5_instance
