"""
新闻抓取模块
负责从newsnow API获取新闻数据
"""

import json
import random
import time
import logging
import requests
from typing import Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


class NewsCrawler:
    """新闻抓取器"""

    def __init__(self, proxy_url: Optional[str] = None):
        """
        初始化抓取器

        Args:
            proxy_url: 代理URL（可选）
        """
        self.proxy_url = proxy_url
        self.session = requests.Session()

    def _make_request(
        self,
        url: str,
        timeout: int = 10,
        max_retries: int = 2,
    ) -> Optional[dict]:
        """
        发送HTTP请求（支持重试）

        Args:
            url: 请求URL
            timeout: 超时时间（秒）
            max_retries: 最大重试次数

        Returns:
            响应JSON或None
        """
        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

        for retry in range(max_retries + 1):
            try:
                response = self.session.get(url, proxies=proxies, headers=headers, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                status = data.get("status", "unknown")

                if status not in ["success", "cache"]:
                    logger.warning(f"响应状态异常: {status}")

                return data

            except Exception as e:
                if retry < max_retries:
                    wait_time = random.uniform(2, 5) * (retry + 1)
                    logger.warning(f"请求失败 ({retry + 1}/{max_retries}): {e}, {wait_time:.1f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"请求失败: {e}")
                    return None

        return None

    def fetch_from_source(
        self,
        source_id: str,
        source_name: str,
        timeout: int = 10,
    ) -> List[Dict]:
        """
        从单个数据源抓取新闻

        Args:
            source_id: 数据源ID
            source_name: 数据源名称
            timeout: 超时时间

        Returns:
            新闻列表
        """
        url = f"https://newsnow.busiyi.world/api/s?id={source_id}&latest"

        logger.info(f"抓取数据源: {source_name} ({source_id})")

        data = self._make_request(url, timeout)

        if not data:
            logger.error(f"获取数据失败: {source_name}")
            return []

        status = data.get("status", "unknown")
        items = data.get("items", [])

        if not items:
            logger.warning(f"数据为空: {source_name}")
            return []

        news_list = []
        for idx, item in enumerate(items, start=1):
            title = item.get("title")

            if not title or isinstance(title, float):
                continue

            title = str(title).strip()
            if not title:
                continue

            news = {
                "title": title,
                "url": item.get("url", ""),
                "mobile_url": item.get("mobileUrl", ""),
                "source_id": source_id,
                "source_name": source_name,
                "rank": idx,
            }

            news_list.append(news)

        status_info = "最新数据" if status == "success" else "缓存数据"
        logger.info(f"获取 {source_name} 成功: {len(news_list)} 条 ({status_info})")

        return news_list

    def fetch_all(
        self,
        sources: List[Dict],
        interval: int = 1000,
        timeout: int = 10,
    ) -> List[Dict]:
        """
        批量抓取所有数据源

        Args:
            sources: 数据源列表
            interval: 请求间隔（毫秒）
            timeout: 超时时间

        Returns:
            所有新闻列表
        """
        all_news = []

        for source in sources:
            source_id = source.get("id", "")
            source_name = source.get("name", "")

            if not source_id:
                continue

            news_list = self.fetch_from_source(source_id, source_name, timeout)
            all_news.extend(news_list)

            if interval > 0 and source != sources[-1]:
                time.sleep(interval / 1000)

        logger.info(f"抓取完成: 总计 {len(all_news)} 条新闻")
        return all_news

    def parse_response(self, data: dict) -> List[Dict]:
        """
        解析newsnow API响应

        Args:
            data: API响应数据

        Returns:
            新闻列表
        """
        items = data.get("items", [])
        return [self._parse_item(item, data) for item in items]

    def _parse_item(self, item: dict, source_data: dict) -> Dict:
        """解析单个新闻项"""
        source_id = source_data.get("source_id", "unknown")
        source_name = source_data.get("source_name", "未知")

        return {
            "title": str(item.get("title", "")),
            "url": item.get("url", ""),
            "mobile_url": item.get("mobileUrl", ""),
            "source_id": source_id,
            "source_name": source_name,
            "rank": item.get("rank", 0),
        }
