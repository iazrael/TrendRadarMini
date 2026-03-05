"""
日报生成模块
负责生成HTML和JSON格式的日报
"""

import json
import logging
from typing import Dict
from pathlib import Path
from datetime import datetime


logger = logging.getLogger(__name__)


class ReportGenerator:
    """日报生成器"""

    def __init__(self, output_dir: str = "output"):
        """
        初始化报告生成器

        Args:
            output_dir: 输出目录
        """
        self.base_dir = Path(output_dir)
        self.html_dir = self.base_dir / "daily"
        self.api_dir = self.base_dir / "api"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保输出目录存在"""
        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.api_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"输出目录已准备: {self.base_dir}")

    def generate_html(
        self,
        date: str,
        matched_data: Dict[str, List[Dict]],
        stats: List[Dict],
        ai_summary: str,
    ) -> str:
        """
        生成HTML日报

        Args:
            date: 日期
            matched_data: 匹配数据
            stats: 统计数据
            ai_summary: AI总结

        Returns:
            HTML内容
        """
        template = self._get_html_template()

        stats_html = self._render_stats(stats)
        news_html = self._render_news_by_group(matched_data)

        html = template.format(
            date=date,
            ai_summary=ai_summary,
            stats=stats_html,
            news=news_html,
            generated_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        logger.info(f"HTML日报生成完成: {date}")
        return html

    def generate_json(
        self,
        date: str,
        matched_data: Dict[str, List[Dict]],
        stats: List[Dict],
        ai_summary: str,
    ) -> str:
        """
        生成JSON数据

        Args:
            date: 日期
            matched_data: 匹配数据
            stats: 统计数据
            ai_summary: AI总结

        Returns:
            JSON字符串
        """
        data = {
            "date": date,
            "ai_summary": ai_summary,
            "stats": stats,
            "news": matched_data,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        logger.info(f"JSON数据生成完成: {date}")
        return json_str

    def save_report(
        self,
        date: str,
        html: str,
        json_data: str,
    ):
        """
        保存日报文件

        Args:
            date: 日期
            html: HTML内容
            json_data: JSON数据
        """
        html_path = self.html_dir / f"{date}.html"
        json_path = self.api_dir / f"{date}.json"

        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

            with open(json_path, "w", encoding="utf-8") as f:
                f.write(json_data)

            logger.info(f"日报已保存:")
            logger.info(f"  HTML: {html_path}")
            logger.info(f"  JSON: {json_path}")

        except Exception as e:
            logger.error(f"保存日报失败: {e}")
            raise

    def _get_html_template(self) -> str:
        """获取HTML模板"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrendRadar日报 - {date}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}

        .header .date {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .section {{
            padding: 30px;
            border-bottom: 1px solid #eee;
        }}

        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}

        .ai-summary {{
            background: #f8f9ff;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 4px;
            line-height: 1.8;
        }}

        .ai-summary p {{
            margin-bottom: 10px;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}

        .stat-card {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }}

        .stat-card h3 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.2em;
        }}

        .stat-card .count {{
            font-size: 2em;
            font-weight: bold;
            color: #764ba2;
            margin-bottom: 10px;
        }}

        .stat-card .keywords {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .keyword-tag {{
            background: #e0e7ff;
            color: #667eea;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.9em;
        }}

        .news-group {{
            margin-bottom: 30px;
        }}

        .news-group h3 {{
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}

        .news-item {{
            padding: 15px;
            margin-bottom: 10px;
            background: #f9f9f9;
            border-radius: 4px;
            border-left: 3px solid #667eea;
            transition: all 0.3s;
        }}

        .news-item:hover {{
            background: #f0f0f0;
            transform: translateX(5px);
        }}

        .news-item .keyword {{
            color: #667eea;
            font-weight: bold;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}

        .news-item .title {{
            font-size: 1.1em;
            color: #333;
            margin-bottom: 5px;
        }}

        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 TrendRadar日报</h1>
            <div class="date">{date}</div>
        </div>

        <div class="section">
            <h2>🤖 AI总结</h2>
            <div class="ai-summary">
                {ai_summary}
            </div>
        </div>

        <div class="section">
            <h2>📈 关键词统计</h2>
            <div class="stats">
                {stats}
            </div>
        </div>

        <div class="section">
            <h2>📰 匹配新闻</h2>
            {news}
        </div>

        <div class="footer">
            生成时间: {generated_time} | TrendRadar v2.0
        </div>
    </div>
</body>
</html>"""

    def _render_stats(self, stats: List[Dict]) -> str:
        """渲染统计卡片"""
        cards = []

        for group in stats:
            group_name = group["group_name"]
            count = group["count"]
            keywords = group.get("keywords", [])

            keyword_tags = " ".join(
                [f'<span class="keyword-tag">{kw["keyword"]} ({kw["count"]})</span>' for kw in keywords[:5]]
            )

            card = f"""
            <div class="stat-card">
                <h3>{group_name}</h3>
                <div class="count">{count}</div>
                <div class="keywords">{keyword_tags}</div>
            </div>
            """
            cards.append(card)

        return "".join(cards)

    def _render_news_by_group(self, matched_data: Dict[str, List[Dict]]) -> str:
        """渲染新闻列表（按分组）"""
        groups_html = []

        for group_name, news_list in matched_data.items():
            if not news_list:
                continue

            items_html = []

            for news in news_list[:20]:
                title = news.get("title", "")
                keyword = news.get("keyword", "")

                item = f"""
                <div class="news-item">
                    <div class="keyword">[{keyword}]</div>
                    <div class="title">{title}</div>
                </div>
                """
                items_html.append(item)

            group_html = f"""
            <div class="news-group">
                <h3>{group_name}</h3>
                {"".join(items_html)}
            </div>
            """
            groups_html.append(group_html)

        return "".join(groups_html)
