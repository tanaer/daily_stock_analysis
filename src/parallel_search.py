# -*- coding: utf-8 -*-
"""
===================================
并行搜索服务扩展
===================================

为SearchService添加多源并行搜索功能
"""

import time
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .search_service import SearchService, SearchResponse, SearchResult, ParallelSearchResponse

logger = logging.getLogger(__name__)


def enable_parallel_search(
    search_service: SearchService,
    max_concurrent: int = 4,
    merge_strategy: str = "dedupe_by_url"
) -> SearchService:
    """
    为现有SearchService实例启用并行搜索功能
    
    Args:
        search_service: 原始SearchService实例
        max_concurrent: 最大并发数
        merge_strategy: 合并策略 ("dedupe_by_url", "score_based", "keep_all")
        
    Returns:
        增强后的SearchService实例
    """
    # 添加并行搜索方法到实例
    search_service.max_concurrent_searches = max_concurrent
    search_service.merge_strategy = merge_strategy
    
    # 绑定并行搜索方法
    search_service.search_parallel = lambda query, max_results=5, days=7: _search_parallel(
        search_service, query, max_results, days, merge_strategy
    )
    
    # 绑定股票并行搜索方法
    search_service.search_stock_news_parallel = lambda code, name, max_results=5: _search_stock_news_parallel(
        search_service, code, name, max_results, merge_strategy
    )
    
    logger.info(f"[并行搜索] 已为SearchService启用并行功能 (最大并发: {max_concurrent})")
    return search_service


def _search_parallel(
    service: SearchService,
    query: str,
    max_results_per_engine: int = 5,
    days: int = 7,
    merge_strategy: str = "dedupe_by_url"
) -> ParallelSearchResponse:
    """
    执行多源并行搜索的核心实现
    """
    if not service._providers:
        return ParallelSearchResponse(
            query=query,
            results=[],
            providers_used=[],
            provider_details={},
            success=False,
            error_message="未配置任何搜索引擎"
        )
    
    start_time = time.time()
    available_providers = [p for p in service._providers if p.is_available]
    
    if not available_providers:
        return ParallelSearchResponse(
            query=query,
            results=[],
            providers_used=[],
            provider_details={},
            success=False,
            error_message="无可用的搜索引擎"
        )
    
    logger.info(f"[并行搜索] 启动多源搜索: '{query}'，使用 {len(available_providers)} 个搜索引擎")
    
    # 并行执行所有搜索引擎
    provider_details = {}
    providers_used = []
    
    max_workers = min(len(available_providers), getattr(service, 'max_concurrent_searches', 4))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有搜索任务
        future_to_provider = {
            executor.submit(provider.search, query, max_results_per_engine, days): provider
            for provider in available_providers
        }
        
        # 收集结果
        for future in as_completed(future_to_provider):
            provider = future_to_provider[future]
            try:
                response = future.result()
                provider_details[provider.name] = response
                providers_used.append(provider.name)
                
                if response.success:
                    logger.info(f"[{provider.name}] 搜索完成，返回 {len(response.results)} 条结果，耗时 {response.search_time:.2f}s")
                else:
                    logger.warning(f"[{provider.name}] 搜索失败: {response.error_message}")
                    
            except Exception as e:
                error_response = SearchResponse(
                    query=query,
                    results=[],
                    provider=provider.name,
                    success=False,
                    error_message=str(e)
                )
                provider_details[provider.name] = error_response
                providers_used.append(provider.name)
                logger.error(f"[{provider.name}] 搜索异常: {e}")
    
    # 合并结果
    merged_results, merge_stats = _merge_search_results(
        provider_details, 
        strategy=merge_strategy
    )
    
    total_time = time.time() - start_time
    
    logger.info(f"[并行搜索] 完成，总计获得 {len(merged_results)} 条去重结果，总耗时 {total_time:.2f}s")
    
    return ParallelSearchResponse(
        query=query,
        results=merged_results,
        providers_used=providers_used,
        provider_details=provider_details,
        success=True,
        total_search_time=total_time,
        merge_stats=merge_stats
    )


def _search_stock_news_parallel(
    service: SearchService,
    stock_code: str,
    stock_name: str,
    max_results_per_engine: int = 5,
    merge_strategy: str = "dedupe_by_url"
) -> ParallelSearchResponse:
    """
    股票新闻的并行搜索
    """
    # 构建搜索查询
    query = f"{stock_name} {stock_code} 股票 最新消息"
    
    # 智能确定搜索时间范围
    import datetime
    today_weekday = datetime.datetime.now().weekday()
    if today_weekday == 0:  # 周一
        search_days = 3
    elif today_weekday >= 5:  # 周六、周日
        search_days = 2
    else:  # 周二至周五
        search_days = 1
    
    return _search_parallel(service, query, max_results_per_engine, search_days, merge_strategy)


def _merge_search_results(
    provider_responses: Dict[str, SearchResponse],
    strategy: str = "dedupe_by_url"
) -> tuple[List[SearchResult], Dict[str, int]]:
    """
    合并多个搜索引擎的结果
    
    Args:
        provider_responses: 各搜索引擎的响应字典
        strategy: 合并策略
        
    Returns:
        (合并后的结果列表, 各源贡献统计)
    """
    all_results = []
    source_stats = {}
    
    # 收集所有结果
    for provider_name, response in provider_responses.items():
        if response.success and response.results:
            all_results.extend(response.results)
            source_stats[provider_name] = len(response.results)
    
    if not all_results:
        return [], source_stats
    
    # 根据策略合并
    if strategy == "dedupe_by_url":
        # 按URL去重，保留最早出现的结果
        seen_urls = set()
        deduped_results = []
        
        for result in all_results:
            url_key = result.url.lower().strip()
            if url_key and url_key not in seen_urls:
                seen_urls.add(url_key)
                deduped_results.append(result)
        
        logger.info(f"[结果合并] 去重前: {len(all_results)} 条，去重后: {len(deduped_results)} 条")
        return deduped_results, source_stats
        
    elif strategy == "score_based":
        # 基于分数排序（假设有相关性分数）
        # 这里简化处理，按来源权重排序
        sorted_results = sorted(all_results, key=lambda x: (
            x.source in ["Exa", "Tavily"],  # 高质量源优先
            len(x.snippet)  # 内容更长的优先
        ), reverse=True)
        return sorted_results[:len(all_results)//2], source_stats  # 取前一半
        
    else:  # keep_all
        return all_results, source_stats


# 使用示例和测试函数
def demo_parallel_search():
    """
    演示并行搜索功能的使用方法
    """
    print("=== 并行搜索功能演示 ===")
    print("1. 启用并行搜索:")
    print("   search_service = enable_parallel_search(search_service)")
    print("")
    print("2. 执行并行搜索:")
    print("   response = search_service.search_parallel('人工智能 股票')")
    print("")
    print("3. 股票新闻并行搜索:")
    print("   response = search_service.search_stock_news_parallel('600519', '贵州茅台')")
    print("")
    print("4. 查看合并结果:")
    print("   print(response.to_context())")
    print("   print(f'使用搜索引擎: {response.providers_used}')")
    print("   print(f'各源贡献: {response.merge_stats}')")


if __name__ == "__main__":
    demo_parallel_search()
