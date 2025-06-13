# OKX API数据获取模块
import requests
import pandas as pd
import asyncio
import logging
import random
import time
from datetime import datetime
from config import TRADING_PAIRS
from functools import wraps

def async_retry(max_retries=3, base_delay=1.0, max_delay=60.0, backoff_factor=2.0):
    """
    异步重试装饰器，支持指数退避和随机抖动
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        backoff_factor: 退避因子
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    # 最后一次尝试不需要延迟
                    if attempt == max_retries:
                        break
                    
                    # 计算延迟时间：指数退避 + 随机抖动
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    jitter = random.uniform(0.1, 0.5) * delay
                    total_delay = delay + jitter
                    
                    # 记录重试信息
                    logger = logging.getLogger(__name__)
                    logger.warning(f"{func.__name__} 第{attempt + 1}次尝试失败: {e}")
                    logger.info(f"将在 {total_delay:.2f} 秒后重试...")
                    
                    await asyncio.sleep(total_delay)
            
            # 所有重试都失败了，抛出最后一个异常
            raise last_exception
            
        return wrapper
    return decorator

class OKXDataFetcher:
    def __init__(self):
        """初始化OKX数据获取器"""
        self.base_url = "https://www.okx.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.logger = logging.getLogger(__name__)
        self._all_contracts = None  # 缓存所有合约数据
        
    def _convert_symbol(self, symbol):
        """将交易对格式转换为OKX格式 (BTC/USDT -> BTC-USDT)"""
        return symbol.replace('/', '-')
        
    async def fetch_all_contracts(self, force_refresh=False):
        """
        获取OKX所有USDT本位永续合约
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            list: 所有USDT本位永续合约列表 ['BTC/USDT', 'ETH/USDT', ...]
        """
        if self._all_contracts is not None and not force_refresh:
            return self._all_contracts
            
        try:
            # 只获取USDT本位永续合约
            swap_symbols = await self._fetch_instruments('SWAP')
            
            # 过滤出USDT本位永续合约
            usdt_swap_symbols = []
            exclude_patterns = ['UP', 'DOWN', '3L', '3S', 'BEAR', 'BULL', 'MOVE']
            
            for symbol in swap_symbols:
                if symbol.endswith('/USDT'):
                    base = symbol.replace('/USDT', '')
                    # 过滤掉杠杆代币等不适合交易的品种
                    if not any(pattern in base for pattern in exclude_patterns):
                        usdt_swap_symbols.append(symbol)
            
            # 按市值和流动性排序（热门币种优先）
            priority_coins = [
                'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 'DOT', 'MATIC', 'SHIB',
                'AVAX', 'TRX', 'LINK', 'UNI', 'LTC', 'BCH', 'NEAR', 'ATOM', 'FTM', 'MANA',
                'SAND', 'ALGO', 'ICP', 'VET', 'FIL', 'HBAR', 'ETC', 'THETA', 'XLM', 'AAVE',
                'PEPE', 'ARB', 'OP', 'APT', 'SUI', 'SEI', 'INJ', 'TIA', 'WLD', 'JUP'
            ]
            
            sorted_symbols = []
            remaining_symbols = []
            
            # 先添加优先币种的永续合约
            for coin in priority_coins:
                symbol = f"{coin}/USDT"
                if symbol in usdt_swap_symbols:
                    sorted_symbols.append(symbol)
            
            # 再添加其他永续合约
            for symbol in usdt_swap_symbols:
                if symbol not in sorted_symbols:
                    remaining_symbols.append(symbol)
            
            # 最终列表：所有USDT本位永续合约
            final_symbols = sorted_symbols + remaining_symbols
            
            self._all_contracts = final_symbols
            self.logger.info(f"获取到 {len(final_symbols)} 个 USDT本位永续合约")
            
            return final_symbols
            
        except Exception as e:
            self.logger.error(f"获取USDT本位永续合约失败: {e}")
            # 返回默认列表作为备选
            return TRADING_PAIRS
    
    @async_retry(max_retries=2, base_delay=2.0)
    async def _fetch_instruments(self, inst_type):
        """
        获取指定类型的交易工具
        
        Args:
            inst_type: 'SPOT', 'SWAP', 'FUTURES'
            
        Returns:
            list: 交易对列表
        """
        try:
            url = f"{self.base_url}/api/v5/public/instruments"
            params = {'instType': inst_type}
            
            response = await asyncio.to_thread(
                self.session.get, 
                url, 
                params=params, 
                timeout=15
            )
            
            if response.status_code != 200:
                self.logger.error(f"获取{inst_type}交易对HTTP错误: {response.status_code}")
                return []
                
            data = response.json()
            
            if data.get('code') != '0':
                self.logger.error(f"获取{inst_type}交易对API错误: {data}")
                return []
                
            instruments = data.get('data', [])
            symbols = []
            
            for inst in instruments:
                inst_id = inst.get('instId', '')
                
                # 处理不同类型的交易工具
                if inst_type == 'SWAP':
                    # 永续合约格式: BTC-USDT-SWAP -> BTC/USDT
                    if inst_id.endswith('-USDT-SWAP'):
                        symbol = inst_id.replace('-USDT-SWAP', '/USDT')
                        symbols.append(symbol)
                else:
                    # 现货格式: BTC-USDT -> BTC/USDT  
                    if '-' in inst_id and inst_id.endswith('-USDT'):
                        symbol = inst_id.replace('-', '/')
                        symbols.append(symbol)
            
            self.logger.info(f"获取到 {len(symbols)} 个 {inst_type} USDT本位永续合约" if inst_type == 'SWAP' else f"获取到 {len(symbols)} 个 {inst_type} USDT交易对")
            return symbols
            
        except Exception as e:
            self.logger.error(f"获取{inst_type}交易对失败: {e}")
            return []
        
    @async_retry(max_retries=3, base_delay=1.5)
    async def fetch_ohlcv(self, symbol, timeframe='1m', limit=100):
        """
        获取OHLCV数据（开盘价、最高价、最低价、收盘价、成交量）
        
        Args:
            symbol: 交易对符号，如 'BTC/USDT'
            timeframe: 时间框架，如 '1m', '5m', '1h'
            limit: 获取的K线数量
            
        Returns:
            DataFrame: 包含OHLCV数据的DataFrame
        """
        try:
            okx_symbol = self._convert_symbol(symbol)
            
            # OKX K线API
            url = f"{self.base_url}/api/v5/market/candles"
            params = {
                'instId': okx_symbol,
                'bar': timeframe,
                'limit': str(limit)
            }
            
            response = await asyncio.to_thread(
                self.session.get, 
                url, 
                params=params, 
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.error(f"HTTP错误 {response.status_code}: {response.text}")
                return None
                
            data = response.json()
            
            if data.get('code') != '0':
                self.logger.error(f"API错误: {data}")
                return None
                
            candles = data.get('data', [])
            if not candles:
                self.logger.warning(f"没有获取到 {symbol} 的K线数据")
                return None
            
            # 转换为DataFrame
            # OKX返回格式: [时间戳, 开盘价, 最高价, 最低价, 收盘价, 成交量, 成交额]
            df_data = []
            for candle in reversed(candles):  # OKX返回最新的在前，需要反转
                df_data.append([
                    int(candle[0]),  # timestamp
                    float(candle[1]),  # open
                    float(candle[2]),  # high
                    float(candle[3]),  # low
                    float(candle[4]),  # close
                    float(candle[5])   # volume
                ])
            
            df = pd.DataFrame(
                df_data, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # 转换时间戳
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            
            self.logger.info(f"成功获取 {symbol} {timeframe} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 数据失败: {str(e)}")
            return None
    
    @async_retry(max_retries=3, base_delay=1.0)
    async def fetch_ticker(self, symbol):
        """
        获取实时ticker数据
        
        Args:
            symbol: 交易对符号
            
        Returns:
            dict: ticker数据
        """
        try:
            okx_symbol = self._convert_symbol(symbol)
            
            url = f"{self.base_url}/api/v5/market/ticker"
            params = {'instId': okx_symbol}
            
            response = await asyncio.to_thread(
                self.session.get, 
                url, 
                params=params, 
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.error(f"Ticker HTTP错误 {response.status_code}")
                return None
                
            data = response.json()
            
            if data.get('code') != '0' or not data.get('data'):
                self.logger.error(f"Ticker API错误: {data}")
                return None
                
            ticker_data = data['data'][0]
            
            # 转换为标准格式
            last_price = float(ticker_data['last'])
            open_price = float(ticker_data['open24h'])
            percentage_change = ((last_price - open_price) / open_price) * 100 if open_price != 0 else 0
            
            ticker = {
                'symbol': symbol,
                'last': last_price,
                'high': float(ticker_data['high24h']),
                'low': float(ticker_data['low24h']),
                'baseVolume': float(ticker_data['vol24h']),
                'percentage': percentage_change,
                'datetime': datetime.now().isoformat()
            }
            
            return ticker
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} ticker失败: {str(e)}")
            return None
    
    @async_retry(max_retries=2, base_delay=1.0)
    async def fetch_order_book(self, symbol, limit=20):
        """
        获取订单簿数据
        
        Args:
            symbol: 交易对符号
            limit: 深度限制
            
        Returns:
            dict: 订单簿数据
        """
        try:
            okx_symbol = self._convert_symbol(symbol)
            
            url = f"{self.base_url}/api/v5/market/books"
            params = {'instId': okx_symbol, 'sz': str(limit)}
            
            response = await asyncio.to_thread(
                self.session.get, 
                url, 
                params=params, 
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.error(f"订单簿HTTP错误 {response.status_code}")
                return None
                
            data = response.json()
            
            if data.get('code') != '0' or not data.get('data'):
                self.logger.error(f"订单簿API错误: {data}")
                return None
                
            book_data = data['data'][0]
            
            # 转换为标准格式
            order_book = {
                'symbol': symbol,
                'bids': [[float(bid[0]), float(bid[1])] for bid in book_data['bids']],
                'asks': [[float(ask[0]), float(ask[1])] for ask in book_data['asks']],
                'timestamp': int(book_data['ts'])
            }
            
            return order_book
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 订单簿失败: {str(e)}")
            return None
    
    async def get_market_data(self, symbol, timeframe='1m'):
        """
        获取综合市场数据
        
        Args:
            symbol: 交易对符号
            timeframe: 时间框架
            
        Returns:
            dict: 包含各种市场数据的字典
        """
        try:
            # 并行获取数据
            tasks = [
                self.fetch_ohlcv(symbol, timeframe, 100),
                self.fetch_ticker(symbol),
                self.fetch_order_book(symbol)
            ]
            
            ohlcv_data, ticker_data, order_book_data = await asyncio.gather(*tasks)
            
            return {
                'ohlcv': ohlcv_data,
                'ticker': ticker_data,
                'order_book': order_book_data,
                'symbol': symbol,
                'timeframe': timeframe,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 综合数据失败: {str(e)}")
            return None
    
    def get_swap_trading_url(self, symbol):
        """
        获取永续合约交易链接
        
        Args:
            symbol: 交易对符号，如 'BTC/USDT'
            
        Returns:
            str: OKX永续合约交易链接
        """
        try:
            # 转换为OKX永续合约格式: BTC/USDT -> btc-usdt-swap
            base_symbol = self._convert_symbol(symbol).lower()  # BTC/USDT -> btc-usdt
            swap_symbol = base_symbol + "-swap"  # btc-usdt-swap
            return f"https://www.okx.com/trade-swap/{swap_symbol}"
        except Exception as e:
            self.logger.error(f"生成交易链接失败: {e}")
            return f"https://www.okx.com/trade-swap/btc-usdt-swap"
    
    def get_supported_symbols(self):
        """获取支持的交易对列表"""
        try:
            # 验证交易对是否存在
            url = f"{self.base_url}/api/v5/public/instruments"
            params = {'instType': 'SWAP'}  # 改为验证永续合约
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0':
                    instruments = data.get('data', [])
                    available_symbols = []
                    
                    for symbol in TRADING_PAIRS:
                        okx_symbol = self._convert_symbol(symbol)
                        for inst in instruments:
                            if inst.get('instId') == okx_symbol:
                                available_symbols.append(symbol)
                                break
                    
                    self.logger.info(f"验证的永续合约: {available_symbols}")
                    return available_symbols
                    
        except Exception as e:
            self.logger.error(f"获取支持的永续合约失败: {str(e)}")
            
        return TRADING_PAIRS  # 返回默认列表 