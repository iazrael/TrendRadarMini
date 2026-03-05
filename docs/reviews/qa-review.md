# TrendRadar v2.0 质量评审报告

**评审日期**: 2026-03-05
**评审专家**: Senior QA Strategist

---

## 一、测试覆盖分析

### 1.1 当前状态：零测试覆盖

经检查，项目**完全没有测试代码**，存在严重的质量保障缺失：

| 目录/文件 | 状态 |
|-----------|------|
| `test_*.py` | 不存在 |
| `*_test.py` | 不存在 |
| `tests/` 目录 | 不存在 |
| pytest/unittest 配置 | 不存在 |

### 1.2 关键测试场景清单

按照测试金字塔，建议的测试覆盖策略：

#### 单元测试

| 模块 | 关键测试场景 | 优先级 |
|------|-------------|--------|
| `core/config.py` | 配置文件缺失/格式错误/默认值回退/环境变量覆盖 | 高 |
| `core/crawler.py` | 网络超时/重试机制/代理配置/空响应/异常JSON解析 | 高 |
| `core/storage.py` | 去重逻辑/批量插入/关键词匹配算法/数据库连接异常 | 高 |
| `core/analyzer.py` | API调用失败/空输入/超长输入/token限制 | 高 |
| `core/reporter.py` | HTML转义/JSON序列化/文件写入权限 | 中 |

#### 集成测试

| 场景 | 描述 |
|------|------|
| 抓取->存储->匹配流水线 | 验证数据流转完整性 |
| 关键词加载与匹配 | 验证配置到数据库的同步 |
| AI总结生成 | Mock API 响应验证 Prompt 构建 |

#### 端到端测试

| 场景 | 验证点 |
|------|--------|
| 完整日报生成流程 | 从抓取到HTML/JSON输出 |
| 空数据处理 | 无新闻/无匹配的优雅降级 |
| 重复运行幂等性 | 同一天多次运行不会产生重复数据 |

---

## 二、风险分析

### 2.1 高风险点清单

#### R1: 关键词匹配逻辑缺陷 [高风险]

**位置**: `core/storage.py` 第 154-162 行

```python
def match_keywords(self, news_id: int, title: str) -> List[Tuple[int, str, str]]:
    # ...
    title_lower = title.lower()
    for kw in keywords:
        keyword = kw["keyword"]
        if keyword.lower() in title_lower:  # 问题：子字符串匹配
            matched.append((keyword_id, group_name, keyword))
```

**问题分析**:
1. **误匹配风险**: 使用 `in` 进行子字符串匹配，会导致如 "笔试" 匹配到 "试" 关键词
2. **大小写转换丢失**: 对中文关键词 `.lower()` 无意义，但英文关键词可能漏匹配特殊大小写
3. **无词边界检查**: "OpenAIsomething" 会匹配 "OpenAI"

**测试用例建议**:
```python
# 边界条件测试
assert match_keywords(1, "考试时间安排") == []  # 不应匹配"试"
assert match_keywords(1, "OpenAI发布新模型") != []  # 应匹配
assert match_keywords(1, "OpenAIsomething") == []  # 不应匹配（需词边界）
```

---

#### R2: 去重逻辑不完整 [高风险]

**位置**: `models/database.py` 第 17 行

```sql
UNIQUE(title, source_id)
```

**问题分析**:
1. **标题微小变动绕过去重**: 添加空格、标点符号即可绕过唯一约束
2. **无标题相似度检查**: 近似标题无法识别
3. **无URL去重**: 同一新闻URL可能以不同标题出现

**场景矩阵**:

| 场景 | 当前行为 | 期望行为 |
|------|----------|----------|
| 完全相同标题+来源 | 去重成功 | 去重成功 |
| 标题添加空格 | 插入重复 | 应去重 |
| 标题修改标点 | 插入重复 | 应去重/标记疑似重复 |
| 相同URL不同标题 | 插入重复 | 应去重 |

---

#### R3: AI API 调用无超时和熔断机制 [高风险]

**位置**: `core/analyzer.py` 第 184-195 行

```python
def _call_ai(self, prompt: str) -> str:
    response = self.client.chat.completions.create(
        model=self.model,
        messages=[...],
        max_tokens=self.max_tokens,
        temperature=self.temperature,
    )
    return response.choices[0].message.content
```

**问题分析**:
1. **无请求超时设置**: 网络问题可能导致程序无限期挂起
2. **无重试机制**: 临时性故障直接失败
3. **无熔断机制**: API持续不可用时无降级策略
4. **异常处理不完善**: `choices[0]` 可能 IndexError

**What-If 分析**:
- API 响应超过 60 秒会怎样? -> 程序卡死
- API 返回空 choices 会怎样? -> IndexError 崩溃
- 连续调用失败 10 次会怎样? -> 无熔断，继续尝试

---

#### R4: 数据库连接无连接池和并发保护 [中风险]

**位置**: `core/storage.py` 第 30 行

```python
self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
```

**问题分析**:
1. `check_same_thread=False` 允许多线程访问，但 SQLite 本身并发能力有限
2. 无连接池管理
3. 长连接无健康检查
4. 异常后无自动重连机制

---

#### R5: 外部 API 单点故障 [高风险]

**位置**: `core/crawler.py` 第 100 行

```python
url = f"https://newsnow.busiyi.world/api/s?id={source_id}&latest"
```

**问题分析**:
1. **硬编码单一 API 端点**: 无法配置备用数据源
2. **无健康检查**: 不检测 API 可用性
3. **无数据有效性校验**: 不验证返回数据结构

---

### 2.2 边界条件处理缺陷

| 边界条件 | 当前处理 | 风险等级 |
|----------|----------|----------|
| 空关键词配置 | 程序继续执行，无提示 | 中 |
| 空新闻列表 | 正确处理，输出警告 | 低 |
| 超长标题 (>1000字符) | 未截断，可能影响AI调用 | 中 |
| 特殊字符标题 (HTML/SQL注入) | HTML未转义，SQL使用参数化 | 中 |
| 并发运行同一程序 | SQLite锁竞争，可能数据损坏 | 高 |
| 磁盘空间不足 | 未捕获 IOError | 中 |
| 配置文件编码异常 | 未显式处理 | 低 |

---

### 2.3 错误处理健壮性分析

#### 良好实践
- `crawler.py`: HTTP 请求有重试机制 (第 59-79 行)
- `storage.py`: 数据库操作有事务回滚 (第 93-96 行)
- `main.py`: 有顶层异常捕获和 finally 清理 (第 162-180 行)

#### 需要改进
- `analyzer.py`: AI API 调用无超时和重试
- `reporter.py`: 文件写入异常处理后仍 re-raise，未提供替代方案
- 缺少结构化错误码和错误分类

---

## 三、数据质量分析

### 3.1 去重逻辑可靠性评估

| 维度 | 当前实现 | 可靠性评分 |
|------|----------|-----------|
| 完全相同数据去重 | `(title, source_id)` UNIQUE 约束 | 8/10 |
| 近似数据去重 | 无 | 0/10 |
| URL 级别去重 | 无 | 0/10 |
| 跨源去重 | 无 | 0/10 |

**建议增强**:
1. 添加标题预处理（去除空格、标点）
2. 增加 URL 字段唯一索引
3. 可选：引入标题相似度算法

---

### 3.2 关键词匹配准确性评估

**当前匹配策略**: `keyword.lower() in title.lower()`

**问题场景**:

| 关键词 | 标题 | 是否应匹配 | 当前结果 |
|--------|------|-----------|----------|
| "AI" | "铁路" | 否 | 是(误匹配) |
| "试" | "考试时间" | 否 | 是(误匹配) |
| "OpenAI" | "OpenAI发布GPT-5" | 是 | 是 |
| "AI" | "AI时代到来" | 是 | 是 |

**改进建议**:
- 使用正则表达式词边界匹配
- 实现中文分词匹配
- 支持关键词别称/同义词

---

### 3.3 数据存储设计评审

**优点**:
- 索引设计合理 (`idx_news_crawled_at`, `idx_matches_news_keyword` 等)
- 外键约束设置了 `ON DELETE CASCADE`
- 使用 `INSERT OR IGNORE` 实现幂等写入

**缺陷**:
1. **无数据归档策略**: 长期运行后数据库会无限增长
2. **无数据版本控制**: 关键词配置变更无法追溯历史匹配
3. **无敏感数据保护**: API Key 以明文存储在配置文件

**数据库索引缺失**:
```sql
-- 缺少：按日期查询匹配新闻的复合索引
CREATE INDEX idx_matches_date_news ON matches(matched_at, news_id);
```

---

## 四、验收标准与测试策略

### 4.1 模块级验收标准

#### crawler 模块

```
AC-001: 网络超时处理
  Given: API 响应时间超过 timeout 配置
  When: 执行抓取
  Then: 在 max_retries 次重试后返回空列表，不抛出异常

AC-002: 空响应处理
  Given: API 返回 {"items": []}
  When: 执行抓取
  Then: 返回空列表，记录警告日志

AC-003: 异常数据过滤
  Given: API 返回包含 null 标题的项目
  When: 解析响应
  Then: 过滤掉无效项目，只返回有效数据
```

#### storage 模块

```
AC-004: 去重验证
  Given: 已存在新闻 (title="测试", source_id="weibo")
  When: 插入相同 标题+来源
  Then: 忽略重复，saved_ids 不包含该记录ID

AC-005: 关键词匹配准确性
  Given: 标题 "OpenAI发布GPT-5模型"
  And: 关键词 ["OpenAI", "GPT"]
  When: 执行匹配
  Then: 返回两个关键词的匹配记录

AC-006: 关键词匹配边界
  Given: 标题 "考试时间安排"
  And: 关键词 ["试"]
  When: 执行匹配
  Then: 不返回匹配（需修复后验证）
```

#### analyzer 模块

```
AC-007: API 不可用降级
  Given: API 密钥为空
  When: 调用 summarize_news
  Then: 返回 "AI功能未启用"，不抛出异常

AC-008: 超时处理
  Given: API 响应超过 60 秒
  When: 调用 AI 总结
  Then: 捕获超时异常，返回错误信息
```

---

### 4.2 端到端测试场景设计

#### E2E-001: 正常日报生成流程

```
前置条件: 配置文件有效，网络正常
步骤:
  1. 执行 python main.py
  2. 等待程序完成
验证点:
  - 控制台输出 "日报生成完成"
  - output/daily/YYYY-MM-DD.html 文件存在
  - output/api/YYYY-MM-DD.json 文件存在
  - JSON 文件包含 date, ai_summary, stats, news 字段
  - 数据库新增新闻记录
```

#### E2E-002: 无新数据场景

```
前置条件: 数据库中已存在当天所有新闻
步骤:
  1. 执行 python main.py
验证点:
  - 输出 "没有新增新闻"
  - 程序正常退出，无异常
  - 不生成新的日报文件
```

#### E2E-003: 网络异常场景

```
前置条件: 断开网络或 API 不可达
步骤:
  1. 执行 python main.py
验证点:
  - 程序不崩溃
  - 日志记录网络错误
  - 程序以非零状态码退出
```

#### E2E-004: 配置缺失场景

```
前置条件: 删除 config/config.yaml
步骤:
  1. 执行 python main.py
验证点:
  - 输出明确的配置文件错误信息
  - 程序以状态码 1 退出
```

---

### 4.3 回归测试策略

#### 建议的测试命令

```bash
# 安装测试依赖
pip install pytest pytest-cov pytest-mock

# 运行所有测试
pytest tests/ -v

# 运行带覆盖率
pytest tests/ -v --cov=core --cov=models --cov-report=html

# 运行特定标记
pytest tests/ -v -m "not slow"  # 跳过慢速测试
pytest tests/ -v -m "integration"  # 只运行集成测试
```

#### CI/CD 集成建议

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov pytest-mock
      - run: pytest tests/ -v --cov=core --cov=models
```

---

## 五、优先改进建议

### P0 - 立即修复（安全/数据完整性）

| 问题 | 修复建议 | 预估工时 |
|------|----------|----------|
| 零测试覆盖 | 建立测试框架，编写核心模块单元测试 | 2-3 天 |
| 关键词误匹配 | 改用词边界匹配或分词匹配 | 0.5 天 |
| AI API 无超时 | 添加 timeout 参数和重试机制 | 0.5 天 |
| API Key 明文存储 | 改用环境变量，支持 secrets 文件 | 0.5 天 |

### P1 - 短期改进（稳定性）

| 问题 | 修复建议 | 预估工时 |
|------|----------|----------|
| 去重逻辑不完善 | 添加标题预处理和 URL 去重 | 1 天 |
| 外部 API 单点故障 | 支持多数据源配置 | 1 天 |
| 无数据归档策略 | 添加历史数据清理任务 | 0.5 天 |

### P2 - 中期改进（可维护性）

| 问题 | 修复建议 | 预估工时 |
|------|----------|----------|
| HTML 输出未转义 | 使用 html.escape 处理动态内容 | 0.5 天 |
| 无日志轮转 | 集成 logging.handlers.RotatingFileHandler | 0.5 天 |
| 无监控告警 | 添加关键指标采集和告警 | 1-2 天 |

---

## 六、总结

### 风险矩阵

| 概率 \ 影响 | 低 | 中 | 高 |
|-------------|----|----|----|
| **高** | 配置缺失处理 | 关键词误匹配 | 零测试覆盖 |
| **中** | 日志无轮转 | HTML未转义 | API无超时熔断 |
| **低** | 编码异常 | 磁盘空间 | 并发数据损坏 |

### 质量评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 代码结构 | 7/10 | 模块化清晰，但缺少接口抽象 |
| 错误处理 | 6/10 | 部分模块有处理，但不完整 |
| 测试覆盖 | 0/10 | 完全缺失 |
| 数据完整性 | 5/10 | 基础去重有效，高级去重缺失 |
| 安全性 | 4/10 | API Key 明文，HTML 未转义 |
| 可维护性 | 6/10 | 日志完善，但无监控 |

### 核心建议

1. **立即建立测试体系**: 这是当前最大的质量风险，建议先为核心模块编写单元测试，覆盖率达到 60% 以上
2. **修复关键词匹配逻辑**: 这是影响数据准确性的核心问题
3. **增强外部依赖的容错能力**: AI API 和数据源 API 都需要超时、重试、熔断机制