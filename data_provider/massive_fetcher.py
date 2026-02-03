# -*- coding: utf-8 -*-
"""
===================================
Massive数据源获取器
===================================

支持功能：
1. 财经新闻聚合
2. 市场情绪分析
3. 行业动态
4. 公司公告
5. 宏观经济数据

API文档：https://massive.com/docs/rest/quickstart
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


class MassiveFetcher(BaseFetcher):
    """
    Massive数据获取器
    
    特点：
    - 专业的财经新闻和市场数据
    - 多语言支持
    - 实时更新
    - 高质量内容筛选
    """
    
    name = "Massive"
    priority = 7  # 高优先级
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化
        
        Args:
            api_key: Massive API密钥（可从环境变量MASSIVE_API_KEY获取）
        """
        self.api_key = api_key or os.getenv("MASSIVE_API_KEY")
        if not self.api_key:
            raise ValueError("Massive API密钥未配置，请设置MASSIVE_API_KEY环境变量")
        
        self.base_url = "https://api.massive.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
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
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                raise RateLimitError("Massive API请求频率超限")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise DataFetchError(f"Massive API请求失败: {str(e)}")
    
    def search_news(
        self,
        query: str,
        language: str = "zh",
        categories: Optional[List[str]] = None,
        limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """
        搜索财经新闻
        
        Args:
            query: 搜索关键词
            language: 语言 ('zh', 'en')
            categories: 分类列表 (可选: business, finance, economy, tech, markets)
            limit: 返回结果数量
            
        Returns:
            新闻列表
        """
        try:
            params = {
                "q": query,
                "language": language,
                "limit": limit
            }
            
            if categories:
                params["categories"] = ",".join(categories)
            
            data = self._make_request("news/search", params)
            
            articles = data.get("articles", [])
            results = []
            
            for article in articles:
                results.append({
                    "title": article.get("title", ""),
                    "summary": article.get("summary", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "published_at": article.get("published_at", ""),
                    "sentiment": article.get("sentiment", "neutral"),
                    "relevance_score": article.get("relevance_score", 0)
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"[{self.name}] 搜索新闻失败: {e}")
            return None
    
    def get_company_news(
        self,
        symbol: str,
        days: int = 7,
        limit: int = 15
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取公司相关新闻
        
        Args:
            symbol: 股票代码
            days: 获取最近几天的新闻
            limit: 返回结果数量
            
        Returns:
            公司新闻列表
        """
        try:
            # 构造搜索查询
            company_name = self._get_company_name(symbol)
            query = f"{company_name} OR {symbol}"
            
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            params = {
                "q": query,
                "language": "zh",
                "published_after": since_date,
                "limit": limit,
                "sort": "published_at:desc"
            }
            
            data = self._make_request("news/search", params)
            
            articles = data.get("articles", [])
            results = []
            
            for article in articles:
                published_date = datetime.fromisoformat(
                    article.get("published_at", "").replace("Z", "+00:00")
                )
                
                # 只保留近期新闻
                if published_date >= datetime.now() - timedelta(days=days):
                    results.append({
                        "title": article.get("title", ""),
                        "summary": article.get("summary", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", {}).get("name", ""),
                        "published_at": article.get("published_at", ""),
                        "sentiment": article.get("sentiment", "neutral"),
                        "relevance_score": article.get("relevance_score", 0),
                        "symbols": article.get("symbols", [])
                    })
            
            return results
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取公司新闻失败 {symbol}: {e}")
            return None
    
    def get_market_sentiment(
        self,
        symbol: str,
        days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        获取市场情绪分析
        
        Args:
            symbol: 股票代码
            days: 分析天数
            
        Returns:
            情绪分析结果
        """
        try:
            company_name = self._get_company_name(symbol)
            query = f"{company_name} OR {symbol}"
            
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            params = {
                "q": query,
                "language": "zh",
                "published_after": since_date,
                "limit": 50
            }
            
            data = self._make_request("news/search", params)
            articles = data.get("articles", [])
            
            if not articles:
                return None
            
            # 计算情绪得分
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            total_relevance = 0
            
            for article in articles:
                sentiment = article.get("sentiment", "neutral")
                relevance = article.get("relevance_score", 0)
                
                if sentiment == "positive":
                    positive_count += 1
                elif sentiment == "negative":
                    negative_count += 1
                else:
                    neutral_count += 1
                
                total_relevance += relevance
            
            total_articles = len(articles)
            avg_relevance = total_relevance / total_articles if total_articles > 0 else 0
            
            # 计算情绪指数 (-1到1)
            sentiment_score = (positive_count - negative_count) / total_articles if total_articles > 0 else 0
            
            return {
                "symbol": symbol,
                "period_days": days,
                "total_articles": total_articles,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "average_relevance": round(avg_relevance, 3),
                "sentiment_score": round(sentiment_score, 3),
                "sentiment_label": self._classify_sentiment(sentiment_score),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取市场情绪失败 {symbol}: {e}")
            return None
    
    def get_industry_news(
        self,
        industry: str,
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取行业相关新闻
        
        Args:
            industry: 行业名称
            limit: 返回结果数量
            
        Returns:
            行业新闻列表
        """
        try:
            # 行业关键词映射
            industry_keywords = {
                "科技": ["科技", "半导体", "人工智能", "云计算"],
                "金融": ["银行", "保险", "证券", "金融科技"],
                "医疗": ["医药", "生物技术", "医疗器械", "健康"],
                "消费": ["消费", "零售", "食品饮料", "电商"],
                "能源": ["能源", "石油", "天然气", "新能源"],
                "制造业": ["制造", "工业", "机械", "汽车"]
            }
            
            keywords = industry_keywords.get(industry, [industry])
            query = " OR ".join(keywords)
            
            params = {
                "q": query,
                "language": "zh",
                "limit": limit,
                "sort": "published_at:desc"
            }
            
            data = self._make_request("news/search", params)
            
            articles = data.get("articles", [])
            results = []
            
            for article in articles:
                results.append({
                    "title": article.get("title", ""),
                    "summary": article.get("summary", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "published_at": article.get("published_at", ""),
                    "sentiment": article.get("sentiment", "neutral"),
                    "relevance_score": article.get("relevance_score", 0),
                    "industries": article.get("industries", [])
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取行业新闻失败 {industry}: {e}")
            return None
    
    def get_economic_calendar(
        self,
        country: str = "CN",
        days: int = 7
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取经济日历事件
        
        Args:
            country: 国家代码 ('CN', 'US', 'HK')
            days: 获取未来几天的事件
            
        Returns:
            经济事件列表
        """
        try:
            until_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            
            params = {
                "country": country,
                "published_before": until_date,
                "limit": 50
            }
            
            data = self._make_request("economic/calendar", params)
            
            events = data.get("events", [])
            results = []
            
            for event in events:
                results.append({
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                    "country": event.get("country", ""),
                    "impact": event.get("impact", "low"),  # low, medium, high
                    "currency": event.get("currency", ""),
                    "actual": event.get("actual"),
                    "forecast": event.get("forecast"),
                    "previous": event.get("previous"),
                    "published_at": event.get("published_at", "")
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取经济日历失败: {e}")
            return None
    
    def _get_company_name(self, symbol: str) -> str:
        """
        根据股票代码获取公司名称（简化版）
        """
        # 股票代码到公司名称的映射（实际应调用公司信息API）
        name_map = {
            "AAPL": "苹果",
            "MSFT": "微软",
            "GOOGL": "谷歌",
            "AMZN": "亚马逊",
            "TSLA": "特斯拉",
            "NVDA": "英伟达",
            "META": "Meta",
            "600519": "贵州茅台",
            "000001": "平安银行",
            "300750": "宁德时代",
            "00700": "腾讯控股"
        }
        return name_map.get(symbol.upper(), symbol)
    
    def _classify_sentiment(self, score: float) -> str:
        """
        将数值情绪得分转换为标签
        """
        if score >= 0.2:
            return "积极"
        elif score <= -0.2:
            return "消极"
        else:
            return "中性"
    
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Massive主要用于新闻和情绪数据，不提供历史价格数据
        """
        raise NotImplementedError("Massive不提供历史价格数据")
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        不适用
        """
        return df
    
    def get_main_indices(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取主要指数相关新闻摘要
        """
        try:
            indices = ["上证指数", "深证成指", "创业板指", "恒生指数", "道琼斯", "纳斯达克", "标普500"]
            
            all_news = []
            for index in indices:
                news = self.search_news(
                    query=index,
                    language="zh",
                    categories=["markets", "economy"],
                    limit=3
                )
                if news:
                    for item in news:
                        item["index"] = index
                        all_news.append(item)
            
            return all_news[:20] if all_news else None
            
        except Exception as e:
            logger.warning(f"[{self.name}] 获取指数新闻失败: {e}")
            return None
