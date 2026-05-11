#!/usr/bin/env python3
"""Write the final Markdown note into an Obsidian-style vault."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from common import (
    default_wiki_maintainer_ingest_script,
    emit,
    ensure_parent,
    maybe_load_json_record,
    normalize_paper_note_frontmatter,
    resolve_domain_subdir,
    resolve_note_output_mode,
    resolve_obsidian_note_path,
    runtime_config,
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__ or "write obsidian note")
    p.add_argument("--input", default="", help="Metadata JSON path or JSON string.")
    p.add_argument("--content-file", default="", help="Path to the final Markdown content.")
    p.add_argument("--content", default="", help="Inline Markdown content.")
    p.add_argument("--stdin", action="store_true", help="Read Markdown content from stdin.")
    p.add_argument("--lint-json", default="", help="Optional lint JSON path. Refuse write if structure, style, or math gate failed.")
    p.add_argument("--title", default="", help="Explicit title override.")
    p.add_argument("--output", default="", help="JSON status output path.")
    p.add_argument("--vault", default="", help="Target Obsidian vault path.")
    p.add_argument("--subdir", default="", help="Vault-relative subdirectory.")
    p.add_argument("--filename", default="", help="Explicit note filename.")
    p.add_argument("--asset-subdir", default="images", help="Asset folder name relative to the note directory.")
    p.add_argument("--paper-id", default="", help="Canonical paper id.")
    return p


def main() -> None:
    args = parser().parse_args()

    record = maybe_load_json_record(args.input) or {}
    title = args.title or str(record.get("title", "")).strip()
    if not title:
        raise SystemExit("write_obsidian_note.py requires --title or metadata with a title.")

    if args.lint_json:
        lint = json.loads(Path(args.lint_json).expanduser().resolve().read_text(encoding="utf-8"))
        if not lint.get("passes_basic_structure", False):
            raise SystemExit("write_obsidian_note.py refused to write note because basic structure lint failed.")
        if not lint.get("passes_style_gate", False):
            raise SystemExit("write_obsidian_note.py refused to write note because style gate failed.")
        if not lint.get("passes_math_gate", False):
            raise SystemExit("write_obsidian_note.py refused to write note because math gate failed.")

    if args.content_file:
        note_text = Path(args.content_file).expanduser().resolve().read_text(encoding="utf-8")
    elif args.content:
        note_text = args.content
    elif args.stdin:
        note_text = sys.stdin.read()
    else:
        raise SystemExit("write_obsidian_note.py requires --content-file, --content, or --stdin.")

    config = runtime_config()
    if args.vault:
        config["obsidian_vault"] = args.vault
    resolved_subdir = resolve_domain_subdir(
        config,
        title=title,
        abstract=str(record.get("abstract", "")),
        subdir=args.subdir,
    )
    note_text = normalize_paper_note_frontmatter(
        note_text,
        record=record,
        config=config,
        title=title,
        resolved_subdir=resolved_subdir,
    )

    target_path = resolve_obsidian_note_path(
        config,
        title=title,
        subdir=resolved_subdir,
        filename=args.filename,
    )
    ensure_parent(target_path)
    Path(target_path).write_text(note_text, encoding="utf-8")
    asset_dir = target_path.parent / args.asset_subdir
    asset_dir.mkdir(parents=True, exist_ok=True)
    maintenance_payload: dict[str, object] = {"triggered": False}
    maintainer_script = default_wiki_maintainer_ingest_script(config)
    if config.get("obsidian_vault") and maintainer_script is not None:
        maintenance_payload["triggered"] = True
        maintenance_payload["script_path"] = str(maintainer_script)
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(maintainer_script),
                    "--vault",
                    str(Path(config["obsidian_vault"]).expanduser().resolve()),
                    "--note",
                    str(target_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            maintenance_payload["status"] = "ok"
            stdout = (result.stdout or "").strip()
            if stdout:
                try:
                    maintenance_payload["result"] = json.loads(stdout)
                except Exception:
                    maintenance_payload["stdout"] = stdout
        except subprocess.CalledProcessError as exc:
            maintenance_payload["status"] = "failed"
            maintenance_payload["stderr"] = (exc.stderr or "").strip()
            maintenance_payload["returncode"] = exc.returncode

    payload = {
        "status": "ok",
        "script": "write_obsidian_note.py",
        "paper_id": args.paper_id or record.get("paper_id", ""),
        "title": title,
        "note_path": str(target_path),
        "subdir": resolved_subdir,
        "images_dir": str(asset_dir),
        "maintenance": maintenance_payload,
    }
    output_mode, root_path = resolve_note_output_mode(config)
    payload["output_mode"] = output_mode
    payload["base_output_root"] = str(root_path)
    if config.get("obsidian_vault"):
        payload["vault"] = str(Path(config["obsidian_vault"]).expanduser().resolve())
    emit(payload, args.output)


if __name__ == "__main__":
    main()
