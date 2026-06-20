import logging
import json
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


FED_SPEAKERS = [
    "Jerome Powell", "John Williams", "Christopher Waller",
    "Michelle Bowman", "Lisa Cook", "Philip Jefferson",
    "Michael Barr", "Raphael Bostic", "Austan Goolsbee",
    "Neel Kashkari", "Lorie Logan", "Mary Daly",
    "Patrick Harker", "Jeffrey Schmid", "Alberto Musalem",
    "Beth Hammack", "Tom Barkin",
]


ECONOMIC_INDICATORS = {
    "cpi": {"name": "مؤشر أسعار المستهلكين CPI", "impact": "high", "description": "يُصدر شهرياً"},
    "core_cpi": {"name": "مؤشر CPI الأساسي", "impact": "high", "description": "يُصدر شهرياً"},
    "nfp": {"name": "الوظائف غير الزراعية NFP", "impact": "high", "description": "يُصدر شهرياً"},
    "unemployment": {"name": "معدل البطالة", "impact": "high", "description": "يُصدر شهرياً"},
    "fomc_rate": {"name": "قرار الفائدة الفيدرالية", "impact": "high", "description": "8 مرات سنوياً"},
    "gdp": {"name": "الناتج المحلي الإجمالي GDP", "impact": "high", "description": "يُصدر فصلياً"},
    "retail_sales": {"name": "مبيعات التجزئة", "impact": "medium", "description": "يُصدر شهرياً"},
    "industrial_production": {"name": "الإنتاج الصناعي", "impact": "medium", "description": "يُصدر شهرياً"},
    "consumer_confidence": {"name": "ثقة المستهلك", "impact": "medium", "description": "يُصدر شهرياً"},
    "jobless_claims": {"name": "طلبات البطالة الأسبوعية", "impact": "medium", "description": "أسبوعياً"},
    "ppi": {"name": "مؤشر أسعار المنتجين PPI", "impact": "high", "description": "يُصدر شهرياً"},
    "durable_goods": {"name": "السلع المعمرة", "impact": "medium", "description": "يُصدر شهرياً"},
}


class FundamentalAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze_fed_policy(
        self, fed_funds_rate: float = 5.5, cpi_yoy: float = 3.1, core_cpi_yoy: float = 3.2
    ) -> dict:
        real_rate = fed_funds_rate - cpi_yoy
        is_hawkish = real_rate > 1.0
        is_dovish = real_rate < 0.5
        if cpi_yoy > 4.0:
            inflation_status = "مرتفع جداً - ضغط تضخمي قوي"
            fed_stance = "hawkish"
        elif cpi_yoy > 2.5:
            inflation_status = "فوق المستهدف - ضغط تضخمي معتدل"
            fed_stance = "moderately_hawkish"
        elif cpi_yoy > 1.5:
            inflation_status = "قريب من المستهدف - مستقر"
            fed_stance = "neutral"
        else:
            inflation_status = "أقل من المستهدف - مخاوف انكماشية"
            fed_stance = "dovish"
        return {
            "fed_funds_rate": fed_funds_rate,
            "cpi_yoy": cpi_yoy,
            "core_cpi_yoy": core_cpi_yoy,
            "real_rate": round(real_rate, 2),
            "inflation_status": inflation_status,
            "fed_stance": fed_stance,
            "is_hawkish": is_hawkish,
            "is_dovish": is_dovish,
            "summary": f"معدل الفائدة {fed_funds_rate}%، التضخم {cpi_yoy}%، المعدل الحقيقي {real_rate:.1f}%. الفيدرالي {'متشدد' if fed_stance in ['hawkish', 'moderately_hawkish'] else 'متساهل' if fed_stance == 'dovish' else 'محايد'}.",
        }

    def analyze_dollar_index(self, dxy_price: float = 104.0) -> dict:
        if dxy_price >= 107:
            strength = "strong_bullish"
            signal = "قوي جداً - الدولار في أعلى مستوياته"
        elif dxy_price >= 104:
            strength = "bullish"
            signal = "قوي - الدولار في اتجاه صاعد"
        elif dxy_price >= 100:
            strength = "neutral"
            signal = "محايد - الدولار ضمن نطاق متوسط"
        elif dxy_price >= 97:
            strength = "bearish"
            signal = "ضعيف - الدولار في اتجاه هابط"
        else:
            strength = "strong_bearish"
            signal = "ضعيف جداً - الدولار في أدنى مستوياته"
        gold_correlation = "negative"
        if strength in ["bullish", "strong_bullish"]:
            gold_outlook = "ضغط هابط على الذهب"
        elif strength in ["bearish", "strong_bearish"]:
            gold_outlook = "دعم صاعد للذهب"
        else:
            gold_outlook = "تأثير محايد على الذهب"
        return {
            "dxy_price": dxy_price,
            "strength": strength,
            "signal": signal,
            "gold_correlation": gold_correlation,
            "gold_outlook": gold_outlook,
        }

    def analyze_bond_yields(
        self, us_10y_yield: float = 4.5, us_2y_yield: float = 4.8
    ) -> dict:
        yield_spread = us_10y_yield - us_2y_yield
        if yield_spread < 0:
            yield_curve = "inverted"
            inversion_depth = abs(yield_spread)
            if inversion_depth > 0.5:
                recession_signal = "قوي - منحنى مقلوب بعمق يشير إلى ركود محتمل"
            else:
                recession_signal = "ضعيف - انعكاس طفيف في المنحنى"
        elif yield_spread < 0.5:
            yield_curve = "flattening"
            recession_signal = "محايد - المنحنى يتسطح"
        else:
            yield_curve = "normal"
            recession_signal = "منحنى طبيعي - لا توجد إشارات ركود"
        gold_impact = "سلبي" if us_10y_yield > 4.5 and yield_curve == "normal" else \
                      "إيجابي" if us_10y_yield < 3.5 else "محايد"
        return {
            "us_10y": us_10y_yield,
            "us_2y": us_2y_yield,
            "spread": round(yield_spread, 3),
            "yield_curve": yield_curve,
            "recession_signal": recession_signal,
            "gold_impact": gold_impact,
        }

    def analyze_vix_volatility(self, vix: float = 15.0) -> dict:
        if vix < 14:
            level = "low"
            signal = "سوق هادئ - ثقة عالية"
            market_state = "هادئ"
            trading_risk = "منخفض"
        elif vix < 20:
            level = "normal"
            signal = "سوق طبيعي - تقلبات معقولة"
            market_state = "طبيعي"
            trading_risk = "متوسط"
        elif vix < 25:
            level = "elevated"
            signal = "تقلبات مرتفعة - حذر"
            market_state = "متقلب"
            trading_risk = "مرتفع"
        elif vix < 35:
            level = "high"
            signal = "تقلبات عالية جداً - خطر"
            market_state = "متقلب جداً"
            trading_risk = "خطير"
        else:
            level = "extreme"
            signal = "تقلبات قصوى - تجنب التداول"
            market_state = "غير مستقر"
            trading_risk = "خطير جداً"
        return {
            "vix": vix,
            "level": level,
            "signal": signal,
            "market_state": market_state,
            "trading_risk": trading_risk,
            "suitable_for_trading": level not in ["extreme", "high"],
        }

    def analyze_oil(self, oil_price: float = 78.0) -> dict:
        if oil_price > 90:
            impact = "ضغط تضخمي - قد يدفع الفيدرالي للتشديد"
            gold_impact = "إيجابي للذهب كتحوط من التضخم"
        elif oil_price > 75:
            impact = "تضخم معتدل - تأثير محايد مع ميل صاعد"
            gold_impact = "محايد إيجابي"
        elif oil_price > 60:
            impact = "مستقر - تأثير محايد"
            gold_impact = "محايد"
        else:
            impact = "انكماشي - قد يدفع الفيدرالي للتسهيل"
            gold_impact = "سلبي للذهب"
        return {
            "oil_price": oil_price,
            "impact": impact,
            "gold_impact": gold_impact,
        }

    def analyze_stock_market(self, sp500: float = 4800.0) -> dict:
        if sp500 > 5000:
            risk_appetite = "high"
            signal = "شهية عالية للمخاطرة - ضغط سلبي على الذهب"
        elif sp500 > 4700:
            risk_appetite = "moderate"
            signal = "شهية معتدلة للمخاطرة - تأثير محايد"
        elif sp500 > 4400:
            risk_appetite = "low"
            signal = "شهية منخفضة للمخاطرة - دعم للذهب كملاذ آمن"
        else:
            risk_appetite = "fear"
            signal = "خوف - إقبال على الذهب كملاذ آمن"
        return {
            "sp500": sp500,
            "risk_appetite": risk_appetite,
            "signal": signal,
        }

    def analyze_sentiment(
        self, long_percent: float = 55.0, short_percent: float = 45.0
    ) -> dict:
        if long_percent > 75:
            sentiment = "bullish_extreme"
            signal = "تفاؤل مفرط - احتمال انعكاس"
            market_sentiment = "إيجابي مفرط"
        elif long_percent > 60:
            sentiment = "bullish"
            signal = "تفاؤل - سوق صاعد"
            market_sentiment = "إيجابي"
        elif long_percent < 25:
            sentiment = "bearish_extreme"
            signal = "تشاؤم مفرط - احتمال انعكاس"
            market_sentiment = "سلبي مفرط"
        elif long_percent < 40:
            sentiment = "bearish"
            signal = "تشاؤم - سوق هابط"
            market_sentiment = "سلبي"
        else:
            sentiment = "neutral"
            signal = "محايد - لا ترجيح"
            market_sentiment = "محايد"
        return {
            "sentiment": sentiment,
            "signal": signal,
            "market_sentiment": market_sentiment,
            "long_percent": long_percent,
            "short_percent": short_percent,
        }

    def full_fundamental_analysis(
        self,
        dxy: float = 104.0,
        vix: float = 15.0,
        oil: float = 78.0,
        sp500: float = 4800.0,
        us10y: float = 4.5,
        us2y: float = 4.8,
        fed_rate: float = 5.5,
        cpi: float = 3.1,
    ) -> dict:
        doll_analysis = self.analyze_dollar_index(dxy)
        vix_analysis = self.analyze_vix_volatility(vix)
        oil_analysis = self.analyze_oil(oil)
        stock_analysis = self.analyze_stock_market(sp500)
        bond_analysis = self.analyze_bond_yields(us10y, us2y)
        fed_analysis = self.analyze_fed_policy(fed_rate, cpi)
        is_suitable = vix_analysis["suitable_for_trading"]
        risk_factors = []
        if not is_suitable:
            risk_factors.append(f"VIX مرتفع ({vix}) - تقلبات خطيرة")
        if doll_analysis["strength"] in ["strong_bullish", "strong_bearish"]:
            risk_factors.append(f"حركة حادة في الدولار ({dxy})")
        if bond_analysis["yield_curve"] == "inverted" and abs(bond_analysis["spread"]) > 0.5:
            risk_factors.append("منحنى العوائد مقلوب بعمق - إشارة ركود")
        if fed_analysis["fed_stance"] in ["hawkish", "moderately_hawkish"] and cpi > 3.5:
            risk_factors.append("سياسة تشديدية مع تضخم مرتفع")
        summary_parts = [
            f"الدولار: {doll_analysis['signal']}",
            f"VIX: {vix_analysis['signal']}",
            f"السندات: {bond_analysis['recession_signal']}",
            f"النفط: {oil_analysis['impact']}",
            f"الأسهم: {stock_analysis['signal']}",
            f"الفيدرالي: {'متشدد' if fed_analysis['fed_stance'] in ['hawkish', 'moderately_hawkish'] else 'متساهل' if fed_analysis['fed_stance'] == 'dovish' else 'محايد'}",
        ]
        return {
            "dollar": doll_analysis,
            "vix": vix_analysis,
            "oil": oil_analysis,
            "stocks": stock_analysis,
            "bonds": bond_analysis,
            "fed": fed_analysis,
            "is_suitable_for_trading": is_suitable,
            "risk_factors": risk_factors,
            "summary": " | ".join(summary_parts),
        }
