# TrendRadar v2.0 - New Version

## 概述

TrendRadar v2.0 是一个全新的重构版本，专注于核心功能：新闻抓取、存储去重、AI总结、生成日报。

## 主要特性

- ✅ **模块化架构**: 清晰的代码结构，易于维护
- ✅ **SQLite存储**: 本地数据库，高效去重
- ✅ **AI智能总结**: 集成OpenAI API，自动生成日报
- ✅ **双格式输出**: HTML可视化 + JSON API
- ✅ **关键词分组**: 支持多维度分类统计

## 目录结构

```
New/
├── main.py                  # 主程序入口
├── core/
│   ├── config.py            # 配置管理
│   ├── crawler.py           # 新闻抓取
│   ├── storage.py           # SQLite存储
│   ├── analyzer.py          # AI总结
│   └── reporter.py          # 日报生成
├── models/
│   └── database.py          # 数据模型
├── config/
│   ├── config.yaml          # 主配置
│   └── keywords.yaml        # 关键词配置
├── output/
│   ├── trendradar.db        # SQLite数据库
│   ├── daily/               # HTML日报
│   └── api/                 # JSON数据
└── requirements.txt         # 依赖
```

## 快速开始

### 1. 安装依赖

```bash
cd New
pip install -r requirements.txt
```

### 2. 配置文件

编辑 `config/config.yaml`:

```yaml
ai:
  api_key: "your-openai-api-key"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o"

crawler:
  sources:
    - id: "weibo"
      name: "微博热搜"
    - id: "zhihu"
      name: "知乎热榜"
```

### 3. 运行

```bash
python main.py
```

## 配置说明

### AI配置

- `api_key`: OpenAI API密钥（必须）
- `base_url`: API基础URL（支持自定义）
- `model`: 模型名称（推荐 gpt-4o）
- `max_tokens`: 最大token数
- `temperature`: 温度参数

### 数据源配置

支持从 newsnow.busiyi.world 获取数据，可配置多个数据源。

### 关键词配置

在 `config/keywords.yaml` 中配置关键词分组：

```yaml
groups:
  - name: AI技术
    keywords:
      - OpenAI
      - ChatGPT
      - Claude
```

## 输出文件

### HTML日报

路径: `output/daily/YYYY-MM-DD.html`

可视化日报，包含：
- AI总结
- 关键词统计
- 匹配新闻列表

### JSON数据

路径: `output/api/YYYY-MM-DD.json`

结构化数据，便于API调用：

```json
{
  "date": "2025-03-05",
  "ai_summary": "...",
  "stats": [...],
  "news": {...}
}
```

## 数据库

路径: `output/trendradar.db`

SQLite数据库，包含以下表：

- `news`: 新闻数据（去重）
- `keywords`: 关键词
- `matches`: 匹配记录
- `daily_reports`: 日报记录

## 日志

路径: `output/trendradar.log`

记录程序运行日志，级别可配置。

## 与旧版本对比

| 特性 | 旧版本 | v2.0 |
|------|--------|------|
| 代码行数 | 5500+ | ~900 |
| 存储方式 | 纯文本 | SQLite |
| 去重 | 文件解析 | 数据库约束 |
| AI集成 | MCP独立 | 主流程集成 |
| 配置 | 复杂 | 简洁 |

## 后续扩展

- [ ] Web界面
- [ ] 实时推送
- [ ] 数据可视化
- [ ] 多用户支持

## License

GPL-3.0
