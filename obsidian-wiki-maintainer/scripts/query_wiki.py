#!/usr/bin/env python3
"""Search the wiki and optionally surface raw-source evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (
    base_parser,
    present_search_hit,
    emit,
    ensure_schema_dirs,
    load_schema,
    refresh_search_index,
    search_index,
    search_index_path,
)


def parser() -> argparse.ArgumentParser:
    p = base_parser(__doc__ or "query wiki")
    p.add_argument("--query", required=True, help="Natural-language query.")
    p.add_argument("--top-k", type=int, default=8, help="Maximum number of ranked hits.")
    p.add_argument("--refresh", action="store_true", help="Refresh the search index before searching.")
    p.add_argument("--log-query", action="store_true", help="Append a concise audit entry to ops/log.md.")
    return p


def needs_raw_layer(query: str, hits: list[dict[str, object]]) -> bool:
    lower = query.lower()
    if any(token in lower for token in ["原文", "证据", "页码", "quote", "pdf", "细节", "具体数据"]):
        return True
    if not hits:
        return True
    top_score = float(hits[0].get("score", 0) or 0)
    return top_score < 35


def main() -> None:
    args = parser().parse_args()
    vault_root = Path(args.vault).expanduser().resolve()
    schema = load_schema(vault_root)
    paths = ensure_schema_dirs(vault_root, schema)
    index_path = search_index_path(paths["ops_dir"])
    if args.refresh or not index_path.exists():
        payload = refresh_search_index(vault_root, schema)
    else:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    hits = search_index(payload, args.query, top_k=max(args.top_k * 2, 8))
    use_raw = needs_raw_layer(args.query, hits)
    wiki_hits = [present_search_hit(hit, args.query) for hit in hits if str(hit.get("source_type", "")) == "wiki"][: args.top_k]
    raw_hits = [present_search_hit(hit, args.query) for hit in hits if str(hit.get("source_type", "")) == "raw_cache"][: args.top_k]
    result = {
        "status": "ok",
        "script": "query_wiki.py",
        "query": args.query,
        "used_raw_layer": use_raw,
        "wiki_hits": wiki_hits,
        "raw_hits": raw_hits if use_raw else [],
        "index_path": str(index_path),
    }
    if args.log_query:
        from common import append_log_entry

        append_log_entry(
            paths["ops_dir"],
            f"[query] {args.query} | wiki_hits={len(wiki_hits)} raw_hits={len(result['raw_hits'])} raw_layer={use_raw}",
        )
    emit(result, args.output)


if __name__ == "__main__":
    main()
