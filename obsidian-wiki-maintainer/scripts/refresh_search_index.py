#!/usr/bin/env python3
"""Refresh the local wiki search index."""

from __future__ import annotations

from pathlib import Path

from common import base_parser, emit, load_schema, refresh_search_index


def main() -> None:
    parser = base_parser(__doc__ or "refresh search index")
    args = parser.parse_args()
    vault_root = Path(args.vault).expanduser().resolve()
    schema = load_schema(vault_root)
    payload = refresh_search_index(vault_root, schema)
    payload.update(
        {
            "status": "ok",
            "script": "refresh_search_index.py",
            "vault": str(vault_root),
        }
    )
    emit(payload, args.output)


if __name__ == "__main__":
    main()
