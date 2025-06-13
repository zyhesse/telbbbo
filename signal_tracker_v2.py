#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版信号追踪器 v2.0
- 多时间窗口验证（3min/5min/10min）
- 更大的盈亏阈值（≥0.3%-0.5%）
- 滚动胜率统计和盈亏比追踪
- DRAW状态后续追踪
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

class SignalStatus(Enum):
    ACTIVE = "ACTIVE"
    WIN = "WIN"
    LOSS = "LOSS"
    DRAW = "DRAW"
    EXPIRED = "EXPIRED"

@dataclass
class ValidationWindow:
    """验证时间窗口"""
    duration_minutes: int
    profit_threshold: float  # 盈利阈值
    loss_threshold: float    # 亏损阈值
    name: str

@dataclass
class SignalEvaluation:
    """信号评估结果"""
    symbol: str
    entry_price: float
    entry_time: datetime
    current_price: float
    current_time: datetime
    
    # 多窗口结果
    window_results: Dict[str, str]  # 窗口名称 -> 结果状态
    
    # 统计信息
    max_profit_pct: float = 0.0
    max_loss_pct: float = 0.0
    duration_minutes: float = 0.0
    
    # 最终状态
    final_status: SignalStatus = SignalStatus.ACTIVE
    final_profit_pct: float = 0.0

@dataclass
class PerformanceStats:
    """性能统计"""
    total_signals: int = 0
    
    # 按时间窗口分类
    win_3min: int = 0
    loss_3min: int = 0
    draw_3min: int = 0
    
    win_5min: int = 0
    loss_5min: int = 0
    draw_5min: int = 0
    
    win_10min: int = 0
    loss_10min: int = 0
    draw_10min: int = 0
    
    # 综合统计
    total_wins: int = 0
    total_losses: int = 0
    total_draws: int = 0
    
    # 收益统计
    total_profit_pct: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    
    # 高级指标
    profit_factor: float = 0.0  # 总盈利/总亏损
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    def win_rate(self, window: str = "overall") -> float:
        """计算胜率"""
        if window == "3min":
            total = self.win_3min + self.loss_3min + self.draw_3min
            return self.win_3min / total if total > 0 else 0.0
        elif window == "5min":
            total = self.win_5min + self.loss_5min + self.draw_5min
            return self.win_5min / total if total > 0 else 0.0
        elif window == "10min":
            total = self.win_10min + self.loss_10min + self.draw_10min
            return self.win_10min / total if total > 0 else 0.0
        else:  # overall
            total = self.total_wins + self.total_losses + self.total_draws
            return self.total_wins / total if total > 0 else 0.0

class ImprovedSignalTracker:
    """改进版信号追踪器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 验证窗口配置
        self.validation_windows = [
            ValidationWindow(3, 0.3, -0.3, "3min"),   # 3分钟，±0.3%
            ValidationWindow(5, 0.4, -0.4, "5min"),   # 5分钟，±0.4%
            ValidationWindow(10, 0.5, -0.5, "10min")  # 10分钟，±0.5%
        ]
        
        # 活跃信号存储
        self.active_signals: Dict[str, Dict] = {}  # signal_id -> signal_data
        
        # 历史记录
        self.signal_history: List[SignalEvaluation] = []
        
        # 性能统计
        self.performance_stats = PerformanceStats()
        
        # 连续胜负追踪
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        
        self.logger.info("ImprovedSignalTracker 初始化完成")

    def add_signal(self, symbol: str, direction: str, entry_price: float, 
                   confidence: float, signal_data: Dict) -> str:
        """添加新信号进行追踪"""
        
        signal_id = f"{symbol}_{direction}_{int(time.time())}"
        entry_time = datetime.now()
        
        signal_info = {
            'id': signal_id,
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'confidence': confidence,
            'signal_data': signal_data,
            
            # 追踪数据
            'max_profit_pct': 0.0,
            'max_loss_pct': 0.0,
            'window_results': {},
            'status': SignalStatus.ACTIVE,
            
            # 价格更新历史
            'price_history': [(entry_time, entry_price)]
        }
        
        # 初始化窗口结果
        for window in self.validation_windows:
            signal_info['window_results'][window.name] = SignalStatus.ACTIVE.value
        
        self.active_signals[signal_id] = signal_info
        self.performance_stats.total_signals += 1
        
        self.logger.info(f"新增信号追踪: {signal_id} - {symbol} {direction} @{entry_price}")
        return signal_id

    def update_prices(self, current_prices: Dict[str, float]) -> List[SignalEvaluation]:
        """更新价格并评估信号状态"""
        current_time = datetime.now()
        evaluations = []
        
        signals_to_remove = []
        
        for signal_id, signal_info in self.active_signals.items():
            symbol = signal_info['symbol']
            
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            entry_price = signal_info['entry_price']
            direction = signal_info['direction']
            entry_time = signal_info['entry_time']
            
            # 计算收益率
            if direction.upper() == "LONG":
                profit_pct = (current_price - entry_price) / entry_price * 100
            else:  # SHORT
                profit_pct = (entry_price - current_price) / entry_price * 100
            
            # 更新最大盈利/亏损
            signal_info['max_profit_pct'] = max(signal_info['max_profit_pct'], profit_pct)
            signal_info['max_loss_pct'] = min(signal_info['max_loss_pct'], profit_pct)
            
            # 添加价格历史
            signal_info['price_history'].append((current_time, current_price))
            
            # 计算持续时间
            duration_minutes = (current_time - entry_time).total_seconds() / 60
            
            # 评估各个时间窗口
            signal_completed = False
            
            for window in self.validation_windows:
                window_name = window.name
                
                # 跳过已完成的窗口
                if signal_info['window_results'][window_name] != SignalStatus.ACTIVE.value:
                    continue
                
                # 检查时间是否到达
                if duration_minutes >= window.duration_minutes:
                    # 根据阈值判断结果
                    if profit_pct >= window.profit_threshold:
                        result = SignalStatus.WIN
                    elif profit_pct <= window.loss_threshold:
                        result = SignalStatus.LOSS
                    else:
                        result = SignalStatus.DRAW
                    
                    signal_info['window_results'][window_name] = result.value
                    self._update_window_stats(window_name, result)
                    
                    self.logger.info(
                        f"窗口完成 {signal_id} {window_name}: {result.value} "
                        f"({profit_pct:.2f}%)"
                    )
                
                # 提前触发盈亏阈值
                elif profit_pct >= window.profit_threshold:
                    signal_info['window_results'][window_name] = SignalStatus.WIN.value
                    self._update_window_stats(window_name, SignalStatus.WIN)
                    
                elif profit_pct <= window.loss_threshold:
                    signal_info['window_results'][window_name] = SignalStatus.LOSS.value
                    self._update_window_stats(window_name, SignalStatus.LOSS)
            
            # 检查信号是否完全完成（所有窗口都有结果）
            all_windows_complete = all(
                result != SignalStatus.ACTIVE.value 
                for result in signal_info['window_results'].values()
            )
            
            # 或者超过最大时间限制（15分钟）
            if duration_minutes > 15:
                all_windows_complete = True
                for window_name in signal_info['window_results']:
                    if signal_info['window_results'][window_name] == SignalStatus.ACTIVE.value:
                        signal_info['window_results'][window_name] = SignalStatus.EXPIRED.value
            
            if all_windows_complete:
                # 确定最终状态（以最长时间窗口为准）
                final_result = signal_info['window_results']['10min']
                if final_result == SignalStatus.ACTIVE.value:
                    final_result = SignalStatus.EXPIRED.value
                
                signal_info['status'] = final_result
                
                # 更新总体统计
                self._update_overall_stats(final_result, profit_pct)
                
                # 创建评估结果
                evaluation = SignalEvaluation(
                    symbol=symbol,
                    entry_price=entry_price,
                    entry_time=entry_time,
                    current_price=current_price,
                    current_time=current_time,
                    window_results=signal_info['window_results'].copy(),
                    max_profit_pct=signal_info['max_profit_pct'],
                    max_loss_pct=signal_info['max_loss_pct'],
                    duration_minutes=duration_minutes,
                    final_status=SignalStatus(final_result),
                    final_profit_pct=profit_pct
                )
                
                evaluations.append(evaluation)
                self.signal_history.append(evaluation)
                signals_to_remove.append(signal_id)
                
                self.logger.info(f"信号完成: {signal_id} - 最终结果: {final_result} ({profit_pct:.2f}%)")
        
        # 移除已完成的信号
        for signal_id in signals_to_remove:
            del self.active_signals[signal_id]
        
        return evaluations

    def _update_window_stats(self, window_name: str, result: SignalStatus):
        """更新窗口统计"""
        if window_name == "3min":
            if result == SignalStatus.WIN:
                self.performance_stats.win_3min += 1
            elif result == SignalStatus.LOSS:
                self.performance_stats.loss_3min += 1
            else:
                self.performance_stats.draw_3min += 1
                
        elif window_name == "5min":
            if result == SignalStatus.WIN:
                self.performance_stats.win_5min += 1
            elif result == SignalStatus.LOSS:
                self.performance_stats.loss_5min += 1
            else:
                self.performance_stats.draw_5min += 1
                
        elif window_name == "10min":
            if result == SignalStatus.WIN:
                self.performance_stats.win_10min += 1
            elif result == SignalStatus.LOSS:
                self.performance_stats.loss_10min += 1
            else:
                self.performance_stats.draw_10min += 1

    def _update_overall_stats(self, result: str, profit_pct: float):
        """更新总体统计"""
        if result == SignalStatus.WIN.value:
            self.performance_stats.total_wins += 1
            self.performance_stats.total_profit_pct += profit_pct
            
            # 更新平均盈利
            if self.performance_stats.total_wins > 0:
                total_win_profit = (self.performance_stats.avg_win_pct * (self.performance_stats.total_wins - 1) + profit_pct)
                self.performance_stats.avg_win_pct = total_win_profit / self.performance_stats.total_wins
            
            # 连续胜负追踪
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.performance_stats.max_consecutive_wins = max(
                self.performance_stats.max_consecutive_wins, 
                self.consecutive_wins
            )
            
        elif result == SignalStatus.LOSS.value:
            self.performance_stats.total_losses += 1
            self.performance_stats.total_profit_pct += profit_pct  # 负数
            
            # 更新平均亏损
            if self.performance_stats.total_losses > 0:
                total_loss_profit = (self.performance_stats.avg_loss_pct * (self.performance_stats.total_losses - 1) + profit_pct)
                self.performance_stats.avg_loss_pct = total_loss_profit / self.performance_stats.total_losses
            
            # 连续胜负追踪
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self.performance_stats.max_consecutive_losses = max(
                self.performance_stats.max_consecutive_losses,
                self.consecutive_losses
            )
            
        else:  # DRAW or EXPIRED
            self.performance_stats.total_draws += 1
        
        # 更新盈利因子
        total_win_amount = self.performance_stats.avg_win_pct * self.performance_stats.total_wins
        total_loss_amount = abs(self.performance_stats.avg_loss_pct * self.performance_stats.total_losses)
        
        if total_loss_amount > 0:
            self.performance_stats.profit_factor = total_win_amount / total_loss_amount
        else:
            self.performance_stats.profit_factor = float('inf') if total_win_amount > 0 else 0

    def get_active_signals_count(self) -> int:
        """获取活跃信号数量"""
        return len(self.active_signals)

    def get_performance_summary(self) -> Dict:
        """获取性能总结"""
        stats = self.performance_stats
        
        return {
            "总信号数": stats.total_signals,
            "活跃信号": len(self.active_signals),
            
            "3分钟窗口": {
                "胜率": f"{stats.win_rate('3min'):.1%}",
                "胜/负/平": f"{stats.win_3min}/{stats.loss_3min}/{stats.draw_3min}"
            },
            
            "5分钟窗口": {
                "胜率": f"{stats.win_rate('5min'):.1%}",
                "胜/负/平": f"{stats.win_5min}/{stats.loss_5min}/{stats.draw_5min}"
            },
            
            "10分钟窗口": {
                "胜率": f"{stats.win_rate('10min'):.1%}",
                "胜/负/平": f"{stats.win_10min}/{stats.loss_10min}/{stats.draw_10min}"
            },
            
            "总体表现": {
                "胜率": f"{stats.win_rate('overall'):.1%}",
                "总收益": f"{stats.total_profit_pct:.2f}%",
                "平均盈利": f"{stats.avg_win_pct:.2f}%",
                "平均亏损": f"{stats.avg_loss_pct:.2f}%",
                "盈利因子": f"{stats.profit_factor:.2f}",
                "最大连胜": stats.max_consecutive_wins,
                "最大连败": stats.max_consecutive_losses
            }
        }

    def get_recent_signals(self, limit: int = 10) -> List[Dict]:
        """获取最近的信号历史"""
        recent = self.signal_history[-limit:] if len(self.signal_history) >= limit else self.signal_history
        
        results = []
        for eval_result in recent:
            results.append({
                "符号": eval_result.symbol,
                "入场时间": eval_result.entry_time.strftime("%H:%M:%S"),
                "持续时间": f"{eval_result.duration_minutes:.1f}分钟",
                "最终收益": f"{eval_result.final_profit_pct:.2f}%",
                "最大盈利": f"{eval_result.max_profit_pct:.2f}%",
                "最大亏损": f"{eval_result.max_loss_pct:.2f}%",
                "最终状态": eval_result.final_status.value,
                "窗口结果": eval_result.window_results
            })
        
        return results

    def format_performance_message(self) -> str:
        """格式化性能消息"""
        summary = self.get_performance_summary()
        
        msg = "📊 信号追踪性能报告\n"
        msg += "=" * 30 + "\n\n"
        
        msg += f"📈 总体概况:\n"
        msg += f"• 总信号数: {summary['总信号数']}\n"
        msg += f"• 活跃信号: {summary['活跃信号']}\n"
        msg += f"• 总体胜率: {summary['总体表现']['胜率']}\n"
        msg += f"• 累计收益: {summary['总体表现']['总收益']}\n\n"
        
        msg += f"⏱️ 时间窗口表现:\n"
        for window in ["3分钟窗口", "5分钟窗口", "10分钟窗口"]:
            data = summary[window]
            msg += f"• {window}: {data['胜率']} ({data['胜/负/平']})\n"
        
        msg += f"\n📊 详细指标:\n"
        details = summary['总体表现']
        msg += f"• 平均盈利: {details['平均盈利']}\n"
        msg += f"• 平均亏损: {details['平均亏损']}\n"
        msg += f"• 盈利因子: {details['盈利因子']}\n"
        msg += f"• 最大连胜: {details['最大连胜']}\n"
        msg += f"• 最大连败: {details['最大连败']}\n"
        
        return msg 