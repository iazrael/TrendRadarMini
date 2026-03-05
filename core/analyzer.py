"""
AI分析模块
负责调用AI生成新闻总结和洞察
"""

import logging
from typing import Dict, List
from openai import OpenAI


logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI总结器"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ):
        """
        初始化AI分析器

        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        if not api_key:
            logger.warning("未配置AI API密钥，AI功能将不可用")
            self.enabled = False
        else:
            self.enabled = True

    def summarize_news(
        self,
        matched_data: Dict[str, List[Dict]],
        stats: List[Dict],
    ) -> str:
        """
        生成新闻总结

        Args:
            matched_data: 匹配数据 {group_name: [新闻列表]}
            stats: 统计数据

        Returns:
            AI总结文本
        """
        if not self.enabled:
            return "AI功能未启用"

        prompt = self._build_summary_prompt(matched_data, stats)

        try:
            response = self._call_ai(prompt)
            logger.info("AI总结生成成功")
            return response
        except Exception as e:
            logger.error(f"AI总结生成失败: {e}")
            return f"AI总结生成失败: {str(e)}"

    def generate_insights(self, stats: List[Dict]) -> str:
        """
        生成洞察分析

        Args:
            stats: 统计数据

        Returns:
            洞察文本
        """
        if not self.enabled:
            return "AI功能未启用"

        prompt = self._build_insights_prompt(stats)

        try:
            response = self._call_ai(prompt)
            logger.info("AI洞察生成成功")
            return response
        except Exception as e:
            logger.error(f"AI洞察生成失败: {e}")
            return f"AI洞察生成失败: {str(e)}"

    def _build_summary_prompt(
        self,
        matched_data: Dict[str, List[Dict]],
        stats: List[Dict],
    ) -> str:
        """构建总结Prompt"""
        prompt_parts = [
            "你是一个专业的新闻分析师。请根据以下数据生成简明扼要的日报总结：",
            "",
            "【关键词统计】",
        ]

        for group in stats:
            group_name = group["group_name"]
            count = group["count"]
            keywords = ", ".join([kw["keyword"] for kw in group["keywords"][:5]])
            prompt_parts.append(f"- {group_name}: {count}条新闻 ({keywords})")

        prompt_parts.append("")
        prompt_parts.append("【重要新闻】")

        for group_name, news_list in matched_data.items():
            if not news_list:
                continue

            prompt_parts.append(f"\n### {group_name}")

            for news in news_list[:10]:
                title = news.get("title", "")
                keyword = news.get("keyword", "")
                prompt_parts.append(f"- [{keyword}] {title}")

        prompt_parts.extend([
            "",
            "请生成以下内容（使用中文，总字数600字以内）：",
            "",
            "1. **今日热点概述**（100字）",
            "   - 简要总结今日最重要的2-3条新闻",
            "",
            "2. **关键词趋势分析**（200字）",
            "   - 分析各关键词相关的新闻数量和热度",
            "   - 指出上升趋势的关键词",
            "",
            "3. **重要新闻点评**（300字）",
            "   - 挑选3-5条最重要/最有价值的新闻进行点评",
            "   - 给出专业见解和影响分析",
        ])

        return "\n".join(prompt_parts)

    def _build_insights_prompt(self, stats: List[Dict]) -> str:
        """构建洞察Prompt"""
        prompt_parts = [
            "请根据以下关键词统计数据，生成专业的趋势洞察分析：",
            "",
            "【统计数据】",
        ]

        for group in stats:
            group_name = group["group_name"]
            count = group["count"]
            keyword_list = []
            for kw in group["keywords"][:3]:
                keyword_list.append(f'{kw["keyword"]}({kw["count"]})')
            top_keywords = ", ".join(keyword_list)
            prompt_parts.append(f"- {group_name}: {count}条 (Top: {top_keywords})")

        prompt_parts.extend([
            "",
            "请生成（使用中文，总字数300字以内）：",
            "1. 整体趋势分析",
            "2. 重点关键词说明",
            "3. 后续关注建议",
        ])

        return "\n".join(prompt_parts)

    def _call_ai(self, prompt: str) -> str:
        """
        调用AI API

        Args:
            prompt: 提示词

        Returns:
            AI响应文本
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是专业的新闻分析师。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"AI API调用失败: {e}")
            raise

    def analyze_single_news(self, title: str) -> str:
        """
        分析单条新闻

        Args:
            title: 新闻标题

        Returns:
            分析结果
        """
        if not self.enabled:
            return "AI功能未启用"

        prompt = f"请简要分析这条新闻的价值和影响（100字以内）：\n\n{title}"

        try:
            response = self._call_ai(prompt)
            return response
        except Exception as e:
            logger.error(f"单条新闻分析失败: {e}")
            return f"分析失败: {str(e)}"
