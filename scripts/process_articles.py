import shutil
from datetime import date, timedelta
from pathlib import Path

import frontmatter

CLEANUP_DAYS = 3
INPUT_SUBPATH = "A-🔴INPUTS/(C)-🟡RSS/Input"
OUTPUT_SUBPATH = "A-🔴INPUTS/(C)-🟡RSS/Output"


def process(repo_root: Path) -> dict:
    input_dir = repo_root / INPUT_SUBPATH
    output_dir = repo_root / OUTPUT_SUBPATH
    cutoff = date.today() - timedelta(days=CLEANUP_DAYS)
    moved, deleted = [], []
    output_dir.mkdir(parents=True, exist_ok=True)
    for md_file in sorted(input_dir.glob("*.md")):
        try:
            post = frontmatter.load(str(md_file))
        except Exception:
            continue
        if post.get("archived") is True:
            shutil.move(str(md_file), str(output_dir / md_file.name))
            moved.append(md_file.name)
        elif post.get("read") is True:
            try:
                if date.fromisoformat(str(post.get("fetched", ""))) <= cutoff:
                    md_file.unlink()
                    deleted.append(md_file.name)
            except ValueError:
                pass
    print(f"Moved: {len(moved)}, Deleted: {len(deleted)}")
    return {"moved": moved, "deleted": deleted}


def main() -> None:
    process(Path("."))


if __name__ == "__main__":
    main()
