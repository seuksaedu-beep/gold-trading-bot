from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("السعر الحالي للذهب", callback_data="cb_price"),
            InlineKeyboardButton("تحليل السوق الكامل", callback_data="cb_analysis"),
        ],
        [
            InlineKeyboardButton("توصية سكالبينج سريعة ⚡", callback_data="cb_scalp_quick"),
            InlineKeyboardButton("توصية متكاملة", callback_data="cb_full_signal"),
        ],
        [
            InlineKeyboardButton("تحليل صورة شارت", callback_data="cb_chart_image"),
            InlineKeyboardButton("الجلسات والتوقيت", callback_data="cb_sessions"),
        ],
        [
            InlineKeyboardButton("إدارة المخاطر والحساب", callback_data="cb_risk_mgmt"),
            InlineKeyboardButton("سجل الصفقات", callback_data="cb_trades_log"),
        ],
        [
            InlineKeyboardButton("التقارير والإحصائيات", callback_data="cb_reports"),
            InlineKeyboardButton("الإعدادات", callback_data="cb_settings"),
        ],
        [
            InlineKeyboardButton("تعليمات المساعدة", callback_data="cb_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def timeframe_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("1 دقيقة", callback_data="cb_tf_1m"),
            InlineKeyboardButton("5 دقائق", callback_data="cb_tf_5m"),
            InlineKeyboardButton("15 دقيقة", callback_data="cb_tf_15m"),
        ],
        [
            InlineKeyboardButton("30 دقيقة", callback_data="cb_tf_30m"),
            InlineKeyboardButton("1 ساعة", callback_data="cb_tf_1h"),
            InlineKeyboardButton("4 ساعات", callback_data="cb_tf_4h"),
        ],
        [
            InlineKeyboardButton("يومي", callback_data="cb_tf_daily"),
            InlineKeyboardButton("كل الفريمات معاً", callback_data="cb_tf_all"),
        ],
        [
            InlineKeyboardButton("كويك سكالب (جميع الفريمات الصغيرة)", callback_data="cb_tf_quick_scalp"),
            InlineKeyboardButton("رجوع", callback_data="cb_back"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_signal_keyboard(timeframe: str):
    keyboard = [
        [
            InlineKeyboardButton("✅ قبول المخاطرة وتأكيد الصفقة", callback_data=f"cb_confirm_tf_{timeframe}"),
        ],
        [
            InlineKeyboardButton("📊 تحليل إضافي كامل", callback_data=f"cb_extra_analysis_{timeframe}"),
        ],
        [
            InlineKeyboardButton("🔄 فريم آخر", callback_data=f"cb_other_tf_{timeframe}"),
            InlineKeyboardButton("🖼 إرسال صورة للتحليل", callback_data=f"cb_send_chart_{timeframe}"),
        ],
        [
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="cb_main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_keyboard(is_active: bool = True, is_paused: bool = False):
    keyboard = [
        [
            InlineKeyboardButton(
                f"{'✅' if is_active else '❌'} تشغيل البوت",
                callback_data="cb_toggle_bot",
            ),
            InlineKeyboardButton(
                f"{'▶️' if is_paused else '⏸️'} إيقاف مؤقت",
                callback_data="cb_toggle_pause",
            ),
        ],
        [
            InlineKeyboardButton("تعديل رأس المال (افتراضي $50)", callback_data="cb_set_capital"),
        ],
        [
            InlineKeyboardButton("تعديل نسبة المخاطرة (%)", callback_data="cb_set_risk_pct"),
        ],
        [
            InlineKeyboardButton("تعديل أقل نسبة ثقة", callback_data="cb_set_min_confidence"),
        ],
        [
            InlineKeyboardButton("وضع حماية رأس المال الصغير", callback_data="cb_toggle_capital_protection"),
        ],
        [
            InlineKeyboardButton("تعديل أقصى صفقات يومية", callback_data="cb_set_max_daily_trades"),
        ],
        [
            InlineKeyboardButton("تفعيل إشعارات الفرص الفائقة", callback_data="cb_toggle_super_opportunities"),
        ],
        [
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="cb_main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def trading_type_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("سكالبينج سريع ⚡", callback_data="cb_type_scalping"),
        ],
        [
            InlineKeyboardButton("تداول يومي 📆", callback_data="cb_type_intraday"),
        ],
        [
            InlineKeyboardButton("سوينغ متوسط 🌊", callback_data="cb_type_swing"),
        ],
        [
            InlineKeyboardButton("جميع الأنواع", callback_data="cb_type_all"),
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="cb_back"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_button(callback: str = "cb_main_menu"):
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data=callback)]]
    return InlineKeyboardMarkup(keyboard)


def backtest_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("▶️ جميع الفريمات", callback_data="cb_run_backtest"),
        ],
        [
            InlineKeyboardButton("1m", callback_data="cb_bt_tf_1m"),
            InlineKeyboardButton("5m", callback_data="cb_bt_tf_5m"),
            InlineKeyboardButton("15m", callback_data="cb_bt_tf_15m"),
            InlineKeyboardButton("30m", callback_data="cb_bt_tf_30m"),
        ],
        [
            InlineKeyboardButton("1H", callback_data="cb_bt_tf_1H"),
            InlineKeyboardButton("4H", callback_data="cb_bt_tf_4H"),
            InlineKeyboardButton("D", callback_data="cb_bt_tf_D"),
        ],
        [
            InlineKeyboardButton("نتائج سابقة", callback_data="cb_past_backtests"),
        ],
        [
            InlineKeyboardButton("⚙️教育ات", callback_data="cb_backtest_settings"),
        ],
        [
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="cb_main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def risk_management_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("إعدادات المخاطرة الحالية", callback_data="cb_show_risk_settings"),
        ],
        [
            InlineKeyboardButton("قواعد إدارة رأس المال", callback_data="cb_capital_rules"),
        ],
        [
            InlineKeyboardButton("حساب حجم الصفقة", callback_data="cb_position_size"),
        ],
        [
            InlineKeyboardButton("حماية رأس المال الصغير", callback_data="cb_small_capital_protection"),
        ],
        [
            InlineKeyboardButton("نسبة المخاطرة الموصى بها", callback_data="cb_recommended_risk"),
        ],
        [
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="cb_main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def alert_settings_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("تفعيل إشعارات الصفقات", callback_data="cb_alert_trades_on"),
        ],
        [
            InlineKeyboardButton("إيقاف الإشعارات", callback_data="cb_alert_trades_off"),
        ],
        [
            InlineKeyboardButton("ضبط مدة التنبيه (دقائق)", callback_data="cb_alert_interval"),
        ],
        [
            InlineKeyboardButton("إشعارات الأسعار المستهدفة", callback_data="cb_alert_price_targets"),
        ],
        [
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="cb_main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def report_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("تقرير يومي", callback_data="cb_report_daily"),
            InlineKeyboardButton("تقرير أسبوعي", callback_data="cb_report_weekly"),
        ],
        [
            InlineKeyboardButton("تقرير شهري", callback_data="cb_report_monthly"),
            InlineKeyboardButton("تقرير الأداء العام", callback_data="cb_report_performance"),
        ],
        [
            InlineKeyboardButton("تصدير التقرير", callback_data="cb_report_export"),
        ],
        [
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="cb_main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def session_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("الجلسة الآسيوية", callback_data="cb_session_asia"),
            InlineKeyboardButton("الجلسة الأوروبية", callback_data="cb_session_europe"),
        ],
        [
            InlineKeyboardButton("الجلسة الأمريكية", callback_data="cb_session_us"),
            InlineKeyboardButton("تقاطع الجلسات", callback_data="cb_session_overlap"),
        ],
        [
            InlineKeyboardButton("أوقات التداول الموصى بها", callback_data="cb_session_recommended"),
        ],
        [
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="cb_main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
