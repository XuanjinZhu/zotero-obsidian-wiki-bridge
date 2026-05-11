#!/usr/bin/env python3
"""Lint the wiki for frontmatter, links, and maintenance drift."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    WIKILINK_PATTERN,
    base_parser,
    emit,
    ensure_schema_dirs,
    load_schema,
    normalize_string_list,
    normalize_whitespace,
    read_page,
    required_paper_frontmatter_keys,
    schema_path,
    section_text,
)


def parser() -> argparse.ArgumentParser:
    p = base_parser(__doc__ or "lint wiki")
    return p


def main() -> None:
    args = parser().parse_args()
    vault_root = Path(args.vault).expanduser().resolve()
    schema = load_schema(vault_root)
    paths = ensure_schema_dirs(vault_root, schema)
    kb_root = schema_path(vault_root, schema, "knowledge_base_root")
    pages = [read_page(vault_root, path) for path in kb_root.rglob("*.md") if path.is_file()]
    basename_map = {}
    alias_map = {}
    for page in pages:
        basename_map[Path(str(page["path"])).stem] = page
        for alias in normalize_string_list(page["frontmatter"].get("aliases", [])):
            alias_map[alias] = page

    inbound_counts = {str(page["path"]): 0 for page in pages}
    broken_links: list[dict[str, str]] = []
    missing_frontmatter: list[dict[str, object]] = []
    stale_pages: list[str] = []
    duplicate_topics: list[str] = []
    topic_titles_seen: set[str] = set()

    for page in pages:
        frontmatter = page["frontmatter"]
        if page["page_type"] == "paper":
            missing = [key for key in required_paper_frontmatter_keys(schema) if not frontmatter.get(key)]
            if missing:
                missing_frontmatter.append(
                    {
                        "path": page["relative_path"],
                        "missing_keys": missing,
                    }
                )
            if normalize_whitespace(str(frontmatter.get("source_status", ""))) != "current":
                stale_pages.append(page["relative_path"])
        if page["page_type"] == "topic":
            normalized_title = normalize_whitespace(page["title"]).lower()
            if normalized_title in topic_titles_seen:
                duplicate_topics.append(page["relative_path"])
            topic_titles_seen.add(normalized_title)
        body = str(page["body"])
        for match in WIKILINK_PATTERN.finditer(body):
            raw_target = match.group(2).split("|", 1)[0].split("#", 1)[0].strip()
            if not raw_target:
                continue
            if raw_target.startswith("Research/"):
                target_path = (vault_root / raw_target).resolve()
                if not target_path.exists():
                    broken_links.append({"source": page["relative_path"], "target": raw_target})
                else:
                    if target_path.suffix == ".md":
                        inbound_counts[str(target_path)] = inbound_counts.get(str(target_path), 0) + 1
                continue
            target_page = basename_map.get(raw_target) or alias_map.get(raw_target)
            if target_page is None:
                broken_links.append({"source": page["relative_path"], "target": raw_target})
            else:
                inbound_counts[str(target_page["path"])] = inbound_counts.get(str(target_page["path"]), 0) + 1

    orphan_pages = [
        page["relative_path"]
        for page in pages
        if inbound_counts.get(str(page["path"]), 0) == 0 and page["page_type"] == "paper"
    ]

    conflicts_registry = (paths["ops_dir"] / "conflicts.md").read_text(encoding="utf-8") if (paths["ops_dir"] / "conflicts.md").exists() else ""
    unregistered_conflicts: list[str] = []
    for page in pages:
        if page["page_type"] != "paper":
            continue
        conflict_text = section_text(str(page["body"]), "与既有结论的冲突")
        cleaned = normalize_whitespace(conflict_text.replace("-", " "))
        if cleaned and cleaned not in {"无", "暂无", "none"} and page["title"] not in conflicts_registry:
            unregistered_conflicts.append(page["relative_path"])

    emit(
        {
            "status": "ok",
            "script": "lint_wiki.py",
            "broken_links": broken_links,
            "orphan_pages": orphan_pages,
            "missing_frontmatter": missing_frontmatter,
            "stale_pages": stale_pages,
            "duplicate_topics": duplicate_topics,
            "unregistered_conflicts": unregistered_conflicts,
        },
        args.output,
    )


if __name__ == "__main__":
    main()
