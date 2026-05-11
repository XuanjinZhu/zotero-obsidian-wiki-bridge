#!/usr/bin/env python3
"""Persist a high-value query result into a topic or entity page."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (
    append_log_entry,
    append_query_filing_block,
    base_parser,
    build_query_filing_entry,
    emit,
    ensure_entity_page,
    ensure_schema_dirs,
    ensure_topic_page,
    format_filing_evidence,
    load_schema,
    parse_frontmatter_and_body,
    present_search_hit,
    query_filing_exists,
    refresh_search_index,
    render_frontmatter,
    select_query_filing_hits,
    search_index,
    search_index_path,
    write_markdown,
)


def parser() -> argparse.ArgumentParser:
    p = base_parser(__doc__ or "file query result")
    p.add_argument("--query", required=True, help="User query that produced the insight.")
    p.add_argument("--answer", required=True, help="Condensed answer to persist.")
    p.add_argument("--target-type", choices=["topic", "entity"], required=True, help="Wiki page type to file into.")
    p.add_argument("--target-key", required=True, help="Axis key for topic or entity display name for entity.")
    p.add_argument("--query-json", default="", help="Optional query_wiki JSON result path.")
    p.add_argument("--top-k", type=int, default=4, help="Number of evidence hits to persist when query-json is not supplied.")
    p.add_argument("--refresh", action="store_true", help="Refresh the search index before collecting evidence.")
    return p


def load_or_build_query_payload(vault_root: Path, schema: dict[str, object], *, query: str, query_json: str, top_k: int, refresh: bool) -> dict[str, object]:
    if query_json:
        payload = json.loads(Path(query_json).expanduser().resolve().read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    paths = ensure_schema_dirs(vault_root, schema)
    index_path = search_index_path(paths["ops_dir"])
    if refresh or not index_path.exists():
        index_payload = refresh_search_index(vault_root, schema)
    else:
        index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    hits = search_index(index_payload, query, top_k=max(top_k * 2, 8))
    wiki_hits = [present_search_hit(hit, query) for hit in hits if str(hit.get("source_type", "")) == "wiki"][:top_k]
    raw_hits = [present_search_hit(hit, query) for hit in hits if str(hit.get("source_type", "")) == "raw_cache"][:top_k]
    return {
        "query": query,
        "wiki_hits": wiki_hits,
        "raw_hits": raw_hits,
    }


def target_page_path(vault_root: Path, schema: dict[str, object], *, target_type: str, target_key: str) -> Path:
    if target_type == "topic":
        return ensure_topic_page(vault_root, schema, target_key)
    return ensure_entity_page(vault_root, schema, target_key)


def main() -> None:
    args = parser().parse_args()
    vault_root = Path(args.vault).expanduser().resolve()
    schema = load_schema(vault_root)
    paths = ensure_schema_dirs(vault_root, schema)
    query_payload = load_or_build_query_payload(
        vault_root,
        schema,
        query=args.query,
        query_json=args.query_json,
        top_k=args.top_k,
        refresh=args.refresh,
    )
    hits = select_query_filing_hits(
        query_payload=query_payload,
        target_type=args.target_type,
        target_key=args.target_key,
        top_k=args.top_k,
    )
    evidence_lines = [format_filing_evidence(hit) for hit in hits[: args.top_k]]
    entry_block = build_query_filing_entry(query=args.query, answer=args.answer, evidence_lines=evidence_lines)

    page_path = target_page_path(vault_root, schema, target_type=args.target_type, target_key=args.target_key)
    existing_text = page_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter_and_body(existing_text)
    title = ""
    for line in body.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = args.target_key
    if query_filing_exists(body, query=args.query, answer=args.answer):
        emit(
            {
                "status": "ok",
                "script": "file_query_result.py",
                "target_type": args.target_type,
                "target_key": args.target_key,
                "page_path": str(page_path),
                "skipped": True,
                "reason": "duplicate_query_filing",
            },
            args.output,
        )
        return
    updated_body = append_query_filing_block(body, entry_block)
    if frontmatter:
        payload = render_frontmatter(frontmatter)
        page_path.write_text(f"{payload}\n\n{updated_body.rstrip()}\n", encoding="utf-8")
    else:
        write_markdown(page_path, {}, title, updated_body)

    refresh_payload = refresh_search_index(vault_root, schema)
    append_log_entry(paths["ops_dir"], f"[query-file] Filed query into {args.target_type}:{args.target_key}")
    emit(
        {
            "status": "ok",
            "script": "file_query_result.py",
            "target_type": args.target_type,
            "target_key": args.target_key,
            "page_path": str(page_path),
            "evidence_count": len(evidence_lines),
            "search_index_entries": len(refresh_payload.get("entries", [])),
        },
        args.output,
    )


if __name__ == "__main__":
    main()
