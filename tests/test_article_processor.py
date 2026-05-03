from unittest.mock import MagicMock

from scripts.article_processor import (
    build_frontmatter,
    build_md_content,
    detect_language,
    make_filename,
    slugify,
    split_paragraphs,
    strip_html,
)


def test_detect_language_chinese():
    assert detect_language("这是一篇中文文章，介绍了人工智能技术的最新进展和应用。") == "zh"


def test_detect_language_english():
    assert detect_language("This is an English article about machine learning and AI.") == "en"


def test_detect_language_fallback_on_empty():
    assert detect_language("") == "zh"


def test_slugify_spaces_to_hyphens():
    assert slugify("Hello World") == "hello-world"


def test_slugify_removes_special_chars():
    assert slugify("Hello, World! (2026)") == "hello-world-2026"


def test_slugify_keeps_chinese_title_readable():
    assert slugify("为什么很多人接不住真诚？") == "为什么很多人接不住真诚"


def test_strip_html_removes_tags():
    result = strip_html("<p>Hello <b>World</b></p>")
    assert "Hello" in result
    assert "World" in result
    assert "<" not in result


def test_strip_html_collapses_excess_blank_lines():
    result = strip_html("<p>First</p>   \n\n\n<p>Second</p>")
    assert result == "First\n\nSecond"


def test_strip_html_keeps_inline_link_text_in_same_paragraph():
    result = strip_html('<p>Postman has been the default <a href="https://x.com">API testing</a> tool.</p>')
    assert result == "Postman has been the default API testing tool."


def test_split_paragraphs():
    parts = split_paragraphs("Para one.\n\nPara two.\n\nPara three.")
    assert parts == ["Para one.", "Para two.", "Para three."]


def test_build_frontmatter_fields():
    fm = build_frontmatter("Test", "https://x.com", "Medium", "2026-05-03", "en")
    assert 'title: "Test"' in fm
    assert 'url: "https://x.com"' in fm
    assert "language: en" in fm
    assert "read: false" in fm
    assert "archived: false" in fm
    assert "tags: []" in fm


def test_build_md_content_chinese_no_translation():
    llm = MagicMock()
    md = build_md_content(
        "中文标题",
        "https://x.com",
        "WeChat",
        "2026-05-03",
        "正文内容",
        "正文内容",
        "摘要内容",
        "zh",
        llm,
    )
    assert "AI 摘要" in md
    assert "摘要内容" in md
    assert "正文内容" in md
    llm.translate_paragraph.assert_not_called()


def test_build_md_content_english_without_translate_flag():
    llm = MagicMock()
    md = build_md_content(
        "English Title",
        "https://x.com",
        "Medium",
        "2026-05-03",
        "<p>First paragraph has enough words to translate.</p>",
        "First paragraph has enough words to translate.",
        "Summary",
        "en",
        llm,
        translate=False,
    )
    assert "<p>First paragraph" in md
    llm.translate_paragraph.assert_not_called()


def test_build_md_content_english_with_translation_when_enabled():
    llm = MagicMock()
    llm.translate_paragraph.return_value = "这是中文翻译"
    md = build_md_content(
        "English Title",
        "https://x.com",
        "Medium",
        "2026-05-03",
        "<p>First paragraph has enough words to translate.</p>",
        "First paragraph has enough words to translate.",
        "Summary",
        "en",
        llm,
        translate=True,
    )
    assert "<p>First paragraph" in md
    assert "## 中文对照" in md
    assert "这是中文翻译" in md
    assert llm.translate_paragraph.call_count == 1


def test_make_filename_format():
    assert make_filename("2026-05-03", "Hello World Test") == "2026-05-03-hello-world-test.md"
