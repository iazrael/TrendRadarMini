"""
SQLite存储管理器
负责新闻存储、去重、关键词匹配和查询
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from models.database import get_init_sql


logger = logging.getLogger(__name__)


class NewsStorage:
    """SQLite存储管理器"""

    def __init__(self, db_path: str):
        """
        初始化存储管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        """初始化数据库表结构"""
        try:
            sql = get_init_sql()
            self.conn.executescript(sql)
            self.conn.commit()
            logger.info(f"数据库初始化成功: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def save_news(self, news_list: List[Dict]) -> List[int]:
        """
        批量保存新闻（自动去重）

        Args:
            news_list: 新闻字典列表

        Returns:
            新增的news_id列表
        """
        if not news_list:
            return []

        saved_ids = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            for news in news_list:
                try:
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO news
                        (title, url, mobile_url, source_id, source_name, rank, crawled_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            news.get("title"),
                            news.get("url"),
                            news.get("mobile_url"),
                            news.get("source_id"),
                            news.get("source_name"),
                            news.get("rank"),
                            now,
                        ),
                    )
                    cursor = self.conn.execute(
                        "SELECT last_insert_rowid() WHERE changes() > 0"
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        saved_ids.append(row[0])
                except sqlite3.IntegrityError:
                    pass

            self.conn.commit()
            logger.info(f"保存新闻: {len(news_list)} 条, 新增: {len(saved_ids)} 条")
            return saved_ids

        except Exception as e:
            self.conn.rollback()
            logger.error(f"保存新闻失败: {e}")
            raise

    def load_keywords(self, keywords: Dict[str, List[str]]):
        """
        加载关键词到数据库

        Args:
            keywords: 关键词字典 {分组名: [关键词列表]}
        """
        try:
            for group_name, keyword_list in keywords.items():
                for keyword in keyword_list:
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO keywords (group_name, keyword)
                        VALUES (?, ?)
                        """,
                        (group_name, keyword),
                    )
            self.conn.commit()
            logger.info(f"加载关键词: {len(keywords)} 个分组")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"加载关键词失败: {e}")
            raise

    def get_keyword_by_name(self, keyword: str) -> Optional[int]:
        """
        根据关键词获取ID

        Args:
            keyword: 关键词

        Returns:
            keyword_id或None
        """
        cursor = self.conn.execute(
            "SELECT id FROM keywords WHERE keyword = ?",
            (keyword,),
        )
        row = cursor.fetchone()
        return row["id"] if row else None

    def match_keywords(self, news_id: int, title: str) -> List[Tuple[int, str, str]]:
        """
        匹配标题中的关键词

        Args:
            news_id: 新闻ID
            title: 新闻标题

        Returns:
            匹配到的关键词列表 [(keyword_id, group_name, keyword), ...]
        """
        cursor = self.conn.execute("SELECT id, group_name, keyword FROM keywords")
        keywords = cursor.fetchall()

        matched = []
        title_lower = title.lower()

        for kw in keywords:
            keyword_id = kw["id"]
            group_name = kw["group_name"]
            keyword = kw["keyword"]

            if keyword.lower() in title_lower:
                matched.append((keyword_id, group_name, keyword))

        return matched

    def save_matches(self, matches: List[Tuple[int, int]]):
        """
        批量保存匹配记录

        Args:
            matches: 匹配列表 [(news_id, keyword_id), ...]
        """
        try:
            for news_id, keyword_id in matches:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO matches (news_id, keyword_id)
                    VALUES (?, ?)
                    """,
                    (news_id, keyword_id),
                )
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"保存匹配记录失败: {e}")
            raise

    def match_and_save_all(
        self, news_ids: List[int], keywords_config: Optional[Dict] = None
    ) -> Dict[str, List[Dict]]:
        """
        批量匹配并保存关键词

        Args:
            news_ids: 新闻ID列表
            keywords_config: 关键词配置（可选）

        Returns:
            匹配数据 {group_name: [新闻列表]}
        """
        if not news_ids:
            return {}

        matched_data = {}
        all_matches = []

        for news_id in news_ids:
            cursor = self.conn.execute(
                "SELECT title FROM news WHERE id = ?", (news_id,)
            )
            row = cursor.fetchone()

            if not row:
                continue

            title = row["title"]
            matched_keywords = self.match_keywords(news_id, title)

            for keyword_id, group_name, keyword in matched_keywords:
                all_matches.append((news_id, keyword_id))

                news_info = {
                    "news_id": news_id,
                    "title": title,
                    "keyword": keyword,
                }

                if group_name not in matched_data:
                    matched_data[group_name] = []
                matched_data[group_name].append(news_info)

        if all_matches:
            self.save_matches(all_matches)
            logger.info(f"匹配关键词: {len(all_matches)} 次")

        return matched_data

    def get_news_by_date(self, date: str) -> List[Dict]:
        """
        获取指定日期的新闻

        Args:
            date: 日期字符串 (YYYY-MM-DD)

        Returns:
            新闻列表
        """
        cursor = self.conn.execute(
            """
            SELECT id, title, url, mobile_url, source_id, source_name, rank, crawled_at
            FROM news
            WHERE DATE(crawled_at) = ?
            ORDER BY rank ASC
            """,
            (date,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_keyword_stats(
        self, group_name: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        获取关键词统计

        Args:
            group_name: 分组名称（可选）

        Returns:
            统计数据 {keyword: {count, group_name}}
        """
        if group_name:
            cursor = self.conn.execute(
                """
                SELECT k.keyword, k.group_name, COUNT(m.news_id) as count
                FROM keywords k
                LEFT JOIN matches m ON k.id = m.keyword_id
                WHERE k.group_name = ?
                GROUP BY k.id
                ORDER BY count DESC
                """,
                (group_name,),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT k.keyword, k.group_name, COUNT(m.news_id) as count
                FROM keywords k
                LEFT JOIN matches m ON k.id = m.keyword_id
                GROUP BY k.id
                ORDER BY count DESC
                """
            )

        rows = cursor.fetchall()
        stats = {}
        for row in rows:
            stats[row["keyword"]] = {
                "count": row["count"],
                "group_name": row["group_name"],
            }
        return stats

    def get_group_stats(self) -> List[Dict]:
        """
        获取分组统计

        Returns:
            分组统计列表 [{group_name, count, keywords: [...]}]
        """
        cursor = self.conn.execute(
            """
            SELECT k.group_name, COUNT(DISTINCT m.news_id) as count
            FROM keywords k
            LEFT JOIN matches m ON k.id = m.keyword_id
            GROUP BY k.group_name
            ORDER BY count DESC
            """
        )

        groups = []
        for row in cursor.fetchall():
            group_name = row["group_name"]
            group_cursor = self.conn.execute(
                """
                SELECT k.keyword, COUNT(m.news_id) as count
                FROM keywords k
                LEFT JOIN matches m ON k.id = m.keyword_id
                WHERE k.group_name = ?
                GROUP BY k.id
                ORDER BY count DESC
                """,
                (group_name,),
            )

            keywords = [
                {"keyword": kw["keyword"], "count": kw["count"]}
                for kw in group_cursor.fetchall()
            ]

            groups.append(
                {"group_name": group_name, "count": row["count"], "keywords": keywords}
            )

        return groups

    def get_daily_summary(self, date: str) -> Dict:
        """
        获取每日汇总数据

        Args:
            date: 日期字符串 (YYYY-MM-DD)

        Returns:
            汇总数据
        """
        group_stats = self.get_group_stats()

        cursor = self.conn.execute(
            """
            SELECT n.*, GROUP_CONCAT(k.keyword) as keywords
            FROM news n
            JOIN matches m ON n.id = m.news_id
            JOIN keywords k ON m.keyword_id = k.id
            WHERE DATE(n.crawled_at) = ?
            GROUP BY n.id
            ORDER BY n.rank ASC
            """,
            (date,),
        )

        news_list = [dict(row) for row in cursor.fetchall()]

        return {"date": date, "groups": group_stats, "news": news_list}

    def save_report(self, date: str, html: str, json_data: str, ai_summary: str):
        """
        保存日报记录

        Args:
            date: 日期
            html: HTML内容
            json_data: JSON数据
            ai_summary: AI总结
        """
        try:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO daily_reports
                (date, summary_html, summary_json, ai_summary, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    date,
                    html,
                    json_data,
                    ai_summary,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"保存日报记录失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
