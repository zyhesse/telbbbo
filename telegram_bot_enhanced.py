# 增强版Telegram机器人模块 - 支持内联按钮和自选关注
import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Set
import pandas as pd
import time

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, ContextTypes, 
                         CallbackQueryHandler, MessageHandler, filters)
from telegram.constants import ParseMode

from config import (TELEGRAM_BOT_TOKEN, TRADING_PAIRS, CHANNELS, PERFORMANCE_CHANNEL,
                   RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
                   MA_SHORT, MA_LONG, BOLLINGER_PERIOD, BOLLINGER_STD,
                   EMA_FAST, EMA_SLOW, EMA_SIGNAL, VOLUME_SMA_PERIOD,
                   VOLUME_THRESHOLD, SUPPORT_RESISTANCE_PERIOD)
from data_fetcher_okx import OKXDataFetcher

class EnhancedTelegramBot:
    def __init__(self):
        """初始化增强版Telegram机器人"""
        self.token = TELEGRAM_BOT_TOKEN
        self.app = Application.builder().token(self.token).build()
        self.logger = logging.getLogger(__name__)
        
        # 用户管理
        self.subscribers = set()  # 订阅用户集合
        self.user_watchlists = {}  # 用户自选关注 {user_id: set(symbols)}
        self.user_settings = {}   # 用户设置 {user_id: settings}
        
        # 信号缓存
        self.signal_cache = {}    # 信号详情缓存 {signal_id: signal_data}
        self.recent_signals = {}  # 最近信号 {symbol: signal_data}
        
        self.data_fetcher = OKXDataFetcher()
        
        # 设置命令处理器
        self.setup_handlers()
        
        # 初始化频道配置 - 科学分级推送
        self.main_channel = '@btczyz_signals_2025'     # 主信号频道 - 极强/强信号
        self.detail_channel = '@ethzyz_signals_2025'   # 副频道 - 中信号/增强弱信号
        
    def setup_handlers(self):
        """设置命令处理器"""
        handlers = [
            # 基础命令
            CommandHandler("start", self.start_command),
            CommandHandler("help", self.help_command),
            CommandHandler("subscribe", self.subscribe_command),
            CommandHandler("unsubscribe", self.unsubscribe_command),
            
            # 查询功能
            CommandHandler("price", self.price_command),
            CommandHandler("status", self.status_command),
            
            # 自选关注功能
            CommandHandler("add", self.add_watchlist_command),
            CommandHandler("remove", self.remove_watchlist_command),
            CommandHandler("watchlist", self.show_watchlist_command),
            CommandHandler("clear", self.clear_watchlist_command),
            CommandHandler("addall", self.add_all_coins_command),  # 新增：一键关注所有币种
            
            # 币种查询（支持 /btc, /eth 等）
            MessageHandler(filters.Regex(r'^/[a-zA-Z]{2,10}$'), self.coin_query_command),
            
            # 内联按钮回调
            CallbackQueryHandler(self.handle_callback_query),
            
            # 系统命令
            CommandHandler("pairs", self.pairs_command),
            CommandHandler("channels", self.channels_command),
        ]
        
        for handler in handlers:
            self.app.add_handler(handler)
            
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理/start命令"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "未知用户"
        
        # 初始化用户设置
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                'notification_level': 'HIGH',  # HIGH, MEDIUM, ALL
                'watchlist_only': False,
                'created_at': datetime.now()
            }
        
        welcome_message = f"""
🎯 **欢迎使用增强版加密货币交易信号机器人！**

👋 欢迎，{username}！

🚀 **核心功能**：
• 📊 **智能信号**：基于多指标分析的高质量交易信号
• 🔍 **内联查询**：点击按钮查看详细分析
• ⭐ **自选关注**：添加感兴趣的币种到关注列表
• 💬 **快速查询**：发送 /btc 快速查看BTC信号
• 🔥 **一键关注**：支持一键关注所有77个币种

📋 **快速开始**：
/subscribe - 订阅交易信号
/addall - 一键关注所有币种
/btc - 查看BTC实时分析
/help - 查看详细帮助

🎯 **信号等级**：
🔥 **高质量** - 70%+ 置信度，强推荐
⚡ **中等质量** - 30%+ 置信度，参考用
📊 **实时查询** - 随时查看技术分析

💡 点击按钮开始使用 👇
        """
        
        # 创建快速操作按钮
        keyboard = [
            [
                InlineKeyboardButton("🔔 订阅信号", callback_data="action_subscribe"),
                InlineKeyboardButton("🔥 一键关注所有币种", callback_data="action_addall")
            ],
            [
                InlineKeyboardButton("⭐ 管理关注", callback_data="action_watchlist"),
                InlineKeyboardButton("📊 热门币种", callback_data="action_hot_coins")
            ],
            [
                InlineKeyboardButton("❓ 获取帮助", callback_data="action_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理/help命令"""
        help_message = """
📚 **详细使用说明**

🔔 **订阅管理**：
/subscribe - 开始接收高质量信号推送
/unsubscribe - 停止接收信号推送
/status - 查看订阅状态和统计

⭐ **自选关注**：
/add BTC ETH SOL - 添加币种到关注列表
/addall - 🔥 一键关注所有币种（77个）
/remove BTC - 从关注列表移除币种
/watchlist - 查看当前关注列表
/clear - 清空关注列表

🔍 **快速查询**：
/btc - 查看BTC实时分析
/eth - 查看ETH实时分析
/price BTC - 查看BTC价格信息
/币种符号 - 支持大部分主流币种

📊 **信号说明**：
🔥 **HIGH** - 70%+ 置信度，强烈推荐
⚡ **MEDIUM** - 30%+ 置信度，谨慎参考
🟢 **LONG** - 做多信号（买入）
🔴 **SHORT** - 做空信号（卖出）

🎛️ **高级功能**：
• 点击信号消息中的"🔍 查看详情"按钮获取完整分析
• 添加关注列表后只接收关注币种的信号
• 支持设置信号质量过滤（仅高质量/全部）
• 一键关注功能可快速监控所有77个币种

⚠️ **风险提示**：
本机器人仅提供技术分析信号，不构成投资建议。
请结合自己的分析判断，谨慎投资，注意风险控制。
        """
        await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)
        
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理订阅命令"""
        user_id = update.effective_user.id
        if user_id in self.subscribers:
            keyboard = [
                [InlineKeyboardButton("⚙️ 设置", callback_data="action_settings")],
                [InlineKeyboardButton("⭐ 管理关注", callback_data="action_watchlist")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ 您已经订阅了交易信号推送！\n\n"
                "💡 点击下方按钮管理您的设置：",
                reply_markup=reply_markup
            )
        else:
            self.subscribers.add(user_id)
            
            keyboard = [
                [InlineKeyboardButton("⭐ 添加关注币种", callback_data="action_add_coins")],
                [InlineKeyboardButton("🔥 查看热门信号", callback_data="action_hot_signals")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🎉 **订阅成功！**\n\n"
                "您将收到高质量交易信号推送。\n"
                "💡 建议添加关注币种以获得更精准的信号。\n\n"
                "使用 /unsubscribe 可随时取消订阅。",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            self.logger.info(f"用户 {user_id} 订阅了信号推送")
            
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理取消订阅命令"""
        user_id = update.effective_user.id
        if user_id in self.subscribers:
            self.subscribers.remove(user_id)
            await update.message.reply_text(
                "❌ 已取消订阅交易信号推送。\n\n"
                "💡 使用 /subscribe 可重新订阅。"
            )
            self.logger.info(f"用户 {user_id} 取消了信号推送订阅")
        else:
            await update.message.reply_text("⚠️ 您还没有订阅交易信号推送。")
            
    async def add_watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """添加币种到关注列表"""
        user_id = update.effective_user.id
        
        if not context.args:
            # 显示可选币种
            all_contracts = await self.data_fetcher.fetch_all_contracts()
            hot_coins = all_contracts[:20] if all_contracts else TRADING_PAIRS
            
            message = f"📝 **添加关注币种**\n\n"
            message += f"💡 使用方法：/add BTC ETH SOL\n\n"
            message += f"🔥 **热门币种**：\n"
            for i, symbol in enumerate(hot_coins):
                coin = symbol.replace('/USDT', '')
                message += f"`{coin}` "
                if (i + 1) % 6 == 0:
                    message += "\n"
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            return
            
        # 初始化用户关注列表
        if user_id not in self.user_watchlists:
            self.user_watchlists[user_id] = set()
            
        added_coins = []
        invalid_coins = []
        
        # 获取所有可用合约
        all_contracts = await self.data_fetcher.fetch_all_contracts()
        available_symbols = set()
        for symbol in all_contracts:
            available_symbols.add(symbol)
            available_symbols.add(symbol.replace('/USDT', ''))  # 支持简写
        
        for arg in context.args:
            coin = arg.upper()
            # 标准化币种格式
            symbol = f"{coin}/USDT" if not coin.endswith('/USDT') else coin
            
            if symbol in available_symbols or coin in available_symbols:
                self.user_watchlists[user_id].add(symbol)
                added_coins.append(coin)
            else:
                invalid_coins.append(coin)
        
        response = ""
        if added_coins:
            response += f"✅ 已添加关注：{', '.join(added_coins)}\n"
        if invalid_coins:
            response += f"❌ 无效币种：{', '.join(invalid_coins)}\n"
            
        response += f"\n📊 当前关注数量：{len(self.user_watchlists[user_id])}"
        
        # 添加快速操作按钮
        keyboard = [
            [InlineKeyboardButton("📋 查看关注列表", callback_data="action_show_watchlist")],
            [InlineKeyboardButton("🔔 信号设置", callback_data="action_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup)
        
    async def remove_watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """从关注列表移除币种"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_watchlists or not self.user_watchlists[user_id]:
            await update.message.reply_text("⚠️ 您的关注列表为空。")
            return
            
        if not context.args:
            await update.message.reply_text(
                "📝 请指定要移除的币种\n"
                "💡 使用方法：/remove BTC ETH"
            )
            return
            
        removed_coins = []
        not_found_coins = []
        
        for arg in context.args:
            coin = arg.upper()
            symbol = f"{coin}/USDT"
            
            # 检查各种格式
            removed = False
            for watched_symbol in list(self.user_watchlists[user_id]):
                if coin in watched_symbol or symbol == watched_symbol:
                    self.user_watchlists[user_id].remove(watched_symbol)
                    removed_coins.append(coin)
                    removed = True
                    break
                    
            if not removed:
                not_found_coins.append(coin)
        
        response = ""
        if removed_coins:
            response += f"✅ 已移除关注：{', '.join(removed_coins)}\n"
        if not_found_coins:
            response += f"❌ 未找到币种：{', '.join(not_found_coins)}\n"
            
        response += f"\n📊 当前关注数量：{len(self.user_watchlists[user_id])}"
        
        await update.message.reply_text(response)
        
    async def show_watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示关注列表"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_watchlists or not self.user_watchlists[user_id]:
            keyboard = [
                [InlineKeyboardButton("⭐ 添加关注币种", callback_data="action_add_coins")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📋 您的关注列表为空\n\n"
                "💡 点击下方按钮添加感兴趣的币种：",
                reply_markup=reply_markup
            )
            return
            
        watchlist = list(self.user_watchlists[user_id])
        message = f"⭐ **您的关注列表** ({len(watchlist)} 个币种)\n\n"
        
        for i, symbol in enumerate(watchlist, 1):
            coin = symbol.replace('/USDT', '')
            message += f"{i}. `{coin}` "
            if i % 5 == 0:
                message += "\n"
        
        message += f"\n\n💡 使用 /remove 币种名 移除关注"
        message += f"\n💡 使用 /clear 清空关注列表"
        
        # 添加管理按钮
        keyboard = [
            [InlineKeyboardButton("➕ 添加更多", callback_data="action_add_coins")],
            [InlineKeyboardButton("🗑️ 清空列表", callback_data="action_clear_watchlist")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def clear_watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """清空关注列表"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_watchlists or not self.user_watchlists[user_id]:
            await update.message.reply_text("⚠️ 您的关注列表已经为空。")
            return
            
        count = len(self.user_watchlists[user_id])
        self.user_watchlists[user_id].clear()
        
        await update.message.reply_text(
            f"🗑️ 已清空关注列表 ({count} 个币种)\n\n"
            "💡 使用 /add 重新添加币种"
        )
        
    async def add_all_coins_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """一键关注所有币种"""
        user_id = update.effective_user.id
        
        try:
            # 获取所有合约币种
            all_contracts = await self.data_fetcher.fetch_all_contracts()
            
            if not all_contracts:
                await update.message.reply_text("❌ 获取币种列表失败，请稍后重试")
                return
            
            # 初始化用户关注列表
            if user_id not in self.user_watchlists:
                self.user_watchlists[user_id] = set()
            
            # 获取当前关注数量
            original_count = len(self.user_watchlists[user_id])
            
            # 添加所有币种到关注列表
            self.user_watchlists[user_id].update(all_contracts)
            
            # 计算新增数量
            new_count = len(self.user_watchlists[user_id])
            added_count = new_count - original_count
            
            # 格式化消息
            message = f"""
🎉 **一键关注完成！**

📊 **关注统计**：
• 总币种数量：{len(all_contracts)} 个
• 新增关注：{added_count} 个
• 当前关注：{new_count} 个

💡 **热门币种**（前15个）：
{' '.join([coin.replace('/USDT', '') for coin in all_contracts[:15]])}

⚡ **信号设置**：
现在您将收到所有 {new_count} 个币种的交易信号，包括：
🔥 高质量信号（70%+ 置信度）
⚡ 中等信号（30%+ 置信度）

🔧 使用 /watchlist 查看完整列表
🗑️ 使用 /clear 清空关注列表
            """
            
            # 添加管理按钮
            keyboard = [
                [
                    InlineKeyboardButton("📋 查看列表", callback_data="action_show_watchlist"),
                    InlineKeyboardButton("⚙️ 信号设置", callback_data="action_settings")
                ],
                [
                    InlineKeyboardButton("🔥 热门币种", callback_data="action_hot_coins"),
                    InlineKeyboardButton("🗑️ 清空列表", callback_data="action_clear_watchlist")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            self.logger.info(f"用户 {user_id} 一键关注了所有 {new_count} 个币种")
            
        except Exception as e:
            self.logger.error(f"一键关注所有币种失败: {e}")
            await update.message.reply_text("❌ 一键关注失败，请稍后重试")
        
    async def coin_query_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理币种查询命令 (/btc, /eth 等)"""
        command = update.message.text[1:].upper()  # 移除 / 并转大写
        symbol = f"{command}/USDT"
        
        # 检查是否为有效币种
        all_contracts = await self.data_fetcher.fetch_all_contracts()
        if symbol not in all_contracts:
            await update.message.reply_text(
                f"❌ 不支持的币种：{command}\n\n"
                f"💡 使用 /pairs 查看支持的币种列表"
            )
            return
            
        await self.send_coin_analysis(update, symbol)
        
    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理价格查询命令"""
        if not context.args:
            await update.message.reply_text(
                "📝 请指定币种\n💡 例如：/price BTC"
            )
            return
            
        coin = context.args[0].upper()
        symbol = f"{coin}/USDT"
        
        try:
            ticker = await self.data_fetcher.fetch_ticker(symbol)
            if ticker:
                price_message = f"""
💰 **{symbol} 价格信息**

🔸 **当前价格**：${ticker['last']:.6f}
📈 **24h 最高**：${ticker['high']:.6f}
📉 **24h 最低**：${ticker['low']:.6f}
📊 **24h 成交量**：{ticker['baseVolume']:,.0f}
🔄 **24h 涨跌幅**：{ticker['percentage']:+.2f}%
⏰ **更新时间**：{datetime.now().strftime('%H:%M:%S')}
                """
                
                # 添加查看详细分析按钮
                keyboard = [
                    [InlineKeyboardButton("📊 技术分析", callback_data=f"analysis_{coin}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    price_message, 
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(f"❌ 获取 {symbol} 价格失败")
        except Exception as e:
            self.logger.error(f"查询价格失败: {e}")
            await update.message.reply_text("❌ 查询价格失败，请稍后重试")
            
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理状态查询命令"""
        user_id = update.effective_user.id
        is_subscribed = user_id in self.subscribers
        watchlist_count = len(self.user_watchlists.get(user_id, set()))
        
        status_message = f"""
📊 **您的状态**

👤 **订阅状态**：{'✅ 已订阅' if is_subscribed else '❌ 未订阅'}
⭐ **关注币种**：{watchlist_count} 个
👥 **总订阅用户**：{len(self.subscribers)}
🤖 **机器人状态**：🟢 运行中

📋 **系统信息**：
🔄 监控间隔：30秒
🎯 信号质量：70%+ 置信度
📡 数据源：OKX API
        """
        
        # 添加操作按钮
        keyboard = []
        if is_subscribed:
            keyboard.append([InlineKeyboardButton("⚙️ 信号设置", callback_data="action_settings")])
        else:
            keyboard.append([InlineKeyboardButton("🔔 立即订阅", callback_data="action_subscribe")])
            
        keyboard.append([InlineKeyboardButton("⭐ 管理关注", callback_data="action_watchlist")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            status_message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def pairs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示支持的交易对列表"""
        try:
            all_contracts = await self.data_fetcher.fetch_all_contracts()
            
            message = f"📋 **支持的交易对** (共 {len(all_contracts)} 个)\n\n"
            message += "🔥 **热门币种**：\n"
            
            for i, symbol in enumerate(all_contracts[:30]):
                coin = symbol.replace('/USDT', '')
                message += f"`{coin}` "
                if (i + 1) % 6 == 0:
                    message += "\n"
            
            if len(all_contracts) > 30:
                message += f"\n\n📊 还有 {len(all_contracts) - 30} 个其他币种...\n"
                
            message += "\n💡 使用方法：\n"
            message += "• /btc - 查看BTC分析\n"
            message += "• /add BTC ETH - 添加到关注列表"
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            self.logger.error(f"获取交易对列表失败: {e}")
            await update.message.reply_text("❌ 获取交易对列表失败")
            
    async def channels_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示频道信息"""
        message = f"""
📺 **官方频道配置**

🔥 **主信号频道**：{self.main_channel}
• 极强信号推送（80%+ 置信度）
• 强信号推送（65%+ 置信度）
• 适合主力资金介入的高质量信号

⚠️ **副信号频道**：{self.detail_channel}  
• 中信号推送（50%+ 置信度）
• 增强弱信号推送（有突破迹象）
• 谨慎对待，适合小仓试探

💡 **信号分级说明**：
🔥 极强信号 - 强烈推荐，适合主力资金
✅ 强信号 - 可交易，需看大盘趋势  
⚠️ 中信号 - 谨慎对待，小仓试探
🟡 增强弱信号 - 有突破迹象，仅供观察

📋 **使用建议**：
• 新手：重点关注主频道的🔥极强信号
• 专业：同时关注两个频道，灵活操作
• 保守：只关注主频道的高质量信号

💬 **私聊功能**：
使用机器人私聊获得个性化服务和详细分析
        """
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理内联按钮回调"""
        query = update.callback_query
        await query.answer()
        
        action = query.data
        user_id = query.from_user.id
        
        if action == "action_subscribe":
            if user_id not in self.subscribers:
                self.subscribers.add(user_id)
                await query.edit_message_text(
                    "🎉 **订阅成功！**\n\n您将收到高质量交易信号推送。",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text("✅ 您已经订阅了信号推送！")
                
        elif action == "action_addall":
            try:
                # 获取所有合约币种
                all_contracts = await self.data_fetcher.fetch_all_contracts()
                if all_contracts:
                    # 清理用户现有关注列表
                    if user_id not in self.user_settings:
                        self.user_settings[user_id] = {}
                    self.user_settings[user_id]['watchlist'] = [
                        coin.replace('/USDT', '') for coin in all_contracts
                    ]
                    
                    await query.edit_message_text(
                        f"🔥 **一键关注成功！**\n\n"
                        f"已添加 **{len(all_contracts)}** 个币种到您的关注列表。\n\n"
                        f"包括：{', '.join([coin.replace('/USDT', '') for coin in all_contracts[:10]])}...\n\n"
                        f"使用 /watchlist 查看完整列表。",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await query.edit_message_text("❌ 获取币种列表失败，请稍后重试。")
            except Exception as e:
                self.logger.error(f"一键关注失败: {e}")
                await query.edit_message_text("❌ 一键关注失败，请稍后重试。")
        
        # 处理信号详情查看
        elif action.startswith("details_"):
            signal_id = action.replace("details_", "")
            await self.show_signal_details(query, signal_id)
        
        # 处理币种分析查看
        elif action.startswith("analysis_"):
            symbol = action.replace("analysis_", "")
            await self.show_symbol_analysis(query, symbol)
        
        elif action == "action_watchlist":
            await self._show_watchlist_inline(query)
            
        elif action == "action_help":
            await query.edit_message_text(
                "📚 **快速帮助**\n\n"
                "🔔 /subscribe - 订阅信号\n"
                "🔥 /addall - 一键关注所有币种\n"
                "⭐ /add BTC ETH - 添加关注\n"
                "🔍 /btc - 查看BTC分析\n"
                "💰 /price BTC - 查看价格\n\n"
                "💡 发送 /help 查看完整帮助",
                parse_mode=ParseMode.MARKDOWN
            )
            
        else:
            await query.edit_message_text("⚠️ 未知操作")
            
    async def show_signal_details(self, query, signal_id: str):
        """显示信号详情"""
        try:
            if signal_id in self.signal_cache:
                signal_info = self.signal_cache[signal_id]
                symbol = signal_info['symbol']
                data = signal_info['data']
                detailed_analysis = signal_info['detailed_analysis']
                priority = signal_info['priority']
                
                # 格式化详细分析
                priority_emoji = {
                    'EXTREME': '🔥',
                    'HIGH': '✅', 
                    'MEDIUM': '⚠️',
                    'LOW_ENHANCED': '🟡',
                    'LOW': '📝'
                }.get(priority, '📊')
                
                detail_message = f"""
{priority_emoji} **{symbol.replace('/USDT', '')} 详细分析**

📊 **信号强度**: {priority}
🎯 **置信度**: {data.get('confidence', 0):.1%}
📈 **方向**: {data.get('direction', 'UNKNOWN')}
💰 **入场价**: ${data.get('entry_price', 0):.4f}
🛡️ **止损价**: ${data.get('stop_loss', 0):.4f}
🎯 **止盈价**: ${data.get('take_profit', 0):.4f}

📋 **技术指标分析**:
{detailed_analysis}

⏰ **信号时间**: {datetime.fromtimestamp(signal_info['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}

⚠️ **风险提示**: 
本分析仅供参考，请结合市场环境和个人风险承受能力谨慎决策。
"""
                
                # 添加更多操作按钮
                keyboard = [
                    [InlineKeyboardButton("📈 查看永续合约K线", url=f"https://www.okx.com/trade-swap/{symbol.replace('/USDT', '-usdt-swap').lower()}")],
                    [InlineKeyboardButton("⭐ 添加关注", callback_data=f"watch_{symbol.replace('/USDT', '')}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    detail_message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text("❌ 信号详情已过期或不存在。")
                
        except Exception as e:
            self.logger.error(f"显示信号详情失败: {e}")
            await query.edit_message_text("❌ 获取详情失败，请稍后重试。")
    
    async def show_symbol_analysis(self, query, symbol: str):
        """显示币种实时分析"""
        try:
            # 添加 USDT 后缀
            full_symbol = f"{symbol}/USDT"
            
            # 获取实时数据并分析
            df = await self.data_fetcher.fetch_ohlcv(full_symbol, '1m', 100)
            
            if df is not None and len(df) >= 50:
                # 使用简化的信号分析
                analysis_result = self._analyze_symbol_simple(full_symbol, df)
                
                # 获取当前价格
                current_price = df['close'].iloc[-1]
                price_change = ((current_price - df['close'].iloc[-24]) / df['close'].iloc[-24]) * 100
                
                analysis_message = f"""
📊 **{symbol} 实时分析**

💰 **当前价格**: ${current_price:.4f}
📈 **24h涨跌**: {price_change:+.2f}%

🎯 **信号分析**:
📊 置信度: {analysis_result['confidence']:.1%}
📈 方向: {analysis_result['direction']}

🔍 **技术指标**:
• 当前RSI: {analysis_result['rsi']:.1f if isinstance(analysis_result['rsi'], (int, float)) else analysis_result['rsi']}
• 价格趋势: {analysis_result['trend']}
• 价格变化: {analysis_result['price_change']:.2f}%

⏰ **更新时间**: {datetime.now().strftime('%H:%M:%S')}

⚠️ **注意**: 实时分析仅供参考，建议结合多个时间周期综合判断。
"""
                
                # 添加操作按钮
                keyboard = [
                    [InlineKeyboardButton("📈 查看永续合约K线", url=f"https://www.okx.com/trade-swap/{symbol.lower()}-usdt-swap")],
                    [InlineKeyboardButton("⭐ 添加关注", callback_data=f"watch_{symbol}")],
                    [InlineKeyboardButton("🔄 刷新分析", callback_data=f"analysis_{symbol}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    analysis_message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(f"❌ 获取 {symbol} 数据失败，请稍后重试。")
                
        except Exception as e:
            self.logger.error(f"显示币种分析失败: {e}")
            await query.edit_message_text("❌ 分析失败，请稍后重试。")
        
    async def _show_watchlist_inline(self, query):
        """内联显示关注列表"""
        user_id = query.from_user.id
        watchlist = self.user_watchlists.get(user_id, set())
        
        if not watchlist:
            message = "📋 关注列表为空\n\n💡 使用 /add 币种名 添加关注"
        else:
            coins = [symbol.replace('/USDT', '') for symbol in watchlist]
            message = f"⭐ **关注列表** ({len(coins)} 个)\n\n"
            message += " • ".join(coins)
            
        await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
    
    def _analyze_symbol_simple(self, symbol: str, df):
        """简化的信号分析方法"""
        try:
            import pandas as pd
            import numpy as np
            
            # 获取基本数据
            close_prices = df['close']
            
            # 计算RSI
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # 计算移动平均线
            ma_fast = close_prices.rolling(window=7).mean().iloc[-1]
            ma_slow = close_prices.rolling(window=21).mean().iloc[-1]
            
            # 价格变化
            current_price = close_prices.iloc[-1]
            prev_price = close_prices.iloc[-2]
            price_change = (current_price - prev_price) / prev_price * 100
            
            # 简单信号逻辑
            confidence = 0
            direction = 'NEUTRAL'
            
            if current_rsi < 30:
                direction = 'LONG'
                confidence += 0.4
            elif current_rsi > 70:
                direction = 'SHORT'
                confidence += 0.4
                
            if ma_fast > ma_slow:
                if direction == 'LONG':
                    confidence += 0.3
                elif direction == 'NEUTRAL':
                    direction = 'LONG'
                    confidence += 0.2
            else:
                if direction == 'SHORT':
                    confidence += 0.3
                elif direction == 'NEUTRAL':
                    direction = 'SHORT'
                    confidence += 0.2
            
            return {
                'confidence': confidence,
                'direction': direction,
                'rsi': current_rsi,
                'trend': 'UP' if ma_fast > ma_slow else 'DOWN',
                'price_change': price_change
            }
            
        except Exception as e:
            self.logger.error(f"简化分析失败: {e}")
            return {
                'confidence': 0,
                'direction': 'NEUTRAL',
                'rsi': 'N/A',
                'trend': 'N/A',
                'price_change': 0
            }
        
    async def run(self):
        """启动机器人"""
        try:
            # 设置机器人命令菜单
            commands = [
                BotCommand("start", "🎯 启动机器人"),
                BotCommand("help", "📚 查看帮助"),
                BotCommand("subscribe", "🔔 订阅信号"),
                BotCommand("add", "⭐ 添加关注"),
                BotCommand("addall", "🔥 一键关注所有币种"),
                BotCommand("watchlist", "📋 查看关注"),
                BotCommand("price", "💰 查询价格"),
                BotCommand("status", "📊 查看状态"),
                BotCommand("pairs", "📋 支持币种"),
            ]
            await self.app.bot.set_my_commands(commands)
            
            # 启动机器人
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            self.logger.info("🚀 增强版Telegram机器人启动成功")
            
        except Exception as e:
            self.logger.error(f"启动机器人失败: {e}")
            raise
            
    async def stop(self):
        """停止机器人"""
        try:
            if self.app.updater.running:
                await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            self.logger.info("增强版Telegram机器人已停止")
        except Exception as e:
            self.logger.error(f"停止机器人失败: {e}")
            
    def get_subscriber_count(self):
        """获取订阅用户数量"""
        return len(self.subscribers)

    async def broadcast_signal(self, message: str, symbol: str, signal_data: dict, priority: str = 'LOW'):
        """广播信号 - 支持科学分级推送"""
        try:
            # 🎯 科学分级置信度系统配置
            priority_config = {
                'EXTREME': {
                    'emoji': '🔥',
                    'title': '极强信号',
                    'description': '强烈关注，适合主力资金介入',
                    'channel': self.main_channel,  # 高频频道
                    'urgent': True,
                    'confidence_range': '80-100%'
                },
                'HIGH': {
                    'emoji': '✅',
                    'title': '强信号',
                    'description': '可交易，但仍需看大盘与趋势',
                    'channel': self.main_channel,  # 高频频道
                    'urgent': False,
                    'confidence_range': '65-80%'
                },
                'MEDIUM': {
                    'emoji': '⚠️',
                    'title': '中信号',
                    'description': '谨慎对待，仅适合小仓试探',
                    'channel': self.detail_channel,  # 中频频道
                    'urgent': False,
                    'confidence_range': '50-65%'
                },
                'LOW_ENHANCED': {
                    'emoji': '🟡',
                    'title': '弱信号',
                    'description': '暂不建议直接交易，可观察',
                    'channel': self.detail_channel,  # 中频频道
                    'urgent': False,
                    'confidence_range': '35-50%'
                },
                'NOISE': {
                    'emoji': '❌',
                    'title': '噪音信号',
                    'description': '回测中表现差，已过滤',
                    'channel': None,  # 不推送到任何频道
                    'urgent': False,
                    'confidence_range': '0-35%'
                }
            }
            
            config = priority_config.get(priority, priority_config['NOISE'])
            
            # 🛑 NOISE信号不推送到任何频道或用户
            if priority == 'NOISE':
                self.logger.info(f"过滤NOISE信号: {symbol} (置信度过低)")
                return
            
            # 格式化信号消息
            confidence = signal_data.get('confidence', 0)
            direction = signal_data.get('direction', 'UNKNOWN')
            entry_price = signal_data.get('entry_price', 0)
            
            # 创建简洁的信号消息
            brief_message = f"""{config['emoji']} <b>{config['title']}</b> - {symbol.replace('/USDT', '')}

📊 <b>方向</b>: {direction}
🎯 <b>置信度</b>: {confidence:.1%}
💰 <b>入场价</b>: ${entry_price:.4f}
📋 <b>建议</b>: {config['description']}

⏰ {datetime.now().strftime('%H:%M:%S')}"""
            
            # 创建内联按钮
            signal_id = f"{symbol}_{direction}_{int(time.time())}"
            self.signal_cache[signal_id] = {
                'symbol': symbol,
                'data': signal_data,
                'detailed_analysis': message,
                'timestamp': time.time(),
                'priority': priority
            }
            
            keyboard = [
                [InlineKeyboardButton("🔍 查看详情", callback_data=f"details_{signal_id}")],
                [InlineKeyboardButton(f"📊 {symbol.replace('/USDT', '')} 分析", callback_data=f"analysis_{symbol.replace('/USDT', '')}")]
            ]
            
            if config['urgent']:
                keyboard.insert(0, [InlineKeyboardButton("⚡ 立即查看永续合约", url=f"https://www.okx.com/trade-swap/{symbol.replace('/USDT', '-usdt-swap').lower()}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 发送到配置的频道（如果配置了频道）
            if config['channel']:
                try:
                    await self.app.bot.send_message(
                        chat_id=config['channel'],
                        text=brief_message,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    self.logger.info(f"成功发送 {symbol} {priority} 信号到频道")
                except Exception as e:
                    self.logger.error(f"发送到频道失败: {e}")
            else:
                self.logger.info(f"跳过频道发送（{priority} 信号不推送到频道）")
            
            # 发送给已订阅的用户（根据用户设置过滤）
            successful_sends = 0
            total_subscribers = len(self.subscribers)
            
            for user_id in list(self.subscribers):
                try:
                    # 检查用户的信号质量偏好
                    user_settings = self.user_settings.get(user_id, {})
                    notification_level = user_settings.get('notification_level', 'HIGH')
                    watchlist_only = user_settings.get('watchlist_only', False)
                    user_watchlist = user_settings.get('watchlist', [])
                    
                    # 信号质量过滤
                    should_send = False
                    if notification_level == 'ALL':
                        should_send = priority in ['EXTREME', 'HIGH', 'MEDIUM', 'LOW_ENHANCED']
                    elif notification_level == 'HIGH':
                        should_send = priority in ['EXTREME', 'HIGH']
                    elif notification_level == 'MEDIUM':
                        should_send = priority in ['EXTREME', 'HIGH', 'MEDIUM']
                    
                    # 关注列表过滤
                    if watchlist_only and user_watchlist:
                        coin_symbol = symbol.replace('/USDT', '')
                        if coin_symbol not in user_watchlist:
                            should_send = False
                    
                    if should_send:
                        await self.app.bot.send_message(
                            chat_id=user_id,
                            text=brief_message,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup
                        )
                        successful_sends += 1
                        
                except Exception as e:
                    self.logger.warning(f"发送给用户 {user_id} 失败: {e}")
                    if "bot was blocked" in str(e).lower():
                        self.subscribers.discard(user_id)
            
            self.logger.info(f"信号广播完成: {successful_sends}/{total_subscribers} 用户")
            
        except Exception as e:
            self.logger.error(f"广播信号失败: {e}") 