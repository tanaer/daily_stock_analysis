# -*- coding: utf-8 -*-
"""
===================================
Coindesk数据源获取器
===================================

支持功能：
1. 加密货币实时价格行情 (Index CC API)
2. 财经新闻资讯 (News API)
3. 市场数据和指数
4. 历史价格数据

API文档：
- 价格行情: https://developers.coindesk.com/documentation/data-api/index_cc_v1_latest_tick
- 新闻资讯: https://developers.coindesk.com/documentation/data-api/news_v1_article_list
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


class CoindeskFetcher(BaseFetcher):
    """
    Coindesk数据获取器
    
    特点：
    - 权威的加密货币数据提供商
    - 实时价格和新闻资讯
    - 高质量数据源
    - 免费API访问
    """
    
    name = "Coindesk"
    priority = 2  # 高优先级（与Finnhub同级，虚拟货币备用源）
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化
        
        Args:
            api_key: Coindesk API密钥（目前大部分API免费）
        """
        self.api_key = api_key or os.getenv("COINDESK_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StockAnalysisBot/1.0",
            "Accept": "application/json"
        })
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """
        发起API请求
        
        Args:
            url: API端点URL
            params: 查询参数
            
        Returns:
            API响应数据
        """
        try:
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                raise RateLimitError("Coindesk API请求频率超限")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise DataFetchError(f"Coindesk API请求失败: {str(e)}")
    
    def get_crypto_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取加密货币实时价格（Index CC API）
        
        Args:
            symbol: 货币符号（如 BTC, ETH）
            
        Returns:
            价格数据字典
        """
        try:
            # Coindesk Index CC API endpoint
            url = "https://api.coindesk.com/index/cc/v1/latest/tick"
            
            # 符号映射
            symbol_map = {
                'BTC': 'XBT',
                'ETH': 'ETH',
                'BCH': 'BCH',
                'LTC': 'LTC',
                'XRP': 'XRP'
            }
            
            coindesk_symbol = symbol_map.get(symbol.upper())
            if not coindesk_symbol:
                logger.warning(f"[{self.name}] 不支持的货币: {symbol}")
                return None
            
            params = {
                "index": f"{coindesk_symbol}-USD",
                "precision": "2"
            }
            
            data = self._make_request(url, params)
            
            if not data or "data" not in data:
                return None
            
            tick_data = data["data"]
            index_data = tick_data.get("index", {})
            ohlc_data = tick_data.get("ohlc", {})
            
            return {
                "symbol": symbol.upper(),
                "name": f"{symbol.upper()}/USD",
                "price": float(index_data.get("value", 0)),
                "price_change_24h": float(ohlc_data.get("change24h", 0)),
                "price_change_percentage_24h": float(ohlc_data.get("changepct24h", 0)),
                "open_24h": float(ohlc_data.get("open24h", 0)),
                "high_24h": float(ohlc_data.get("high24h", 0)),
                "low_24h": float(ohlc_data.get("low24h", 0)),
                "volume_24h": float(ohlc_data.get("volume24h", 0)),
                "timestamp": int(datetime.now().timestamp()),
                "source": "Coindesk Index CC"
            }
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取价格失败 {symbol}: {e}")
            return None
    
    def get_news_list(
        self,
        limit: int = 20,
        category: str = "all"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取新闻列表（News API）
        
        Args:
            limit: 返回新闻数量
            category: 新闻分类 ('all', 'markets', 'tech', 'policy', 'features')
            
        Returns:
            新闻列表
        """
        try:
            # Coindesk News API endpoint
            url = "https://api.coindesk.com/news/v1/article/list"
            
            params = {
                "limit": limit,
                "categories": category if category != "all" else None
            }
            
            # 移除None值
            params = {k: v for k, v in params.items() if v is not None}
            
            data = self._make_request(url, params)
            
            if not data or "data" not in data:
                return None
            
            articles = data["data"].get("articles", [])
            results = []
            
            for article in articles:
                results.append({
                    "title": article.get("title", ""),
                    "summary": article.get("abstract", ""),
                    "url": article.get("url", ""),
                    "source": "Coindesk",
                    "published_at": article.get("date", ""),
                    "author": article.get("authors", [{}])[0].get("name", "") if article.get("authors") else "",
                    "tags": [tag.get("name", "") for tag in article.get("tags", [])],
                    "category": article.get("primaryCategory", {}).get("name", "")
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取新闻失败: {e}")
            return None
    
    def get_market_indices(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取加密货币市场指数
        
        Returns:
            指数数据列表
        """
        try:
            # 获取多个主要货币的价格作为市场概览
            major_coins = ["BTC", "ETH", "BCH", "LTC", "XRP"]
            results = []
            
            for symbol in major_coins:
                price_data = self.get_crypto_price(symbol)
                if price_data:
                    results.append({
                        "symbol": price_data["symbol"],
                        "name": price_data["name"],
                        "price": price_data["price"],
                        "change_24h": price_data["price_change_24h"],
                        "change_percent_24h": price_data["price_change_percentage_24h"],
                        "volume_24h": price_data["volume_24h"],
                        "timestamp": price_data["timestamp"]
                    })
            
            return results if results else None
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取市场指数失败: {e}")
            return None
    
    def get_historical_prices(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[pd.DataFrame]:
        """
        获取历史价格数据（模拟实现）
        
        注意：Coindesk Index CC API主要是实时数据，
        历史数据需要通过其他途径或使用已有数据源
        
        Args:
            symbol: 货币符号
            days: 天数
            
        Returns:
            历史数据DataFrame
        """
        try:
            # 这里提供一个框架，实际需要根据Coindesk的具体历史API实现
            logger.info(f"[{self.name}] 历史数据获取需要额外的历史API支持")
            
            # 返回空DataFrame作为占位
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount", "pct_chg"])
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取历史数据失败 {symbol}: {e}")
            return None
    
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取历史数据（适配BaseFetcher接口）"""
        return self.get_historical_prices(stock_code) or pd.DataFrame()
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """标准化数据列名"""
        required_columns = ["date", "open", "high", "low", "close", "volume", "amount", "pct_chg"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0.0
        return df[required_columns]
    
    def get_main_indices(self) -> Optional[List[Dict[str, Any]]]:
        """获取主要市场指数"""
        return self.get_market_indices()
