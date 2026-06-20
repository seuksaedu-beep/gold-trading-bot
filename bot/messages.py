from datetime import datetime


WELCOME_MESSAGE = """
*مرحباً بك في Gold AI Trader* 🤖

*بوت تداول ذهب احترافي | XAUUSD*

نظام تحليل مؤسسي - إشارات عالية الجودة فقط (1-3 يومياً)
مُحسَّن لحماية رأس المال الصغير (50 دولار)

*مبادئ التداول:*
• جودة قبل كمية - لا ندخل إلا الفرص العالية الثقة
• حماية رأس المال هي الأولوية المطلقة
• إدارة مخاطر صارمة تناسب حساب $50

*الأوامر المتاحة:*
/price - سعر الذهب والمؤشرات الآن
/signal - توصية ذهب فورية
/analysis - تحليل سوق شامل
/stats - إحصائيات الأداء
/trades - آخر الصفقات
/settings - الإعدادات
/help - المساعدة الكاملة

*جاهز للتدايل الذكي*
"""


def format_current_price(data: dict) -> str:
    source_map = {
        "mt5": "MT5 مباشر",
        "real": "API مباشر",
        "api": "API مباشر",
        "mixed": "مصادر متعددة",
        "simulated": "تقديري",
    }
    source = source_map.get(data.get("data_source", "api"), "API")

    session = data.get("session", "")
    session_text = ""
    if session:
        session_names = {"asia": "آسيوية", "london": "لندن", "new_york": "نيويورك", "overlap": "تقاطع لندن ونيويورك"}
        session_text = f"الجلسة: {session_names.get(session.lower(), session)}"

    spread = data.get("spread")
    spread_text = f"السبريد: {spread}" if spread is not None else ""

    return f"""*سعر الذهب XAUUSD والمؤشرات*

🥇 الذهب: `{data.get('gold', 'N/A')}`
💵 مؤشر الدولار DXY: `{data.get('dxy', 'N/A')}`
📈 VIX: `{data.get('vix', 'N/A')}`
🛢 النفط الخام: `{data.get('oil', 'N/A')}`
🏢 S&P 500: `{data.get('sp500', 'N/A')}`
📜 عوائد 10 سنوات: `{data.get('us10y', 'N/A')}%`

{f'🌍 {session_text}' if session_text else ''}{f' | {spread_text}' if spread_text else ''}
📡 المصدر: {source}
🕐 آخر تحديث: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"""


def format_trade_signal(trade_data: dict) -> str:
    trade = trade_data.get("trade", trade_data)
    is_buy = trade.get("trade_type", "").lower() == "buy"
    direction_emoji = "🟢" if is_buy else "🔴"
    direction_text = "شراء" if is_buy else "بيع"

    entry = trade.get("entry_price", 0)
    sl = trade.get("stop_loss", 0)
    tp1 = trade.get("take_profit_1", 0)
    tp2 = trade.get("take_profit_2", 0)
    tp3 = trade.get("take_profit_3", 0)

    risk = abs(entry - sl)
    rr1 = f"1:{abs(tp1 - entry) / risk:.2f}" if risk > 0 else "N/A"
    rr2 = f"1:{abs(tp2 - entry) / risk:.2f}" if risk > 0 else "N/A"
    rr3 = f"1:{abs(tp3 - entry) / risk:.2f}" if risk > 0 else "N/A"

    style = trade.get("trading_style_name", trade.get("trading_style", "عادية"))
    style_map = {"normal": "عادية", "scalp": "Quick Scalp", "wait": "انتظار"}
    style_text = style_map.get(style.lower(), style) if isinstance(style, str) else style

    confidence = trade.get("confidence", 0)
    capital = trade.get("capital", trade_data.get("capital", 50))
    risk_amount = trade.get("capital_at_risk", trade.get("risk_amount", 0))
    lot = trade.get("lot_size", trade.get("lot", 0.01))
    daily_trades = trade.get("daily_trades_count", trade_data.get("daily_trades", 0))
    max_trades = trade.get("max_trades_per_day", trade_data.get("max_trades_per_day", 3))
    can_handle = "نعم ✅" if risk_amount <= capital * 0.02 else "لا ❌"

    compatible_tfs = trade.get("compatible_timeframes", trade.get("timeframes", []))
    if isinstance(compatible_tfs, list):
        tf_text = "، ".join(compatible_tfs) if compatible_tfs else "جميع الفريمات متوافقة"
    else:
        tf_text = str(compatible_tfs)

    entry_reason = trade.get("entry_reason", trade.get("reason", ""))
    liquidity = trade.get("liquidity_analysis", trade.get("liquidity", ""))
    management = trade.get("trade_management", trade.get("management", ""))
    risk_note = trade.get("risk_note", trade.get("risk_level", ""))
    account_risk = f"{risk_amount} دولار" if risk_amount else ""

    return f"""*Gold XAUUSD Signal* 📊

{direction_emoji} *النوع:* {direction_text}
📋 *نوع الصفقة:* {style_text}
💰 *السعر الحالي:* `{trade.get('current_price', trade.get('price', ''))}`
🎯 *منطقة الدخول:* `{entry}`
🛑 *وقف الخسارة:* `{sl}`
━━━━━━━━━━━━━━━━
🥇 *الهدف 1:* `{tp1}` (RR: {rr1})
🥇 *الهدف 2:* `{tp2}` (RR: {rr2})
🥇 *الهدف 3:* `{tp3}` (RR: {rr3})
━━━━━━━━━━━━━━━━
📊 *نسبة الثقة:* {confidence}%
📐 *الفريمات المتوافقة:* {tf_text}
💡 *سبب الدخول:*
{entry_reason}

🌊 *منطقة السيولة:* {liquidity}
📈 *العائد مقابل المخاطرة:* {rr3}
💵 *رأس المال:* ${capital:.2f}
⚠️ *المخاطرة:* ${risk_amount:.2f}{f' ({account_risk})' if account_risk else ''}
📦 *اللوت المقترح:* {lot}
🔍 *هل الحساب يتحمل الصفقة:* {can_handle}
📅 *عدد صفقات اليوم:* {daily_trades}/{max_trades}

📌 *إدارة الصفقة:*
{management}

⚠️ *ملاحظة المخاطر:*
{risk_note}"""


def format_no_trade(data: dict, current_price: float) -> str:
    reasons = data.get("reason", data.get("reasons", "لم تتوفر شروط الدخول المناسبة"))
    if isinstance(reasons, list):
        reason_text = "\n".join(f"• {r}" for r in reasons)
    else:
        reason_text = reasons

    confidence = data.get("confidence")
    min_req = data.get("min_required", data.get("min_confidence", 85))
    direction = data.get("direction", data.get("trend", "محايد"))
    direction_map = {"buy": "صاعد 📈", "sell": "هابط 📉", "neutral": "محايد ⚖️"}
    dir_text = direction_map.get(direction.lower(), direction) if isinstance(direction, str) else str(direction)

    msg = f"""*تحليل XAUUSD - لا توجد توصية* 📊

💰 *السعر الحالي:* `{current_price}`
❌ *لا توجد صفقة مناسبة الآن*

*الأسباب:*
{reason_text}
"""
    if confidence is not None:
        msg += f"\n📊 *نسبة الثقة:* {confidence}%"
    if min_req:
        msg += f"\n📊 *الحد الأدنى المطلوب:* {min_req}%"
    msg += f"\n📈 *اتجاه السوق:* {dir_text}"

    tech_trend = data.get("technical_trend", data.get("trend_analysis"))
    if tech_trend:
        msg += f"\n📉 *التحليل الفني:* {tech_trend}"

    fundamental = data.get("fundamental_summary", data.get("fundamental"))
    if fundamental:
        msg += f"\n\n*التحليل الأساسي:*\n{fundamental}"

    ai_reasoning = data.get("ai_reasoning", data.get("ai_summary"))
    if ai_reasoning:
        msg += f"\n\n*تحليل الذكاء الاصطناعي:*\n{ai_reasoning}"

    news = data.get("news_impact")
    if news:
        impact = news.get("overall_impact", "محايد")
        msg += f"\n\n*تأثير الأخبار:* {impact}"
        if news.get("volatility_warning"):
            msg += f"\n⚠️ {news['volatility_warning']}"

    return msg


def format_market_analysis(analysis: dict) -> str:
    if "error" in analysis:
        return f"*خطأ في التحليل:* {analysis['error']}"

    msg = f"""*تحليل سوق XAUUSD الشامل* 📊
{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC

*المؤشرات الرئيسية:*
🥇 الذهب: `${analysis.get('gold_price', analysis.get('gold', 'N/A'))}`
💵 DXY: `{analysis.get('dxy_price', analysis.get('dxy', 'N/A'))}`
📈 VIX: `{analysis.get('vix_price', analysis.get('vix', 'N/A'))}`
🛢 النفط: `${analysis.get('oil_price', analysis.get('oil', 'N/A'))}`
🏢 S&P 500: `{analysis.get('sp500_price', analysis.get('sp500', 'N/A'))}`
📜 عوائد 10Y: `{analysis.get('us_bond_yield', analysis.get('us10y', 'N/A'))}%`
━━━━━━━━━━━━━━━━
*اتجاه السوق:* {analysis.get('trend', analysis.get('bias', 'محايد'))}
*التقلب:* {analysis.get('volatility', 'متوسط')}
━━━━━━━━━━━━━━━━"""

    fundamental = analysis.get("fundamental", analysis.get("fundamentals", {}))
    if fundamental:
        dollar = fundamental.get("dollar", {})
        vix = fundamental.get("vix", {})
        bonds = fundamental.get("bonds", {})
        stocks = fundamental.get("stocks", {})
        oil = fundamental.get("oil", {})
        fed = fundamental.get("fed", {})

        fed_stance = fed.get("fed_stance", "محايد")
        if isinstance(fed_stance, str):
            if fed_stance in ("hawkish", "moderately_hawkish"):
                fed_emoji = "🔥 متشدد"
            elif fed_stance in ("dovish", "moderately_dovish"):
                fed_emoji = "❄️ متساهل"
            else:
                fed_emoji = "⚖️ محايد"
        else:
            fed_emoji = "⚖️ محايد"

        msg += f"""
*التحليل الأساسي:*
💵 الدولار: {dollar.get('signal', 'N/A')}
📈 VIX: {vix.get('signal', 'N/A')} | المخاطرة: {vix.get('trading_risk', 'N/A')}
📜 السندات: {bonds.get('recession_signal', 'N/A')}
🏢 الأسهم: {stocks.get('signal', 'N/A')}
🛢 النفط: {oil.get('gold_impact', 'N/A')}
🏛 الفيدرالي: {fed_emoji} ({fed.get('fed_funds_rate', 'N/A')}%)"""

    tf_summary = analysis.get("timeframe_summary", {})
    if tf_summary:
        msg += "\n\n*تحليل الفريمات:*"
        for tf, tf_data in tf_summary.items():
            trend = tf_data.get("trend", "-")
            rsi = tf_data.get("rsi", "-")
            emoji = "🟢" if "bullish" in str(trend).lower() else "🔴" if "bearish" in str(trend).lower() else "⚪"
            msg += f"\n{emoji} {tf}: {trend} | RSI: {rsi}"

    sms = analysis.get("sms_support", {})
    if sms:
        ds = sms.get("demand_supply", {})
        msg += f"""
\n*Smart Money:*
• BOS: {sms.get('bos_choch_4h', {}).get('bos', '-')} | CHOCH: {sms.get('bos_choch_4h', {}).get('choch', '-')}
• مناطق الطلب: {len(ds.get('demand_zones', []))} | العرض: {len(ds.get('supply_zones', []))}
• كسح سيولة: {len(sms.get('liquidity_sweeps', []))} | FVG: {len(sms.get('fvgs', []))}"""

    confidence_4h = analysis.get("confidence_4h")
    confidence_d = analysis.get("confidence_daily")
    if confidence_4h:
        msg += f"\n\n*الثقة 4H:* {confidence_4h}%"
    if confidence_d:
        msg += f"\n*الثقة Daily:* {confidence_d}%"

    news = analysis.get("news_impact")
    if news:
        msg += f"\n\n*الأخبار:* {news.get('overall_impact', 'N/A')}"
        if news.get("volatility_warning"):
            msg += f"\n⚠️ {news['volatility_warning']}"

    events = analysis.get("upcoming_events", [])
    if events:
        msg += "\n\n*الأحداث القادمة:*"
        for e in events[:5]:
            msg += f"\n• {e.get('event', '')} - {e.get('date', '')}"

    ai_summary = analysis.get("ai_summary", analysis.get("summary"))
    if ai_summary:
        msg += f"\n\n*الملخص:*\n{ai_summary}"

    return msg


def format_settings(settings_obj, alerts_enabled: bool = True) -> str:
    status = "🟢 نشط" if settings_obj.is_active else "🔴 متوقف"
    pause = "⏸ متوقف مؤقتاً" if settings_obj.is_paused else "▶️ يعمل"
    alert_status = "🔔 مفعلة" if alerts_enabled else "🔕 متوقفة"

    return f"""*الإعدادات الحالية* ⚙️

• الحالة: {status} ({pause})
• رأس المال: `${settings_obj.capital:.2f}`
• المخاطرة: {settings_obj.risk_percent}%
• أقل نسبة ثقة: {settings_obj.min_confidence}%
• أقصى رافعة: 1:{settings_obj.max_leverage}
• نوع التداول: {settings_obj.trading_type}
• أقصى صفقات/يوم: {settings_obj.max_trades_per_day}
• حد الخسائر المتتالية: {settings_obj.consecutive_losses}
• الإشعارات: {alert_status}"""


def format_statistics(stats: dict) -> str:
    total = stats.get("total", stats.get("total_trades", 0))
    wins = stats.get("wins", stats.get("winning_trades", 0))
    losses = stats.get("losses", stats.get("losing_trades", 0))
    pending = stats.get("pending", stats.get("pending_trades", 0))
    win_rate = stats.get("win_rate", 0)
    total_pnl = stats.get("total_pnl", stats.get("pnl", 0))
    best_tf = stats.get("best_timeframe", stats.get("best_tf", "-"))
    best_session = stats.get("best_session", "-")
    consecutive_losses = stats.get("consecutive_losses", stats.get("max_consecutive_losses", 0))
    max_dd = stats.get("max_drawdown", stats.get("drawdown", 0))
    avg_rr = stats.get("avg_risk_reward", stats.get("avg_rr", 0))
    profit_factor = stats.get("profit_factor", stats.get("pf", 0))

    return f"""*إحصائيات التداول* 📊

• إجمالي الصفقات: {total}
• الرابحة: {wins}
• الخاسرة: {losses}
• المعلقة: {pending}
• نسبة الربح: {win_rate}%
• إجمالي الربح/الخسارة: `${total_pnl:,.2f}`
• أفضل فريم: {best_tf}
• أفضل جلسة: {best_session}
• الخسائر المتتالية: {consecutive_losses}
• أقصى سحوب: {max_dd}%
• متوسط RR: {avg_rr}
• عامل الربح: {profit_factor}"""


def format_recent_trades(trades: list) -> str:
    if not trades:
        return "*آخر الصفقات*\n\nلا توجد صفقات حتى الآن."

    msg = "*آخر الصفقات* 📜\n\n"
    for t in trades[:10]:
        if hasattr(t, "result"):
            result = t.result
        elif isinstance(t, dict):
            result = t.get("result")
        else:
            result = None

        if hasattr(t, "trade_type"):
            trade_type = t.trade_type
        elif isinstance(t, dict):
            trade_type = t.get("trade_type")
        else:
            trade_type = None

        if hasattr(t, "entry_price"):
            entry_price = t.entry_price
        elif isinstance(t, dict):
            entry_price = t.get("entry_price")
        else:
            entry_price = 0

        if hasattr(t, "confidence"):
            confidence = t.confidence
        elif isinstance(t, dict):
            confidence = t.get("confidence")
        else:
            confidence = 0

        if hasattr(t, "pnl"):
            pnl = t.pnl
        elif isinstance(t, dict):
            pnl = t.get("pnl")
        else:
            pnl = 0

        status_emoji = "✅" if result == "win" else "❌" if result == "loss" else "⏳"

        if result == "win":
            pnl_str = f"+${pnl:.2f}" if pnl else "N/A"
        elif result == "loss":
            pnl_str = f"-${abs(pnl):.2f}" if pnl else "N/A"
        else:
            pnl_str = f"${pnl:.2f}" if pnl else "معلقة"

        direction = "شراء 🟢" if trade_type == "buy" else "بيع 🔴"
        msg += f"{status_emoji} {direction} | الدخول: {entry_price} | الثقة: {confidence}% | {pnl_str}\n"

    return msg


def format_backtest_result(result) -> str:
    start = result.start_date.strftime('%Y-%m-%d') if hasattr(result, 'start_date') else result.get('start_date', 'N/A')
    end = result.end_date.strftime('%Y-%m-%d') if hasattr(result, 'end_date') else result.get('end_date', 'N/A')
    total = result.total_trades if hasattr(result, 'total_trades') else result.get('total_trades', 0)
    wins = result.winning_trades if hasattr(result, 'winning_trades') else result.get('winning_trades', 0)
    losses = result.losing_trades if hasattr(result, 'losing_trades') else result.get('losing_trades', 0)
    win_rate = result.win_rate if hasattr(result, 'win_rate') else result.get('win_rate', 0)
    pnl = result.total_pnl if hasattr(result, 'total_pnl') else result.get('total_pnl', 0)
    dd = result.max_drawdown if hasattr(result, 'max_drawdown') else result.get('max_drawdown', 0)
    avg_conf = result.avg_confidence if hasattr(result, 'avg_confidence') else result.get('avg_confidence', 0)
    profit_factor = getattr(result, 'profit_factor', result.get('profit_factor', 0)) if hasattr(result, 'profit_factor') else result.get('profit_factor', 0)

    return f"""*نتيجة الاختبار الخلفي* 📊

• الفترة: {start} → {end}
• إجمالي الصفقات: {total}
• الرابحة: {wins}
• الخاسرة: {losses}
• نسبة الربح: {win_rate}%
• إجمالي الربح: `${pnl:,.2f}`
• أقصى سحوب: {dd}%
• متوسط الثقة: {avg_conf}%
• عامل الربح: {profit_factor}"""


HELP_MESSAGE = """
*مساعدة Gold AI Trader* 🤖

*بوت تداول ذهب احترافي* - XAUUSD
إشارات عالية الجودة (1-3 يومياً) | محسّن لحساب $50

*الأوامر:*
/start - تشغيل البوت
/price - سعر الذهب والمؤشرات الحية
/signal - توصية تداول فورية
/analysis - تحليل سوق شامل
/stats - إحصائيات الأداء
/trades - آخر الصفقات
/settings - الإعدادات والتعديل
/risk - تقرير إدارة المخاطر
/backtest - تشغيل اختبار خلفي
/help - هذه المساعدة

*استراتيجية التداول:*
• تحليل متعدد الفريمات (1m → Daily)
• Smart Money Concepts (BOS, CHOCH, FVG, السيولة)
• تأكيد من المؤشرات (RSI, MACD, BB, Volume Profile)
• تصفية أساسية (DXY, VIX, السندات, النفط, الفيدرالي)
• نظام ثقة صارم (الحد الأدنى 85%)

*إدارة المخاطز لحساب $50:*
• المخاطرة القصوى: 1-2% لكل صفقة ($0.50-$1)
• الوقف الخسارة إلزامي في كل صفقة
• حد أقصى صفقتين خاسرتين متتاليتين = توقف إلزامي
• الحد الأقصى: 3 صفقات يومياً
• لا تداول أثناء الأخبار عالية التأثير

*أنواع الصفقات:*
• عادية - فرص قياسية عالية الثقة
• Quick Scalp - فرص سريعة 1m/5m (خبرة مطلوبة)
• انتظار - فرص معلقة تتطلب مراقبة

*تنبيه:* التداول في الذهب ينطوي على مخاطر عالية. ليس هناك تداول مضمون 100%."""


def format_alert_notification(trade: dict, timeframe: str) -> str:
    is_buy = trade.get("trade_type", "").lower() == "buy"
    direction_emoji = "🟢" if is_buy else "🔴"
    direction_text = "شراء" if is_buy else "بيع"

    tf_names = {"1m": "1د", "5m": "5د", "15m": "15د", "30m": "30د", "1H": "1س", "4H": "4س", "D": "يومي"}
    tf_name = tf_names.get(timeframe, timeframe)

    confidence = trade.get("confidence", trade.get("confidence_level", "N/A"))
    entry = trade.get("entry_price", trade.get("price", 0))
    sl = trade.get("stop_loss", 0)
    tp1 = trade.get("take_profit_1", trade.get("tp1", 0))
    risk_level = trade.get("risk_level", trade.get("risk", "متوسط"))

    return f"""*تنبيه - فرصة تداول جديدة* 🚨

{direction_emoji} {direction_text} XAUUSD ({tf_name})
💰 السعر: {entry}
🎯 الثقة: {confidence}%

🛑 وقف: {sl} | 🥇 هدف: {tp1}
⚠️ المخاطرة: {risk_level}"""


def format_scalp_signal_detailed(trade: dict, analysis: dict) -> str:
    is_buy = trade.get("trade_type", "").lower() == "buy"
    direction_emoji = "🟢" if is_buy else "🔴"
    direction_text = "شراء" if is_buy else "بيع"

    style = trade.get("trading_style_name", trade.get("trading_style", "Quick Scalp"))
    tf = trade.get("timeframe", trade.get("tf", "5m"))
    entry = trade.get("entry_price", trade.get("price", 0))
    sl = trade.get("stop_loss", 0)
    tp1 = trade.get("take_profit_1", trade.get("tp1", 0))
    tp2 = trade.get("take_profit_2", trade.get("tp2", 0))
    tp3 = trade.get("take_profit_3", trade.get("tp3", 0))

    risk = abs(entry - sl)
    rr1 = f"1:{abs(tp1 - entry) / risk:.2f}" if risk > 0 else "N/A"
    rr2 = f"1:{abs(tp2 - entry) / risk:.2f}" if risk > 0 else "N/A"
    rr3 = f"1:{abs(tp3 - entry) / risk:.2f}" if risk > 0 else "N/A"

    confidence = trade.get("confidence", trade.get("confidence_level", 0))
    lot = trade.get("lot_size", trade.get("lot", 0.01))
    risk_amount = trade.get("capital_at_risk", trade.get("risk_amount", 0))

    tf_analysis = analysis.get("timeframe_summary", {})
    m1 = tf_analysis.get("1m", {})
    m5 = tf_analysis.get("5m", {})
    m15 = tf_analysis.get("15m", {})

    m1_trend = m1.get("trend", "-")
    m1_rsi = m1.get("rsi", "-")
    m5_trend = m5.get("trend", "-")
    m5_rsi = m5.get("rsi", "-")
    m15_trend = m15.get("trend", "-")
    m15_rsi = m15.get("rsi", "-")

    entry_reason = trade.get("entry_reason", trade.get("reason", ""))
    liquidity = trade.get("liquidity_analysis", trade.get("liquidity", ""))
    management = trade.get("trade_management", trade.get("management", ""))
    risk_note = trade.get("risk_note", trade.get("risk_level", ""))

    session = analysis.get("session", "")
    session_names = {"asia": "آسيوية", "london": "لندن", "new_york": "نيويورك", "overlap": "تقاطع"}
    session_text = session_names.get(session.lower(), session) if session else "غير محددة"

    return f"""*Gold XAUUSD | {style}* ⚡

{direction_emoji} *النوع:* {direction_text} | *الفريم:* {tf}
━━━━━━━━━━━━━━━━
💰 *السعر الحالي:* `{trade.get('current_price', trade.get('price', ''))}`
🎯 *منطقة الدخول:* `{entry}`
🛑 *وقف الخسارة:* `{sl}`
━━━━━━━━━━━━━━━━
🥇 *الهدف 1:* `{tp1}` (RR: {rr1})
🥇 *الهدف 2:* `{tp2}` (RR: {rr2})
🥇 *الهدف 3:* `{tp3}` (RR: {rr3})
━━━━━━━━━━━━━━━━
📊 *نسبة الثقة:* {confidence}%
🌍 *الجلسة:* {session_text}

*تحليل الفريمات:*
⚪ 1m: {m1_trend} | RSI: {m1_rsi}
⚪ 5m: {m5_trend} | RSI: {m5_rsi}
⚪ 15m: {m15_trend} | RSI: {m15_rsi}

*سبب الدخول:*
{entry_reason}

*السيولة:* {liquidity}
━━━━━━━━━━━━━━━━
💰 *رأس المال:* ${trade.get('capital', 50):.2f}
⚠️ *المخاطرة:* ${risk_amount:.2f}
📦 *اللوت:* {lot}

*إدارة الصفقة:*
{management}

*ملاحظة المخاطرة:*
{risk_note}

⏳ *مدة متوقعة:* {trade.get('expected_duration', 'قصيرة (دقائق)')}
⚠️ سكالبينج سريع - يرصد السوق لحظة بلحظة"""


def format_entry_zone(entry_zone: dict) -> str:
    direction = entry_zone.get("direction", "")
    direction_text = "شراء 🟢" if direction == "buy" else "بيع 🔴"
    zone_high = entry_zone.get("zone_high", entry_zone.get("high", 0))
    zone_low = entry_zone.get("zone_low", entry_zone.get("low", 0))
    current_price = entry_zone.get("current_price", entry_zone.get("price", 0))
    confidence = entry_zone.get("confidence", entry_zone.get("confidence_level", 0))
    reason = entry_zone.get("reason", entry_zone.get("entry_reason", ""))
    tf = entry_zone.get("timeframe", entry_zone.get("tf", ""))
    sl = entry_zone.get("stop_loss", entry_zone.get("sl", 0))
    tp1 = entry_zone.get("take_profit_1", entry_zone.get("tp1", 0))
    tp2 = entry_zone.get("take_profit_2", entry_zone.get("tp2", 0))

    status = entry_zone.get("status", "بانتظار")
    status_text = "بانتظار الوصول إلى المنطقة ⏳" if status == "waiting" else "نشطة" if status == "active" else status

    return f"""*منطقة دخول - XAUUSD* 🎯

{direction_text}
{status_text}

*المنطقة:* `{zone_low} - {zone_high}`
💰 *السعر الحالي:* `{current_price}`
📐 *الفريم:* {tf}
📊 *الثقة:* {confidence}%

🛑 *وقف:* `{sl}`
🥇 *هدف 1:* `{tp1}`
🥇 *هدف 2:* `{tp2}`

*السبب:*
{reason}"""


def format_missed_entry(direction: str, current_price: float, entry_zone: dict) -> str:
    direction_text = "شراء 🟢" if direction == "buy" else "بيع 🔴"
    zone_high = entry_zone.get("zone_high", entry_zone.get("high", 0))
    zone_low = entry_zone.get("zone_low", entry_zone.get("low", 0))

    return f"""*فاتتك منطقة الدخول* ⏰

{direction_text} XAUUSD

*كانت منطقة الدخول:* `{zone_low} - {zone_high}`
💰 *السعر الحالي:* `{current_price}`

تحرك السوق بسرعة ولم تصل إلى المنطقة المحددة.
⚡ استخدم /signal للحصول على التوصية التالية."""


def format_risk_report(report: str, filters: dict) -> str:
    max_risk = filters.get("max_risk_percent", filters.get("risk_percent", 2))
    min_confidence = filters.get("min_confidence", 85)
    max_daily = filters.get("max_trades_per_day", 3)
    max_consecutive = filters.get("consecutive_losses", 2)

    return f"""*تقرير إدارة المخاطر* ⚠️

*إعدادات المخاطرة المطبقة:*
• أقصى مخاطرة: {max_risk}%
• أقل ثقة: {min_confidence}%
• أقصى صفقات/يوم: {max_daily}
• حد الخسائر المتتالية: {max_consecutive}

*تقرير المخاطرة:*
{report}

*توصيات إدارة المخاطر لحساب $50:*
• حجم اللوت المناسب: 0.01 (10 سنت لكل نقطة)
• المخاطرة القصوى لكل صفقة: $1 (2%)
• الهدف اليومي: $1-$3 (2-6%)
• التوقف بعد خسارتين متتاليتين إلزامي"""


def format_image_analysis(analysis: dict, live_data: dict) -> str:
    direction = analysis.get("direction", analysis.get("trend", "محايد"))
    support = analysis.get("support", analysis.get("nearest_support", analysis.get("support_level", "N/A")))
    resistance = analysis.get("resistance", analysis.get("nearest_resistance", analysis.get("resistance_level", "N/A")))
    liquidity = analysis.get("liquidity_zone", analysis.get("liquidity", "N/A"))
    entry_zone_found = analysis.get("entry_zone_found", analysis.get("has_entry_zone", False))
    entry_text = "نعم ✅" if entry_zone_found else "لا ❌"
    timeframe = analysis.get("timeframe", analysis.get("extracted_tf", "غير محدد"))

    live_price = live_data.get("gold", live_data.get("price", "N/A"))
    m15_trend = live_data.get("m15_trend", analysis.get("m15_trend", "N/A"))
    h1_trend = live_data.get("h1_trend", analysis.get("h1_trend", "N/A"))
    h4_trend = live_data.get("h4_trend", analysis.get("h4_trend", "N/A"))
    spread = live_data.get("spread", analysis.get("spread", "N/A"))
    volatility = live_data.get("volatility", analysis.get("volatility", "N/A"))

    match_status = analysis.get("match_status", analysis.get("image_match", ""))
    if not match_status:
        live_price_f = float(live_price) if live_price != "N/A" else 0
        img_price = analysis.get("image_price", analysis.get("price_at_screenshot", 0))
        price_diff = abs(live_price_f - img_price) if live_price_f and img_price else 0
        match_status = "متطابقة ✅" if price_diff < 5 else "غير متطابقة ⚠️"
    else:
        match_status_text = "متطابقة ✅" if match_status in ("matched", "متطابقة") else "غير متطابقة ⚠️"
        match_status = match_status_text

    decision = analysis.get("decision", analysis.get("final_decision", analysis.get("recommendation", "")))
    if not decision:
        confidence = analysis.get("confidence", 0)
        has_entry = analysis.get("has_entry_zone", entry_zone_found)
        decision = "موصى به ✅" if (has_entry and confidence and confidence >= 80) else "غير موصى به ❌"
    else:
        if isinstance(decision, str):
            if "موصى" in decision or "yes" in decision.lower() or "recommend" in decision.lower():
                decision = "موصى به ✅"
            elif "غير" in decision or "no" in decision.lower() or "avoid" in decision.lower():
                decision = "غير موصى به ❌"

    decision_reason = analysis.get("decision_reason", analysis.get("reason", analysis.get("summary", "")))

    direction_map = {"buy": "صاعد 📈", "sell": "هابط 📉", "neutral": "محايد ⚖️", "sideways": "عرضي ↔️"}
    direction_text = direction_map.get(direction.lower(), str(direction)) if isinstance(direction, str) else str(direction)

    return f"""*تحليل صورة الشارت* 📷

*الرمز:* XAUUSD
*الفريم:* {timeframe}
*الاتجاه:* {direction_text}
*أقرب دعم:* {support}
*أقرب مقاومة:* {resistance}
*منطقة السيولة:* {liquidity}
*منطقة دخول:* {entry_text}
*مطابقة مع السوق الحي:* {match_status}
━━━━━━━━━━━━━━━━
*السعر الحالي:* {live_price}
*اتجاه M15:* {m15_trend}
*اتجاه H1:* {h1_trend}
*اتجاه H4:* {h4_trend}
*السبريد:* {spread}
*التذبذب:* {volatility}
━━━━━━━━━━━━━━━━
*القرار النهائي:* {decision}
*سبب القرار:*
{decision_reason}"""


def format_daily_report(trades: list, stats: dict, analysis: dict) -> str:
    total_trades = stats.get("total", stats.get("total_trades", len(trades)))
    wins = stats.get("wins", stats.get("winning_trades", 0))
    losses = stats.get("losses", stats.get("losing_trades", 0))
    win_rate = stats.get("win_rate", 0)
    total_pnl = stats.get("total_pnl", stats.get("pnl", 0))
    best_trade = stats.get("best_trade", stats.get("max_profit", 0))
    worst_trade = stats.get("worst_trade", stats.get("max_loss", 0))
    avg_rr = stats.get("avg_risk_reward", stats.get("avg_rr", 0))

    direction = analysis.get("trend", analysis.get("bias", "محايد"))
    volatility = analysis.get("volatility", "متوسط")
    session = analysis.get("session", "")

    pnl_emoji = "✅" if total_pnl >= 0 else "❌"
    pnl_sign = "+" if total_pnl >= 0 else ""

    if session:
        session_names = {"asia": "آسيوية", "london": "لندن", "new_york": "نيويورك", "overlap": "تقاطع"}
        session_text = session_names.get(session.lower(), session)
    else:
        session_text = "متنوعة"

    trades_summary = ""
    for t in trades[-5:]:
        if hasattr(t, "result"):
            result = t.result
            trade_type = getattr(t, "trade_type", "")
            pnl = getattr(t, "pnl", 0)
        elif isinstance(t, dict):
            result = t.get("result")
            trade_type = t.get("trade_type", "")
            pnl = t.get("pnl", 0)
        else:
            continue

        emoji = "✅" if result == "win" else "❌" if result == "loss" else "⏳"
        direction_icon = "🟢" if trade_type == "buy" else "🔴"
        pnl_str = f"+${pnl:.2f}" if pnl and result == "win" else f"-${abs(pnl):.2f}" if pnl else "N/A"
        trades_summary += f"\n{emoji} {direction_icon} | {pnl_str}"

    return f"""*التقرير اليومي - XAUUSD* 📊
{datetime.utcnow().strftime('%Y-%m-%d')}

{pnl_emoji} *إجمالي الربح/الخسارة:* {pnl_sign}${total_pnl:,.2f}
━━━━━━━━━━━━━━━━
*إحصائيات اليوم:*
• إجمالي الصفقات: {total_trades}
• الرابحة: {wins}
• الخاسرة: {losses}
• نسبة الربح: {win_rate}%
• متوسط RR: {avg_rr}
• أفضل صفقة: ${best_trade:,.2f}
• أسوأ صفقة: -${abs(worst_trade):,.2f}
━━━━━━━━━━━━━━━━
*تحليل السوق:*
• الاتجاه العام: {direction}
• التذبذب: {volatility}
• الجلسة النشطة: {session_text}

*آخر الصفقات:*{trades_summary}

━━━━━━━━━━━━━━━━
*خلاصة اليوم:*
{analysis.get('ai_summary', analysis.get('summary', 'تم تحديث التقرير بنجاح.'))}
━━━━━━━━━━━━━━━━
*إدارة المخاطر:* {stats.get('risk_note', 'الحفاظ على الانضباط هو مفتاح النجاح.')}
⚠️ التداول ينطوي على مخاطر - ليس هناك أرباح مضمونة."""
