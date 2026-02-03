# -*- coding: utf-8 -*-
"""
===================================
Exa搜索提供者适配器
===================================

将ExaSearchService适配为BaseSearchProvider接口
"""

import logging
from typing import List, Optional
from .search_service import BaseSearchProvider, SearchResponse, SearchResult
from .exa_search import ExaSearchService, ExaSearchError

logger = logging.getLogger(__name__)


class ExaSearchProviderAdapter(BaseSearchProvider):
    """
    Exa搜索提供者适配器
    
    将ExaSearchService包装为符合BaseSearchProvider接口的类
    """
    
    def __init__(self, api_keys: List[str]):
        """
        初始化Exa搜索适配器
        
        Args:
            api_keys: Exa API密钥列表（支持轮询）
        """
        super().__init__(api_keys, "Exa")
        # 初始化Exa服务实例
        self._exa_services = []
        for key in api_keys:
            try:
                service = ExaSearchService(api_key=key)
                self._exa_services.append(service)
                logger.debug(f"[Exa] API Key {key[:8]}... 初始化成功")
            except Exception as e:
                logger.warning(f"[Exa] API Key {key[:8]}... 初始化失败: {e}")
        
        if not self._exa_services:
            logger.error("[Exa] 没有可用的API Key")
    
    @property
    def is_available(self) -> bool:
        """检查是否有可用的服务实例"""
        return len(self._exa_services) > 0
    
    def _get_next_service(self) -> Optional[ExaSearchService]:
        """
        获取下一个可用的Exa服务实例（轮询）
        """
        if not self._exa_services:
            return None
        
        # 简单轮询策略
        service = self._exa_services[0]
        # 将使用的service移到队尾实现轮询
        self._exa_services = self._exa_services[1:] + [service]
        return service
    
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """
        执行Exa搜索（实现BaseSearchProvider接口）
        
        Args:
            query: 搜索查询词
            api_key: API密钥（在适配器中不直接使用）
            max_results: 最大结果数
            days: 时间范围（天）
            
        Returns:
            SearchResponse对象
        """
        service = self._get_next_service()
        if not service:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="无可用的Exa服务实例"
            )
        
        try:
            # 使用Exa的搜索并提取功能
            results = service.search_and_extract(
                query=query,
                num_results=max_results
            )
            
            if not results:
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message="搜索未返回结果"
                )
            
            # 转换为标准SearchResult格式
            search_results = []
            for item in results:
                search_results.append(SearchResult(
                    title=item.get("title", ""),
                    snippet=item.get("summary", "")[:500],  # 截取摘要前500字符
                    url=item.get("url", ""),
                    source=self._extract_domain(item.get("url", "")),
                    published_date=item.get("published_date", "")
                ))
            
            return SearchResponse(
                query=query,
                results=search_results,
                provider=self.name,
                success=True
            )
            
        except ExaSearchError as e:
            error_msg = f"Exa搜索错误: {str(e)}"
            logger.warning(f"[{self.name}] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """从URL提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or '未知来源'
        except:
            return '未知来源'
