# TrendRadar 重构设计方案

> **版本**: v2.0
> **日期**: 2025-03-05
> **状态**: 设计阶段

---

## 📋 目录

- [项目概述](#项目概述)
- [重构目标](#重构目标)
- [架构设计](#架构设计)
- [数据库设计](#数据库设计)
- [模块设计](#模块设计)
- [配置文件设计](#配置文件设计)
- [API设计](#api设计)
- [实现计划](#实现计划)
- [迁移策略](#迁移策略)

---

## 项目概述

### 当前问题

1. **单体架构**: main.py 5500+ 行，维护困难
2. **存储方式**: 纯文本文件存储，查询效率低
3. **去重机制**: 文件解析去重，性能差
4. **AI功能**: MCP Server独立，未集成到主流程
5. **推送复杂**: 多渠道推送代码冗余（3000+ 行）

### 重构目标

- ✅ 根据关键字和分组抓取新闻
- ✅ 存档去重（本地SQLite数据库）
- ✅ AI总结（远程API）
- ✅ 生成日报（HTML + JSON）

### 核心功能

```
抓取 → 存储 → 去重 → 匹配 → AI总结 → 日报生成
```

---

## 架构设计

### 目录结构

```
TrendRadar/
├── main.py                  # 入口（<500行）
├── core/
│   ├── __init__.py
│   ├── config.py            # 配置管理
│   ├── crawler.py           # 新闻抓取
│   ├── storage.py           # SQLite存储+去重
│   ├── analyzer.py          # AI总结
│   └── reporter.py          # 日报生成
├── models/
│   ├── __init__.py
│   └── database.py          # 数据模型
├── config/
│   ├── config.yaml          # 主配置
│   └── keywords.yaml        # 关键词+分组配置
├── output/
│   ├── trendradar.db        # SQLite数据库
│   ├── daily/               # HTML日报
│   │   └── 2025-03-05.html
│   └── api/                 # JSON数据
│       └── 2025-03-05.json
├── requirements.txt
└── REFACTOR_PLAN.md         # 本文档
```

### 模块依赖

```
main.py
  ├── Config
  ├── NewsCrawler
  ├── NewsStorage
  ├── AIAnalyzer
  └── ReportGenerator
```

---

## 数据库设计

### 表结构

#### 1. news（新闻表）

```sql
CREATE TABLE news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT,
    mobile_url TEXT,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    rank INTEGER,
    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title, source_id)
);

-- 索引
CREATE INDEX idx_news_crawled_at ON news(crawled_at);
CREATE INDEX idx_news_source ON news(source_id);
```

#### 2. keywords（关键词表）

```sql
CREATE TABLE keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT NOT NULL,
    keyword TEXT NOT NULL,
    UNIQUE(group_name, keyword)
);

-- 索引
CREATE INDEX idx_keywords_group ON keywords(group_name);
```

#### 3. matches（匹配记录表）

```sql
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id INTEGER NOT NULL,
    keyword_id INTEGER NOT NULL,
    matched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE,
    UNIQUE(news_id, keyword_id)
);

-- 索引
CREATE INDEX idx_matches_news ON matches(news_id);
CREATE INDEX idx_matches_keyword ON matches(keyword_id);
CREATE INDEX idx_matches_date ON matches(matched_at);
```

#### 4. daily_reports（日报表）

```sql
CREATE TABLE daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,
    summary_html TEXT,
    summary_json TEXT,
    ai_summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 数据关系

```
news (新闻)
  ├── source_id → 外部数据源
  └── id → matches.news_id

keywords (关键词)
  ├── group_name → 分组
  └── id → matches.keyword_id

matches (匹配)
  ├── news_id → news.id
  └── keyword_id → keywords.id

daily_reports (日报)
  └── date → 报告日期
```

---

## 模块设计

### core/config.py

**职责**: 配置文件加载与管理

```python
class Config:
    """配置管理器"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self.load_yaml(config_path)

    def load_yaml(self, path: str) -> dict:
        """加载YAML配置"""

    @property
    def ai_api_key(self) -> str:
        """获取AI API密钥"""

    @property
    def ai_model(self) -> str:
        """获取AI模型"""

    @property
    def db_path(self) -> str:
        """获取数据库路径"""

    def get_sources(self) -> List[Dict]:
        """获取数据源列表"""

    def get_keywords(self) -> Dict[str, List[str]]:
        """获取关键词分组"""
```

**代码量**: ~80行

---

### core/crawler.py

**职责**: 新闻数据抓取

```python
class NewsCrawler:
    """新闻抓取器"""

    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url
        self.session = requests.Session()

    def fetch_from_source(
        self, source_id: str, source_name: str
    ) -> List[Dict]:
        """从单个数据源抓取新闻"""

    def fetch_all(self, sources: List[Dict]) -> List[Dict]:
        """批量抓取所有数据源"""

    def parse_response(self, data: dict) -> List[Dict]:
        """解析newsnow API响应"""

    def _make_request(self, url: str) -> Optional[dict]:
        """发送HTTP请求"""
```

**返回数据结构**:
```python
{
    "title": "标题",
    "url": "链接",
    "mobile_url": "移动端链接",
    "source_id": "数据源ID",
    "source_name": "数据源名称",
    "rank": 1
}
```

**代码量**: ~200行

---

### core/storage.py

**职责**: SQLite存储、去重、查询

```python
class NewsStorage:
    """SQLite存储管理器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.init_db()

    def init_db(self):
        """初始化数据库表"""

    def save_news(self, news_list: List[Dict]) -> List[int]:
        """批量保存新闻（自动去重，返回新增的news_id）"""

    def load_keywords(self, keywords: Dict[str, List[str]]):
        """加载关键词到数据库"""

    def match_keywords(self, news_id: int, title: str) -> List[int]:
        """匹配关键词，返回keyword_id列表"""

    def save_matches(self, matches: List[Tuple[int, int]]):
        """批量保存匹配记录"""

    def match_and_save_all(self, news_ids: List[int], keywords_config: Dict):
        """批量匹配并保存"""

    def get_news_by_date(self, date: str) -> List[Dict]:
        """获取指定日期的新闻"""

    def get_keyword_stats(self, group_name: Optional[str] = None) -> Dict:
        """获取关键词统计（按分组）"""

    def get_daily_summary(self, date: str) -> Dict:
        """获取每日汇总数据"""

    def close(self):
        """关闭数据库连接"""
```

**代码量**: ~300行

---

### core/analyzer.py

**职责**: AI总结生成

```python
class AIAnalyzer:
    """AI总结器"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def summarize_news(self, news_data: Dict) -> str:
        """生成新闻总结"""

    def generate_insights(self, stats: Dict) -> str:
        """生成洞察分析"""

    def _build_prompt(self, news_data: Dict, stats: Dict) -> str:
        """构建AI提示词"""

    def _call_ai(self, prompt: str, max_tokens: int = 2000) -> str:
        """调用AI API"""
```

**Prompt设计**:
```
你是一个专业的新闻分析师。请根据以下数据生成简明扼要的日报总结：

【关键词统计】
- AI技术: 15条新闻
- 大模型: 8条新闻

【重要新闻】
1. OpenAI发布GPT-5
2. Claude 4支持多模态

请生成：
1. 今日热点概述（100字）
2. 关键词趋势分析（200字）
3. 重要新闻点评（300字）
```

**代码量**: ~150行

---

### core/reporter.py

**职责**: 日报生成（HTML + JSON）

```python
class ReportGenerator:
    """日报生成器"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.html_dir = os.path.join(output_dir, "daily")
        self.api_dir = os.path.join(output_dir, "api")
        self._ensure_dirs()

    def generate_html(
        self,
        date: str,
        news_data: Dict,
        ai_summary: str
    ) -> str:
        """生成HTML日报"""

    def generate_json(
        self,
        date: str,
        news_data: Dict,
        ai_summary: str
    ) -> str:
        """生成JSON数据"""

    def save_report(self, date: str, html: str, json_data: str):
        """保存日报文件"""

    def _render_html_template(self, data: Dict) -> str:
        """渲染HTML模板"""

    def _ensure_dirs(self):
        """确保输出目录存在"""
```

**HTML模板结构**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>TrendRadar日报 - {date}</title>
    <style>...</style>
</head>
<body>
    <h1>📊 TrendRadar日报</h1>
    <div class="ai-summary">{ai_summary}</div>
    <div class="stats">{keyword_stats}</div>
    <div class="news-list">{news_list}</div>
</body>
</html>
```

**JSON格式**:
```json
{
    "date": "2025-03-05",
    "ai_summary": "...",
    "stats": {
        "AI技术": {"count": 15, "news": [...]},
        "大模型": {"count": 8, "news": [...]}
    }
}
```

**代码量**: ~200行

---

## 配置文件设计

### config/config.yaml

```yaml
# AI配置
ai:
  api_key: "sk-xxxxxxxxxxxxxxxx"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o"
  max_tokens: 2000
  temperature: 0.7

# 数据源配置
crawler:
  sources:
    - id: "weibo"
      name: "微博热搜"
      alias: "微博"
    - id: "zhihu"
      name: "知乎热榜"
      alias: "知乎"
    - id: "36kr"
      name: "36氪快讯"
      alias: "36氪"
    - id: "hackernews"
      name: "Hacker News"
      alias: "HN"

  request_interval: 1000  # 毫秒
  timeout: 10  # 秒
  max_retries: 2

  proxy:
    enabled: false
    url: "http://127.0.0.1:10086"

# 存储配置
storage:
  db_path: "output/trendradar.db"
  batch_size: 100  # 批量插入大小

# 报告配置
report:
  output_dir: "output"
  html_template: "templates/daily_report.html"

# 日志配置
logging:
  level: "INFO"
  file: "output/trendradar.log"
```

### config/keywords.yaml

```yaml
groups:
  - name: AI技术
    priority: 1
    keywords:
      - OpenAI
      - ChatGPT
      - Claude
      - Anthropic
      - DeepSeek
      - Kimi
      - 通义千问
      - 文心一言

  - name: 大模型
    priority: 2
    keywords:
      - Llama
      - Gemma
      - Yi
      - Qwen
      - Baichuan
      - GLM

  - name: 多模态
    priority: 3
    keywords:
      - 视觉模型
      - 图像生成
      - Sora
      - Midjourney
      - DALL-E

  - name: 应用场景
    priority: 4
    keywords:
      - AI Agent
      - RAG
      - 代码助手
      - 智能客服
```

---

## API设计

### 1. main.py - 主流程

```python
def main():
    """主流程"""
    # 1. 初始化
    config = Config()
    storage = NewsStorage(config.db_path)
    crawler = NewsCrawler(proxy_url=config.proxy_url)
    analyzer = AIAnalyzer(config.ai_api_key, config.ai_base_url, config.ai_model)
    reporter = ReportGenerator(output_dir=config.output_dir)

    # 2. 加载关键词
    keywords = config.get_keywords()
    storage.load_keywords(keywords)

    # 3. 抓取新闻
    sources = config.get_sources()
    news_list = crawler.fetch_all(sources)

    if not news_list:
        print("⚠️ 未获取到任何新闻")
        return

    # 4. 存储去重
    saved_ids = storage.save_news(news_list)

    if not saved_ids:
        print("✅ 没有新增新闻")
        return

    print(f"💾 新增新闻: {len(saved_ids)} 条")

    # 5. 关键词匹配
    matched_data = storage.match_and_save_all(saved_ids, keywords)
    print(f"🔍 匹配关键词: {sum(len(v) for v in matched_data.values())} 次")

    # 6. 获取统计数据
    today = datetime.now().strftime("%Y-%m-%d")
    stats = storage.get_keyword_stats()

    # 7. AI总结
    print("🤖 生成AI总结...")
    ai_summary = analyzer.summarize_news(stats, matched_data)

    # 8. 生成日报
    html_report = reporter.generate_html(today, matched_data, stats, ai_summary)
    json_report = reporter.generate_json(today, matched_data, stats, ai_summary)
    reporter.save_report(today, html_report, json_report)

    print(f"✅ 日报已生成: {today}")
    print(f"   📄 HTML: {reporter.html_dir}/{today}.html")
    print(f"   📦 JSON: {reporter.api_dir}/{today}.json")

    # 9. 清理
    storage.close()


if __name__ == "__main__":
    main()
```

---

## 实现计划

### Phase 1: 基础设施（1-2天）

- [x] 创建目录结构
- [ ] 实现 `core/config.py`
- [ ] 实现 `models/database.py`
- [ ] 创建配置文件模板

### Phase 2: 数据层（2-3天）

- [ ] 实现 `core/storage.py`
  - [ ] 数据库初始化
  - [ ] 新闻存储（去重）
  - [ ] 关键词加载
  - [ ] 匹配逻辑
  - [ ] 查询接口

### Phase 3: 抓取层（1-2天）

- [ ] 实现 `core/crawler.py`
  - [ ] 单源抓取
  - [ ] 批量抓取
  - [ ] 错误处理
  - [ ] 代理支持

### Phase 4: AI层（1-2天）

- [ ] 实现 `core/analyzer.py`
  - [ ] OpenAI客户端集成
  - [ ] Prompt设计
  - [ ] 总结生成
  - [ ] 洞察分析

### Phase 5: 报表层（1-2天）

- [ ] 实现 `core/reporter.py`
  - [ ] HTML模板
  - [ ] JSON格式化
  - [ ] 文件保存

### Phase 6: 主流程（1天）

- [ ] 实现 `main.py`
- [ ] 集成各模块
- [ ] 错误处理
- [ ] 日志记录

### Phase 7: 测试优化（2-3天）

- [ ] 单元测试
- [ ] 性能优化
- [ ] 文档完善
- [ ] Bug修复

**总计**: 10-15天

---

## 迁移策略

### 数据迁移

**旧数据**: `output/2025年X月X日/txt/` 纯文本文件
**新数据**: SQLite数据库

**迁移脚本**:
```python
def migrate_old_data():
    """迁移历史数据到SQLite"""
    txt_dir = Path("output")
    for date_folder in txt_dir.iterdir():
        if not date_folder.is_dir():
            continue
        # 解析txt文件
        # 存储到SQLite
        # 关键词匹配
        # 生成日报
```

### 配置迁移

**旧配置**: `config/config.yaml`, `config/frequency_words.txt`
**新配置**: `config/config.yaml`, `config/keywords.yaml`

**转换规则**:
- `frequency_words.txt` 的注释 `# 分组名` → keywords.yaml 的 `groups[].name`
- 注释下的关键词 → `groups[].keywords`

### 向后兼容

保留旧的 `main.py` 为 `main_legacy.py`，确保过渡期间可用。

---

## 技术栈

| 模块 | 技术 |
|------|------|
| 主程序 | Python 3.10+ |
| 数据库 | SQLite3 (标准库) |
| HTTP客户端 | requests |
| 配置解析 | PyYAML |
| AI客户端 | openai |
| HTML生成 | Jinja2 (可选) |

### requirements.txt

```
requests>=2.32.0,<3.0.0
PyYAML>=6.0.0,<7.0.0
openai>=1.0.0,<2.0.0
pytz>=2024.0
```

---

## 性能指标

| 指标 | 目标值 |
|------|--------|
| 抓取速度 | >10条/秒 |
| 去重准确率 | 100% |
| 数据库大小 | <10MB/月 |
| AI响应时间 | <30秒 |
| 日报生成 | <5秒 |

---

## 风险与应对

| 风险 | 应对 |
|------|------|
| AI API限流 | 添加缓存机制 |
| 数据库锁定 | 使用事务+连接池 |
| 数据源失效 | 降级处理+告警 |
| 大量数据 | 分页查询+归档 |

---

## 后续扩展

1. **Web界面**: Flask/FastAPI
2. **实时推送**: WebSocket
3. **数据可视化**: ECharts/D3.js
4. **多用户支持**: 用户认证
5. **API服务**: RESTful API

---

## 附录

### A. 代码示例

完整代码示例见各模块实现文件。

### B. 数据库ER图

```
┌───────────┐         ┌───────────┐         ┌───────────┐
│   news    │────────▶│  matches  │◀────────│ keywords  │
├───────────┤         ├───────────┤         ├───────────┤
│ id        │         │ id        │         │ id        │
│ title     │         │ news_id   │         │ group_name│
│ url       │         │ keyword_id│         │ keyword   │
│ source_id │         │ matched_at│         └───────────┘
│ crawled_at│         └───────────┘
└───────────┘
         │
         ▼
┌─────────────────┐
│ daily_reports   │
├─────────────────┤
│ id              │
│ date            │
│ summary_html    │
│ summary_json    │
│ ai_summary      │
└─────────────────┘
```

### C. 参考资料

- [SQLite文档](https://www.sqlite.org/docs.html)
- [OpenAI API](https://platform.openai.com/docs)
- [Python最佳实践](https://peps.python.org/pep-0008/)
