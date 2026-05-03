from unittest.mock import MagicMock, patch

import yaml

from scripts.llm_client import LLMClient


CONFIG = {
    "settings": {"llm_primary": "qwen", "llm_fallback": "deepseek", "cleanup_days": 3},
    "llm": {
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "api_key_env": "QWEN_API_KEY",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "api_key_env": "DEEPSEEK_API_KEY",
            "thinking": False,
        },
    },
    "feeds": [],
}


def _config_file(tmp_path):
    f = tmp_path / "feeds.yml"
    f.write_text(yaml.safe_dump(CONFIG), encoding="utf-8")
    return f


def _mock_response(text: str):
    r = MagicMock()
    r.choices[0].message.content = text
    return r


@patch("scripts.llm_client.OpenAI")
def test_generate_summary_calls_primary(mock_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "test-qwen")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek")
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_response("摘要内容")
    mock_cls.return_value = client
    llm = LLMClient(str(_config_file(tmp_path)))
    assert llm.generate_summary("文章正文") == "摘要内容"
    client.chat.completions.create.assert_called_once()


@patch("scripts.llm_client.OpenAI")
def test_falls_back_on_primary_failure(mock_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "test-qwen")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek")
    primary = MagicMock()
    primary.chat.completions.create.side_effect = Exception("timeout")
    fallback = MagicMock()
    fallback.chat.completions.create.return_value = _mock_response("备用摘要")
    mock_cls.side_effect = [primary, fallback]
    llm = LLMClient(str(_config_file(tmp_path)))
    assert llm.generate_summary("文章正文") == "备用摘要"


@patch("scripts.llm_client.OpenAI")
def test_translate_paragraph(mock_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "test-qwen")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek")
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_response("中文翻译结果")
    mock_cls.return_value = client
    llm = LLMClient(str(_config_file(tmp_path)))
    assert llm.translate_paragraph("English paragraph.") == "中文翻译结果"
