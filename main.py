"""
TrendRadar 主程序 v2.0
功能：抓取新闻、存储去重、AI总结、生成日报
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from core.config import Config
from core.crawler import NewsCrawler
from core.storage import NewsStorage
from core.analyzer import AIAnalyzer
from core.reporter import ReportGenerator


def setup_logging(log_file: str, level: str = "INFO"):
    """配置日志"""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main():
    """主流程"""
    storage = None
    try:
        print("=" * 60)
        print("TrendRadar v2.0 启动中...")
        print("=" * 60)

        # 1. 初始化配置
        print("\n[1/7] 加载配置...")
        config = Config()
        setup_logging(config.log_file, config.log_level)
        logger = logging.getLogger(__name__)

        # 2. 初始化组件
        print("[2/7] 初始化存储...")
        storage = NewsStorage(config.db_path)

        print("[3/7] 初始化抓取器...")
        crawler = NewsCrawler(proxy_url=config.proxy_url)

        print("[4/7] 初始化AI分析器...")
        analyzer = AIAnalyzer(
            api_key=config.ai_api_key,
            base_url=config.ai_base_url,
            model=config.ai_model,
            max_tokens=config.ai_max_tokens,
            temperature=config.ai_temperature,
        )

        print("[5/7] 初始化报告生成器...")
        reporter = ReportGenerator(output_dir=config.output_dir)

        # 3. 加载关键词
        print("\n[6/7] 加载关键词配置...")
        keywords = config.get_keywords()
        storage.load_keywords(keywords)
        logger.info(f"加载关键词: {len(keywords)} 个分组")

        # 4. 抓取新闻
        print("\n[7/7] 开始抓取新闻...")
        sources = config.get_sources()
        logger.info(f"数据源数量: {len(sources)}")

        news_list = crawler.fetch_all(
            sources=sources,
            interval=config.request_interval,
            timeout=config.request_timeout,
        )

        if not news_list:
            logger.warning("未获取到任何新闻")
            storage.close()
            return

        logger.info(f"获取新闻: {len(news_list)} 条")

        # 5. 存储去重
        logger.info("存储新闻...")
        saved_ids = storage.save_news(news_list)

        if not saved_ids:
            print("\n✅ 没有新增新闻")
            logger.info("没有新增新闻，程序结束")
            storage.close()
            return

        print(f"💾 新增新闻: {len(saved_ids)} 条")
        logger.info(f"新增新闻: {len(saved_ids)} 条")

        # 6. 关键词匹配
        logger.info("匹配关键词...")
        matched_data = storage.match_and_save_all(saved_ids, keywords)
        match_count = sum(len(v) for v in matched_data.values())
        print(f"🔍 匹配关键词: {match_count} 次")
        logger.info(f"匹配关键词: {match_count} 次")

        if not matched_data:
            print("\n⚠️ 未匹配到任何关键词")
            storage.close()
            return

        # 7. 获取统计数据
        logger.info("获取统计数据...")
        stats = storage.get_group_stats()

        # 8. AI总结
        print("\n🤖 生成AI总结...")
        logger.info("生成AI总结...")
        ai_summary = analyzer.summarize_news(matched_data, stats)

        # 9. 生成日报
        print("📄 生成日报...")
        logger.info("生成日报...")

        today = datetime.now().strftime("%Y-%m-%d")

        html_report = reporter.generate_html(
            date=today,
            matched_data=matched_data,
            stats=stats,
            ai_summary=ai_summary,
        )

        json_report = reporter.generate_json(
            date=today,
            matched_data=matched_data,
            stats=stats,
            ai_summary=ai_summary,
        )

        reporter.save_report(today, html_report, json_report)

        # 10. 保存到数据库
        storage.save_report(today, html_report, json_report, ai_summary)

        # 11. 完成
        print("\n" + "=" * 60)
        print("✅ 日报生成完成！")
        print("=" * 60)
        print(f"📅 日期: {today}")
        print(f"📰 新增新闻: {len(saved_ids)} 条")
        print(f"🔍 匹配关键词: {match_count} 次")
        print(f"📄 HTML: {reporter.html_dir / f'{today}.html'}")
        print(f"📦 JSON: {reporter.api_dir / f'{today}.json'}")
        print("=" * 60)

        logger.info("程序执行完成")

    except FileNotFoundError as e:
        print(f"\n❌ 配置文件错误: {e}")
        print("\n请确保以下文件存在:")
        print("  • New/config/config.yaml")
        print("  • New/config/keywords.yaml")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ 程序运行错误: {e}")
        logging.exception("程序异常")
        sys.exit(1)

    finally:
        # 清理
        if storage:
            try:
                storage.close()
            except:
                pass


if __name__ == "__main__":
    main()
