from datetime import date, timedelta

from scripts.process_articles import process


def _write_article(path, *, read=False, archived=False, fetched=None):
    fetched = fetched or date.today().isoformat()
    path.write_text(
        "---\n"
        'title: "T"\n'
        "url: https://example.com/t\n"
        f"fetched: {fetched}\n"
        f"read: {str(read).lower()}\n"
        f"archived: {str(archived).lower()}\n"
        "---\n"
        "Body\n",
        encoding="utf-8",
    )


def test_process_moves_archived_articles(tmp_path):
    input_dir = tmp_path / "A-🔴INPUTS/(C)-🟡RSS/Input"
    output_dir = tmp_path / "A-🔴INPUTS/(C)-🟡RSS/Output"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    _write_article(input_dir / "archived.md", archived=True)

    result = process(tmp_path)

    assert result["moved"] == ["archived.md"]
    assert not (input_dir / "archived.md").exists()
    assert (output_dir / "archived.md").exists()


def test_process_deletes_stale_read_articles(tmp_path):
    input_dir = tmp_path / "A-🔴INPUTS/(C)-🟡RSS/Input"
    output_dir = tmp_path / "A-🔴INPUTS/(C)-🟡RSS/Output"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    old_day = (date.today() - timedelta(days=4)).isoformat()
    _write_article(input_dir / "old.md", read=True, fetched=old_day)

    result = process(tmp_path)

    assert result["deleted"] == ["old.md"]
    assert not (input_dir / "old.md").exists()


def test_process_keeps_recent_read_articles(tmp_path):
    input_dir = tmp_path / "A-🔴INPUTS/(C)-🟡RSS/Input"
    output_dir = tmp_path / "A-🔴INPUTS/(C)-🟡RSS/Output"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    _write_article(input_dir / "recent.md", read=True)

    result = process(tmp_path)

    assert result["deleted"] == []
    assert (input_dir / "recent.md").exists()
