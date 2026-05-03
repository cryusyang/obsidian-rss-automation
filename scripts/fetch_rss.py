import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import frontmatter as fm_lib
import yaml

from scripts.article_processor import (
    build_md_content,
    detect_language,
    make_filename,
    strip_html,
)
from scripts.llm_client import LLMClient


def load_existing_urls(input_dir: Path, output_dir: Path) -> set[str]:
    urls: set[str] = set()
    for md_file in list(input_dir.glob("*.md")) + list(output_dir.glob("*.md")):
        try:
            post = fm_lib.load(str(md_file))
        except Exception:
            continue
        if post.get("url"):
            urls.add(post["url"])
    return urls


def extract_entry_body(entry) -> str:
    return strip_html(extract_entry_html(entry))


def extract_entry_html(entry) -> str:
    content = entry.get("content")
    if content:
        for item in content:
            value = item.get("value")
            if value:
                return value.strip()
    summary = entry.get("summary") or entry.get("description") or ""
    return summary.strip() if summary else ""


def _entry_pub_date(entry) -> str:
    raw_date = entry.get("published") or entry.get("updated")
    if raw_date:
        try:
            return parsedate_to_datetime(raw_date).date().isoformat()
        except (TypeError, ValueError):
            pass
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6]).date().isoformat()
    return datetime.today().date().isoformat()


def process_feed(feed_config: dict, existing_urls: set[str], llm: LLMClient, output_dir: Path) -> int:
    parsed = feedparser.parse(feed_config["url"])
    count = 0
    output_dir.mkdir(parents=True, exist_ok=True)
    for entry in parsed.entries:
        url = entry.get("link") or entry.get("guid") or entry.get("id") or ""
        if not url or url in existing_urls:
            continue
        title = entry.get("title", "Untitled").strip() or "Untitled"
        body_html = extract_entry_html(entry)
        body_text = strip_html(body_html) if body_html else ""
        pub_date = _entry_pub_date(entry)
        language = detect_language(body_text)
        summary = llm.generate_summary(body_text) if body_text else "（无正文内容）"
        should_translate = bool(feed_config.get("Translate", feed_config.get("translate", False)))
        md_content = build_md_content(
            title=title,
            url=url,
            source=feed_config["name"],
            pub_date=pub_date,
            body_content=body_html,
            body_text=body_text,
            summary=summary,
            language=language,
            llm_client=llm if language == "en" else None,
            translate=should_translate,
        )
        filename = make_filename(pub_date, title)
        (output_dir / filename).write_text(md_content, encoding="utf-8")
        existing_urls.add(url)
        count += 1
    return count


def main() -> None:
    config_path = Path("config/feeds.yml")
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    notes_repo = Path(os.environ["NOTES_REPO_PATH"])
    input_dir = notes_repo / "A-🔴INPUTS/(C)-🟡RSS/Input"
    output_dir = notes_repo / "A-🔴INPUTS/(C)-🟡RSS/Output"
    llm = LLMClient(str(config_path))
    existing_urls = load_existing_urls(input_dir, output_dir)
    total = 0
    for feed in config["feeds"]:
        n = process_feed(feed, existing_urls, llm, input_dir)
        print(f"[{feed['name']}] {n} new articles")
        total += n
    print(f"Total: {total} new articles")


if __name__ == "__main__":
    main()
