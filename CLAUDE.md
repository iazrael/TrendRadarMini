# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

TrendRadar v2.0 - 新闻抓取、存储去重、AI总结、日报生成系统。从 newsnow API 抓取热点新闻，通过关键词匹配分类，使用 OpenAI API 生成 AI 总结，输出 HTML 和 JSON 格式的日报。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行主程序
python main.py
```

## 架构

```
main.py                    # 主程序入口，编排完整工作流
├── core/config.py         # 配置管理，加载 YAML 配置
├── core/crawler.py        # 新闻抓取，从 newsnow API 获取数据
├── core/storage.py        # SQLite 存储，负责去重和关键词匹配
├── core/analyzer.py       # AI 分析，调用 OpenAI API 生成总结
└── core/reporter.py       # 日报生成，输出 HTML 和 JSON

models/database.py         # 数据库表结构定义
config/config.yaml         # 主配置（AI、数据源、存储）
config/keywords.yaml       # 关键词分组配置
```

### 数据流

1. **配置加载**: `Config` 读取 `config.yaml` 和 `keywords.yaml`
2. **新闻抓取**: `NewsCrawler` 从 newsnow API 获取多源新闻
3. **存储去重**: `NewsStorage` 通过 `(title, source_id)` 唯一约束自动去重
4. **关键词匹配**: 标题关键词匹配，按分组统计
5. **AI 总结**: `AIAnalyzer` 调用 OpenAI API 生成日报总结
6. **报告输出**: HTML 可视化日报 + JSON API 数据

### 数据库表

- `news`: 新闻数据，`(title, source_id)` 唯一约束实现去重
- `keywords`: 关键词分组
- `matches`: 新闻-关键词匹配记录
- `daily_reports`: 日报存档

## 配置说明

### AI 配置 (config.yaml)

```yaml
ai:
  api_key: "your-openai-api-key"  # 或通过 OPENAI_API_KEY 环境变量设置
  base_url: "https://api.openai.com/v1"  # 支持自定义 API 端点
  model: "gpt-4o"
```

### 数据源配置

数据源 ID 对应 newsnow API 的 `s` 参数，例如 `weibo` 对应微博热搜。

### 关键词分组 (keywords.yaml)

```yaml
groups:
  - name: AI技术
    priority: 1
    keywords:
      - OpenAI
      - ChatGPT
```

## 输出文件

- `output/trendradar.db`: SQLite 数据库
- `output/daily/YYYY-MM-DD.html`: HTML 日报
- `output/api/YYYY-MM-DD.json`: JSON 数据
- `output/trendradar.log`: 运行日志