# -*- coding: utf-8 -*-
"""
===================================
Exa搜索引擎集成
===================================

支持功能：
1. 高级网页搜索
2. 内容提取和摘要
3. 相关文章推荐
4. 实时信息检索

API文档：https://exa.ai/docs/reference/search-best-practices
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ExaSearchError(Exception):
    """Exa搜索异常"""
    pass


class ExaSearchService:
    """
    Exa搜索引擎服务
    
    特点：
    - 高质量网页内容提取
    - 支持精确搜索和语义搜索
    - 提供内容摘要和要点提取
    - 实时信息检索能力
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化
        
        Args:
            api_key: Exa API密钥（可从环境变量EXA_API_KEY获取）
        """
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ValueError("Exa API密钥未配置，请设置EXA_API_KEY环境变量")
        
        self.base_url = "https://api.exa.ai"
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}"
        })
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        use_autoprompt: bool = True,
        type: str = "neural"
    ) -> Optional[Dict[str, Any]]:
        """
        执行搜索
        
        Args:
            query: 搜索查询词
            num_results: 返回结果数量
            include_domains: 限定域名列表
            exclude_domains: 排除域名列表
            start_crawl_date: 开始爬取日期 (YYYY-MM-DD)
            end_crawl_date: 结束爬取日期 (YYYY-MM-DD)
            start_published_date: 开始发布日期 (YYYY-MM-DD)
            end_published_date: 结束发布日期 (YYYY-MM-DD)
            use_autoprompt: 是否使用自动提示优化查询
            type: 搜索类型 ('keyword', 'neural', 'magic')
            
        Returns:
            搜索结果字典
        """
        try:
            payload = {
                "query": query,
                "numResults": num_results,
                "useAutoprompt": use_autoprompt,
                "type": type
            }
            
            if include_domains:
                payload["includeDomains"] = include_domains
            if exclude_domains:
                payload["excludeDomains"] = exclude_domains
            if start_crawl_date:
                payload["startCrawlDate"] = start_crawl_date
            if end_crawl_date:
                payload["endCrawlDate"] = end_crawl_date
            if start_published_date:
                payload["startPublishedDate"] = start_published_date
            if end_published_date:
                payload["endPublishedDate"] = end_published_date
            
            response = self.session.post(
                f"{self.base_url}/search",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 429:
                raise ExaSearchError("Exa API请求频率超限")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ExaSearchError(f"Exa搜索请求失败: {str(e)}")
    
    def get_contents(
        self,
        urls: List[str],
        text: bool = True,
        highlights: bool = True,
        summary: bool = True,
        livecrawl: str = "never"
    ) -> Optional[Dict[str, Any]]:
        """
        获取网页内容
        
        Args:
            urls: URL列表
            text: 是否返回全文
            highlights: 是否返回高亮内容
            summary: 是否返回摘要
            livecrawl: 实时爬取选项 ('never', 'fallback', 'always')
            
        Returns:
            内容结果字典
        """
        try:
            payload = {
                "urls": urls,
                "text": text,
                "highlights": highlights,
                "summary": summary,
                "livecrawl": livecrawl
            }
            
            response = self.session.post(
                f"{self.base_url}/contents",
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ExaSearchError(f"Exa内容获取失败: {str(e)}")
    
    def find_similar(
        self,
        url: str,
        num_results: int = 10,
        include_text: bool = True,
        include_highlights: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        查找相似内容
        
        Args:
            url: 目标URL
            num_results: 返回结果数量
            include_text: 是否包含文本内容
            include_highlights: 是否包含高亮内容
            
        Returns:
            相似内容结果
        """
        try:
            payload = {
                "url": url,
                "numResults": num_results,
                "includeText": include_text,
                "includeHighlights": include_highlights
            }
            
            response = self.session.post(
                f"{self.base_url}/findSimilar",
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ExaSearchError(f"Exa相似内容查找失败: {str(e)}")
    
    def search_and_extract(
        self,
        query: str,
        num_results: int = 5,
        extract_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索并提取结构化信息
        
        Args:
            query: 搜索查询
            num_results: 结果数量
            extract_fields: 要提取的字段列表
            
        Returns:
            结构化结果列表
        """
        try:
            # 执行搜索
            search_result = self.search(
                query=query,
                num_results=num_results,
                type="neural"
            )
            
            if not search_result or "results" not in search_result:
                return []
            
            results = search_result["results"]
            extracted_data = []
            
            # 提取每个结果的关键信息
            for item in results:
                extracted_item = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "score": item.get("score", 0),
                    "published_date": item.get("publishedDate", ""),
                    "author": item.get("author", "")
                }
                
                # 如果需要额外字段，获取页面内容
                if extract_fields:
                    content_result = self.get_contents(
                        urls=[item["url"]],
                        text=False,
                        highlights=True,
                        summary=True
                    )
                    
                    if content_result and "results" in content_result:
                        content = content_result["results"][0]
                        extracted_item["summary"] = content.get("summary", "")
                        extracted_item["highlights"] = content.get("highlights", [])
                
                extracted_data.append(extracted_item)
            
            return extracted_data
            
        except Exception as e:
            logger.warning(f"搜索并提取失败: {e}")
            return []
    
    def search_stock_intelligence(
        self,
        stock_code: str,
        stock_name: str,
        days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        搜索股票相关情报
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            days: 搜索最近几天的内容
            
        Returns:
            情报数据字典
        """
        try:
            # 构造搜索查询
            query = f"{stock_name} {stock_code} 股票分析 最新消息"
            
            # 设置时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 执行搜索
            search_result = self.search(
                query=query,
                num_results=15,
                include_domains=[
                    "sina.com.cn",
                    "163.com",
                    "eastmoney.com",
                    "cs.com.cn",
                    "cnstock.com",
                    "yicai.com",
                    "caixin.com",
                    "ftchinese.com"
                ],
                start_published_date=start_date.strftime("%Y-%m-%d"),
                end_published_date=end_date.strftime("%Y-%m-%d"),
                type="neural"
            )
            
            if not search_result or "results" not in search_result:
                return None
            
            # 提取内容
            urls = [item["url"] for item in search_result["results"][:5]]
            if urls:
                content_result = self.get_contents(
                    urls=urls,
                    text=False,
                    highlights=True,
                    summary=True
                )
            else:
                content_result = None
            
            # 整理结果
            intelligence_data = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "query_time": datetime.now().isoformat(),
                "search_query": query,
                "time_range": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                },
                "search_results": [],
                "content_summary": ""
            }
            
            # 添加搜索结果
            for item in search_result["results"]:
                intelligence_data["search_results"].append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "score": item.get("score", 0),
                    "published_date": item.get("publishedDate", "")
                })
            
            # 添加内容摘要
            if content_result and "results" in content_result:
                summaries = []
                for content in content_result["results"]:
                    if content.get("summary"):
                        summaries.append(content["summary"])
                
                if summaries:
                    intelligence_data["content_summary"] = "\n\n".join(summaries[:3])
            
            return intelligence_data
            
        except Exception as e:
            logger.warning(f"股票情报搜索失败 {stock_code}: {e}")
            return None
    
    def search_market_news(
        self,
        market: str = "A股",
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        搜索市场新闻
        
        Args:
            market: 市场类型 ('A股', '港股', '美股', '全球')
            limit: 返回结果数量
            
        Returns:
            新闻列表
        """
        try:
            market_queries = {
                "A股": "A股市场 最新动态 上证指数 深证成指 创业板指",
                "港股": "港股市场 恒生指数 最新行情 港股通",
                "美股": "美股市场 道琼斯 纳斯达克 标普500",
                "全球": "全球股市 国际市场 金融市场 动态"
            }
            
            query = market_queries.get(market, market_queries["A股"])
            
            search_result = self.search(
                query=query,
                num_results=limit,
                include_domains=[
                    "sina.com.cn",
                    "163.com",
                    "eastmoney.com",
                    "cnstock.com",
                    "yicai.com",
                    "caixin.com",
                    "ftchinese.com",
                    "reuters.com",
                    "bloomberg.com"
                ],
                type="neural"
            )
            
            if not search_result or "results" not in search_result:
                return None
            
            news_list = []
            for item in search_result["results"]:
                news_list.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "score": item.get("score", 0),
                    "published_date": item.get("publishedDate", ""),
                    "author": item.get("author", "")
                })
            
            return news_list
            
        except Exception as e:
            logger.warning(f"市场新闻搜索失败 {market}: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            是否可用
        """
        try:
            # 简单的可用性检查
            result = self.search("test", num_results=1)
            return result is not None
        except Exception:
            return False
