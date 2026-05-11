#!/usr/bin/env python3
"""Update wiki maintenance pages after a new paper note is added."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    append_log_entry,
    base_parser,
    emit,
    ensure_schema_dirs,
    load_schema,
    read_page,
    refresh_search_index,
    rewrite_axis_topic_page,
    rewrite_conflicts_page,
    rewrite_entity_pages,
    rewrite_index_page,
    schema_path,
    update_note_related_pages_section,
    normalize_string_list,
)


def parser() -> argparse.ArgumentParser:
    p = base_parser(__doc__ or "maintain wiki after ingest")
    p.add_argument("--note", required=True, help="Path to the new or updated paper note.")
    return p


def main() -> None:
    args = parser().parse_args()
    vault_root = Path(args.vault).expanduser().resolve()
    note_path = Path(args.note).expanduser().resolve()
    schema = load_schema(vault_root)
    paths = ensure_schema_dirs(vault_root, schema)
    papers_root = schema_path(vault_root, schema, "papers_dir")
    pages = [read_page(vault_root, path) for path in papers_root.rglob("*.md") if path.is_file()]
    paper_pages = [page for page in pages if page["page_type"] == "paper"]
    target_page = read_page(vault_root, note_path)
    axis = target_page["primary_axis"] or "inbox"
    axis_pages = [page for page in paper_pages if (page["primary_axis"] or "inbox") == axis]
    topic_page = rewrite_axis_topic_page(vault_root, schema, axis, axis_pages)
    entity_pages = rewrite_entity_pages(vault_root, schema, paper_pages)
    index_page = rewrite_index_page(vault_root, schema, paper_pages)
    conflicts_page = rewrite_conflicts_page(vault_root, schema, paper_pages)
    update_note_related_pages_section(
        note_path,
        axis=axis,
        related_entities=normalize_string_list(target_page["frontmatter"].get("related_entities", [])),
    )
    refresh_payload = refresh_search_index(vault_root, schema)
    append_log_entry(paths["ops_dir"], f"[ingest] Updated {target_page['title']} under axis {axis}")
    emit(
        {
            "status": "ok",
            "script": "ingest_maintain.py",
            "note": str(note_path),
            "axis": axis,
            "topic_page": str(topic_page),
            "entity_pages": [str(path) for path in entity_pages],
            "index_page": str(index_page),
            "conflicts_page": str(conflicts_page),
            "search_index_entries": len(refresh_payload.get("entries", [])),
        },
        args.output,
    )


if __name__ == "__main__":
    main()
