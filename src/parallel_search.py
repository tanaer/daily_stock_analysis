# -*- coding: utf-8 -*-
"""
===================================
并行搜索服务模块
===================================

提供多搜索引擎并行调用能力，实现：
1. 同时调用多个搜索引擎
2. 故障自动隔离和切换
3. 结果智能合并和去重
4. 性能优化和超时控制

此模块独立于原有的search_service.py，避免修改复杂文件带来的风险。
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime, timedelta

from src.search_service import SearchResponse, BaseSearchProvider

logger = logging.getLogger(__name__)


@dataclass
class ParallelSearchResult:
    """并行搜索结果"""
    query: str
    results: List[Dict[str, Any]]
    providers_used: List[str]
    success_count: int
    failed_providers: List[str]
    execution_time: float
    merged_results: List[Dict[str, Any]]


class ParallelSearchService:
    """
    并行搜索服务
    
    特点：
    - 非阻塞并行调用
    - 智能结果合并
    - 故障隔离
    - 超时控制
    """
    
    def __init__(self, providers: List[BaseSearchProvider], max_workers: int = 3):
        """
        初始化并行搜索服务
        
        Args:
            providers: 搜索提供者列表
            max_workers: 最大并发数
        """
        self.providers = [p for p in providers if p.is_available]
        self.max_workers = min(max_workers, len(self.providers))
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        logger.info(f"[并行搜索] 初始化完成，可用引擎: {[p.name for p in self.providers]}, 并发数: {self.max_workers}")
    
    def search_parallel(
        self,
        query: str,
        max_results: int = 10,
        timeout: float = 30.0
    ) -> ParallelSearchResult:
        """
        并行搜索
        
        Args:
            query: 搜索查询
            max_results: 每个引擎最大结果数
            timeout: 总体超时时间（秒）
            
        Returns:
            并行搜索结果
        """
        start_time = datetime.now()
        
        if not self.providers:
            return ParallelSearchResult(
                query=query,
                results=[],
                providers_used=[],
                success_count=0,
                failed_providers=[],
                execution_time=0.0,
                merged_results=[]
            )
        
        # 并行执行所有可用引擎
        futures = {}
        for provider in self.providers:
            future = self.executor.submit(
                self._search_single_provider,
                provider,
                query,
                max_results
            )
            futures[future] = provider.name
        
        # 收集结果
        results = []
        providers_used = []
        failed_providers = []
        
        for future in as_completed(futures, timeout=timeout):
            provider_name = futures[future]
            try:
                result = future.result(timeout=timeout)
                if result and result.success:
                    results.append(result.to_dict())
                    providers_used.append(provider_name)
                    logger.info(f"[并行搜索] {provider_name} 搜索成功，获得 {len(result.results)} 条结果")
                else:
                    failed_providers.append(provider_name)
                    logger.warning(f"[并行搜索] {provider_name} 搜索失败")
            except Exception as e:
                failed_providers.append(provider_name)
                logger.error(f"[并行搜索] {provider_name} 执行异常: {e}")
        
        # 计算执行时间
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # 合并结果（简单去重）
        merged_results = self._merge_results(results, max_results)
        
        logger.info(f"[并行搜索] 完成 - 成功: {len(providers_used)}, 失败: {len(failed_providers)}, "
                   f"总结果: {len(merged_results)}, 耗时: {execution_time:.2f}s")
        
        return ParallelSearchResult(
            query=query,
            results=results,
            providers_used=providers_used,
            success_count=len(providers_used),
            failed_providers=failed_providers,
            execution_time=execution_time,
            merged_results=merged_results
        )
    
    async def search_parallel_async(
        self,
        query: str,
        max_results: int = 10,
        timeout: float = 30.0
    ) -> ParallelSearchResult:
        """
        异步并行搜索（推荐使用）
        
        Args:
            query: 搜索查询
            max_results: 每个引擎最大结果数
            timeout: 总体超时时间
            
        Returns:
            并行搜索结果
        """
        start_time = datetime.now()
        
        if not self.providers:
            return ParallelSearchResult(
                query=query,
                results=[],
                providers_used=[],
                success_count=0,
                failed_providers=[],
                execution_time=0.0,
                merged_results=[]
            )
        
        # 创建异步任务
        tasks = []
        for provider in self.providers:
            task = asyncio.create_task(
                self._search_single_provider_async(provider, query, max_results)
            )
            tasks.append((task, provider.name))
        
        # 等待所有任务完成
        results = []
        providers_used = []
        failed_providers = []
        
        done, pending = await asyncio.wait(
            [task for task, _ in tasks],
            timeout=timeout,
            return_when=asyncio.ALL_COMPLETED
        )
        
        # 处理完成的任务
        for task, provider_name in tasks:
            if task in done:
                try:
                    result = task.result()
                    if result and result.success:
                        results.append(result.to_dict())
                        providers_used.append(provider_name)
                        logger.info(f"[并行搜索] {provider_name} 搜索成功，获得 {len(result.results)} 条结果")
                    else:
                        failed_providers.append(provider_name)
                        logger.warning(f"[并行搜索] {provider_name} 搜索失败")
                except Exception as e:
                    failed_providers.append(provider_name)
                    logger.error(f"[并行搜索] {provider_name} 执行异常: {e}")
            else:
                failed_providers.append(provider_name)
                logger.warning(f"[并行搜索] {provider_name} 超时")
        
        # 取消未完成的任务
        for task in pending:
            task.cancel()
        
        # 计算执行时间
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # 合并结果
        merged_results = self._merge_results(results, max_results)
        
        logger.info(f"[并行搜索] 完成 - 成功: {len(providers_used)}, 失败: {len(failed_providers)}, "
                   f"总结果: {len(merged_results)}, 耗时: {execution_time:.2f}s")
        
        return ParallelSearchResult(
            query=query,
            results=results,
            providers_used=providers_used,
            success_count=len(providers_used),
            failed_providers=failed_providers,
            execution_time=execution_time,
            merged_results=merged_results
        )
    
    def _search_single_provider(
        self,
        provider: BaseSearchProvider,
        query: str,
        max_results: int
    ) -> Optional[SearchResponse]:
        """单个提供者搜索（同步版本）"""
        try:
            return provider.search(query, max_results)
        except Exception as e:
            logger.error(f"[并行搜索] {provider.name} 搜索异常: {e}")
            return None
    
    async def _search_single_provider_async(
        self,
        provider: BaseSearchProvider,
        query: str,
        max_results: int
    ) -> Optional[SearchResponse]:
        """单个提供者搜索（异步版本）"""
        try:
            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                provider.search,
                query,
                max_results
            )
        except Exception as e:
            logger.error(f"[并行搜索] {provider.name} 搜索异常: {e}")
            return None
    
    def _merge_results(
        self,
        results: List[Dict],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        合并多个搜索结果，去除重复项
        
        Args:
            results: 多个引擎的结果列表
            max_results: 最大返回结果数
            
        Returns:
            合并后的结果列表
        """
        if not results:
            return []
        
        # 收集所有结果
        all_items = []
        for result_dict in results:
            items = result_dict.get('results', [])
            all_items.extend(items)
        
        if not all_items:
            return []
        
        # 基于标题去重（简单策略）
        seen_titles = set()
        unique_items = []
        
        for item in all_items:
            title = item.get('title', '').strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_items.append(item)
                if len(unique_items) >= max_results:
                    break
        
        return unique_items[:max_results]
    
    def close(self):
        """关闭资源"""
        self.executor.shutdown(wait=True)
        logger.info("[并行搜索] 服务已关闭")


# 便捷函数
def create_parallel_search_service(
    providers: List[BaseSearchProvider],
    max_workers: int = 3
) -> ParallelSearchService:
    """
    创建并行搜索服务实例
    
    Args:
        providers: 搜索提供者列表
        max_workers: 最大并发数
        
    Returns:
        并行搜索服务实例
    """
    return ParallelSearchService(providers, max_workers)
