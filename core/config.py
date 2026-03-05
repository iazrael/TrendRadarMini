"""
配置管理模块
负责加载和管理项目配置
"""

import os
import yaml
from typing import Dict, List, Optional
from pathlib import Path


class Config:
    """配置管理器"""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.base_dir = Path(__file__).parent.parent
        self.config_path = self.base_dir / config_path
        self.keywords_path = self.base_dir / "config/keywords.yaml"

        self.config = self._load_yaml(self.config_path)
        self.keywords_config = self._load_yaml(self.keywords_path)

    def _load_yaml(self, path: Path) -> Dict:
        """
        加载YAML配置文件

        Args:
            path: YAML文件路径

        Returns:
            配置字典
        """
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def ai_api_key(self) -> str:
        """获取AI API密钥"""
        return self.config.get("ai", {}).get("api_key", os.environ.get("OPENAI_API_KEY", ""))

    @property
    def ai_base_url(self) -> str:
        """获取AI API基础URL"""
        return self.config.get("ai", {}).get("base_url", "https://api.openai.com/v1")

    @property
    def ai_model(self) -> str:
        """获取AI模型名称"""
        return self.config.get("ai", {}).get("model", "gpt-4o")

    @property
    def ai_max_tokens(self) -> int:
        """获取AI最大token数"""
        return self.config.get("ai", {}).get("max_tokens", 2000)

    @property
    def ai_temperature(self) -> float:
        """获取AI温度参数"""
        return self.config.get("ai", {}).get("temperature", 0.7)

    @property
    def db_path(self) -> str:
        """获取数据库路径"""
        path = self.config.get("storage", {}).get("db_path", "output/trendradar.db")
        return str(self.base_dir / path)

    @property
    def output_dir(self) -> str:
        """获取输出目录"""
        path = self.config.get("report", {}).get("output_dir", "output")
        return str(self.base_dir / path)

    @property
    def log_file(self) -> str:
        """获取日志文件路径"""
        path = self.config.get("logging", {}).get("file", "output/trendradar.log")
        return str(self.base_dir / path)

    def get_sources(self) -> List[Dict]:
        """
        获取数据源列表

        Returns:
            数据源字典列表
        """
        return self.config.get("crawler", {}).get("sources", [])

    def get_keywords(self) -> Dict[str, List[str]]:
        """
        获取关键词分组

        Returns:
            字典: {分组名: [关键词列表]}
        """
        groups = self.keywords_config.get("groups", [])
        result = {}
        for group in groups:
            group_name = group.get("name", "")
            keywords = group.get("keywords", [])
            if group_name and keywords:
                result[group_name] = keywords
        return result

    def get_keywords_with_priority(self) -> List[Dict]:
        """
        获取带优先级的关键词分组

        Returns:
            字典列表: [{"name": "", "priority": 1, "keywords": []}]
        """
        return self.keywords_config.get("groups", [])

    @property
    def request_interval(self) -> int:
        """获取请求间隔（毫秒）"""
        return self.config.get("crawler", {}).get("request_interval", 1000)

    @property
    def request_timeout(self) -> int:
        """获取请求超时（秒）"""
        return self.config.get("crawler", {}).get("timeout", 10)

    @property
    def max_retries(self) -> int:
        """获取最大重试次数"""
        return self.config.get("crawler", {}).get("max_retries", 2)

    @property
    def proxy_enabled(self) -> bool:
        """是否启用代理"""
        return self.config.get("crawler", {}).get("proxy", {}).get("enabled", False)

    @property
    def proxy_url(self) -> Optional[str]:
        """获取代理URL"""
        if self.proxy_enabled:
            return self.config.get("crawler", {}).get("proxy", {}).get("url", "")
        return None

    @property
    def batch_size(self) -> int:
        """获取批量插入大小"""
        return self.config.get("storage", {}).get("batch_size", 100)

    @property
    def log_level(self) -> str:
        """获取日志级别"""
        return self.config.get("logging", {}).get("level", "INFO")
