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

    def translate_article(self, text: str) -> str:
        """Translate a full article body in one API call instead of paragraph by paragraph."""
        return self.call(
            [
                {
                    "role": "system",
                    "content": (
                        "你是专业英译中助手。将英文文章翻译为中文，保持原意和段落结构。"
                        "保留原文段落换行，只输出译文，不要输出原文。"
                    ),
                },
                {"role": "user", "content": text[:30000]},
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
