#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX USDT永续合约监控系统
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List
import pandas as pd
import numpy as np

from signal_tracker_v2 import ImprovedSignalTracker
from telegram_bot_enhanced import EnhancedTelegramBot
from data_fetcher_okx import OKXDataFetcher
from config import *

class SimpleOKXMonitor:
    """OKX监控器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # 核心组件
        self.data_fetcher = OKXDataFetcher()
        self.signal_tracker = ImprovedSignalTracker()
        self.telegram_bot = EnhancedTelegramBot()
        
        # 监控配置 - 动态获取合约列表
        self.symbols = []  # 将在启动时动态获取
        self.running = False
        
        # 性能优化配置
        self.max_concurrent_requests = 5  # 进一步降低并发数避免429错误
        self.semaphore = None  # 将在start()中创建
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    async def init_symbols(self):
        """动态获取所有USDT永续合约"""
        try:
            self.logger.info("正在获取最新的USDT永续合约列表...")
            
            # 获取动态合约列表
            dynamic_symbols = await self.data_fetcher.fetch_all_contracts(force_refresh=True)
            
            if dynamic_symbols and len(dynamic_symbols) > 0:
                self.symbols = dynamic_symbols
                self.logger.info(f"✅ 动态获取到 {len(self.symbols)} 个活跃USDT永续合约")
                
                # 显示前20个合约作为示例
                sample_symbols = [s.replace('/USDT', '') for s in self.symbols[:20]]
                self.logger.info(f"📋 合约示例: {', '.join(sample_symbols)}...")
                
            else:
                # 后备方案：使用静态列表
                self.symbols = TRADING_PAIRS
                self.logger.warning(f"⚠️ 动态获取失败，使用静态列表: {len(self.symbols)} 个合约")
                
        except Exception as e:
            # 后备方案：使用静态列表
            self.symbols = TRADING_PAIRS
            self.logger.error(f"❌ 动态获取合约失败: {e}")
            self.logger.info(f"🔄 使用静态后备列表: {len(self.symbols)} 个合约")

    async def start(self):
        """启动监控系统"""
        self.logger.info("启动OKX监控系统")
        
        try:
            # 创建并发限制信号量
            self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)
            
            # 动态获取合约列表
            await self.init_symbols()
            
            # 启动Telegram机器人
            asyncio.create_task(self.telegram_bot.run())
            await asyncio.sleep(3)  # 等待机器人启动
            
            # 日志输出监控范围
            self.logger.info(f"🚀 准备开始监控 {len(self.symbols)} 个USDT永续合约")
            self.logger.info(f"⚡ 并发限制: {self.max_concurrent_requests} 个请求")
            self.logger.info(f"⏰ 监控间隔: {SIGNAL_CHECK_INTERVAL} 秒")
            
            # 开始监控循环
            self.running = True
            await self.monitoring_loop()
            
        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
        except Exception as e:
            self.logger.error(f"系统错误: {e}")
            raise
        finally:
            await self.stop()

    async def monitoring_loop(self):
        """主监控循环"""
        self.logger.info(f"开始监控 {len(self.symbols)} 个合约")
        
        while self.running:
            try:
                await self.process_contracts()
                await asyncio.sleep(SIGNAL_CHECK_INTERVAL)  # 使用配置文件参数
                
            except Exception as e:
                self.logger.error(f"监控错误: {e}")
                await asyncio.sleep(SIGNAL_CHECK_INTERVAL)

    async def process_contracts(self):
        """处理合约数据 - 并发批量处理"""
        
        # 创建并发处理任务
        tasks = []
        for symbol in self.symbols:
            task = self.process_single_contract(symbol)
            tasks.append(task)
        
        # 并发执行所有任务
        start_time = datetime.now()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计处理结果
        success_count = sum(1 for r in results if r is not None and not isinstance(r, Exception))
        error_count = sum(1 for r in results if isinstance(r, Exception))
        duration = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(f"批量处理完成: 成功 {success_count}/{len(self.symbols)} 个合约，"
                        f"耗时 {duration:.2f}秒，错误 {error_count} 个")
    
    async def process_single_contract(self, symbol: str):
        """处理单个合约数据 - 带并发限制"""
        async with self.semaphore:  # 限制并发数
            try:
                # 获取市场数据
                market_data = await self.data_fetcher.get_market_data(symbol)
                
                if market_data and market_data['ohlcv'] is not None:
                    # 信号分析
                    signal = self.analyze_simple_signal(symbol, market_data)
                    
                    if signal:
                        await self.handle_signal(symbol, signal, market_data)
                        return signal
                
                return None
                
            except Exception as e:
                self.logger.debug(f"处理 {symbol} 失败: {e}")
                raise e

    def analyze_simple_signal(self, symbol: str, market_data: Dict) -> Dict:
        """信号分析"""
        try:
            df = market_data['ohlcv']
            ticker = market_data['ticker']
            
            if df is None or len(df) < 50:
                return None
            
            close_prices = df['close']
            
            # RSI计算 - 使用配置文件参数
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # 移动平均线 - 使用配置文件参数
            ma_fast = close_prices.rolling(window=MA_SHORT).mean().iloc[-1]
            ma_slow = close_prices.rolling(window=MA_LONG).mean().iloc[-1]
            
            # 价格变化
            price_change = (ticker['last'] - close_prices.iloc[-2]) / close_prices.iloc[-2] * 100
            
            # 信号逻辑
            signals = []
            confidence = 0
            
            # RSI信号 - 使用配置文件参数
            if current_rsi < RSI_OVERSOLD:
                signals.append('LONG')
                confidence += 0.4
            elif current_rsi > RSI_OVERBOUGHT:
                signals.append('SHORT')
                confidence += 0.4
            
            # 均线信号
            if ma_fast > ma_slow:
                signals.append('LONG')
                confidence += 0.3
            else:
                signals.append('SHORT')
                confidence += 0.3
            
            # 价格突破信号
            if abs(price_change) > 2:
                if price_change > 0:
                    signals.append('LONG')
                else:
                    signals.append('SHORT')
                confidence += 0.4
            
            # 成交量确认 - 使用配置文件参数
            if 'volume' in df.columns and len(df) >= VOLUME_SMA_PERIOD:
                volume_ma = df['volume'].rolling(window=VOLUME_SMA_PERIOD).mean().iloc[-1]
                current_volume = df['volume'].iloc[-1]
                if current_volume > volume_ma * VOLUME_THRESHOLD:
                    confidence += 0.2
            
            # 判断信号方向
            if len(signals) >= 2 and confidence >= 0.5:
                long_count = signals.count('LONG')
                short_count = signals.count('SHORT')
                
                if long_count > short_count:
                    direction = 'LONG'
                elif short_count > long_count:
                    direction = 'SHORT'
                else:
                    return None
                
                return {
                    'direction': direction,
                    'confidence': confidence,
                    'rsi': current_rsi,
                    'price_change': price_change,
                    'entry_price': ticker['last']
                }
            
            return None
            
        except Exception as e:
            self.logger.debug(f"分析 {symbol} 信号失败: {e}")
            return None

    async def handle_signal(self, symbol: str, signal: Dict, market_data: Dict):
        """处理信号"""
        try:
            # 添加到信号跟踪器
            self.signal_tracker.add_signal(
                symbol=symbol,
                direction=signal['direction'],
                entry_price=signal['entry_price'],
                confidence=signal['confidence'],
                signal_data=signal
            )
            
            # 发送到Telegram
            await self.send_telegram_signal(symbol, signal, market_data)
            
            self.logger.info(f"发现信号: {symbol} {signal['direction']} (置信度: {signal['confidence']:.1%})")
            
        except Exception as e:
            self.logger.error(f"处理信号失败: {e}")

    async def send_telegram_signal(self, symbol: str, signal: Dict, market_data: Dict):
        """发送信号到Telegram"""
        try:
            ticker = market_data['ticker']
            confidence = signal['confidence']
            
            # 确定优先级
            if confidence >= 0.8:
                priority = 'EXTREME'
                priority_desc = '极强信号'
            elif confidence >= 0.65:
                priority = 'HIGH'
                priority_desc = '强信号'
            elif confidence >= 0.5:
                priority = 'MEDIUM'
                priority_desc = '中信号'
            else:
                return  # 过滤低置信度信号
            
            # 生成交易链接
            trading_url = self.data_fetcher.get_swap_trading_url(symbol)
            
            # 构建消息
            direction_text = '做多' if signal['direction'] == 'LONG' else '做空'
            message = f"""{priority_desc} - {symbol.replace('/USDT', '')}

方向: {direction_text}
价格: ${ticker['last']:.6f}
置信度: {signal['confidence']:.1%}

技术指标:
• RSI: {signal['rsi']:.1f}
• 价格变化: {signal['price_change']:.2f}%
• 24H涨跌: {ticker['percentage']:.2f}%

交易链接: {trading_url}
时间: {datetime.now().strftime('%H:%M:%S')}"""
            
            # 发送消息
            await self.telegram_bot.broadcast_signal(
                message=message,
                symbol=symbol,
                signal_data=signal,
                priority=priority
            )
            
        except Exception as e:
            self.logger.error(f"发送Telegram信号失败: {e}")

    async def stop(self):
        """停止系统"""
        self.logger.info("停止监控系统")
        self.running = False
        
        if hasattr(self.telegram_bot, 'stop'):
            await self.telegram_bot.stop()

async def main():
    """主函数"""
    monitor = SimpleOKXMonitor()
    await monitor.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序启动失败: {e}") 