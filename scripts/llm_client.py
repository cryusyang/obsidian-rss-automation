import os

import yaml
from openai import OpenAI


class LLMClient:
    def __init__(self, config_path: str):
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        self._llm_config = config["llm"]
        self._primary = config["settings"]["llm_primary"]
        self._fallback = config["settings"]["llm_fallback"]
        self._clients: dict[str, OpenAI] = {}
        for name, cfg in self._llm_config.items():
            self._clients[name] = OpenAI(
                api_key=os.environ[cfg["api_key_env"]],
                base_url=cfg["base_url"],
            )

    def _call(self, provider: str, messages: list[dict]) -> str:
        cfg = self._llm_config[provider]
        extra: dict = {}
        if provider == "deepseek" and not cfg.get("thinking", True):
            extra["extra_body"] = {"thinking": {"type": "disabled"}}
        if provider == "qwen":
            extra["extra_body"] = {"enable_thinking": False}
        response = self._clients[provider].chat.completions.create(
            model=cfg["model"],
            messages=messages,
            **extra,
        )
        return response.choices[0].message.content

    def call(self, messages: list[dict]) -> str:
        try:
            return self._call(self._primary, messages)
        except Exception:
            return self._call(self._fallback, messages)

    def generate_summary(self, text: str) -> str:
        return self.call(
            [
                {
                    "role": "system",
                    "content": "你是专业文章摘要助手。用3-5句中文概括文章核心内容，只输出摘要。",
                },
                {"role": "user", "content": f"请为以下文章生成摘要：\n\n{text[:3000]}"},
            ]
        )

    def translate_article(self, html: str) -> str:
        """Convert HTML to Obsidian Markdown and output bilingual paragraph interleave."""
        return self.call(
            [
                {
                    "role": "system",
                    "content": (
                        "你是中英文对照排版助手。用户发给你一段HTML英文文章，你需要：\n"
                        "1. 将HTML转为Obsidian兼容Markdown（图片用 ![描述](url)，保留链接、粗体、斜体、标题层级）\n"
                        "2. 严格按【英文段落原文 → 中文翻译】交替输出，每段之间空一行\n\n"
                        "输出格式示例：\n"
                        "This is the first English paragraph.\n\n"
                        "这是第一段的中文翻译。\n\n"
                        "This is the **second** paragraph with a [link](https://example.com).\n\n"
                        "这是带有**粗体**和链接的第二段中文翻译。\n\n"
                        "强制规则：\n"
                        "- 每个英文段落必须原样保留（转为Markdown后），不得省略\n"
                        "- 英文段落之后立刻输出对应中文翻译段落\n"
                        "- 纯图片行无需翻译，直接保留\n"
                        "- 只输出正文对照内容，不输出任何说明文字"
                    ),
                },
                {"role": "user", "content": html[:30000]},
            ]
        )

    def translate_paragraph(self, paragraph: str) -> str:
        return self.call(
            [
                {
                    "role": "system",
                    "content": "你是专业英译中助手。将英文段落翻译为中文，保持原意。只输出译文。",
                },
                {"role": "user", "content": paragraph},
            ]
        )
