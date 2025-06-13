# 加密货币交易信号Telegram机器人

🚀 基于实时技术指标分析的加密货币交易信号推送系统

## 📋 功能特性

- ✅ **实时数据获取**: 通过OKX API获取实时K线数据
- ✅ **技术指标分析**: 支持RSI、MACD、布林带、移动平均线等多种指标
- ✅ **智能信号检测**: 基于技术指标变化识别做多做空时机
- ✅ **Telegram推送**: 实时推送交易信号到Telegram
- ✅ **信号过滤**: 避免重复信号，减少干扰
- ✅ **多交易对监控**: 同时监控BTC、ETH、SOL等多个主流币种
- ✅ **用户订阅管理**: 支持用户自主订阅/取消订阅
- ✅ **实时价格查询**: 查询任意支持交易对的实时价格
- ✅ **手动信号查询**: 主动查询特定交易对的交易信号

## 🛠️ 技术栈

- **Python 3.10+**
- **ccxt**: 加密货币交易所API库
- **python-telegram-bot**: Telegram机器人库
- **pandas/numpy**: 数据处理和技术指标计算
- **asyncio**: 异步编程

## 📦 安装指南

### 1. 环境准备

确保您的系统已安装Python 3.10或更高版本：

```bash
python --version
```

### 2. 克隆或下载项目

如果是从Git仓库克隆：
```bash
git clone <repository-url>
cd btc
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 环境配置

复制环境变量示例文件并配置：
```bash
# 复制环境变量模板（如果存在）
cp .env.example .env

# 编辑环境变量文件
nano .env
```

在 `.env` 文件中设置：
```bash
# Telegram Bot Token - 从 @BotFather 获取
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

**⚠️ 安全提示：**
- 请勿将包含真实Token的 `.env` 文件提交到版本控制系统
- 确保 `.env` 文件在 `.gitignore` 中

### 5. 配置设置

编辑 `config.py` 文件，根据需要调整以下配置：

- 技术指标参数（RSI、MACD等）
- `TRADING_PAIRS`: 要监控的交易对列表
- `SIGNAL_CHECK_INTERVAL`: 信号检查间隔（秒）

## 🚀 使用方法

### 启动机器人

**推荐方式**：
```bash
python main.py
```

### Telegram机器人命令

1. **启动机器人**: 在Telegram中搜索您的机器人并发送 `/start`

2. **订阅信号**: `/subscribe` - 开始接收交易信号推送

3. **查询价格**: `/price BTC` - 查询比特币实时价格

4. **币种分析**: `/btc` - 获取BTC实时分析

5. **查看支持的交易对**: `/pairs`

6. **查看状态**: `/status`

7. **取消订阅**: `/unsubscribe`

8. **帮助信息**: `/help`

## 📊 信号类型说明

### 信号标识
- 🟢 **LONG**: 做多信号（买入）
- 🔴 **SHORT**: 做空信号（卖出）

### 信号强度
- 🔥 **EXTREME**: 极强信号（80%+ 置信度）
- ✅ **HIGH**: 强信号（65%+ 置信度）
- ⚠️ **MEDIUM**: 中等强度信号（50%+ 置信度）

### 信号来源
1. **RSI超买超卖**: RSI指标穿越20/80阈值
2. **移动平均线交叉**: 短期均线与长期均线交叉
3. **价格突破**: 价格突破关键支撑阻力位
4. **成交量确认**: 放量突破增强信号可靠性

## ⚙️ 配置说明

### 主要配置参数

```python
# 技术分析参数（已优化为1分钟高频参数）
RSI_PERIOD = 9           # RSI周期
RSI_OVERSOLD = 20        # RSI超卖阈值
RSI_OVERBOUGHT = 80      # RSI超买阈值

MA_SHORT = 7             # 短期均线周期
MA_LONG = 30             # 长期均线周期

BOLLINGER_PERIOD = 14    # 布林带周期
BOLLINGER_STD = 1.5      # 布林带标准差

# 信号检查间隔
SIGNAL_CHECK_INTERVAL = 30  # 信号检查间隔（秒）
```

### 支持的交易对

系统支持241个USDT永续合约，包括：
- BTC/USDT, ETH/USDT, SOL/USDT
- DOGE/USDT, XRP/USDT, ADA/USDT
- 以及更多主流和新兴币种

使用 `/pairs` 命令查看完整列表。

## 📝 日志文件

程序运行时会生成 `trading.log` 文件，包含：
- 系统启动/停止信息
- 数据获取状态
- 信号检测结果
- 用户订阅操作
- 错误和异常信息

## ⚠️ 风险提示

1. **仅供参考**: 本机器人提供的信号仅基于技术分析，不构成投资建议
2. **风险自负**: 请结合自己的分析判断，谨慎投资
3. **市场风险**: 加密货币市场波动较大，请注意风险控制
4. **技术限制**: 技术指标存在滞后性，可能产生虚假信号

## 🔧 故障排除

### 常见问题

1. **无法获取数据**
   - 检查网络连接
   - 确认OKX API可访问
   - 查看日志文件中的错误信息

2. **Telegram机器人无响应**
   - 验证Bot Token是否正确设置在环境变量中
   - 确认机器人已启动
   - 检查网络连接

3. **环境变量未设置**
   - 确保创建了 `.env` 文件
   - 验证 `TELEGRAM_BOT_TOKEN` 正确设置
   - 重启程序使环境变量生效

4. **依赖安装失败**
   - 更新pip: `pip install --upgrade pip`
   - 使用国内镜像: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/`

### 解决方案

如果遇到依赖安装问题，可以尝试：

```bash
# 更新pip
python -m pip install --upgrade pip

# 使用清华镜像安装
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 或者逐个安装关键依赖
pip install ccxt python-telegram-bot pandas numpy python-dotenv asyncio aiohttp
```

## 📞 支持

如果您遇到问题或有建议，请：
1. 查看日志文件获取详细错误信息
2. 确认配置文件和环境变量设置正确
3. 检查网络连接和API访问权限

## 📄 许可证

此项目仅供学习和研究使用。请遵守相关法律法规和交易所使用条款。 