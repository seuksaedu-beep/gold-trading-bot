from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional


class SessionDetector:
    SESSION_TIMES = {
        "asian": {"open": 0, "close": 9},
        "london": {"open": 8, "close": 17},
        "new_york": {"open": 13, "close": 22},
        "london_ny_overlap": {"open": 13, "close": 17},
        "asia_london_overlap": {"open": 8, "close": 9},
    }

    SESSION_VOLATILITY = {
        "asian": "low",
        "london": "high",
        "new_york": "high",
        "london_ny_overlap": "extreme",
        "asia_london_overlap": "medium",
    }

    SESSION_QUALITY = {
        "asian": "poor",
        "london": "good",
        "new_york": "good",
        "london_ny_overlap": "excellent",
        "asia_london_overlap": "fair",
    }

    SESSION_NAMES = {
        "asian": "Asian (Tokyo)",
        "london": "London",
        "new_york": "New York",
        "london_ny_overlap": "London/NY Overlap",
        "asia_london_overlap": "Asia/London Overlap",
    }

    VOLATILITY_XAU_MULTIPLIER = {
        "low": 1.0,
        "medium": 1.5,
        "high": 2.5,
        "extreme": 3.5,
    }

    def __init__(self, now: Optional[datetime] = None):
        self._now = (now if now is not None else datetime.now(timezone.utc)).replace(
            second=0, microsecond=0
        )
        self._current_hour = self._now.hour
        self._current_minute = self._now.minute
        self._time_decimal = self._current_hour + self._current_minute / 60.0

    def _is_in_session(self, open_hour: int, close_hour: int) -> bool:
        if open_hour <= close_hour:
            return open_hour <= self._time_decimal < close_hour
        return self._time_decimal >= open_hour or self._time_decimal < close_hour

    def get_current_session(self) -> dict:
        priority_order = ["asia_london_overlap", "london_ny_overlap", "asian", "london", "new_york"]

        active_sessions = []
        for key in priority_order:
            times = self.SESSION_TIMES[key]
            if self._is_in_session(times["open"], times["close"]):
                active_sessions.append(key)

        session_key = active_sessions[0] if active_sessions else None

        if session_key is None:
            return {
                "session": None,
                "session_name": "Closed / No Active Session",
                "open_utc": None,
                "close_utc": None,
                "is_major": False,
                "volatility": "none",
                "quality": "none",
                "time_remaining_minutes": 0,
                "fraction_elapsed": 1.0,
                "is_fresh_start": False,
                "is_near_end": False,
                "sub_sessions": [],
            }

        times = self.SESSION_TIMES[session_key]
        open_utc = self._now.replace(hour=times["open"], minute=0, second=0, microsecond=0)
        close_utc = self._now.replace(hour=times["close"], minute=0, second=0, microsecond=0)

        session_duration_minutes = (times["close"] - times["open"]) * 60
        elapsed_minutes = int(self._time_decimal * 60) - times["open"] * 60
        fraction_elapsed = elapsed_minutes / session_duration_minutes if session_duration_minutes > 0 else 0.0

        time_remaining = session_duration_minutes - elapsed_minutes

        is_fresh = fraction_elapsed < 0.15
        is_near_end = fraction_elapsed > 0.85

        sub_sessions = []
        for key in active_sessions:
            sub_sessions.append({
                "key": key,
                "name": self.SESSION_NAMES.get(key, key),
                "volatility": self.SESSION_VOLATILITY.get(key, "medium"),
            })

        return {
            "session": session_key,
            "session_name": self.SESSION_NAMES.get(session_key, session_key),
            "open_utc": open_utc.isoformat(),
            "close_utc": close_utc.isoformat(),
            "is_major": session_key in ("london", "new_york", "london_ny_overlap"),
            "volatility": self.SESSION_VOLATILITY.get(session_key, "medium"),
            "quality": self.SESSION_QUALITY.get(session_key, "poor"),
            "time_remaining_minutes": max(0, time_remaining),
            "fraction_elapsed": round(fraction_elapsed, 4),
            "is_fresh_start": is_fresh,
            "is_near_end": is_near_end,
            "sub_sessions": sub_sessions,
        }

    def is_major_session(self) -> bool:
        info = self.get_current_session()
        return info["is_major"]

    def get_session_volatility(self, session: str) -> str:
        return self.SESSION_VOLATILITY.get(session, "medium")

    def get_session_quality(self) -> str:
        info = self.get_current_session()
        return info["quality"]

    def get_session_time_remaining(self) -> int:
        info = self.get_current_session()
        return info["time_remaining_minutes"]

    def get_previous_day_high_low(self, prices: List[Dict]) -> Dict:
        if not prices:
            return {"high": None, "low": None, "open": None, "close": None}

        target_date = (self._now - timedelta(days=1)).date()
        prev_day_prices = [
            p for p in prices
            if isinstance(p.get("time"), datetime) and p["time"].date() == target_date
        ]

        if not prev_day_prices:
            latest_date = max(
                p["time"].date() for p in prices if isinstance(p.get("time"), datetime)
            )
            prev_day_prices = [
                p for p in prices
                if isinstance(p.get("time"), datetime) and p["time"].date() == latest_date
            ]

        if not prev_day_prices:
            return {"high": None, "low": None, "open": None, "close": None}

        high = max(p["high"] for p in prev_day_prices if "high" in p)
        low = min(p["low"] for p in prev_day_prices if "low" in p)
        open_price = prev_day_prices[0].get("open") or prev_day_prices[0].get("close")
        close_price = prev_day_prices[-1].get("close") or prev_day_prices[-1].get("open")

        pivot = (high + low + close_price) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)

        return {
            "high": high,
            "low": low,
            "open": open_price,
            "close": close_price,
            "pivot": round(pivot, 5),
            "support_1": round(s1, 5),
            "support_2": round(s2, 5),
            "resistance_1": round(r1, 5),
            "resistance_2": round(r2, 5),
            "range": round(high - low, 5),
            "date": str(target_date),
        }

    def get_session_volatility_profile(self) -> Dict:
        info = self.get_current_session()
        base = info["volatility"]
        multiplier = self.VOLATILITY_XAU_MULTIPLIER.get(base, 1.0)
        return {
            "session": info["session"],
            "base_volatility": base,
            "xau_multiplier": multiplier,
            "expected_move_pips": self._estimate_xau_pips(base, info["fraction_elapsed"]),
        }

    def _estimate_xau_pips(self, vol: str, fraction: float) -> float:
        remaining = 1.0 - fraction
        base_pips = {"low": 5, "medium": 12, "high": 20, "extreme": 35}
        return round(base_pips.get(vol, 10) * remaining, 1)

    def next_session_start(self) -> Optional[Dict]:
        order = ["asian", "asia_london_overlap", "london", "london_ny_overlap", "new_york"]
        current = self.get_current_session()
        current_key = current["session"]

        if current_key is None:
            for key in order:
                times = self.SESSION_TIMES[key]
                start = self._now.replace(hour=times["open"], minute=0, second=0, microsecond=0)
                if start > self._now:
                    return {
                        "session": key,
                        "name": self.SESSION_NAMES[key],
                        "start_utc": start.isoformat(),
                        "minutes_until": int((start - self._now).total_seconds() / 60),
                    }
            return None

        current_idx = (
            order.index(current_key) if current_key in order else len(order) - 1
        )

        for key in order[current_idx + 1:]:
            times = self.SESSION_TIMES[key]
            start = self._now.replace(hour=times["open"], minute=0, second=0, microsecond=0)
            if start > self._now:
                return {
                    "session": key,
                    "name": self.SESSION_NAMES[key],
                    "start_utc": start.isoformat(),
                    "minutes_until": int((start - self._now).total_seconds() / 60),
                }

        first_key = order[0]
        times = self.SESSION_TIMES[first_key]
        tomorrow = self._now + timedelta(days=1)
        start = tomorrow.replace(hour=times["open"], minute=0, second=0, microsecond=0)
        return {
            "session": first_key,
            "name": self.SESSION_NAMES[first_key],
            "start_utc": start.isoformat(),
            "minutes_until": int((start - self._now).total_seconds() / 60),
        }

    def get_session_summary(self, prices: Optional[List[Dict]] = None) -> Dict:
        summary = {
            "current_time_utc": self._now.isoformat(),
            "current_session": self.get_current_session(),
            "next_session": self.next_session_start(),
            "volatility_profile": self.get_session_volatility_profile(),
        }

        if prices:
            summary["previous_day"] = self.get_previous_day_high_low(prices)

        return summary
