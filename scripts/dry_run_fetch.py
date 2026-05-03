import argparse
from pathlib import Path

import yaml

from scripts.fetch_rss import (
    INPUT_SUBPATH,
    OUTPUT_SUBPATH,
    SEEN_URLS_SUBPATH,
    load_existing_urls,
    load_seen_urls,
    process_feed,
    save_seen_urls,
)


class DryRunLLM:
    def generate_summary(self, text: str) -> str:
        compact = " ".join(text.split())
        return f"DRY RUN 摘要：{compact[:180]}"

    def translate_paragraph(self, paragraph: str) -> str:
        return f"DRY RUN 翻译占位：{paragraph[:180]}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch configured RSS feeds without calling LLM APIs.")
    parser.add_argument("--config", default="config/feeds.yml")
    parser.add_argument("--notes-repo", default=".tmp/notes-dry-run")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    notes_repo = Path(args.notes_repo)
    input_dir = notes_repo / INPUT_SUBPATH
    output_dir = notes_repo / OUTPUT_SUBPATH
    seen_file = notes_repo / SEEN_URLS_SUBPATH
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    llm = DryRunLLM()
    existing_urls = load_existing_urls(input_dir, output_dir) | load_seen_urls(seen_file)
    total = 0
    for feed in config["feeds"]:
        count = process_feed(feed, existing_urls, llm, input_dir)
        print(f"[{feed['name']}] {count} new articles")
        total += count
    save_seen_urls(seen_file, existing_urls)
    print(f"Total: {total} new articles")
    print(f"Output directory: {input_dir}")


if __name__ == "__main__":
    main()
