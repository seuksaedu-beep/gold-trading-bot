import logging
import random
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

SAMPLE_NEWS_POOL = [
    {"title": "الفيدرالي يبقي على أسعار الفائدة دون تغيير", "impact": "high", "sentiment": "neutral", "relevant": True},
    {"title": "تقرير الوظائف الأمريكي يفوق التوقعات", "impact": "high", "sentiment": "positive_dollar", "relevant": True},
    {"title": "التضخم الأمريكي يتراجع إلى 3.1%", "impact": "high", "sentiment": "negative_dollar", "relevant": True},
    {"title": "تصريحات باول: قد نرفع الفائدة إذا لزم الأمر", "impact": "high", "sentiment": "positive_dollar", "relevant": True},
    {"title": "الطلب على الذهب كملاذ آمن يرتفع", "impact": "medium", "sentiment": "positive_gold", "relevant": True},
    {"title": "مبيعات التجزئة الأمريكية تتراجع", "impact": "medium", "sentiment": "negative_dollar", "relevant": True},
    {"title": "تراجع عوائد السندات الأمريكية مع تزايد التوقعات بخفض الفائدة", "impact": "medium", "sentiment": "positive_gold", "relevant": True},
    {"title": "الاحتياطي الفيدرالي: التضخم لا يزال مرتفعاً", "impact": "high", "sentiment": "positive_dollar", "relevant": True},
    {"title": "صندوق النقد الدولي يخفض توقعات النمو العالمي", "impact": "medium", "sentiment": "positive_gold", "relevant": True},
    {"title": "ارتفاع مؤشر الدولار إلى أعلى مستوى في شهر", "impact": "medium", "sentiment": "positive_dollar", "relevant": True},
]


class NewsCollector:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def get_latest_news(self, count: int = 10) -> list[dict]:
        news_count = min(count, len(SAMPLE_NEWS_POOL))
        selected = random.sample(SAMPLE_NEWS_POOL, news_count)
        return [
            {
                **item,
                "time": (datetime.utcnow() - timedelta(hours=random.randint(0, 24))).isoformat(),
            }
            for item in selected
        ]

    async def get_fed_news(self) -> list[dict]:
        fed_news = [
            n for n in SAMPLE_NEWS_POOL
            if any(w in n["title"] for w in ["الفيدرالي", "باول", "الاحتياطي", "الفائدة"])
        ]
        return fed_news if fed_news else SAMPLE_NEWS_POOL[:3]

    async def analyze_news_impact(self, news_list: list[dict]) -> dict:
        if not news_list:
            return {"overall_impact": "neutral", "dollar_impact": 0, "gold_impact": 0}
        positive_dollar = sum(1 for n in news_list if n.get("sentiment") == "positive_dollar")
        negative_dollar = sum(1 for n in news_list if n.get("sentiment") == "negative_dollar")
        positive_gold = sum(1 for n in news_list if n.get("sentiment") == "positive_gold")
        high_impact = sum(1 for n in news_list if n.get("impact") == "high")
        dollar_score = (positive_dollar - negative_dollar)
        gold_score = positive_gold
        if dollar_score > 0:
            gold_impact = -abs(dollar_score) * 0.5
            dollar_impact_text = "إيجابي للدولار - سلبي للذهب"
        elif dollar_score < 0:
            gold_impact = abs(dollar_score) * 0.5
            dollar_impact_text = "سلبي للدولار - إيجابي للذهب"
        else:
            gold_impact = gold_score * 0.3
            dollar_impact_text = "محايد للدولار"
        if high_impact >= 2:
            volatility_warning = "تحذير: عدة أخبار عالية التأثير - توقع تقلبات حادة"
        elif high_impact >= 1:
            volatility_warning = "تنبيه: يوجد خبر عالي التأثير - توقع حركة سعرية"
        else:
            volatility_warning = "لا توجد أخبار عالية التأثير"
        return {
            "overall_impact": dollar_impact_text,
            "gold_impact": "إيجابي" if gold_impact > 0 else "سلبي" if gold_impact < 0 else "محايد",
            "dollar_score": dollar_score,
            "gold_score": gold_score,
            "high_impact_count": high_impact,
            "volatility_warning": volatility_warning,
            "news_count": len(news_list),
        }

    async def check_upcoming_events(self) -> list[dict]:
        return [
            {"event": "اجتماع الفيدرالي القادم", "date": (datetime.utcnow() + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"), "impact": "high"},
            {"event": "تقرير CPI", "date": (datetime.utcnow() + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d"), "impact": "high"},
            {"event": "تقرير الوظائف NFP", "date": (datetime.utcnow() + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d"), "impact": "high"},
        ]
