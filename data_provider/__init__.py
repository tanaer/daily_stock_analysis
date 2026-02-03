# -*- coding: utf-8 -*-
"""
===================================
数据源策略层 - 包初始化
===================================

本包实现策略模式管理多个数据源，实现：
1. 统一的数据获取接口
2. 自动故障切换
3. 防封禁流控策略

数据源优先级（动态调整）：
【港美股+虚拟货币监控优化版】
1. CryptoFetcher (Priority 1) - 🔥 虚拟货币专用（最高优先级）
2. FinnhubFetcher (Priority 2) - 🔥 港美股专用（次高优先级）
3. MassiveFetcher (Priority 3) - 财经新闻专用
4. TushareFetcher (Priority 4) - A股专业数据
5. EfinanceFetcher (Priority 5) - 免费中文数据源
6. AkshareFetcher (Priority 6) - 备选中文数据源
7. PytdxFetcher (Priority 7) - 通达信协议数据
8. BaostockFetcher (Priority 8) - 免费量化数据
9. YfinanceFetcher (Priority 9) - 兜底国际数据源

提示：优先级数字越小越优先，同优先级按初始化顺序排列
"""

from .base import BaseFetcher, DataFetcherManager
from .crypto_fetcher import CryptoFetcher
from .coindesk_fetcher import CoindeskFetcher
from .finnhub_fetcher import FinnhubFetcher
from .massive_fetcher import MassiveFetcher
from .efinance_fetcher import EfinanceFetcher
from .akshare_fetcher import AkshareFetcher
from .tushare_fetcher import TushareFetcher
from .pytdx_fetcher import PytdxFetcher
from .baostock_fetcher import BaostockFetcher
from .yfinance_fetcher import YfinanceFetcher

__all__ = [
    'BaseFetcher',
    'DataFetcherManager',
    'CryptoFetcher',
    'CoindeskFetcher',
    'FinnhubFetcher',
    'MassiveFetcher',
    'EfinanceFetcher',
    'AkshareFetcher',
    'TushareFetcher',
    'PytdxFetcher',
    'BaostockFetcher',
    'YfinanceFetcher',
]
