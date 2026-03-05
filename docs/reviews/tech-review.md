# TrendRadar v2.0 技术评审报告

**评审日期**: 2026-03-05
**评审专家**: Senior Tech Expert

---

## 一、架构设计评审

### 1.1 模块划分评估

**优点:**
- 模块划分遵循单一职责原则，各模块边界清晰：
  - `config.py`: 配置管理
  - `crawler.py`: 新闻抓取
  - `storage.py`: 数据存储
  - `analyzer.py`: AI 分析
  - `reporter.py`: 报告生成
- 数据流清晰：Config -> Crawler -> Storage -> Analyzer -> Reporter

**问题:**

| 问题 | 位置 | 风险等级 |
|------|------|----------|
| 缺少服务层/业务逻辑层 | main.py | 中 |
| main.py 承担过多编排逻辑 | main.py:33-180 | 中 |
| 数据库模型与存储逻辑混合 | models/database.py + storage.py | 低 |

### 1.2 依赖关系

**问题:**
1. **循环依赖风险**: `storage.py` 导入 `models/database.py`，若 `models` 需要引用 `storage` 会产生循环依赖
2. **隐式依赖**: `main.py` 直接依赖所有模块，但没有依赖注入机制

**改进建议:**
```python
# 推荐引入依赖注入容器或工厂模式
class Container:
    def __init__(self, config: Config):
        self.config = config
        self._storage = None
        self._crawler = None

    @property
    def storage(self) -> NewsStorage:
        if self._storage is None:
            self._storage = NewsStorage(self.config.db_path)
        return self._storage
```

---

## 二、代码质量评审

### 2.1 类型注解问题

**严重缺失:**

| 文件 | 问题 | 行号 |
|------|------|------|
| reporter.py | `generate_html` 参数 `matched_data: Dict[str, List[Dict]]` 但 `List` 未导入 | 40 |
| reporter.py | `_render_stats` 返回值缺少类型注解 | 328 |
| reporter.py | `_render_news_by_group` 同上 | 352 |
| crawler.py | `parse_response` 返回 `List[Dict]` 但实际返回的是列表推导式 | 189-190 |

**修复方案:**
```python
# reporter.py 顶部应添加
from typing import Dict, List, Any

def _render_stats(self, stats: List[Dict[str, Any]]) -> str:
    ...

def _render_news_by_group(self, matched_data: Dict[str, List[Dict[str, Any]]]) -> str:
    ...
```

### 2.2 命名问题

| 问题 | 位置 | 建议 |
|------|------|------|
| `ai_api_key` 属性返回空字符串而非 Optional[str] | config.py:46-48 | 应返回 `Optional[str]` 并明确标注 |
| `_make_request` 返回 `Optional[dict]` 但文档字符串说 JSON | crawler.py:35 | 应改为 `Optional[Dict[str, Any]]` |
| `status` 变量命名模糊 | crawler.py:65-67 | 建议改为 `response_status` |

### 2.3 代码重复

**重复逻辑:**

```python
# crawler.py:139-140 和类似日志模式
status_info = "最新数据" if status == "success" else "缓存数据"
logger.info(f"获取 {source_name} 成功: {len(news_list)} 条 ({status_info})")

# storage.py 中多处相似的 try-except-rollback-raise 模式
# 见于: save_news (92-96), load_keywords (117-120), save_matches (183-186)
```

**建议抽取公共方法:**
```python
def _safe_execute(self, operation: Callable, error_msg: str):
    try:
        return operation()
    except Exception as e:
        self.conn.rollback()
        logger.error(f"{error_msg}: {e}")
        raise
```

### 2.4 Python 最佳实践违背

| 问题 | 位置 | 说明 |
|------|------|------|
| 裸 `except` | main.py:178-180 | 应至少使用 `except Exception` 并记录日志 |
| 硬编码 API URL | crawler.py:100 | 应提取到配置中 |
| 使用 `isinstance(title, float)` 检查 NaN | crawler.py:121 | 应使用 `math.isnan()` 更明确 |

---

## 三、性能与可靠性评审

### 3.1 数据库设计问题

**问题清单:**

| 问题 | 影响 | 风险等级 |
|------|------|----------|
| `UNIQUE(title, source_id)` 约束可能导致长标题冲突 | 数据丢失 | 高 |
| 缺少 `updated_at` 字段 | 无法追踪更新时间 | 低 |
| `daily_reports` 表存储完整 HTML/JSON | 数据冗余、查询性能下降 | 中 |
| 未启用 WAL 模式 | 并发写入性能受限 | 中 |

**关键代码问题 (storage.py:64-79):**
```python
# 问题：逐条插入效率低
for news in news_list:
    try:
        self.conn.execute(...)  # N 次数据库操作
```

**改进建议:**
```python
# 批量插入
def save_news(self, news_list: List[Dict]) -> List[int]:
    if not news_list:
        return []

    values = [
        (news.get("title"), news.get("url"), news.get("mobile_url"),
         news.get("source_id"), news.get("source_name"), news.get("rank"), now)
        for news in news_list
    ]

    self.conn.executemany(
        """INSERT OR IGNORE INTO news ... VALUES (?, ?, ?, ?, ?, ?, ?)""",
        values
    )
```

### 3.2 关键词匹配性能问题

**严重问题 (storage.py:150-162):**
```python
# 问题：每次匹配都全表扫描 keywords
cursor = self.conn.execute("SELECT id, group_name, keyword FROM keywords")
keywords = cursor.fetchall()  # 加载全部关键词到内存

for kw in keywords:
    if keyword.lower() in title_lower:  # O(N*M) 复杂度
        ...
```

**性能瓶颈分析:**
- 假设 100 个关键词，1000 条新闻
- 当前实现: 100 * 1000 = 100,000 次字符串匹配
- 且每次匹配都重新加载关键词

**改进方案:**
```python
# 方案1: 使用内存缓存
class NewsStorage:
    def __init__(self, db_path: str):
        ...
        self._keyword_cache: Optional[List[Tuple[int, str, str]]] = None

    def _load_keywords_once(self) -> List[Tuple[int, str, str]]:
        if self._keyword_cache is None:
            cursor = self.conn.execute("SELECT id, group_name, keyword FROM keywords")
            self._keyword_cache = [(r["id"], r["group_name"], r["keyword"]) for r in cursor.fetchall()]
        return self._keyword_cache
```

### 3.3 并发问题

**严重问题 (storage.py:30):**
```python
self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
```

`check_same_thread=False` 允许多线程共享连接，但 SQLite 默认序列化模式下可能导致：
- 竞态条件
- 数据损坏风险

**改进建议:**
```python
# 启用 WAL 模式
self.conn = sqlite3.connect(str(self.db_path))
self.conn.execute("PRAGMA journal_mode=WAL")
self.conn.execute("PRAGMA synchronous=NORMAL")
```

---

## 四、安全性评审

### 4.1 API Key 管理问题

**严重问题 (config/config.yaml:5):**
```yaml
ai:
  api_key: "sk-xxxxxxxxxxxxxxxx"  # 硬编码密钥！
```

**风险:**
- 密钥泄露到版本控制
- 代码审查/日志中可见

**当前代码处理 (config.py:46-48):**
```python
@property
def ai_api_key(self) -> str:
    return self.config.get("ai", {}).get("api_key", os.environ.get("OPENAI_API_KEY", ""))
```

**改进建议:**
```yaml
# config.yaml 应删除 api_key 字段
ai:
  base_url: "http://192.168.200.34:11434/v1"
  model: "qwen3:30b"
```

```python
# config.py 应强制要求环境变量
@property
def ai_api_key(self) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("OPENAI_API_KEY 环境变量未设置")
    return api_key
```

### 4.2 SQL 注入风险

**评估结果: 当前代码无 SQL 注入风险**

所有数据库操作均使用参数化查询:
```python
# storage.py:64-79 - 正确使用参数化
self.conn.execute(
    "INSERT OR IGNORE INTO news ... VALUES (?, ?, ?, ?, ?, ?, ?)",
    (news.get("title"), ...)
)
```

### 4.3 敏感信息处理

**问题:**

| 位置 | 问题 | 风险 |
|------|------|------|
| analyzer.py:67-72 | 异常信息直接返回给用户 | 可能泄露内部结构 |
| config.py:52 | base_url 可能包含内网地址 | 信息泄露 |

**改进:**
```python
# analyzer.py
except Exception as e:
    logger.error(f"AI总结生成失败: {e}", exc_info=True)  # 记录完整堆栈
    return "AI总结生成失败，请查看日志了解详情"  # 用户友好的错误信息
```

---

## 五、可维护性评审

### 5.1 配置管理

**优点:**
- YAML 配置结构清晰
- 支持环境变量覆盖
- 配置属性化访问

**问题:**

| 问题 | 位置 |
|------|------|
| 无配置验证机制 | config.py 全局 |
| 必需字段缺失时无明确错误 | config.py |
| 无配置变更检测 | config.py |

**改进建议:**
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class AIConfig:
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    max_tokens: int = 2000
    temperature: float = 0.7

    @classmethod
    def from_dict(cls, data: Dict) -> "AIConfig":
        return cls(
            api_key=data.get("api_key") or os.environ.get("OPENAI_API_KEY"),
            base_url=data.get("base_url", "https://api.openai.com/v1"),
            ...
        )

    def validate(self):
        if not self.api_key:
            raise ValueError("AI API key is required")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
```

### 5.2 日志问题

**问题清单:**

| 问题 | 位置 | 影响 |
|------|------|------|
| `print` 和 `logger` 混用 | main.py:37-158 | 日志不统一 |
| 缺少结构化日志 | 全局 | 难以分析 |
| 无日志轮转 | main.py:23-29 | 日志文件无限增长 |

**改进:**
```python
import logging.handlers

def setup_logging(log_file: str, level: str = "INFO"):
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
    )
    # 或使用 TimedRotatingFileHandler 按天轮转
```

### 5.3 错误处理问题

**问题清单:**

| 问题 | 位置 | 说明 |
|------|------|------|
| 裸 `except` 吞掉异常 | main.py:178-180 | 无法追踪问题 |
| 异常后未清理资源 | 多处 | 资源泄露风险 |
| 无重试机制 | analyzer.py:184-199 | 网络波动导致失败 |

**改进建议:**
```python
# 使用 tenacity 库实现重试
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def _call_ai(self, prompt: str) -> str:
    ...
```

---

## 六、问题汇总与优先级

### 高优先级 (需立即修复)

| 序号 | 问题 | 文件 | 行号 | 风险 |
|------|------|------|------|------|
| 1 | API Key 硬编码 | config.yaml | 5 | 安全漏洞 |
| 2 | 裸 except 吞异常 | main.py | 178-180 | 调试困难 |
| 3 | UNIQUE 约束潜在冲突 | database.py | 17 | 数据丢失 |
| 4 | check_same_thread=False | storage.py | 30 | 数据损坏 |

### 中优先级 (建议近期修复)

| 序号 | 问题 | 文件 | 说明 |
|------|------|------|------|
| 5 | 类型注解缺失 | reporter.py | 影响代码提示和检查 |
| 6 | 关键词匹配性能 | storage.py:150-162 | O(N*M) 复杂度 |
| 7 | 逐条插入数据库 | storage.py:62-87 | 性能瓶颈 |
| 8 | 无日志轮转 | main.py | 磁盘空间风险 |
| 9 | 无配置验证 | config.py | 运行时错误 |

### 低优先级 (后续优化)

| 序号 | 问题 | 说明 |
|------|------|------|
| 10 | HTML 模板内嵌 | 应提取到独立文件 |
| 11 | 缺少单元测试 | 无法保证质量 |
| 12 | 无 CI/CD 配置 | 部署风险 |
| 13 | print/logger 混用 | 日志不规范 |

---

## 七、改进建议总结

### 架构层面
1. 引入依赖注入容器，解耦组件初始化
2. 将 main.py 的编排逻辑抽取到 Workflow/Orchestrator 类
3. 考虑引入 Repository 模式隔离数据访问

### 代码质量
1. 补全类型注解，引入 mypy 静态检查
2. 使用 dataclasses 定义配置和模型
3. 统一错误处理策略

### 性能优化
1. 关键词匹配引入缓存
2. 批量数据库操作使用 executemany
3. SQLite 启用 WAL 模式

### 安全加固
1. 移除配置文件中的敏感信息
2. 敏感配置仅通过环境变量注入
3. 异常信息脱敏处理

### 运维保障
1. 添加日志轮转
2. 引入结构化日志 (JSON 格式)
3. 添加健康检查端点