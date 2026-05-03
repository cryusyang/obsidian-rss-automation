from pathlib import Path
from unittest.mock import MagicMock, patch

import feedparser

from scripts.fetch_rss import (
    extract_entry_body,
    extract_entry_html,
    load_existing_urls,
    load_seen_urls,
    process_feed,
    save_seen_urls,
)


ROOT = Path(__file__).resolve().parents[2]


def test_load_existing_urls_empty_dirs(tmp_path):
    input_dir = tmp_path / "Input"
    output_dir = tmp_path / "Output"
    input_dir.mkdir()
    output_dir.mkdir()
    assert load_existing_urls(input_dir, output_dir) == set()


def test_load_existing_urls_reads_frontmatter(tmp_path):
    input_dir = tmp_path / "Input"
    output_dir = tmp_path / "Output"
    input_dir.mkdir()
    output_dir.mkdir()
    (input_dir / "test.md").write_text(
        '---\ntitle: "T"\nurl: "https://example.com/a"\n---\nBody',
        encoding="utf-8",
    )
    assert "https://example.com/a" in load_existing_urls(input_dir, output_dir)


def test_seen_urls_round_trip(tmp_path):
    seen_file = tmp_path / "A-🔴INPUTS/(C)-🟡RSS/.seen_urls.yml"
    save_seen_urls(seen_file, {"https://example.com/a", "https://example.com/b"})
    assert load_seen_urls(seen_file) == {"https://example.com/a", "https://example.com/b"}


def test_process_feed_skips_url_recorded_in_seen_file_even_after_md_deleted(tmp_path):
    llm = MagicMock()
    llm.generate_summary.return_value = "摘要"
    seen_file = tmp_path / "A-🔴INPUTS/(C)-🟡RSS/.seen_urls.yml"
    save_seen_urls(seen_file, {"https://mp.weixin.qq.com/s/ZJ3YxynhZ2OS_w9RysIMWA"})

    count = process_feed(
        {"name": "思维重构", "url": str(ROOT / "rss1.md")},
        load_seen_urls(seen_file),
        llm,
        tmp_path / "Input",
    )

    assert count == 0
    assert list((tmp_path / "Input").glob("*.md")) == []


def test_extract_entry_body_prefers_content_encoded_over_summary():
    parsed = feedparser.parse(str(ROOT / "rss1.md"))
    body = extract_entry_body(parsed.entries[0])
    assert "你有没有过这样的经历" in body
    assert "现在的人，每天应付工作压力" in body


def test_extract_entry_html_preserves_images_from_content_encoded():
    parsed = feedparser.parse(str(ROOT / "rss1.md"))
    html = extract_entry_html(parsed.entries[0])
    assert "<img" in html
    assert "mmbiz.qpic.cn" in html


def test_extract_entry_body_handles_medium_content_encoded():
    parsed = feedparser.parse(str(ROOT / "rss2.md"))
    body = extract_entry_body(parsed.entries[0])
    assert "Why We Built APIPeek" in body
    assert "Team Workspaces" in body


@patch("scripts.fetch_rss.feedparser.parse")
def test_process_feed_skips_existing_url(mock_parse, tmp_path):
    mock_parse.return_value.entries = [
        {"title": "Old", "link": "https://x.com/old", "summary": "内容"}
    ]
    llm = MagicMock()
    llm.generate_summary.return_value = "摘要"
    count = process_feed({"name": "Feed", "url": "https://rss.x.com"}, {"https://x.com/old"}, llm, tmp_path)
    assert count == 0


@patch("scripts.fetch_rss.feedparser.parse")
def test_process_feed_creates_new_md(mock_parse, tmp_path):
    mock_parse.return_value.entries = [
        {"title": "New Article", "link": "https://x.com/new", "summary": "这是中文内容测试正文。"}
    ]
    llm = MagicMock()
    llm.generate_summary.return_value = "生成摘要"
    count = process_feed({"name": "Feed", "url": "https://rss.x.com"}, set(), llm, tmp_path)
    assert count == 1
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "New Article" in content
    assert "生成摘要" in content


def test_process_feed_with_local_wechat_sample_uses_full_content(tmp_path):
    llm = MagicMock()
    llm.generate_summary.return_value = "微信摘要"
    count = process_feed({"name": "思维重构", "url": str(ROOT / "rss1.md")}, set(), llm, tmp_path)
    assert count == 1
    files = list(tmp_path.glob("*.md"))
    assert files[0].name.startswith("2026-05-02-")
    content = files[0].read_text(encoding="utf-8")
    assert "为什么很多人接不住真诚" in content
    assert "<img" in content
    assert "mmbiz.qpic.cn" in content
    assert "以后再交付真心的时候" in content


def test_process_feed_with_local_medium_sample_does_not_translate_by_default(tmp_path):
    llm = MagicMock()
    llm.generate_summary.return_value = "Medium 摘要"
    llm.translate_paragraph.return_value = "中文译文"
    count = process_feed({"name": "Medium", "url": str(ROOT / "rss2.md")}, set(), llm, tmp_path)
    assert count == 1
    content = next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
    assert "<p>" in content
    assert "Why We Built APIPeek" in content
    assert "中文译文" not in content
    llm.translate_paragraph.assert_not_called()


def test_process_feed_with_translate_true_translates_english(tmp_path):
    llm = MagicMock()
    llm.generate_summary.return_value = "Medium 摘要"
    llm.translate_paragraph.return_value = "中文译文"
    count = process_feed(
        {"name": "Medium", "url": str(ROOT / "rss2.md"), "Translate": True},
        set(),
        llm,
        tmp_path,
    )
    assert count == 1
    content = next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
    assert "## 中文对照" in content
    assert "中文译文" in content
    assert llm.translate_paragraph.call_count >= 1
