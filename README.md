# 股票盯盘、看盘系统

基于 FastAPI + 东方财富数据 + DeepSeek AI 的股票监控与分析系统。

## 功能特性

- **实时行情监控** - 通过填写股票代码添加关注，实时获取行情数据
- **涨跌幅提醒** - 设置关注股票的涨跌幅提醒阈值，支持连续涨跌提醒
- **市场情绪数据** - 实时获取上涨/下跌家数、涨停/跌停统计、北向资金等数据
- **资金流向分析** - 获取个股主力资金、散户资金流入流出数据
- **AI 新闻解读** - 使用 DeepSeek AI 解读股票相关新闻和公告
- **AI 行情分析** - 使用 AI 分析股票走势和市场情绪

## 项目结构

```text
clawdbot-stocks/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 主应用
│   ├── config.py            # 配置文件
│   ├── models.py            # 数据模型
│   ├── services/
│   │   ├── stock_service.py     # 股票数据服务
│   │   ├── alert_service.py     # 提醒服务
│   │   └── deepseek_service.py  # DeepSeek AI 服务
│   ├── routers/
│   │   ├── stocks.py        # 股票相关路由
│   │   ├── alerts.py        # 提醒相关路由
│   │   └── analysis.py      # AI 分析路由
│   └── utils/
│       └── eastmoney.py     # 东方财富 API 封装
├── static/
│   └── index.html           # 前端界面
├── requirements.txt
├── run.py                   # 启动脚本
├── .env.example             # 环境变量示例
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置 DeepSeek API Key
```

### 3. 启动服务

```bash
python run.py
```

服务将在 `http://localhost:8000` 启动。

访问 `http://localhost:8000/docs` 查看 API 文档。

## API 接口

### 股票相关

| 接口                                | 方法   | 说明           |
| ----------------------------------- | ------ | -------------- |
| `/api/stocks/search?keyword=xxx`    | GET    | 搜索股票       |
| `/api/stocks/quote/{code}`          | GET    | 获取单只股票行情 |
| `/api/stocks/capital-flow/{code}`   | GET    | 获取个股资金流向 |
| `/api/stocks/watch-list`            | GET    | 获取关注列表    |
| `/api/stocks/watch-list/quotes`     | GET    | 获取关注列表行情 |
| `/api/stocks/watch-list`            | POST   | 添加股票到关注列表 |
| `/api/stocks/watch-list/{code}`     | DELETE | 从关注列表移除   |
| `/api/stocks/watch-list/{code}/alert` | PUT  | 更新提醒设置    |
| `/api/stocks/market/sentiment`      | GET    | 获取市场情绪    |

### 提醒相关

| 接口                 | 方法   | 说明           |
| -------------------- | ------ | -------------- |
| `/api/alerts`        | GET    | 获取提醒列表    |
| `/api/alerts/check`  | POST   | 检查并触发提醒  |
| `/api/alerts`        | DELETE | 清除所有提醒    |
| `/api/alerts/settings` | POST | 更新提醒设置    |

### AI 分析相关

| 接口                              | 方法 | 说明              |
| --------------------------------- | ---- | ----------------- |
| `/api/analysis/stock/{code}`      | GET  | AI 分析股票行情    |
| `/api/analysis/market`            | GET  | AI 分析市场情绪    |
| `/api/analysis/news`              | POST | AI 解读新闻        |
| `/api/analysis/announcement`      | POST | AI 解读公告        |
| `/api/analysis/news/{code}`       | GET  | 获取并分析股票新闻  |
| `/api/analysis/announcements/{code}` | GET | 获取股票公告列表  |
| `/api/analysis/daily-summary`     | GET  | 生成每日盯盘总结   |

## 使用示例

### 添加股票到关注列表

```bash
curl -X POST "http://localhost:8000/api/stocks/watch-list" \
  -H "Content-Type: application/json" \
  -d '{"code": "600519", "alert_up": 5.0, "alert_down": -5.0, "note": "茅台"}'
```

### 获取关注列表行情

```bash
curl "http://localhost:8000/api/stocks/watch-list/quotes"
```

### AI 分析股票

```bash
curl "http://localhost:8000/api/analysis/stock/600519"
```

### AI 分析市场情绪

```bash
curl "http://localhost:8000/api/analysis/market"
```

### 获取并分析股票新闻

```bash
curl "http://localhost:8000/api/analysis/news/600519?analyze=true"
```

### 生成每日盯盘总结

```bash
curl "http://localhost:8000/api/analysis/daily-summary"
```

## 配置说明

| 配置项                    | 说明                 | 默认值 |
| ------------------------- | -------------------- | ------ |
| `DEEPSEEK_API_KEY`        | DeepSeek API 密钥    | -      |
| `ALERT_THRESHOLD_UP`      | 默认涨幅提醒阈值(%)  | 3.0    |
| `ALERT_THRESHOLD_DOWN`    | 默认跌幅提醒阈值(%)  | -3.0   |
| `CONSECUTIVE_ALERT_COUNT` | 连续涨跌提醒天数     | 3      |
| `REFRESH_INTERVAL`        | 数据刷新间隔(秒)     | 10     |

## 数据来源

- 股票行情数据：东方财富公开接口
- 资金流向数据：东方财富公开接口
- 市场情绪数据：东方财富公开接口
- AI 分析：DeepSeek API

## 注意事项

1. DeepSeek API 需要配置有效的 API Key 才能使用 AI 分析功能
2. 东方财富接口为公开接口，请合理使用，避免频繁请求
3. AI 分析结果仅供参考，不构成投资建议
