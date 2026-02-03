# -*- coding: utf-8 -*-
"""
===================================
Finnhub数据源获取器
===================================

支持功能：
1. 实时股价获取
2. 基本面数据（公司信息、财务数据）
3. 技术指标
4. 市场新闻
5. 行业分类

API文档：https://finnhub.io/docs/api
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import requests
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from data_provider.base import BaseFetcher, DataFetchError, RateLimitError

logger = logging.getLogger(__name__)


class FinnhubFetcher(BaseFetcher):
    """
    Finnhub数据获取器
    
    特点：
    - 支持全球市场（美股、港股、A股等）
    - 实时数据更新
    - 丰富的基本面和技术面数据
    - 免费额度较高（免费版每月60次API调用）
    """
    
    name = "Finnhub"
    priority = 2  # 最高优先级（港美股专用）
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化
        
        Args:
            api_key: Finnhub API密钥（可从环境变量FINNHUB_API_KEY获取）
        """
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("Finnhub API密钥未配置，请设置FINNHUB_API_KEY环境变量")
        
        self.base_url = "https://finnhub.io/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StockAnalysisBot/1.0",
            "Accept": "application/json"
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        发起API请求
        
        Args:
            endpoint: API端点
            params: 查询参数
            
        Returns:
            API响应数据
            
        Raises:
            RateLimitError: 请求频率超限
            DataFetchError: 其他API错误
        """
        if params is None:
            params = {}
        
        params["token"] = self.api_key
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                raise RateLimitError("Finnhub API请求频率超限")
            
            response.raise_for_status()
            data = response.json()
            
            # 检查API错误
            if "error" in data:
                raise DataFetchError(f"Finnhub API错误: {data['error']}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise DataFetchError(f"Finnhub API请求失败: {str(e)}")
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取实时报价
        
        Args:
            symbol: 股票代码（如 AAPL, 00700.HK）
            
        Returns:
            {
                'symbol': 'AAPL',
                'price': 150.25,
                'change': 2.5,
                'percent_change': 1.69,
                'high': 152.30,
                'low': 148.90,
                'open': 149.80,
                'previous_close': 147.75,
                'volume': 45678900,
                'timestamp': 1640995200
            }
        """
        try:
            data = self._make_request("quote", {"symbol": symbol})
            
            if not data or data.get("c", 0) == 0:
                return None
            
            return {
                "symbol": symbol,
                "price": data.get("c"),
                "change": data.get("d"),
                "percent_change": data.get("dp"),
                "high": data.get("h"),
                "low": data.get("l"),
                "open": data.get("o"),
                "previous_close": data.get("pc"),
                "volume": data.get("volume", 0),
                "timestamp": data.get("t")
            }
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取实时报价失败 {symbol}: {e}")
            return None
    
    def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取公司基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            公司基本信息字典
        """
        try:
            data = self._make_request("stock/profile2", {"symbol": symbol})
            return data if data else None
        except Exception as e:
            logger.warning(f"[{self.name}] 获取公司信息失败 {symbol}: {e}")
            return None
    
    def get_financials(self, symbol: str, metric: str = "all") -> Optional[Dict[str, Any]]:
        """
        获取财务数据
        
        Args:
            symbol: 股票代码
            metric: 指标类型 ('all', 'price', 'valuation', 'growth')
            
        Returns:
            财务数据字典
        """
        try:
            data = self._make_request("stock/metric", {
                "symbol": symbol,
                "metric": metric
            })
            return data if data else None
        except Exception as e:
            logger.warning(f"[{self.name}] 获取财务数据失败 {symbol}: {e}")
            return None
    
    def get_technical_indicator(
        self, 
        symbol: str, 
        resolution: str = "D",
        indicator: str = "sma",
        period: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取技术指标
        
        Args:
            symbol: 股票代码
            resolution: 时间分辨率 ('1', '5', '15', '30', '60', 'D', 'W', 'M')
            indicator: 指标类型 ('sma', 'ema', 'rsi', 'macd', 'bbands')
            period: 周期
            
        Returns:
            技术指标数据列表
        """
        try:
            # 先获取历史价格数据
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=365)).timestamp())
            
            price_data = self._make_request("stock/candle", {
                "symbol": symbol,
                "resolution": resolution,
                "from": start_time,
                "to": end_time
            })
            
            if not price_data or price_data.get("s") != "ok":
                return None
            
            # 计算简单移动平均线示例
            if indicator == "sma":
                closes = price_data.get("c", [])
                if len(closes) >= period:
                    sma_values = []
                    for i in range(period - 1, len(closes)):
                        avg = sum(closes[i-period+1:i+1]) / period
                        timestamp = price_data.get("t", [])[i]
                        sma_values.append({
                            "timestamp": timestamp,
                            "value": avg
                        })
                    return sma_values
            
            return None
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取技术指标失败 {symbol}: {e}")
            return None
    
    def get_news(self, symbol: str, count: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        获取相关新闻
        
        Args:
            symbol: 股票代码
            count: 返回新闻数量
            
        Returns:
            新闻列表
        """
        try:
            data = self._make_request("company-news", {
                "symbol": symbol,
                "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "to": datetime.now().strftime("%Y-%m-%d")
            })
            
            if isinstance(data, list):
                # 限制返回数量
                return data[:count]
            return None
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取新闻失败 {symbol}: {e}")
            return None
    
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从Finnhub获取历史价格数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            
        Returns:
            标准化的历史数据DataFrame
        """
        try:
            # 转换日期为时间戳
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
            
            # 转换股票代码格式（Finnhub需要市场后缀）
            symbol = self._convert_stock_code(stock_code)
            
            data = self._make_request("stock/candle", {
                "symbol": symbol,
                "resolution": "D",
                "from": start_ts,
                "to": end_ts
            })
            
            if not data or data.get("s") != "ok":
                raise DataFetchError("获取历史数据失败")
            
            # 转换为DataFrame
            df = pd.DataFrame({
                "date": [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in data.get("t", [])],
                "open": data.get("o", []),
                "high": data.get("h", []),
                "low": data.get("l", []),
                "close": data.get("c", []),
                "volume": data.get("v", [])
            })
            
            # 计算涨跌幅
            if len(df) > 1:
                df["pct_chg"] = df["close"].pct_change() * 100
            else:
                df["pct_chg"] = 0.0
            
            # 添加成交额（估算）
            df["amount"] = df["close"] * df["volume"]
            
            return df
            
        except Exception as e:
            raise DataFetchError(f"Finnhub历史数据获取失败: {str(e)}")
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化数据列名
        """
        # Finnhub返回的数据已经基本符合标准格式
        required_columns = ["date", "open", "high", "low", "close", "volume", "amount", "pct_chg"]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0.0
                
        return df[required_columns]
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """
        转换股票代码格式以适应Finnhub
        
        Args:
            stock_code: 原始股票代码
            
        Returns:
            Finnhub格式的股票代码
        """
        # A股: 600519 -> 600519.SS (上海) 或 000001 -> 000001.SZ (深圳)
        if stock_code.startswith(("6", "5")):  # 上海证券交易所
            return f"{stock_code}.SS"
        elif stock_code.startswith(("0", "3")):  # 深圳证券交易所
            return f"{stock_code}.SZ"
        # 港股: 00700 -> 00700.HK
        elif stock_code.isdigit() and len(stock_code) == 5:
            return f"{stock_code}.HK"
        # 美股: AAPL -> AAPL (保持不变)
        else:
            return stock_code.upper()
    
    def get_main_indices(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取主要指数实时行情
        """
        indices = [
            {"symbol": "^GSPC", "name": "标普500"},
            {"symbol": "^IXIC", "name": "纳斯达克"},
            {"symbol": "^DJI", "name": "道琼斯"},
            {"symbol": "000001.SS", "name": "上证指数"},
            {"symbol": "399001.SZ", "name": "深证成指"},
            {"symbol": "HSI", "name": "恒生指数"}
        ]
        
        results = []
        for index in indices:
            quote = self.get_quote(index["symbol"])
            if quote:
                results.append({
                    "symbol": index["symbol"],
                    "name": index["name"],
                    "price": quote["price"],
                    "change": quote["change"],
                    "change_percent": quote["percent_change"],
                    "volume": quote["volume"],
                    "timestamp": quote["timestamp"]
                })
        
        return results if results else None
