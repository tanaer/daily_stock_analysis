# 港美股+虚拟货币监控优化配置指南

## 推荐数据源组合

### 核心数据源（必配）
```
# 虚拟货币监控（最高优先级）
CRYPTO_API_KEY=your_coingecko_key    # CoinGecko免费API
COINDESK_API_KEY=your_coindesk_key   # Coindesk权威数据

# 港美股监控（次高优先级）
FINNHUB_API_KEY=your_finnhub_key     # Finnhub免费额度较高
MASSIVE_API_KEY=your_massive_key     # 财经新闻聚合

# 搜索引擎（信息补充）
EXA_API_KEYS=exa_key1,exa_key2       # 高质量内容提取
TAVILY_API_KEYS=tavily_key1          # AI优化搜索
BOCHA_API_KEYS=bocha_key1            # 中文搜索优化
```

### 自选股配置说明

**使用 STOCK_LIST 变量配置所有标的（股票+虚拟货币）**

```
# 配置格式：混合添加，系统自动识别类型
STOCK_LIST=BTC,ETH,SOL,hk00700,hk03690,AAPL,TSLA,NVDA
```

**标的类型识别规则：**
- **虚拟货币**：BTC, ETH, SOL, XRP, ADA 等标准符号（2-6个字母）
- **港股**：hk00700, hk03690 等（hk前缀或5位数字）
- **美股**：AAPL, TSLA, NVDA 等（全大写字母）
- **A股**：600519, 000001 等（6位数字）

### 示例配置

#### 基础组合（免费）
```bash
STOCK_LIST=BTC,ETH,hk00700,AAPL
CRYPTO_API_KEY=free_coingecko
FINNHUB_API_KEY=free_finnhub
EXA_API_KEYS=trial_key
```

#### 专业组合（全面监控）
```bash
STOCK_LIST=BTC,ETH,SOL,XRP,ADA,hk00700,hk03690,hk09618,AAPL,TSLA,NVDA,MSFT,GOOGL
CRYPTO_API_KEY=paid_coingecko
COINDESK_API_KEY=your_coindesk_key
FINNHUB_API_KEY=pro_finnhub
MASSIVE_API_KEY=pro_massive
EXA_API_KEYS=key1,key2,key3
```

## 智能市场过滤机制

系统会根据 STOCK_LIST 中的标的自动识别市场类型，并只获取相关市场的数据：

✅ **只会返回配置的相关市场指数**
- 配置了BTC,ETH → 只返回虚拟货币市场数据
- 配置了hk00700,hk03690 → 只返回港股市场数据  
- 配置了AAPL,TSLA → 只返回美股市场数据
- 配置了600519,000001 → 只返回A股市场数据

❌ **不会返回无关市场的数据**
- 不会返回未配置市场的指数（如只配置虚拟货币时不返回上证指数）

## 数据源特性对比

| 数据源 | 适用场景 | 优势 | 限制 |
|--------|----------|------|------|
| **CryptoFetcher** | 虚拟货币 | 实时性强、免费、覆盖全 | 仅支持主流币 |
| **CoindeskFetcher** | 虚拟货币 | 权威数据、新闻资讯 | 部分API需付费 |
| **FinnhubFetcher** | 港美股 | 全球覆盖、基本面丰富 | 免费额度有限 |
| **MassiveFetcher** | 财经新闻 | 专业性强、情绪分析 | 需付费订阅 |
| **ExaSearch** | 深度搜索 | 内容精准、摘要质量高 | API调用成本较高 |

## 使用注意事项

1. **API调用频率**：建议设置适当延迟避免限流
2. **数据质量**：虚拟货币数据更新最频繁，港美股次之
3. **成本控制**：Exa等高级API按调用计费，注意用量
4. **监控范围**：可根据需要调整STOCK_LIST中的标的

这种配置既满足了精准的市场过滤需求，又保持了良好的容错性和扩展性。
