# 数据源与搜索API配置指南

## 新增数据源介绍

### 1. Finnhub (finnhub.io)
**功能特性：**
- 全球市场实时股价数据
- 公司基本面信息
- 技术指标计算
- 市场新闻聚合
- 行业分类数据

**获取API密钥：**
1. 访问 [Finnhub官网](https://finnhub.io)
2. 注册免费账户
3. 在Dashboard获取API密钥
4. 免费版每月60次API调用

**配置方式：**
```bash
# 在 .env 文件中添加
FINNHUB_API_KEY=your_api_key_here
```

### 2. Massive (massive.com)
**功能特性：**
- 专业财经新闻聚合
- 市场情绪分析
- 行业动态追踪
- 公司公告监控
- 宏观经济数据

**获取API密钥：**
1. 访问 [Massive官网](https://massive.com)
2. 注册开发者账户
3. 创建应用获取API密钥

**配置方式：**
```bash
# 在 .env 文件中添加
MASSIVE_API_KEY=your_api_key_here
```

### 3. Exa Search (exa.ai)
**功能特性：**
- 高级网页搜索
- 智能内容提取
- 精准信息摘要
- 相似内容推荐
- 实时数据检索

**获取API密钥：**
1. 访问 [Exa官网](https://exa.ai)
2. 注册账户
3. 获取API访问密钥

**配置方式：**
```bash
# 在 .env 文件中添加（支持多个密钥轮询）
EXA_API_KEYS=key1,key2,key3
```

## 配置优先级说明

系统按照以下优先级使用数据源：

1. **Tushare** (最高优先级) - 专业的A股数据
2. **Finnhub** - 全球市场实时数据
3. **AkShare** - 免费的中文数据源
4. **Pytdx** - 通达信协议数据
5. **Baostock** - 免费量化数据
6. **YFinance** - 美股港股数据

搜索API优先级：
1. **Exa** (最高优先级) - 高质量内容提取
2. **Bocha** - 中文搜索优化
3. **Tavily** - 英文内容搜索
4. **SerpAPI** - 多搜索引擎聚合

## 完整配置示例

```bash
# ==================== 核心配置 ====================
STOCK_LIST=600519,000001,300750,AAPL,TSLA,hk00700

# ==================== AI分析配置 ====================
GEMINI_API_KEY=your_gemini_key
# 或使用OpenAI兼容API
# OPENAI_API_KEY=your_openai_key
# OPENAI_BASE_URL=https://api.deepseek.com/v1
# OPENAI_MODEL=deepseek-chat

# ==================== 数据源配置 ====================
# Tushare专业数据（推荐）
TUSHARE_TOKEN=your_tushare_token

# Finnhub全球数据
FINNHUB_API_KEY=your_finnhub_key

# Massive财经数据
MASSIVE_API_KEY=your_massive_key

# ==================== 搜索API配置 ====================
# Exa高级搜索（推荐）
EXA_API_KEYS=key1,key2,key3

# Bocha中文搜索
BOCHA_API_KEYS=bocha_key1,bocha_key2

# Tavily英文搜索
TAVILY_API_KEYS=tavily_key1,tavily_key2

# SerpAPI多引擎搜索
SERPAPI_API_KEYS=serpapi_key1,serpapi_key2

# ==================== 通知配置 ====================
# 企业微信
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# 飞书
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 邮件
EMAIL_SENDER=your_email@qq.com
EMAIL_PASSWORD=your_auth_code

# ==================== 其他配置 ====================
# 报告类型：simple(精简) 或 full(完整)
REPORT_TYPE=full

# 单股推送模式
SINGLE_STOCK_NOTIFY=true

# 分析间隔（秒）
ANALYSIS_DELAY=10
```

## 使用建议

### 免费组合方案
```bash
# 最小配置（完全免费）
STOCK_LIST=600519,AAPL
GEMINI_API_KEY=your_free_gemini_key  # Google提供免费额度
# 使用AkShare和YFinance免费数据源
```

### 专业投资者方案
```bash
# 完整配置
STOCK_LIST=600519,000001,300750,AAPL,TSLA,hk00700
TUSHARE_TOKEN=your_tushare_token      # 专业A股数据
FINNHUB_API_KEY=your_finnhub_key      # 全球市场数据
MASSIVE_API_KEY=your_massive_key      # 财经新闻
EXA_API_KEYS=exa_key1,exa_key2        # 高级搜索
GEMINI_API_KEY=your_gemini_key        # AI分析
```

## 故障排除

### 数据源不可用时
系统会自动切换到下一个可用的数据源，无需人工干预。

### API调用超频
- 系统内置指数退避重试机制
- 建议配置多个API Key实现负载均衡
- 可调整 `ANALYSIS_DELAY` 参数增加请求间隔

### 搜索结果质量
- Exa > Bocha > Tavily > SerpAPI（按质量排序）
- 建议优先配置Exa和Bocha
- 可根据需求选择中英文搜索API

## 性能优化建议

1. **API Key轮询**：为每个服务配置多个Key以提高可用性
2. **合理设置并发数**：避免触发API限流
3. **启用缓存**：系统自动缓存当日数据
4. **选择合适的报告类型**：full模式信息更丰富但耗时较长
