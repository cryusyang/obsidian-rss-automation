import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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

RSS_SUBPATH = "A-🔴INPUTS/(C)-🟡RSS"
INPUT_SUBPATH = f"{RSS_SUBPATH}/Input"
OUTPUT_SUBPATH = f"{RSS_SUBPATH}/Output"
SEEN_URLS_SUBPATH = f"{RSS_SUBPATH}/.seen_urls.yml"


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


def load_seen_urls(seen_file: Path) -> set[str]:
    if not seen_file.exists():
        return set()
    with open(seen_file, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    urls = data.get("urls", []) if isinstance(data, dict) else data
    return {str(url) for url in urls or []}


def save_seen_urls(seen_file: Path, urls: set[str]) -> None:
    seen_file.parent.mkdir(parents=True, exist_ok=True)
    with open(seen_file, "w", encoding="utf-8") as f:
        yaml.safe_dump({"urls": sorted(urls)}, f, allow_unicode=True, sort_keys=False)


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


WORKERS = 5  # concurrent articles per feed; stay well under 300 RPM rate limit


def process_feed(feed_config: dict, existing_urls: set[str], llm: LLMClient, output_dir: Path) -> int:
    parsed = feedparser.parse(feed_config["url"])
    output_dir.mkdir(parents=True, exist_ok=True)
    should_translate = bool(feed_config.get("Translate", feed_config.get("translate", False)))

    lock = threading.Lock()
    count = 0

    def process_entry(entry) -> bool:
        url = entry.get("link") or entry.get("guid") or entry.get("id") or ""
        if not url:
            return False
        # Claim the URL under lock to prevent duplicate processing across threads
        with lock:
            if url in existing_urls:
                return False
            existing_urls.add(url)

        title = entry.get("title", "Untitled").strip() or "Untitled"
        body_html = extract_entry_html(entry)
        body_text = strip_html(body_html) if body_html else ""
        pub_date = _entry_pub_date(entry)
        language = detect_language(body_text)
        summary = llm.generate_summary(body_text) if body_text else "（无正文内容）"
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
        return True

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(process_entry, e) for e in parsed.entries]
        for fut in as_completed(futures):
            try:
                if fut.result():
                    count += 1
            except Exception as e:
                print(f"  [warn] article failed: {e}")

    return count


def git_commit_push(notes_repo: Path, feed_name: str) -> None:
    """Commit and push any new files after each feed so progress is never lost."""
    env = {**os.environ, "GIT_AUTHOR_NAME": "github-actions[bot]",
           "GIT_AUTHOR_EMAIL": "github-actions[bot]@users.noreply.github.com",
           "GIT_COMMITTER_NAME": "github-actions[bot]",
           "GIT_COMMITTER_EMAIL": "github-actions[bot]@users.noreply.github.com"}

    subprocess.run(["git", "add",
                    f"{INPUT_SUBPATH}/",
                    SEEN_URLS_SUBPATH],
                   cwd=notes_repo, env=env, check=False)

    result = subprocess.run(["git", "diff", "--cached", "--quiet"],
                            cwd=notes_repo, env=env)
    if result.returncode == 0:
        return  # nothing to commit

    subprocess.run(["git", "commit", "-m",
                    f"feat: add articles from {feed_name}"],
                   cwd=notes_repo, env=env, check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"],
                   cwd=notes_repo, env=env, check=True)
    print(f"  → committed & pushed")


def main() -> None:
    config_path = Path("config/feeds.yml")
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    notes_repo = Path(os.environ["NOTES_REPO_PATH"])
    input_dir = notes_repo / INPUT_SUBPATH
    output_dir = notes_repo / OUTPUT_SUBPATH
    seen_file = notes_repo / SEEN_URLS_SUBPATH
    llm = LLMClient(str(config_path))
    existing_urls = load_existing_urls(input_dir, output_dir) | load_seen_urls(seen_file)
    total = 0
    for feed in config["feeds"]:
        n = process_feed(feed, existing_urls, llm, input_dir)
        print(f"[{feed['name']}] {n} new articles")
        if n > 0:
            save_seen_urls(seen_file, existing_urls)
            git_commit_push(notes_repo, feed["name"])
        total += n
    print(f"Total: {total} new articles")


if __name__ == "__main__":
    main()
