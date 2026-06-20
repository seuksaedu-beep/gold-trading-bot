import logging
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import settings
from bot.keyboards import (
    main_menu_keyboard,
    timeframe_keyboard,
    confirm_signal_keyboard,
    settings_keyboard,
    back_button,
    risk_management_keyboard,
    report_keyboard,
    session_keyboard,
)
from bot.messages import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    format_current_price,
    format_trade_signal,
    format_no_trade,
    format_market_analysis,
    format_settings,
    format_statistics,
    format_recent_trades,
    format_backtest_result,
    format_alert_notification,
    format_scalp_signal_detailed,
    format_daily_report,
    format_image_analysis,
)
from analysis.market_analyzer import MarketAnalyzer
from analysis.risk_manager import MicroRiskManager
from analysis.session_detector import SessionDetector
from analysis.spread_monitor import SpreadMonitor
from bot.image_analyzer import ImageAnalyzer
from data.price_fetcher import RealPriceFetcher
from data.market_data import MarketDataProvider
from models.scalping_signal import ScalpingProSignal
from models.signal_generator import SignalGenerator
from database.db import (
    get_or_create_user_settings,
    update_user_settings,
    get_trades,
    get_trade_stats,
    get_recent_trades,
    get_trades_count_today,
    get_trade_by_id,
)

logger = logging.getLogger(__name__)

TF_MAP = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1H", "4h": "4H", "daily": "D"}
SCALP_TFS = {"1m", "5m", "15m"}


class TradingBot:
    def __init__(self, token: str):
        self.token = token
        self.market_analyzer = MarketAnalyzer()
        self.price_fetcher = RealPriceFetcher()
        self.market_data = MarketDataProvider()
        self.spread_monitor = SpreadMonitor()
        self._pending_signals: dict[int, dict] = {}
        self._awaiting_input: dict[int, str] = {}
        self._alerts_enabled: dict[int, bool] = {}

    # ── helpers ────────────────────────────────────────────────

    @staticmethod
    def _get_risk_manager(user_id: int) -> MicroRiskManager:
        return MicroRiskManager(user_id)

    @staticmethod
    def _get_user_settings(user_id: int):
        return get_or_create_user_settings(user_id)

    # ── command handlers ───────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            WELCOME_MESSAGE, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
        )

    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text("جاري تحميل البيانات...")
        try:
            snapshot = await self.price_fetcher.fetch_all_snapshot()
            session = SessionDetector().get_current_session()
            spread = self.spread_monitor.get_spread()
            data = {**snapshot, "session": session.get("session", ""), "spread": spread}
            await msg.edit_text(
                format_current_price(data), parse_mode="Markdown", reply_markup=back_button()
            )
        except Exception as e:
            logger.error("Price error", exc_info=True)
            await msg.edit_text(f"خطأ في جلب البيانات: {e}")

    async def cmd_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("اختر الفريم الزمني:", reply_markup=timeframe_keyboard())

    async def cmd_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text("جاري التحليل الشامل...")
        try:
            analysis = await self.market_analyzer.analyze_market_full()
            await msg.edit_text(
                format_market_analysis(analysis), parse_mode="Markdown", reply_markup=back_button()
            )
        except Exception as e:
            logger.error("Analysis error", exc_info=True)
            await msg.edit_text(f"خطأ في التحليل: {e}")

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            stats = get_trade_stats(update.effective_user.id)
            await update.message.reply_text(
                format_statistics(stats), parse_mode="Markdown", reply_markup=back_button()
            )
        except Exception as e:
            logger.error("Stats error", exc_info=True)
            await update.message.reply_text(f"خطأ: {e}")

    async def cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            trades = get_trades(10)
            await update.message.reply_text(
                format_recent_trades(trades), parse_mode="Markdown", reply_markup=back_button()
            )
        except Exception as e:
            logger.error("Trades error", exc_info=True)
            await update.message.reply_text(f"خطأ: {e}")

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            s = self._get_user_settings(user_id)
            alerts = self._alerts_enabled.get(user_id, True)
            await update.message.reply_text(
                format_settings(s, alerts),
                parse_mode="Markdown",
                reply_markup=settings_keyboard(s.is_active, s.is_paused),
            )
        except Exception as e:
            logger.error("Settings error", exc_info=True)
            await update.message.reply_text(f"خطأ: {e}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            HELP_MESSAGE, parse_mode="Markdown", reply_markup=back_button()
        )

    async def cmd_quick(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text("جاري تحليل سريع للسكالبينج...")
        await self._analyze_and_respond(update.effective_user.id, msg, "1m", is_scalp=True)

    async def cmd_scalp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text("جاري تحليل سريع للسكالبينج...")
        await self._analyze_and_respond(update.effective_user.id, msg, "1m", is_scalp=True)

    async def cmd_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text("جاري تحليل أداء اليوم...")
        try:
            user_id = update.effective_user.id
            trades = get_recent_trades(1)
            stats = get_trade_stats(user_id)
            analysis = await self.market_analyzer.analyze_market_full()
            await msg.edit_text(
                format_daily_report(trades, stats, analysis),
                parse_mode="Markdown",
                reply_markup=back_button(),
            )
        except Exception as e:
            logger.error("Today error", exc_info=True)
            await msg.edit_text(f"خطأ: {e}")

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("اختر نوع التقرير:", reply_markup=report_keyboard())

    async def cmd_rejected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text("جاري التحليل لعرض أسباب الرفض...")
        try:
            user_id = update.effective_user.id
            result = await ScalpingProSignal(user_id).generate_scalp_signal("5m")
            reasons = []
            if result.get("no_trade"):
                reasons.append(result.get("reason", "لا توجد معلومات"))
            if result.get("confidence") is not None:
                reasons.append(f"نسبة الثقة: {result['confidence']}%")
            direction = result.get("direction", result.get("analysis", {}).get("direction", "محايد"))
            text = f"*أسباب رفض الصفقات*\n\nالاتجاه: {direction}\n"
            if reasons:
                text += "\n".join(f"• {r}" for r in reasons)
            await msg.edit_text(text, parse_mode="Markdown", reply_markup=back_button())
        except Exception as e:
            logger.error("Rejected error", exc_info=True)
            await msg.edit_text(f"خطأ: {e}")

    async def cmd_sessions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("معلومات الجلسات:", reply_markup=session_keyboard())

    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text("جاري تحميل الأخبار...")
        try:
            from data.news_collector import NewsCollector
            nc = NewsCollector()
            items = await nc.get_latest_news(5)
            fed = await nc.get_fed_news()
            text = "*أخبار الذهب* 📰\n\n"
            if items:
                for item in items[:5]:
                    text += f"• {item.get('title', item.get('headline', 'بدون عنوان'))}\n"
            else:
                text += "لا توجد أخبار حديثة\n"
            if fed:
                text += f"\n*أخبار الفيدرالي:*\n{fed[:200]}"
            await msg.edit_text(text, parse_mode="Markdown", reply_markup=back_button())
        except Exception as e:
            logger.error("News error", exc_info=True)
            await msg.edit_text(f"خطأ: {e}")

    async def cmd_chart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("أرسل صورة الشارت للتحليل:", reply_markup=back_button())

    async def cmd_capital(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if context.args:
            try:
                val = float(context.args[0])
                if val < 10:
                    await update.message.reply_text("❌ رأس المال يجب أن يكون 10 دولار على الأقل")
                    return
                update_user_settings(user_id, capital=val)
                await update.message.reply_text(f"✅ تم تعيين رأس المال: ${val:.2f}")
            except ValueError:
                await update.message.reply_text("❌ قيمة غير صالحة. استخدم: /capital 50")
        else:
            self._awaiting_input[user_id] = "capital"
            await update.message.reply_text("أدخل قيمة رأس المال بالدولار:", reply_markup=back_button())

    async def cmd_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if context.args:
            try:
                val = float(context.args[0])
                if val <= 0 or val > 5:
                    await update.message.reply_text("❌ النسبة يجب أن تكون بين 0.1% و 5%")
                    return
                update_user_settings(user_id, risk_percent=val)
                await update.message.reply_text(f"✅ تم تعيين نسبة المخاطرة: {val}%")
            except ValueError:
                await update.message.reply_text("❌ قيمة غير صالحة. استخدم: /risk 0.5")
        else:
            self._awaiting_input[user_id] = "risk_pct"
            await update.message.reply_text("أدخل نسبة المخاطرة (0.1 - 5):", reply_markup=back_button())

    async def cmd_setmaxtrades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if context.args:
            try:
                val = int(context.args[0])
                if val < 1 or val > 10:
                    await update.message.reply_text("❌ العدد يجب أن يكون بين 1 و 10")
                    return
                update_user_settings(user_id, max_trades_per_day=val)
                await update.message.reply_text(f"✅ تم تعيين أقصى صفقات يومية: {val}")
            except ValueError:
                await update.message.reply_text("❌ قيمة غير صالحة. استخدم: /setmaxtrades 3")
        else:
            self._awaiting_input[user_id] = "max_trades"
            await update.message.reply_text("أدخل أقصى عدد صفقات يومية (1-10):", reply_markup=back_button())

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            s = self._get_user_settings(user_id)
            risk = self._get_risk_manager(user_id)
            session = SessionDetector().get_current_session()
            spread_info = self.spread_monitor.get_spread_status()
            today_cnt = get_trades_count_today()
            text = (
                f"*حالة البوت* 🤖\n\n"
                f"{'🟢 نشط' if s.is_active else '🔴 متوقف'}"
                f"{' (⏸ متوقف مؤقتاً)' if s.is_paused else ''}\n"
                f"💰 رأس المال: ${s.capital:.2f}\n"
                f"📊 صفقات اليوم: {today_cnt}/{risk.max_daily}\n"
                f"⚠️ خسائر متتالية: {s.consecutive_losses}/2\n"
                f"🌍 الجلسة: {session.get('session_name', 'غير معروفة')}\n"
                f"📈 جودة الجلسة: {session.get('quality', 'غير معروفة')}\n"
                f"📐 السبريد: {spread_info['spread']} ({spread_info['status']})\n"
                f"🕐 آخر تحديث: {datetime.utcnow().strftime('%H:%M')} UTC"
            )
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=back_button())
        except Exception as e:
            logger.error("Status error", exc_info=True)
            await update.message.reply_text(f"خطأ: {e}")

    async def cmd_tf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("استخدم: /tf m1, /tf m5, /tf 15m, /tf 30m, /tf 1h, /tf 4h, /tf d")
            return
        raw = context.args[0].lower().replace("h", "H")
        alias = {"m1": "1m", "m5": "5m", "m15": "15m", "m30": "30m", "1h": "1H", "4h": "4H", "d": "D", "daily": "D"}
        tf = alias.get(raw)
        if not tf:
            await update.message.reply_text("❌ فريم غير معروف. استخدم: m1, m5, 15m, 30m, 1h, 4h, d")
            return
        msg = await update.message.reply_text(f"جاري تحليل فريم {tf}...")
        await self._analyze_and_respond(update.effective_user.id, msg, tf, tf in SCALP_TFS)

    # ── analysis core ──────────────────────────────────────────

    async def _analyze_and_respond(self, user_id: int, msg, timeframe: str, is_scalp: bool = False):
        try:
            if is_scalp:
                result = await ScalpingProSignal(user_id).generate_scalp_signal(timeframe)
            else:
                result = await SignalGenerator(user_id).generate_signal_for_timeframe(timeframe)

            if result.get("no_trade"):
                price = result.get("analysis", {}).get("current_price", 0) or 0
                if not price:
                    try:
                        price = await self.price_fetcher.fetch_gold_price()
                    except Exception:
                        price = 0
                await msg.edit_text(
                    format_no_trade(result, price),
                    parse_mode="Markdown",
                    reply_markup=back_button("cb_back"),
                )
            else:
                trade_data = result.get("trade", {})
                self._pending_signals[user_id] = {"timeframe": timeframe, "signal_type": "scalp" if is_scalp else "regular", "result": result}
                text = format_scalp_signal_detailed(trade_data, result.get("analysis", {})) if is_scalp else format_trade_signal(trade_data)
                await msg.edit_text(text, parse_mode="Markdown", reply_markup=confirm_signal_keyboard(timeframe))
        except Exception as e:
            logger.error("Analysis error", exc_info=True)
            try:
                await msg.edit_text(f"❌ حدث خطأ أثناء التحليل: {e}")
            except Exception:
                pass

    # ── image handler ──────────────────────────────────────────

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text("جاري تحليل الصورة...")
        try:
            file = await update.message.photo[-1].get_file()
            analyzer = ImageAnalyzer(self.market_data)
            live = await self.price_fetcher.fetch_all_snapshot()
            analysis = await analyzer.full_image_analysis(file.file_path, live)
            await msg.edit_text(
                format_image_analysis(analysis, live),
                parse_mode="Markdown",
                reply_markup=back_button(),
            )
        except Exception as e:
            logger.error("Image analysis error", exc_info=True)
            await msg.edit_text(f"❌ خطأ في تحليل الصورة: {e}")

    # ── text input handler ─────────────────────────────────────

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in self._awaiting_input:
            return

        mode = self._awaiting_input.pop(user_id, None)
        text = update.message.text.strip()

        try:
            if mode == "capital":
                val = float(text)
                if val < 10:
                    await update.message.reply_text("❌ رأس المال يجب أن يكون 10 دولار على الأقل")
                    return
                update_user_settings(user_id, capital=val)
                await update.message.reply_text(f"✅ تم تعيين رأس المال: ${val:.2f}", reply_markup=main_menu_keyboard())

            elif mode == "risk_pct":
                val = float(text)
                if val <= 0 or val > 5:
                    await update.message.reply_text("❌ النسبة يجب أن تكون بين 0.1% و 5%")
                    return
                update_user_settings(user_id, risk_percent=val)
                await update.message.reply_text(f"✅ تم تعيين نسبة المخاطرة: {val}%", reply_markup=main_menu_keyboard())

            elif mode == "min_confidence":
                val = float(text)
                if val < 60 or val > 100:
                    await update.message.reply_text("❌ النسبة يجب أن تكون بين 60 و 100")
                    return
                update_user_settings(user_id, min_confidence=val)
                await update.message.reply_text(f"✅ تم تعيين أقل نسبة ثقة: {val}%", reply_markup=main_menu_keyboard())

            elif mode == "max_trades":
                val = int(text)
                if val < 1 or val > 10:
                    await update.message.reply_text("❌ العدد يجب أن يكون بين 1 و 10")
                    return
                update_user_settings(user_id, max_trades_per_day=val)
                await update.message.reply_text(f"✅ تم تعيين أقصى صفقات يومية: {val}", reply_markup=main_menu_keyboard())

        except ValueError:
            await update.message.reply_text("❌ قيمة غير صالحة. أدخل رقماً صحيحاً.")

    # ── button handler ─────────────────────────────────────────

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        data = query.data

        # ── main menu / back ──
        if data in ("cb_main_menu", "cb_back"):
            await query.edit_message_text(WELCOME_MESSAGE, parse_mode="Markdown", reply_markup=main_menu_keyboard())
            return

        # ── price ──
        if data == "cb_price":
            await query.edit_message_text("جاري تحميل البيانات...")
            try:
                snapshot = await self.price_fetcher.fetch_all_snapshot()
                session = SessionDetector().get_current_session()
                spread = self.spread_monitor.get_spread()
                await query.edit_message_text(
                    format_current_price({**snapshot, "session": session.get("session", ""), "spread": spread}),
                    parse_mode="Markdown",
                    reply_markup=back_button(),
                )
            except Exception as e:
                logger.error("Price cb error", exc_info=True)
                await query.edit_message_text(f"خطأ: {e}")
            return

        # ── analysis ──
        if data == "cb_analysis":
            await query.edit_message_text("جاري التحليل الشامل...")
            try:
                analysis = await self.market_analyzer.analyze_market_full()
                await query.edit_message_text(format_market_analysis(analysis), parse_mode="Markdown", reply_markup=back_button())
            except Exception as e:
                logger.error("Analysis cb error", exc_info=True)
                await query.edit_message_text(f"خطأ: {e}")
            return

        # ── quick scalp ──
        if data == "cb_scalp_quick":
            await query.edit_message_text("جاري تحليل سريع للسكالبينج...")
            await self._analyze_and_respond(user_id, query.message, "1m", is_scalp=True)
            return

        # ── full signal (TF selection) ──
        if data == "cb_full_signal":
            await query.edit_message_text("اختر الفريم الزمني:", reply_markup=timeframe_keyboard())
            return

        # ── chart image ──
        if data == "cb_chart_image":
            await query.edit_message_text("أرسل صورة الشارت للتحليل:", reply_markup=back_button())
            return

        # ── sessions menu ──
        if data == "cb_sessions":
            await query.edit_message_text("معلومات الجلسات:", reply_markup=session_keyboard())
            return

        # ── risk management menu ──
        if data == "cb_risk_mgmt":
            await query.edit_message_text("إدارة المخاطر:", reply_markup=risk_management_keyboard())
            return

        # ── trades log ──
        if data == "cb_trades_log":
            try:
                await query.edit_message_text(format_recent_trades(get_trades(10)), parse_mode="Markdown", reply_markup=back_button())
            except Exception as e:
                await query.edit_message_text(f"خطأ: {e}")
            return

        # ── reports menu ──
        if data == "cb_reports":
            await query.edit_message_text("اختر نوع التقرير:", reply_markup=report_keyboard())
            return

        # ── settings ──
        if data == "cb_settings":
            try:
                s = self._get_user_settings(user_id)
                alerts = self._alerts_enabled.get(user_id, True)
                await query.edit_message_text(format_settings(s, alerts), parse_mode="Markdown", reply_markup=settings_keyboard(s.is_active, s.is_paused))
            except Exception as e:
                await query.edit_message_text(f"خطأ: {e}")
            return

        # ── help ──
        if data == "cb_help":
            await query.edit_message_text(HELP_MESSAGE, parse_mode="Markdown", reply_markup=back_button())
            return

        # ── Timeframe selection ──
        if data.startswith("cb_tf_"):
            await self._handle_tf_selection(query, user_id, data)
            return

        # ── Confirm trade ──
        if data.startswith("cb_confirm_tf_"):
            await self._handle_confirm_trade(query, user_id, data.replace("cb_confirm_tf_", ""))
            return

        # ── Extra analysis ──
        if data.startswith("cb_extra_analysis_"):
            tf = data.replace("cb_extra_analysis_", "")
            await query.edit_message_text("جاري تحليل إضافي شامل...")
            try:
                analysis = await self.market_analyzer.analyze_market_full()
                await query.edit_message_text(format_market_analysis(analysis), parse_mode="Markdown", reply_markup=back_button())
            except Exception as e:
                await query.edit_message_text(f"خطأ: {e}")
            return

        # ── Other timeframe ──
        if data.startswith("cb_other_tf_"):
            await query.edit_message_text("اختر فريم آخر:", reply_markup=timeframe_keyboard())
            return

        # ── Send chart for this TF ──
        if data.startswith("cb_send_chart_"):
            await query.edit_message_text("أرسل صورة الشارت للتحليل:", reply_markup=back_button())
            return

        # ── Settings toggles ──
        if data == "cb_toggle_bot":
            s = self._get_user_settings(user_id)
            update_user_settings(user_id, is_active=not s.is_active)
            await self._refresh_settings_msg(query, user_id)
            return

        if data == "cb_toggle_pause":
            s = self._get_user_settings(user_id)
            update_user_settings(user_id, is_paused=not s.is_paused)
            await self._refresh_settings_msg(query, user_id)
            return

        if data == "cb_set_capital":
            self._awaiting_input[user_id] = "capital"
            await query.edit_message_text("أدخل قيمة رأس المال بالدولار (مثال: 50):", reply_markup=back_button("cb_settings"))
            return

        if data == "cb_set_risk_pct":
            self._awaiting_input[user_id] = "risk_pct"
            await query.edit_message_text("أدخل نسبة المخاطرة (0.1 - 5):", reply_markup=back_button("cb_settings"))
            return

        if data == "cb_set_min_confidence":
            self._awaiting_input[user_id] = "min_confidence"
            await query.edit_message_text("أدخل أقل نسبة ثقة (60-100):", reply_markup=back_button("cb_settings"))
            return

        if data == "cb_toggle_capital_protection":
            risk = self._get_risk_manager(user_id)
            await query.answer(
                "وضع حماية رأس المال الصغير مفعل تلقائياً" if risk.is_small_capital else "رأس المال أكبر من $200 - الحماية غير مطلوبة",
                show_alert=True,
            )
            return

        if data == "cb_set_max_daily_trades":
            self._awaiting_input[user_id] = "max_trades"
            await query.edit_message_text("أدخل أقصى عدد صفقات يومية (1-10):", reply_markup=back_button("cb_settings"))
            return

        if data == "cb_toggle_super_opportunities":
            current = self._alerts_enabled.get(user_id, True)
            self._alerts_enabled[user_id] = not current
            await query.answer(f"✅ إشعارات الفرص الفائقة {'مفعلة' if not current else 'متوقفة'}", show_alert=True)
            await self._refresh_settings_msg(query, user_id)
            return

        # ── Reports ──
        if data in ("cb_report_daily", "cb_report_weekly", "cb_report_monthly"):
            period_map = {"cb_report_daily": "daily", "cb_report_weekly": "weekly", "cb_report_monthly": "monthly"}
            days_map = {"daily": 1, "weekly": 7, "monthly": 30}
            period = period_map[data]
            await query.edit_message_text(f"جاري تحضير التقرير {period}...")
            try:
                trades = get_recent_trades(days_map[period])
                stats = get_trade_stats(user_id)
                analysis = await self.market_analyzer.analyze_market_full()
                await query.edit_message_text(format_daily_report(trades, stats, analysis), parse_mode="Markdown", reply_markup=back_button())
            except Exception as e:
                await query.edit_message_text(f"خطأ: {e}")
            return

        if data == "cb_report_performance":
            try:
                await query.edit_message_text(format_statistics(get_trade_stats(user_id)), parse_mode="Markdown", reply_markup=back_button())
            except Exception as e:
                await query.edit_message_text(f"خطأ: {e}")
            return

        if data == "cb_report_export":
            await query.answer("🎯 سيتم إضافة خاصية التصدير قريباً", show_alert=True)
            return

        # ── Session info ──
        if data in ("cb_session_asia", "cb_session_europe", "cb_session_us", "cb_session_overlap"):
            key_map = {"cb_session_asia": "asian", "cb_session_europe": "london", "cb_session_us": "new_york", "cb_session_overlap": "london_ny_overlap"}
            await self._show_session_info(query, key_map[data])
            return

        if data == "cb_session_recommended":
            detector = SessionDetector()
            info = detector.get_current_session()
            opt = self.spread_monitor.get_optimal_spread_times()
            text = "*أوقات التداول الموصى بها* ⏰\n\n"
            for o in opt[:5]:
                text += f"• {o.get('label', '')}: {o.get('description', '')}\n"
            text += f"\n*الجلسة الحالية:* {info.get('session_name', 'غير معروفة')}\n*الجودة:* {info.get('quality', 'غير معروفة')}"
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_button())
            return

        # ── Risk management detail ──
        if data == "cb_show_risk_settings":
            risk = self._get_risk_manager(user_id)
            f = risk.get_scalp_filters()
            text = (
                f"*إعدادات المخاطرة الحالية*\n\n"
                f"💰 رأس المال: ${risk.capital:.2f}\n"
                f"⚠️ المخاطرة: {risk.risk_percent}%\n"
                f"📊 رأس مال صغير: {'نعم' if risk.is_small_capital else 'لا'}\n"
                f"📐 أقصى صفقات/يوم: {risk.max_daily}\n"
                f"🎯 أقل ثقة: {f.get('min_confidence', 'N/A')}%\n"
                f"🛑 أقصى سبريد: {f.get('max_spread', 'N/A')}\n"
                f"📏 أقصى وقف: {f.get('max_stop_pips', 'N/A')} نقطة"
            )
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_button())
            return

        if data == "cb_capital_rules":
            await query.edit_message_text(
                "*قواعد إدارة رأس المال* 💰\n\n"
                "1. لا تخاطر بأكثر من 1-2% من رأس المال في صفقة واحدة\n"
                "2. حد أقصى 3 صفقات يومياً\n"
                "3. خسارتين متتاليتين = توقف إلزامي\n"
                "4. استخدم 0.01 لوت لحساب $50\n"
                "5. الهدف اليومي: $1-$3 (2-6%)\n"
                "6. لا تتداول أثناء الأخبار عالية التأثير\n"
                "7. وقف الخسارة إلزامي لكل صفقة",
                parse_mode="Markdown",
                reply_markup=back_button(),
            )
            return

        if data == "cb_position_size":
            await query.edit_message_text(
                "أدخل سعر الدخول ووقف الخسارة (مثال: 2345.50 2330.00):\n\nأرسل الرقمين مفصولين بمسافة",
                reply_markup=back_button(),
            )
            return

        if data == "cb_small_capital_protection":
            risk = self._get_risk_manager(user_id)
            await query.edit_message_text(f"*حماية رأس المال الصغير* 🛡️\n\n{risk.get_small_capital_report()}", parse_mode="Markdown", reply_markup=back_button())
            return

        if data == "cb_recommended_risk":
            await query.edit_message_text(
                "*نسبة المخاطرة الموصى بها*\n\n"
                "• حساب $50: 0.5% - 1% ($0.25 - $0.50)\n"
                "• حساب $100: 0.5% - 1% ($0.50 - $1.00)\n"
                "• حساب $200: 0.5% - 1.5% ($1 - $3)\n"
                "• حساب $500: 1% - 2% ($5 - $10)\n\n"
                "⚠️ القاعدة الذهبية: لا تخاطر أبداً بأكثر من 2%",
                parse_mode="Markdown",
                reply_markup=back_button(),
            )
            return

        # ── Trading types ──
        if data == "cb_type_scalping":
            await query.edit_message_text("جاري تحليل سكالبينج...")
            await self._analyze_and_respond(user_id, query.message, "5m", is_scalp=True)
            return

        if data == "cb_type_intraday":
            await query.edit_message_text("جاري تحليل تداول يومي...")
            await self._analyze_and_respond(user_id, query.message, "1H", is_scalp=False)
            return

        if data == "cb_type_swing":
            await query.edit_message_text("جاري تحليل سوينغ...")
            await self._analyze_and_respond(user_id, query.message, "4H", is_scalp=False)
            return

        if data == "cb_type_all":
            await query.edit_message_text("اختر الفريم:", reply_markup=timeframe_keyboard())
            return

        # ── Backtest ──
        if data == "cb_run_backtest":
            await query.answer("🧪 سيتم إضافة خاصية الاختبار الخلفي قريباً", show_alert=True)
            return

        if data == "cb_past_backtests":
            try:
                from database.db import get_backtest_results
                results = get_backtest_results(5)
                if not results:
                    await query.edit_message_text("لا توجد نتائج اختبار خلفي سابقة.", reply_markup=back_button())
                    return
                text = "*نتائج الاختبارات الخلفية السابقة*\n\n"
                for r in results:
                    text += format_backtest_result(r) + "\n\n"
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_button())
            except Exception as e:
                await query.edit_message_text(f"خطأ: {e}")
            return

        if data == "cb_backtest_settings":
            await query.answer("⚙️ إعدادات الاختبار الخلفي قادمة قريباً", show_alert=True)
            return

        # ── Alerts ──
        if data == "cb_alert_trades_on":
            self._alerts_enabled[user_id] = True
            await query.answer("✅ تم تفعيل الإشعارات", show_alert=True)
            return

        if data == "cb_alert_trades_off":
            self._alerts_enabled[user_id] = False
            await query.answer("🔕 تم إيقاف الإشعارات", show_alert=True)
            return

        if data in ("cb_alert_interval", "cb_alert_price_targets"):
            await query.answer("⏱ قادمة قريباً", show_alert=True)
            return

        logger.warning("Unhandled callback: %s", data)
        await query.answer("الإجراء غير مدعوم حالياً", show_alert=True)

    # ── internal helpers ───────────────────────────────────────

    async def _handle_tf_selection(self, query, user_id: int, data: str):
        raw = data.replace("cb_tf_", "")
        if raw == "all":
            await query.edit_message_text("جاري تحليل جميع الفريمات...")
            try:
                await query.edit_message_text(format_market_analysis(await self.market_analyzer.analyze_market_full()), parse_mode="Markdown", reply_markup=back_button())
            except Exception as e:
                await query.edit_message_text(f"خطأ: {e}")
            return
        if raw == "quick_scalp":
            await query.edit_message_text("جاري تحليل سريع للسكالبينج...")
            await self._analyze_and_respond(user_id, query.message, "1m", is_scalp=True)
            return
        tf = TF_MAP.get(raw)
        if not tf:
            await query.edit_message_text("❌ فريم غير معروف")
            return
        await query.edit_message_text(f"جاري تحليل فريم {raw}...")
        await self._analyze_and_respond(user_id, query.message, tf, tf in SCALP_TFS)

    async def _handle_confirm_trade(self, query, user_id: int, timeframe: str):
        pending = self._pending_signals.get(user_id)
        if not pending:
            await query.edit_message_text("⚠️ انتهت صلاحية التحليل. قم بتحليل جديد.", reply_markup=back_button())
            return
        result = pending.get("result", {})
        if result.get("no_trade"):
            await query.edit_message_text("⚠️ لا توجد صفقة متاحة للتأكيد.", reply_markup=back_button())
            return
        trade_data = result.get("trade", {})
        trade_id = result.get("trade_id")
        if trade_id:
            get_trade_by_id(trade_id)
        text = format_trade_signal(trade_data) + f"\n\n✅ *تم تأكيد الصفقة بنجاح* (ID: {trade_id})" if trade_id else format_trade_signal(trade_data) + "\n\n✅ *تم تأكيد الصفقة*"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_button())

    async def _show_session_info(self, query, session_key: str):
        detector = SessionDetector()
        names = {"asian": "الآسيوية", "london": "الأوروبية (لندن)", "new_york": "الأمريكية (نيويورك)", "london_ny_overlap": "تقاطع لندن ونيويورك"}
        current = detector.get_current_session()
        is_active = current.get("session") == session_key
        name = names.get(session_key, session_key)
        volatility = detector.SESSION_VOLATILITY.get(session_key, "medium")
        quality = detector.SESSION_QUALITY.get(session_key, "poor")
        times = detector.SESSION_TIMES.get(session_key, {})
        vol_map = {"low": "منخفض 📉", "medium": "متوسط 📊", "high": "مرتفع 📈", "extreme": "شديد 🔥"}
        qual_map = {"poor": "ضعيفة ❌", "fair": "مقبولة ⚠️", "good": "جيدة ✅", "excellent": "ممتازة 🏆"}
        text = (
            f"*الجلسة {name}* 🌍\n\n"
            f"{'🟢 نشطة حالياً' if is_active else '🔴 غير نشطة'}\n"
            f"🕐 التوقيت: {times.get('open', 'N/A')}:00 - {times.get('close', 'N/A')}:00 UTC\n"
            f"📊 التذبذب: {vol_map.get(volatility, str(volatility))}\n"
            f"⭐ الجودة: {qual_map.get(quality, str(quality))}\n\n"
            f"*توصية:* {'مناسبة للتداول ✅' if quality in ('good', 'excellent') else 'غير مناسبة للتداول ❌'}"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_button())

    async def _refresh_settings_msg(self, query, user_id: int):
        s = self._get_user_settings(user_id)
        alerts = self._alerts_enabled.get(user_id, True)
        await query.edit_message_text(format_settings(s, alerts), parse_mode="Markdown", reply_markup=settings_keyboard(s.is_active, s.is_paused))

    # ── alert loop ─────────────────────────────────────────────

    async def alert_loop(self, app: Application):
        while True:
            try:
                for user_id, enabled in list(self._alerts_enabled.items()):
                    if not enabled:
                        continue
                    s = self._get_user_settings(user_id)
                    if not s.is_active or s.is_paused:
                        continue
                    risk = self._get_risk_manager(user_id)
                    can, _, _ = risk.can_trade()
                    if not can:
                        continue
                    if not self.spread_monitor.is_spread_tradeable():
                        continue
                    quality = SessionDetector().get_session_quality()
                    if quality in ("poor", "none"):
                        continue
                    scalp = ScalpingProSignal(user_id)
                    for tf in ("1m", "5m", "15m"):
                        try:
                            result = await scalp.generate_scalp_signal(tf)
                            if not result.get("no_trade"):
                                td = result.get("trade", {})
                                if td.get("is_super") and td.get("confidence", 0) >= 90:
                                    text = format_alert_notification(td, tf)
                                    try:
                                        await app.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown", reply_markup=confirm_signal_keyboard(tf))
                                        self._pending_signals[user_id] = {"timeframe": tf, "signal_type": "scalp", "result": result}
                                    except Exception as e:
                                        logger.error("Failed to send alert to %d: %s", user_id, e)
                        except Exception:
                            continue
            except Exception as e:
                logger.error("Alert loop error", exc_info=True)
            await asyncio.sleep(60)

    # ── build app & run ────────────────────────────────────────

    async def _post_init(self, app: Application):
        asyncio.create_task(self.alert_loop(app))

    def build_app(self) -> Application:
        app = (Application.builder().token(self.token).post_init(self._post_init).build())

        handlers = [
            CommandHandler("start", self.cmd_start),
            CommandHandler("price", self.cmd_price),
            CommandHandler("signal", self.cmd_signal),
            CommandHandler("analysis", self.cmd_analysis),
            CommandHandler("stats", self.cmd_stats),
            CommandHandler("trades", self.cmd_trades),
            CommandHandler("settings", self.cmd_settings),
            CommandHandler("help", self.cmd_help),
            CommandHandler("quick", self.cmd_quick),
            CommandHandler("scalp", self.cmd_scalp),
            CommandHandler("today", self.cmd_today),
            CommandHandler("report", self.cmd_report),
            CommandHandler("rejected", self.cmd_rejected),
            CommandHandler("sessions", self.cmd_sessions),
            CommandHandler("news", self.cmd_news),
            CommandHandler("chart", self.cmd_chart),
            CommandHandler("capital", self.cmd_capital),
            CommandHandler("risk", self.cmd_risk),
            CommandHandler("setmaxtrades", self.cmd_setmaxtrades),
            CommandHandler("status", self.cmd_status),
            CommandHandler("tf", self.cmd_tf),
        ]
        for h in handlers:
            app.add_handler(h)

        app.add_handler(CallbackQueryHandler(self.button_handler))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_input))

        return app

    def run(self):
        self.build_app().run_polling()
