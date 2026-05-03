from scripts.dry_run_fetch import DryRunLLM


def test_dry_run_llm_generates_deterministic_summary():
    llm = DryRunLLM()
    summary = llm.generate_summary("第一段内容。\n\n第二段内容。")
    assert summary.startswith("DRY RUN 摘要：")
    assert "第一段内容" in summary


def test_dry_run_llm_generates_translation_marker():
    llm = DryRunLLM()
    assert llm.translate_paragraph("English paragraph.") == "DRY RUN 翻译占位：English paragraph."
