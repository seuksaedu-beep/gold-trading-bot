import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EconomicCalendar:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def get_upcoming_events(self, days: int = 14) -> list[dict]:
        events = [
            {"event": "مؤشر أسعار المستهلكين CPI", "impact": "high", "volatility": "high", "type": "تضخم"},
            {"event": "الوظائف غير الزراعية NFP", "impact": "high", "volatility": "high", "type": "وظائف"},
            {"event": "قرار الفائدة الفيدرالية FOMC", "impact": "high", "volatility": "high", "type": "سياسة نقدية"},
            {"event": "مبيعات التجزئة", "impact": "medium", "volatility": "medium", "type": "استهلاك"},
            {"event": "طلبات البطالة الأسبوعية", "impact": "medium", "volatility": "medium", "type": "وظائف"},
            {"event": "مؤشر مديري المشتريات الصناعي ISM", "impact": "medium", "volatility": "medium", "type": "نشاط اقتصادي"},
            {"event": "الناتج المحلي الإجمالي GDP", "impact": "high", "volatility": "high", "type": "نمو اقتصادي"},
            {"event": "ثقة المستهلك", "impact": "medium", "volatility": "medium", "type": "استهلاك"},
            {"event": "مؤشر أسعار المنتجين PPI", "impact": "high", "volatility": "high", "type": "تضخم"},
            {"event": "تصريحات عضو الفيدرالي", "impact": "medium", "volatility": "medium", "type": "سياسة نقدية"},
        ]
        result = []
        for event in events:
            event_date = datetime.utcnow() + timedelta(
                days=random.randint(0, days), hours=random.randint(0, 23)
            )
            result.append({
                **event,
                "date": event_date.strftime("%Y-%m-%d"),
                "time": event_date.strftime("%H:%M"),
                "forecast": round(random.uniform(-0.5, 0.8), 1) if event["impact"] == "high" else None,
                "previous": round(random.uniform(-0.3, 0.6), 1) if event["impact"] == "high" else None,
            })
        return sorted(result, key=lambda x: x["date"])

    async def get_high_impact_events(self, days: int = 7) -> list[dict]:
        all_events = await self.get_upcoming_events(days)
        return [e for e in all_events if e["impact"] == "high"]
