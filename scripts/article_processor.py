import re
from datetime import date

from bs4 import BeautifulSoup
from langdetect import LangDetectException, detect


def detect_language(text: str) -> str:
    try:
        return "en" if detect(text[:500]) == "en" else "zh"
    except LangDetectException:
        return "zh"


def slugify(title: str, max_len: int = 50) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower(), flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:max_len].rstrip("-")


def strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    block_tags = soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "figcaption", "blockquote"])
    if block_tags:
        blocks = [tag.get_text(" ", strip=True) for tag in block_tags]
    else:
        blocks = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    return "\n\n".join(block for block in blocks if block)


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]


def build_frontmatter(title: str, url: str, source: str, pub_date: str, language: str) -> str:
    today = date.today().isoformat()
    safe_title = title.replace('"', "'")
    return (
        "---\n"
        f'title: "{safe_title}"\n'
        f'url: "{url}"\n'
        f'source: "{source}"\n'
        f"date: {pub_date}\n"
        f"fetched: {today}\n"
        f"language: {language}\n"
        "read: false\n"
        "archived: false\n"
        "tags: []\n"
        "---"
    )


def build_md_content(
    title: str,
    url: str,
    source: str,
    pub_date: str,
    body_content: str,
    body_text: str,
    summary: str,
    language: str,
    llm_client=None,
    translate: bool = False,
) -> str:
    frontmatter = build_frontmatter(title, url, source, pub_date, language)
    callout = f"> [!example] AI 摘要\n> {summary}"
    body = body_content
    if translate and language == "en" and llm_client:
        translation = llm_client.translate_article(body_content)
        if translation:
            body = translation
    return f"{frontmatter}\n\n{callout}\n\n---\n\n{body}\n"


def make_filename(title: str) -> str:
    slug = slugify(title) or "untitled"
    return f"{slug}.md"
