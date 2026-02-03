# 港美股+虚拟货币监控优化配置指南

## 推荐数据源组合

### 核心数据源（必配）
```
# 虚拟货币监控（最高优先级）
CRYPTO_API_KEY=your_coingecko_key  # CoinGecko免费API

# 港美股监控（次高优先级）
FINNHUB_API_KEY=your_finnhub_key   # Finnhub免费额度较高
MASSIVE_API_KEY=your_massive_key   # 财经新闻聚合

# 搜索引擎（信息补充）
EXA_API_KEYS=exa_key1,exa_key2     # 高质量内容提取
TAVILY_API_KEYS=tavily_key1        # AI优化搜索
BOCHA_API_KEYS=bocha_key1          # 中文搜索优化
```

### 自选股示例配置
```
# 港股+美股+虚拟货币组合
STOCK_LIST=hk00700,hk03690,AAPL,TSLA,BTC,ETH,SOL
```

## 数据源特性对比

| 数据源 | 适用场景 | 优势 | 限制 |
|--------|----------|------|------|
| **CryptoFetcher** | 虚拟货币 | 实时性强、免费、覆盖全 | 仅支持主流币 |
| **FinnhubFetcher** | 港美股 | 全球覆盖、基本面丰富 | 免费额度有限 |
| **MassiveFetcher** | 财经新闻 | 专业性强、情绪分析 | 需付费订阅 |
| **ExaSearch** | 深度搜索 | 内容精准、摘要质量高 | API调用成本较高 |

## 优先级策略说明

1. **Crypto > Finnhub > Massive** - 针对你的监控需求定制
2. **Exa + Tavily + Bocha** - 多源信息互补，避免单一依赖
3. **故障自动切换** - 任一源失效不影响整体分析

## 配置建议

### 免费组合（基础监控）
```bash
STOCK_LIST=BTC,ETH,hk00700,AAPL
CRYPTO_API_KEY=free_coingecko  # 免费
FINNHUB_API_KEY=free_finnhub   # 每月60次免费调用
EXA_API_KEYS=trial_key         # 试用额度
```

### 专业组合（全面监控）
```bash
STOCK_LIST=BTC,ETH,SOL,hk00700,hk03690,AAPL,TSLA,NVDA
CRYPTO_API_KEY=paid_coingecko
FINNHUB_API_KEY=pro_finnhub
MASSIVE_API_KEY=pro_massive
EXA_API_KEYS=key1,key2,key3
TAVILY_API_KEYS=key1,key2
```

## 使用注意事项

1. **API调用频率**：建议设置适当延迟避免限流
2. **数据质量**：虚拟货币数据更新最频繁，港美股次之
3. **成本控制**：Exa等高级API按调用计费，注意用量
4. **监控范围**：可根据需要调整STOCK_LIST中的标的

这种配置既满足了你对港美股和虚拟货币的监控需求，又保持了良好的容错性和扩展性。
