# 配置文件
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# 验证必要的环境变量
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN 环境变量未设置！请检查 .env 文件")

# 交易所配置
EXCHANGE = 'okx'      # 使用OKX交易所
SYMBOL = 'BTC/USDT'   # 默认交易对

# ============ High-Frequency (1-Minute) Optimized Parameters ============ #
# 适用币种：BTC/USDT, ETH/USDT, OKB/USDT, ADA/USDT, XRP/USDT, SOL/USDT, DOGE/USDT
# ------------------------------------------------------------------------ #

# 🔍 RSI – Relative Strength Index
RSI_PERIOD = 9       # 更短周期 → 减小滞后
RSI_OVERSOLD = 20    # 超卖阈值（做多）
RSI_OVERBOUGHT = 80  # 超买阈值（做空）

# 📈 Moving Averages – 使用 EMA 做趋势滤波
MA_SHORT = 7         # 快速 EMA（原 MA_SHORT）
MA_LONG = 30         # 慢速 EMA（原 MA_LONG）

# 📊 Bollinger Bands
BOLLINGER_PERIOD = 14  # 缩短周期，带宽更及时
BOLLINGER_STD = 1.5    # 缩窄上下轨，提高突破敏感度

# ⚡ MACD – Moving Average Convergence Divergence
EMA_FAST = 5         # 快线 EMA
EMA_SLOW = 13        # 慢线 EMA
EMA_SIGNAL = 6       # 信号线 EMA

# 📊 Volume Analysis
VOLUME_SMA_PERIOD = 14   # 近期 14 根 K 线平均量
VOLUME_THRESHOLD = 2.0   # 成交量 > 2× 均量 ⇒ "放量"

# 📉 Support / Resistance
SUPPORT_RESISTANCE_PERIOD = 50  # 回看近 50 根 K 线高低点

# ⏱️ Scheduler - 针对全量监控优化
SIGNAL_CHECK_INTERVAL = 60  # 秒 - 增加到60秒，适配全量监控
DATA_FETCH_INTERVAL = 60    # 秒

# 支持的交易对列表 - 所有OKX USDT永续合约 (241个)
TRADING_PAIRS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'SOL/USDT', 'DOGE/USDT', 'DOT/USDT', 'SHIB/USDT', 'AVAX/USDT',
    'TRX/USDT', 'LINK/USDT', 'UNI/USDT', 'LTC/USDT', 'BCH/USDT', 'NEAR/USDT', 'ATOM/USDT', 'MANA/USDT', 'SAND/USDT', 'ALGO/USDT',
    'ICP/USDT', 'FIL/USDT', 'HBAR/USDT', 'ETC/USDT', 'THETA/USDT', 'XLM/USDT', 'AAVE/USDT', 'PEPE/USDT', 'ARB/USDT', 'OP/USDT',
    'APT/USDT', 'SUI/USDT', 'INJ/USDT', 'TIA/USDT', 'WLD/USDT', 'ORDI/USDT', 'SATS/USDT', 'BONK/USDT', 'FLOKI/USDT', 'WIF/USDT',
    'BOME/USDT', 'SLERF/USDT', '1INCH/USDT', 'A/USDT', 'ACE/USDT', 'ACH/USDT', 'ACT/USDT', 'AEVO/USDT', 'AGLD/USDT', 'AI16Z/USDT',
    'AIDOGE/USDT', 'AIXBT/USDT', 'ALCH/USDT', 'ALPHA/USDT', 'ANIME/USDT', 'APE/USDT', 'API3/USDT', 'AR/USDT', 'ARC/USDT', 'ARKM/USDT',
    'ATH/USDT', 'AUCTION/USDT', 'AVAAI/USDT', 'AXS/USDT', 'BABY/USDT', 'BADGER/USDT', 'BAL/USDT', 'BAND/USDT', 'BAT/USDT', 'BERA/USDT',
    'BICO/USDT', 'BIGTIME/USDT', 'BIO/USDT', 'BLUR/USDT', 'BNT/USDT', 'BRETT/USDT', 'CAT/USDT', 'CATI/USDT', 'CELO/USDT', 'CETUS/USDT',
    'CFX/USDT', 'CHZ/USDT', 'COMP/USDT', 'COOKIE/USDT', 'CORE/USDT', 'CRO/USDT', 'CRV/USDT', 'CSPR/USDT', 'CTC/USDT', 'CVC/USDT',
    'CVX/USDT', 'DEGEN/USDT', 'DGB/USDT', 'DOG/USDT', 'DOGS/USDT', 'DOOD/USDT', 'DUCK/USDT', 'DYDX/USDT', 'EGLD/USDT', 'EIGEN/USDT',
    'ENJ/USDT', 'ENS/USDT', 'ETHFI/USDT', 'ETHW/USDT', 'FARTCOIN/USDT', 'FLM/USDT', 'FLOW/USDT', 'FXS/USDT', 'GALA/USDT', 'GAS/USDT',
    'GLM/USDT', 'GMT/USDT', 'GMX/USDT', 'GOAT/USDT', 'GODS/USDT', 'GPS/USDT', 'GRASS/USDT', 'GRIFFAIN/USDT', 'GRT/USDT', 'HMSTR/USDT',
    'HUMA/USDT', 'HYPE/USDT', 'ICX/USDT', 'ID/USDT', 'IMX/USDT', 'INIT/USDT', 'IOST/USDT', 'IOTA/USDT', 'IP/USDT', 'JELLYJELLY/USDT',
    'JOE/USDT', 'JST/USDT', 'JTO/USDT', 'KAITO/USDT', 'KMNO/USDT', 'KNC/USDT', 'KSM/USDT', 'LAUNCHCOIN/USDT', 'LAYER/USDT', 'LDO/USDT',
    'LOOKS/USDT', 'LPT/USDT', 'LQTY/USDT', 'LRC/USDT', 'LSK/USDT', 'LUNA/USDT', 'LUNC/USDT', 'MAGIC/USDT', 'MAJOR/USDT', 'MASK/USDT',
    'ME/USDT', 'MEME/USDT', 'MERL/USDT', 'METIS/USDT', 'MEW/USDT', 'MINA/USDT', 'MKR/USDT', 'MOODENG/USDT', 'MORPHO/USDT', 'MUBARAK/USDT',
    'NC/USDT', 'NEIRO/USDT', 'NEIROETH/USDT', 'NEO/USDT', 'NIL/USDT', 'NMR/USDT', 'NOT/USDT', 'NXPC/USDT', 'OL/USDT', 'OM/USDT',
    'ONDO/USDT', 'ONE/USDT', 'ONT/USDT', 'ORBS/USDT', 'PARTI/USDT', 'PENGU/USDT', 'PEOPLE/USDT', 'PERP/USDT', 'PI/USDT', 'PIPPIN/USDT',
    'PLUME/USDT', 'PNUT/USDT', 'POL/USDT', 'POPCAT/USDT', 'PRCL/USDT', 'PROMPT/USDT', 'PYTH/USDT', 'QTUM/USDT', 'RAY/USDT', 'RDNT/USDT',
    'RENDER/USDT', 'RESOLV/USDT', 'RSR/USDT', 'RVN/USDT', 'S/USDT', 'SCR/USDT', 'SHELL/USDT', 'SIGN/USDT', 'SLP/USDT', 'SNX/USDT',
    'SOLV/USDT', 'SONIC/USDT', 'SOON/USDT', 'SOPH/USDT', 'SSV/USDT', 'STORJ/USDT', 'STRK/USDT', 'STX/USDT', 'SUSHI/USDT', 'SWARMS/USDT',
    'T/USDT', 'TAO/USDT', 'TNSR/USDT', 'TON/USDT', 'TRB/USDT', 'TRUMP/USDT', 'TURBO/USDT', 'UMA/USDT', 'USDC/USDT', 'USTC/USDT',
    'UXLINK/USDT', 'VANA/USDT', 'VINE/USDT', 'VIRTUAL/USDT', 'W/USDT', 'WAL/USDT', 'WAXP/USDT', 'WCT/USDT', 'WOO/USDT', 'XAUT/USDT',
    'XCH/USDT', 'XTZ/USDT', 'YFI/USDT', 'YGG/USDT', 'ZENT/USDT', 'ZEREBRO/USDT', 'ZETA/USDT', 'ZIL/USDT', 'ZK/USDT', 'ZRO/USDT', 'ZRX/USDT'
]

# 每个币种对应的Telegram频道ID (需要您创建频道并添加机器人为管理员)
CHANNELS = {
    'BTC/USDT': '@btczyz_signals_2025',    # BTC信号频道
    'ETH/USDT': '@ethzyz_signals_2025',    # ETH信号频道
    'OKB/USDT': '@okbzyz_signals_2025',    # OKB信号频道
    'ADA/USDT': '@adazyz_signals_2025',    # ADA信号频道
    'XRP/USDT': '@xrpzyz_signals_2025',    # XRP信号频道
    'SOL/USDT': '@solzyz_signals_2025',    # SOL信号频道
    'DOGE/USDT': '@dogezyz_signals_2025'   # DOGE信号频道
}

# 成功率统计频道
PERFORMANCE_CHANNEL = '@cryptozyz_performance_2025'  # 成功率统计频道

# 时间框架
TIMEFRAMES = ['1m', '5m', '15m', '1h'] 