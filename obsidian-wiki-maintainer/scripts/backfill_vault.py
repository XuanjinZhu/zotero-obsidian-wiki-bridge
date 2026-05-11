#!/usr/bin/env python3
"""Backfill legacy notes into the canonical Research/Citrus layout."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    append_log_entry,
    base_parser,
    emit,
    ensure_schema_dirs,
    infer_axis,
    load_schema,
    move_path,
    normalize_paper_frontmatter,
    parse_frontmatter_and_body,
    prune_empty_dirs,
    read_page,
    refresh_search_index,
    relative_to_vault,
    repair_embeds,
    rewrite_axis_topic_page,
    rewrite_conflicts_page,
    rewrite_entity_pages,
    rewrite_index_page,
    schema_path,
    slugify_filename,
    write_markdown,
)


def parser() -> argparse.ArgumentParser:
    p = base_parser(__doc__ or "backfill vault")
    p.add_argument("--legacy-root", default="Research/Papers", help="Legacy root relative to the vault.")
    return p


def main() -> None:
    args = parser().parse_args()
    vault_root = Path(args.vault).expanduser().resolve()
    schema = load_schema(vault_root)
    paths = ensure_schema_dirs(vault_root, schema)
    legacy_root = (vault_root / Path(args.legacy_root)).resolve()
    papers_root = schema_path(vault_root, schema, "papers_dir")
    moved: list[dict[str, str]] = []
    mapping: dict[str, str] = {}

    if legacy_root.exists():
        for note_path in sorted(legacy_root.rglob("*.md")):
            text = note_path.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter_and_body(text)
            title = read_page(vault_root, note_path)["title"]
            axis = normalize_paper_frontmatter(
                frontmatter,
                schema=schema,
                title=title,
                axis=infer_axis(schema, title, body, frontmatter.get("tags", [])),
                body=body,
            )["primary_axis"]
            folder_name = note_path.parent.name if note_path.parent.name != legacy_root.name else slugify_filename(title)
            new_dir = papers_root / axis / folder_name
            new_note_path = new_dir / f"{folder_name}.md"
            normalized_frontmatter = normalize_paper_frontmatter(frontmatter, schema=schema, title=title, axis=axis, body=body)
            write_markdown(new_note_path, normalized_frontmatter, title, body)
            old_note_rel = relative_to_vault(vault_root, note_path)
            new_note_rel = relative_to_vault(vault_root, new_note_path)
            mapping[old_note_rel] = new_note_rel
            images_dir = note_path.parent / "images"
            if images_dir.exists() and images_dir.is_dir():
                new_images_dir = new_dir / "images"
                if not new_images_dir.exists():
                    move_path(images_dir, new_images_dir)
                old_images_rel = relative_to_vault(vault_root, images_dir)
                new_images_rel = relative_to_vault(vault_root, new_images_dir)
                mapping[old_images_rel] = new_images_rel
            moved.append({"from": old_note_rel, "to": new_note_rel})

        for old_rel, new_rel in mapping.items():
            old_abs = (vault_root / old_rel).resolve()
            if old_abs.exists():
                if old_abs.is_file():
                    old_abs.unlink()
                elif old_abs.is_dir():
                    for item in sorted(old_abs.rglob("*"), reverse=True):
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            item.rmdir()
                    old_abs.rmdir()
        prune_empty_dirs(legacy_root)

    paper_pages = [read_page(vault_root, path) for path in papers_root.rglob("*.md") if path.is_file()]
    paper_pages = [page for page in paper_pages if page["page_type"] == "paper"]
    for page in paper_pages:
        updated_body = repair_embeds(Path(str(page["path"])).read_text(encoding="utf-8"), mapping)
        frontmatter, body = parse_frontmatter_and_body(updated_body)
        title = page["title"]
        axis = frontmatter.get("primary_axis") or infer_axis(schema, title, body, frontmatter.get("tags", []))
        normalized_frontmatter = normalize_paper_frontmatter(frontmatter, schema=schema, title=title, axis=str(axis), body=body)
        write_markdown(Path(str(page["path"])), normalized_frontmatter, title, body)

    axis_groups: dict[str, list[dict[str, object]]] = {}
    refreshed_pages = [read_page(vault_root, path) for path in papers_root.rglob("*.md") if path.is_file()]
    refreshed_pages = [page for page in refreshed_pages if page["page_type"] == "paper"]
    for page in refreshed_pages:
        axis_groups.setdefault(page["primary_axis"] or "inbox", []).append(page)
    for axis, axis_pages in axis_groups.items():
        rewrite_axis_topic_page(vault_root, schema, axis, axis_pages)
    rewrite_entity_pages(vault_root, schema, refreshed_pages)
    rewrite_index_page(vault_root, schema, refreshed_pages)
    rewrite_conflicts_page(vault_root, schema, refreshed_pages)
    refresh_payload = refresh_search_index(vault_root, schema)
    append_log_entry(paths["ops_dir"], f"[backfill] Migrated {len(moved)} legacy note(s) into Research")
    emit(
        {
            "status": "ok",
            "script": "backfill_vault.py",
            "moved": moved,
            "search_index_entries": len(refresh_payload.get("entries", [])),
        },
        args.output,
    )


if __name__ == "__main__":
    main()
