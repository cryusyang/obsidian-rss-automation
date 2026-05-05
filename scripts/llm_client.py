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
                        "你是专业英译中助手兼Markdown排版专家。请完成以下任务：\n"
                        "1. 将HTML格式的英文文章转换为Obsidian兼容的Markdown格式"
                        "（保留图片、链接、标题、粗体、斜体，图片使用 ![alt](url) 语法）\n"
                        "2. 采用段落对照格式输出：每个英文段落（Markdown格式）后紧跟对应的中文译文段落，段落之间用空行分隔\n"
                        "3. 纯图片段落无需翻译，保留原样输出\n"
                        "4. 只输出对照内容，不要任何额外说明"
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
