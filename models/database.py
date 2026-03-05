"""
数据库模型定义
定义数据库表结构和SQL语句
"""

DATABASE_SCHEMA = {
    "news": """
        CREATE TABLE IF NOT EXISTS news (
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
    """,
    "news_indices": """
        CREATE INDEX IF NOT EXISTS idx_news_crawled_at ON news(crawled_at);
        CREATE INDEX IF NOT EXISTS idx_news_source ON news(source_id);
        CREATE INDEX IF NOT EXISTS idx_news_title_source ON news(title, source_id);
    """,
    "keywords": """
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL,
            keyword TEXT NOT NULL,
            UNIQUE(group_name, keyword)
        );
    """,
    "keywords_index": """
        CREATE INDEX IF NOT EXISTS idx_keywords_group ON keywords(group_name);
        CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);
    """,
    "matches": """
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id INTEGER NOT NULL,
            keyword_id INTEGER NOT NULL,
            matched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
            FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE,
            UNIQUE(news_id, keyword_id)
        );
    """,
    "matches_indices": """
        CREATE INDEX IF NOT EXISTS idx_matches_news ON matches(news_id);
        CREATE INDEX IF NOT EXISTS idx_matches_keyword ON matches(keyword_id);
        CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(matched_at);
        CREATE INDEX IF NOT EXISTS idx_matches_news_keyword ON matches(news_id, keyword_id);
    """,
    "daily_reports": """
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            summary_html TEXT,
            summary_json TEXT,
            ai_summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "daily_reports_index": """
        CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON daily_reports(date);
    """,
}


def get_init_sql() -> str:
    """
    获取初始化SQL

    Returns:
        创建所有表和索引的SQL语句
    """
    sql_statements = []
    for table_name, sql in DATABASE_SCHEMA.items():
        sql_statements.append(sql)
    return "\n".join(sql_statements)
