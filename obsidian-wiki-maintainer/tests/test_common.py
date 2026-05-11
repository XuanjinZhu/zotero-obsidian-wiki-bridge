from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from common import (
    AUTO_RELATED_END,
    AUTO_RELATED_START,
    append_query_filing_block,
    build_raw_cache_entries,
    present_search_hit,
    rewrite_axis_topic_page,
    select_query_filing_hits,
    update_note_related_pages_section,
)  # noqa: E402


def test_build_raw_cache_entries_splits_pages() -> None:
    payload = {
        "title": "柑橘杂交群体的细胞质遗传分析",
        "primary_axis": "genetics-genomics",
        "source_note_path": "Research/Citrus/papers/genetics-genomics/note.md",
        "zotero_item_key": "PZCL7B39",
        "zotero_attachment_key": "RBNDRL42",
        "zotero_pdf_path": r"C:\Users\xuanjinzhu\Zotero\storage\RBNDRL42\paper.pdf",
        "cache_path": r"C:\vault\Research\Citrus\cache\raw\note.json",
        "cache_relative_path": "note.json",
        "pages": [
            {"page_number": 1, "text": "第一页 细胞质遗传 证据"},
            {"page_number": 3, "text": "第三页 线粒体 泄漏 证据"},
        ],
    }
    frontmatter = {
        "tags": ["papers/citrus", "papers/citrus/genetics-genomics"],
        "aliases": ["English title"],
        "source_status": "current",
    }

    entries = build_raw_cache_entries(payload, frontmatter)

    assert len(entries) == 2
    assert entries[0]["page_number"] == 1
    assert entries[1]["page_number"] == 3
    assert entries[0]["source_note_path"] == "Research/Citrus/papers/genetics-genomics/note.md"
    assert entries[1]["zotero_attachment_key"] == "RBNDRL42"


def test_present_search_hit_exposes_page_number_and_snippet() -> None:
    entry = {
        "source_type": "raw_cache",
        "relative_path": "note.json",
        "title": "柑橘杂交群体的细胞质遗传分析",
        "page_type": "raw_cache",
        "primary_axis": "genetics-genomics",
        "tags": ["papers/citrus/genetics-genomics"],
        "aliases": [],
        "source_status": "current",
        "score": 88,
        "content": "这一页说明了柑橘细胞质遗传的关键证据，尤其是线粒体父系泄漏。",
        "page_number": 5,
        "zotero_pdf_path": r"C:\Users\xuanjinzhu\Zotero\storage\RBNDRL42\paper.pdf",
    }

    presented = present_search_hit(entry, "柑橘细胞质遗传证据")

    assert presented["page_number"] == 5
    assert "关键证据" in presented["snippet"]
    assert presented["zotero_pdf_path"].endswith("paper.pdf")


def test_rewrite_axis_topic_page_builds_summary_sections(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    topic_dir = vault_root / "Research" / "Citrus" / "topics"
    topic_dir.mkdir(parents=True)
    schema = {
        "topics_dir": "Research/Citrus/topics",
        "axes": [
            {"key": "genetics-genomics", "label": "遗传与基因组", "keywords": [], "aliases": []},
        ],
    }
    papers = [
        {
            "path": vault_root / "Research" / "Citrus" / "papers" / "genetics-genomics" / "paper1.md",
            "title": "论文甲",
            "body": "\n".join(
                [
                    "## 一句话总结",
                    "",
                    "这篇论文说明了细胞质遗传并不完全遵循经典母系规律。",
                    "",
                    "## 研究问题",
                    "",
                    "作者要回答柑橘杂交后代的细胞质遗传模式是否稳定。",
                    "",
                    "## 关键结果",
                    "",
                    "- 发现三类细胞质遗传模式。",
                    "",
                    "## 待验证问题",
                    "",
                    "- 类父系遗传是否为真正父系替代。",
                ]
            ),
            "frontmatter": {"related_entities": ["柑橘", "细胞质遗传"]},
        }
    ]

    page_path = rewrite_axis_topic_page(vault_root, schema, "genetics-genomics", papers)
    text = page_path.read_text(encoding="utf-8")

    assert "# 遗传与基因组" in text
    assert "## 主题摘要" in text
    assert "细胞质遗传并不完全遵循经典母系规律" in text
    assert "## 关键研究问题" in text
    assert "## 核心发现" in text
    assert "## 高频实体" in text
    assert "[[Research/Citrus/entities/细胞质遗传.md|细胞质遗传]] (1)" in text
    assert "## 待跟进问题" in text


def test_append_query_filing_block_preserves_existing_entries() -> None:
    body = "# 标题\n\n## 查询沉淀\n\n### 2026-05-11 10:00:00\n\n- 问题: 旧问题\n- 结论: 旧结论\n"
    updated = append_query_filing_block(
        body,
        "### 2026-05-11 12:00:00\n\n- 问题: 新问题\n- 结论: 新结论",
    )

    assert "旧问题" in updated
    assert "新问题" in updated
    assert updated.count("## 查询沉淀") == 1


def test_select_query_filing_hits_prefers_raw_and_paper_and_skips_target_topic() -> None:
    payload = {
        "wiki_hits": [
            {"source_type": "wiki", "page_type": "topic", "relative_path": "Research/Citrus/topics/genetics-genomics/overview.md", "title": "遗传与基因组"},
            {"source_type": "wiki", "page_type": "paper", "relative_path": "Research/Citrus/papers/genetics-genomics/paper.md", "title": "论文甲"},
            {"source_type": "wiki", "page_type": "entity", "relative_path": "Research/Citrus/entities/细胞质遗传.md", "title": "细胞质遗传"},
        ],
        "raw_hits": [
            {"source_type": "raw_cache", "page_type": "raw_cache", "relative_path": "paper.json", "source_note_path": "Research/Citrus/papers/genetics-genomics/paper.md", "page_number": 3, "title": "论文甲"},
        ],
    }

    selected = select_query_filing_hits(
        query_payload=payload,
        target_type="topic",
        target_key="genetics-genomics",
        top_k=3,
    )

    assert selected[0]["source_type"] == "raw_cache"
    assert selected[1]["page_type"] == "paper"
    assert all(hit.get("relative_path") != "Research/Citrus/topics/genetics-genomics/overview.md" for hit in selected)


def test_update_note_related_pages_section_uses_auto_block(tmp_path: Path) -> None:
    note_path = tmp_path / "paper.md"
    note_path.write_text(
        "\n".join(
            [
                "---",
                'page_type: "paper"',
                "---",
                "",
                "# 标题",
                "",
                "## 相关页面",
                "",
                "- 手工备注保留",
            ]
        ),
        encoding="utf-8",
    )

    update_note_related_pages_section(note_path, axis="genetics-genomics", related_entities=["柑橘", "细胞质遗传"])
    text = note_path.read_text(encoding="utf-8")

    assert "- 手工备注保留" in text
    assert AUTO_RELATED_START in text and AUTO_RELATED_END in text
    assert "[[Research/Citrus/topics/genetics-genomics/overview.md|genetics-genomics]]" in text
    assert "[[Research/Citrus/entities/细胞质遗传.md|细胞质遗传]]" in text
