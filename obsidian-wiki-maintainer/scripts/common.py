#!/usr/bin/env python3
"""Shared helpers for the Obsidian Wiki Maintainer skill."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCHEMA_START_MARKER = "<!-- WIKI_SCHEMA_START -->"
SCHEMA_END_MARKER = "<!-- WIKI_SCHEMA_END -->"
WIKILINK_PATTERN = re.compile(r"(!?)\[\[([^\]]+)\]\]")
AUTO_RELATED_START = "<!-- AUTO_RELATED_PAGES_START -->"
AUTO_RELATED_END = "<!-- AUTO_RELATED_PAGES_END -->"

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover
    fitz = None


def emit(payload: dict[str, Any], output_path: str = "") -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output_path:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        return
    print(text)


def base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--vault", required=True, help="Obsidian vault root.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    return parser


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def slugify_filename(text: str) -> str:
    cleaned = normalize_whitespace(text)
    cleaned = re.sub(r"[^\w\s-]", "", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"[-\s]+", "_", cleaned).strip("_")
    return cleaned or "page"


def parse_frontmatter_and_body(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return ({}, text)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ({}, text)
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return ({}, text)
    return (parse_simple_yaml_block(lines[1:end_index]), "\n".join(lines[end_index + 1 :]).lstrip("\n"))


def parse_simple_yaml_block(lines: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    current_key = ""
    list_items: list[Any] | None = None
    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        list_match = re.match(r"^\s*-\s+(.*)$", line)
        if list_match and current_key:
            if list_items is None:
                list_items = []
                parsed[current_key] = list_items
            list_items.append(parse_yaml_scalar(list_match.group(1)))
            continue
        key_match = re.match(r"^([A-Za-z0-9_:-]+):(?:\s+(.*))?$", stripped)
        if not key_match:
            continue
        current_key = key_match.group(1)
        remainder = key_match.group(2)
        list_items = None
        if remainder is None or remainder == "":
            list_items = []
            parsed[current_key] = list_items
        else:
            parsed[current_key] = parse_yaml_scalar(remainder)
    for key, value in list(parsed.items()):
        if value == [] and key not in {"tags", "aliases", "secondary_tags", "related_topics", "related_entities"}:
            parsed[key] = ""
    return parsed


def parse_yaml_scalar(raw: str) -> Any:
    text = raw.strip()
    if text in {"true", "True"}:
        return True
    if text in {"false", "False"}:
        return False
    if text in {"null", "None"}:
        return ""
    if text.startswith('"') and text.endswith('"'):
        try:
            return json.loads(text)
        except Exception:
            return text[1:-1]
    return text


def render_frontmatter(payload: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in payload.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {json.dumps(str(item), ensure_ascii=False)}")
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
            continue
        cleaned = "" if value is None else str(value)
        if cleaned:
            lines.append(f"{key}: {json.dumps(cleaned, ensure_ascii=False)}")
        else:
            lines.append(f"{key}:")
    lines.append("---")
    return "\n".join(lines)


def normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str) and value.strip():
        raw_items = [value]
    else:
        return []
    normalized: list[str] = []
    for item in raw_items:
        cleaned = normalize_whitespace(str(item))
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def load_schema(vault_root: Path) -> dict[str, Any]:
    schema_path = (vault_root / "Research" / "Citrus" / "AGENTS.md").resolve()
    if not schema_path.exists():
        raise RuntimeError(f"Missing schema file: {schema_path}")
    text = schema_path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(SCHEMA_START_MARKER) + r"\s*```json\s*(\{.*?\})\s*```\s*" + re.escape(SCHEMA_END_MARKER),
        flags=re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"Schema markers not found in {schema_path}")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise RuntimeError("Schema payload must be a JSON object.")
    payload["schema_path"] = str(schema_path)
    return payload


def schema_path(vault_root: Path, schema: dict[str, Any], key: str) -> Path:
    rel = normalize_whitespace(str(schema.get(key, "")))
    if not rel:
        raise RuntimeError(f"Schema key '{key}' is missing.")
    return (vault_root / Path(rel)).resolve()


def ensure_schema_dirs(vault_root: Path, schema: dict[str, Any]) -> dict[str, Path]:
    paths = {
        "knowledge_base_root": schema_path(vault_root, schema, "knowledge_base_root"),
        "papers_dir": schema_path(vault_root, schema, "papers_dir"),
        "topics_dir": schema_path(vault_root, schema, "topics_dir"),
        "entities_dir": schema_path(vault_root, schema, "entities_dir"),
        "ops_dir": schema_path(vault_root, schema, "ops_dir"),
        "cache_dir": schema_path(vault_root, schema, "cache_dir"),
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    (paths["ops_dir"] / "search").mkdir(parents=True, exist_ok=True)
    (paths["cache_dir"] / "raw").mkdir(parents=True, exist_ok=True)
    return paths


def normalized_axes(schema: dict[str, Any]) -> list[dict[str, Any]]:
    items = schema.get("axes", [])
    if not isinstance(items, list):
        return []
    axes: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = normalize_whitespace(str(item.get("key", "")))
        if not key:
            continue
        axes.append(
            {
                "key": key,
                "label": normalize_whitespace(str(item.get("label", ""))) or key,
                "keywords": normalize_string_list(item.get("keywords", [])),
                "aliases": normalize_string_list(item.get("aliases", [])),
            }
        )
    return axes


def infer_axis(schema: dict[str, Any], title: str, body: str = "", tags: list[str] | None = None) -> str:
    searchable = normalize_whitespace(" ".join([title, body, " ".join(tags or [])])).lower()
    default_axis = normalize_whitespace(str(schema.get("default_axis", ""))) or "inbox"
    best_axis = default_axis
    best_score = -1
    for axis in normalized_axes(schema):
        score = 0
        if axis["key"].lower() in searchable:
            score += 12
        if axis["label"].lower() in searchable:
            score += 10
        for token in axis["aliases"]:
            if token.lower() in searchable:
                score += 9
        for token in axis["keywords"]:
            if token.lower() in searchable:
                score += 6
        if score > best_score:
            best_score = score
            best_axis = axis["key"]
    return best_axis if best_score > 0 else default_axis


def extract_heading_title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return normalize_whitespace(stripped[2:])
    return normalize_whitespace(fallback)


def required_paper_frontmatter_keys(schema: dict[str, Any]) -> list[str]:
    return normalize_string_list(schema.get("required_paper_frontmatter", []))


def paper_tag_prefix(schema: dict[str, Any]) -> str:
    return normalize_whitespace(str(schema.get("paper_tag_prefix", ""))) or "papers"


def normalize_paper_frontmatter(
    frontmatter: dict[str, Any],
    *,
    schema: dict[str, Any],
    title: str,
    axis: str,
    body: str = "",
) -> dict[str, Any]:
    zotero_item_key = normalize_whitespace(str(frontmatter.get("zotero_item_key", ""))) or extract_core_info_value(body, "Zotero Item Key")
    source_url = normalize_whitespace(str(frontmatter.get("source_url", ""))) or extract_core_info_value(body, "论文链接")
    tags = normalize_string_list(frontmatter.get("tags", []))
    for required_tag in [paper_tag_prefix(schema), f"{paper_tag_prefix(schema)}/{axis}"]:
        if required_tag not in tags:
            tags.append(required_tag)
    normalized = {
        "tags": tags,
        "aliases": normalize_string_list(frontmatter.get("aliases", [])),
        "date": normalize_whitespace(str(frontmatter.get("date", ""))),
        "doi": normalize_whitespace(str(frontmatter.get("doi", ""))),
        "page_type": "paper",
        "primary_axis": axis,
        "secondary_tags": normalize_string_list(frontmatter.get("secondary_tags", [])),
        "zotero_item_key": zotero_item_key,
        "zotero_attachment_key": normalize_whitespace(str(frontmatter.get("zotero_attachment_key", ""))),
        "zotero_pdf_path": normalize_whitespace(str(frontmatter.get("zotero_pdf_path", ""))),
        "source_url": source_url,
        "ingest_date": normalize_whitespace(str(frontmatter.get("ingest_date", ""))) or date.today().isoformat(),
        "source_status": normalize_whitespace(str(frontmatter.get("source_status", ""))) or "current",
        "related_topics": normalize_string_list(frontmatter.get("related_topics", [])),
        "related_entities": normalize_string_list(frontmatter.get("related_entities", [])),
    }
    for key in required_paper_frontmatter_keys(schema):
        normalized.setdefault(key, "")
    return normalized


def write_markdown(path: Path, frontmatter: dict[str, Any], title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = render_frontmatter(frontmatter)
    body_text = body.strip()
    if not body_text.startswith("# "):
        body_text = f"# {title}\n\n{body_text}".strip()
    path.write_text(f"{payload}\n\n{body_text}\n", encoding="utf-8")


def relative_to_vault(vault_root: Path, path: Path) -> str:
    return path.resolve().relative_to(vault_root.resolve()).as_posix()


def collect_markdown_pages(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def read_page(vault_root: Path, path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter_and_body(text)
    title = extract_heading_title(body, path.stem)
    return {
        "path": path.resolve(),
        "relative_path": relative_to_vault(vault_root, path),
        "frontmatter": frontmatter,
        "body": body,
        "title": title,
        "page_type": normalize_whitespace(str(frontmatter.get("page_type", ""))),
        "primary_axis": normalize_whitespace(str(frontmatter.get("primary_axis", ""))),
    }


def section_text(body: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", flags=re.MULTILINE)
    match = pattern.search(body)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+.+$", body[start:], flags=re.MULTILINE)
    if not next_match:
        return body[start:].strip()
    end = start + next_match.start()
    return body[start:end].strip()


def extract_section_block(body: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", flags=re.MULTILINE)
    match = pattern.search(body)
    if not match:
        return ""
    start = match.start()
    next_match = re.search(r"^##\s+.+$", body[match.end() :], flags=re.MULTILINE)
    if not next_match:
        return body[start:].strip()
    end = match.end() + next_match.start()
    return body[start:end].strip()


def extract_core_info_value(body: str, field_name: str) -> str:
    pattern = re.compile(rf"^\s*-\s*{re.escape(field_name)}:\s*(.+?)\s*$", flags=re.MULTILINE)
    match = pattern.search(body)
    if not match:
        return ""
    return normalize_whitespace(match.group(1))


def axis_label(schema: dict[str, Any], axis_key: str) -> str:
    for axis in normalized_axes(schema):
        if axis["key"] == axis_key:
            return str(axis["label"])
    return axis_key


def _clean_markdown_line(line: str) -> str:
    stripped = normalize_whitespace(line)
    if not stripped:
        return ""
    stripped = re.sub(r"#+\s*", "", stripped)
    if stripped.startswith(("![[", "```", "> [!")):
        return ""
    if stripped.startswith(">"):
        stripped = normalize_whitespace(stripped.lstrip(">").strip())
    if stripped.startswith("|"):
        return ""
    if stripped.startswith("- "):
        stripped = normalize_whitespace(stripped[2:])
    stripped = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", stripped)
    stripped = re.sub(r"\[\[([^\]]+)\]\]", r"\1", stripped)
    stripped = stripped.replace("`", "")
    return normalize_whitespace(stripped)


def section_summary(body: str, heading: str, *, max_chars: int = 220) -> str:
    raw = section_text(body, heading)
    if not raw:
        return ""
    parts: list[str] = []
    for line in raw.splitlines():
        cleaned = _clean_markdown_line(line)
        if not cleaned:
            continue
        parts.append(cleaned)
        if len(" ".join(parts)) >= max_chars:
            break
    if not parts:
        return ""
    summary = " ".join(parts)
    if not re.search(r"[。；;：:，,]", summary) and len(summary) <= 80:
        return ""
    if len(summary) > max_chars:
        summary = summary[: max_chars - 3].rstrip() + "..."
    return summary


def collect_open_questions(body: str, *, max_items: int = 3) -> list[str]:
    raw = section_text(body, "待验证问题")
    if not raw:
        return []
    items: list[str] = []
    for line in raw.splitlines():
        cleaned = _clean_markdown_line(line)
        if not cleaned or cleaned in {"暂无", "无", "none"}:
            continue
        if cleaned not in items:
            items.append(cleaned)
        if len(items) >= max_items:
            break
    return items


def append_query_filing_block(body: str, entry_block: str) -> str:
    entry = entry_block.strip()
    if not entry:
        return body.rstrip() + "\n"
    existing = extract_section_block(body, "查询沉淀")
    if existing:
        replacement = existing.rstrip() + "\n\n" + entry
        return body.replace(existing, replacement).rstrip() + "\n"
    return body.rstrip() + "\n\n## 查询沉淀\n\n" + entry + "\n"


def query_filing_exists(body: str, *, query: str, answer: str) -> bool:
    filing_block = extract_section_block(body, "查询沉淀")
    if not filing_block:
        return False
    normalized_query = normalize_whitespace(query)
    normalized_answer = normalize_whitespace(answer)
    return f"- 问题: {normalized_query}" in filing_block and f"- 结论: {normalized_answer}" in filing_block


def upsert_auto_block_in_section(body: str, heading: str, start_marker: str, end_marker: str, block_body: str) -> str:
    entry = f"{start_marker}\n{block_body.rstrip()}\n{end_marker}"
    existing_section = extract_section_block(body, heading)
    if not existing_section:
        new_section = f"## {heading}\n\n{entry}"
        return body.rstrip() + "\n\n" + new_section + "\n"
    marker_pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), flags=re.DOTALL)
    if marker_pattern.search(existing_section):
        replacement = marker_pattern.sub(entry, existing_section)
    else:
        replacement = existing_section.rstrip() + "\n\n" + entry
    return body.replace(existing_section, replacement).rstrip() + "\n"


def build_query_filing_entry(*, query: str, answer: str, evidence_lines: list[str], timestamp: str | None = None) -> str:
    label = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"### {label}",
        "",
        f"- 问题: {normalize_whitespace(query)}",
        f"- 结论: {normalize_whitespace(answer)}",
    ]
    for index, evidence in enumerate(evidence_lines, start=1):
        lines.append(f"- 证据{index}: {normalize_whitespace(evidence)}")
    return "\n".join(lines).rstrip()


def build_related_pages_block(*, axis: str, entity_names: list[str]) -> str:
    lines = [
        "- topic: [[Research/topics/{axis}/overview.md|{axis}]]".format(axis=axis),
    ]
    for entity in entity_names:
        lines.append(f"- entity: [[Research/entities/{slugify_filename(entity)}.md|{entity}]]")
    return "\n".join(lines)


def update_note_related_pages_section(note_path: Path, *, axis: str, related_entities: list[str]) -> None:
    text = note_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter_and_body(text)
    body = body.replace("- 相关 topic 页面待维护脚本统一回填", "").replace("- 相关 topic 页面待维护脚本统一回填\n", "")
    block = build_related_pages_block(axis=axis, entity_names=related_entities)
    updated_body = upsert_auto_block_in_section(
        body,
        "相关页面",
        AUTO_RELATED_START,
        AUTO_RELATED_END,
        block,
    )
    title = extract_heading_title(updated_body, note_path.stem)
    if frontmatter:
        payload = render_frontmatter(frontmatter)
        note_path.write_text(f"{payload}\n\n{updated_body.rstrip()}\n", encoding="utf-8")
    else:
        write_markdown(note_path, {}, title, updated_body)


def ensure_topic_page(vault_root: Path, schema: dict[str, Any], axis: str) -> Path:
    path = schema_path(vault_root, schema, "topics_dir") / axis / "overview.md"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    label = axis_label(schema, axis)
    lines = [
        "---",
        'page_type: "topic"',
        f'primary_axis: "{axis}"',
        f'aliases:\n  - {json.dumps(axis, ensure_ascii=False)}',
        f'tags:\n  - {json.dumps(f"topics/{axis}", ensure_ascii=False)}',
        "---",
        "",
        f"# {label}",
        "",
        "## 概览",
        "",
        "- 论文数量: 0",
        f"- 轴标识: `{axis}`",
        "",
        "## 主题摘要",
        "",
        "- 当前尚无主题摘要。",
        "",
        "## 关键研究问题",
        "",
        "- 当前尚未从现有论文中提炼出稳定问题表述。",
        "",
        "## 核心发现",
        "",
        "- 当前尚未从现有论文中提炼出核心发现摘要。",
        "",
        "## 高频实体",
        "",
        "- 当前没有已登记实体。",
        "",
        "## 待跟进问题",
        "",
        "- 当前没有已登记的待跟进问题。",
        "",
        "## 论文列表",
        "",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def ensure_entity_page(vault_root: Path, schema: dict[str, Any], entity: str) -> Path:
    path = schema_path(vault_root, schema, "entities_dir") / f"{slugify_filename(entity)}.md"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        'page_type: "entity"',
        f'tags:\n  - {json.dumps("entities", ensure_ascii=False)}',
        "---",
        "",
        f"# {entity}",
        "",
        "## 相关论文",
        "",
        "- 当前没有已登记相关论文。",
        "",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def format_filing_evidence(hit: dict[str, Any]) -> str:
    title = normalize_whitespace(str(hit.get("title", "")))
    relative_path = normalize_whitespace(str(hit.get("relative_path", "")))
    snippet = normalize_whitespace(str(hit.get("snippet", "")))
    if str(hit.get("source_type", "")) == "raw_cache":
        source_note_path = normalize_whitespace(str(hit.get("source_note_path", "")))
        page_number = int(hit.get("page_number", 0) or 0)
        attachment_key = normalize_whitespace(str(hit.get("zotero_attachment_key", "")))
        note_ref = f"[[{source_note_path}|{title}]]" if source_note_path else title
        parts = [f"raw: {note_ref}"]
        if page_number > 0:
            parts.append(f"第 {page_number} 页")
        if attachment_key:
            parts.append(f"附件 {attachment_key}")
        if snippet:
            parts.append(f"摘录：{snippet}")
        return "；".join(parts)
    note_ref = f"[[{relative_path}|{title}]]" if relative_path else title
    if snippet:
        return f"wiki: {note_ref}；摘录：{snippet}"
    return f"wiki: {note_ref}"


def select_query_filing_hits(
    *,
    query_payload: dict[str, Any],
    target_type: str,
    target_key: str,
    top_k: int,
) -> list[dict[str, Any]]:
    topic_target_rel = f"Research/topics/{target_key}/overview.md"
    entity_target_rel = f"Research/entities/{slugify_filename(target_key)}.md"
    candidates: list[dict[str, Any]] = []
    for raw_hit in query_payload.get("raw_hits", []) or []:
        if isinstance(raw_hit, dict):
            candidates.append(raw_hit)
    for wiki_hit in query_payload.get("wiki_hits", []) or []:
        if isinstance(wiki_hit, dict):
            candidates.append(wiki_hit)

    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for hit in candidates:
        source_type = str(hit.get("source_type", ""))
        page_type = str(hit.get("page_type", ""))
        relative_path = normalize_whitespace(str(hit.get("relative_path", "")))
        if page_type in {"ops-index", "ops-log", "ops-conflicts"}:
            continue
        if target_type == "topic" and relative_path == topic_target_rel:
            continue
        if target_type == "entity" and relative_path == entity_target_rel:
            continue
        if source_type == "wiki" and page_type in {"topic", "entity"}:
            continue
        key = (
            source_type,
            normalize_whitespace(str(hit.get("source_note_path", ""))) or relative_path,
            int(hit.get("page_number", 0) or 0),
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(hit)
        if len(selected) >= top_k:
            return selected

    if len(selected) < top_k:
        for hit in candidates:
            relative_path = normalize_whitespace(str(hit.get("relative_path", "")))
            if target_type == "topic" and relative_path == topic_target_rel:
                continue
            if target_type == "entity" and relative_path == entity_target_rel:
                continue
            key = (
                str(hit.get("source_type", "")),
                normalize_whitespace(str(hit.get("source_note_path", ""))) or relative_path,
                int(hit.get("page_number", 0) or 0),
            )
            if key in seen:
                continue
            seen.add(key)
            selected.append(hit)
            if len(selected) >= top_k:
                break
    return selected


def raw_cache_path(cache_dir: Path, page: dict[str, Any]) -> Path:
    slug = slugify_filename(Path(str(page["path"])).stem)
    return cache_dir / "raw" / f"{slug}.json"


def extract_pdf_page_texts(pdf_path: Path, *, max_pages: int = 12, min_chars: int = 40) -> list[dict[str, Any]]:
    if fitz is None or not pdf_path.exists():
        return []
    doc = fitz.open(pdf_path)
    parts: list[dict[str, Any]] = []
    try:
        page_limit = min(len(doc), max_pages)
        for page_index in range(page_limit):
            text = normalize_whitespace(doc[page_index].get_text("text"))
            if len(text) < min_chars:
                continue
            parts.append(
                {
                    "page_number": page_index + 1,
                    "text": text,
                }
            )
    finally:
        doc.close()
    return parts


def build_raw_cache_entries(raw_payload: dict[str, Any], frontmatter: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    title = normalize_whitespace(str(raw_payload.get("title", "")))
    source_note_path = normalize_whitespace(str(raw_payload.get("source_note_path", "")))
    tags = normalize_string_list(frontmatter.get("tags", []))
    aliases = normalize_string_list(frontmatter.get("aliases", []))
    source_status = normalize_whitespace(str(frontmatter.get("source_status", ""))) or "current"
    primary_axis = normalize_whitespace(str(raw_payload.get("primary_axis", "")))
    zotero_item_key = normalize_whitespace(str(raw_payload.get("zotero_item_key", "")))
    zotero_attachment_key = normalize_whitespace(str(raw_payload.get("zotero_attachment_key", "")))
    zotero_pdf_path = normalize_whitespace(str(raw_payload.get("zotero_pdf_path", "")))
    cache_relative_path = normalize_whitespace(str(raw_payload.get("cache_relative_path", "")))
    for item in raw_payload.get("pages", []):
        if not isinstance(item, dict):
            continue
        page_number = int(item.get("page_number", 0) or 0)
        text = normalize_whitespace(str(item.get("text", "")))
        if page_number <= 0 or not text:
            continue
        entries.append(
            {
                "source_type": "raw_cache",
                "path": normalize_whitespace(str(raw_payload.get("cache_path", ""))),
                "relative_path": cache_relative_path,
                "title": title,
                "page_type": "raw_cache",
                "primary_axis": primary_axis,
                "tags": tags,
                "aliases": aliases,
                "source_status": source_status,
                "zotero_item_key": zotero_item_key,
                "zotero_attachment_key": zotero_attachment_key,
                "zotero_pdf_path": zotero_pdf_path,
                "source_note_path": source_note_path,
                "page_number": page_number,
                "content": text,
            }
        )
    return entries


def ensure_raw_cache(cache_dir: Path, page: dict[str, Any]) -> list[dict[str, Any]]:
    frontmatter = page["frontmatter"]
    pdf_path_value = normalize_whitespace(str(frontmatter.get("zotero_pdf_path", "")))
    if not pdf_path_value:
        return []
    pdf_path = Path(pdf_path_value).expanduser()
    if not pdf_path.exists():
        return []
    cache_path = raw_cache_path(cache_dir, page)
    if not cache_path.exists() or cache_path.stat().st_mtime < pdf_path.stat().st_mtime:
        page_texts = extract_pdf_page_texts(pdf_path)
        if not page_texts:
            return []
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        raw_payload = {
            "title": page["title"],
            "primary_axis": page["primary_axis"],
            "source_note_path": page["relative_path"],
            "zotero_item_key": normalize_whitespace(str(frontmatter.get("zotero_item_key", ""))),
            "zotero_attachment_key": normalize_whitespace(str(frontmatter.get("zotero_attachment_key", ""))),
            "zotero_pdf_path": normalize_whitespace(str(frontmatter.get("zotero_pdf_path", ""))),
            "cache_path": str(cache_path),
            "cache_relative_path": cache_path.name,
            "pages": page_texts,
        }
        cache_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raw_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        return []
    raw_payload.setdefault("cache_path", str(cache_path))
    raw_payload.setdefault("cache_relative_path", cache_path.name)
    return build_raw_cache_entries(raw_payload, frontmatter)


def tokenize_query(text: str) -> list[str]:
    normalized = normalize_whitespace(text).lower()
    if not normalized:
        return []
    tokens: list[str] = []
    for chunk in re.split(r"[^\w\u4e00-\u9fff]+", normalized):
        if not chunk:
            continue
        tokens.append(chunk)
        if re.search(r"[\u4e00-\u9fff]", chunk) and len(chunk) > 2:
            for index in range(0, len(chunk) - 1):
                tokens.append(chunk[index : index + 2])
    unique: list[str] = []
    for token in tokens:
        if token not in unique:
            unique.append(token)
    return unique


def score_entry(entry: dict[str, Any], query: str) -> float:
    normalized_query = normalize_whitespace(query).lower()
    tokens = tokenize_query(query)
    title = normalize_whitespace(str(entry.get("title", ""))).lower()
    aliases = " ".join(normalize_string_list(entry.get("aliases", []))).lower()
    tags = " ".join(normalize_string_list(entry.get("tags", []))).lower()
    axis = normalize_whitespace(str(entry.get("primary_axis", ""))).lower()
    content = normalize_whitespace(str(entry.get("content", ""))).lower()
    score = 0.0
    if normalized_query and normalized_query in title:
        score += 80
    if normalized_query and normalized_query in aliases:
        score += 70
    if normalized_query and normalized_query in tags:
        score += 60
    if normalized_query and normalized_query in content:
        score += 25
    for token in tokens:
        if token in title:
            score += 18
        if token in aliases:
            score += 16
        if token in tags:
            score += 14
        if token in axis:
            score += 10
        if token in content:
            score += 4
    page_type = normalize_whitespace(str(entry.get("page_type", "")))
    if page_type == "topic":
        score += 8
    if page_type == "entity":
        score += 6
    if normalize_whitespace(str(entry.get("source_status", ""))) == "current":
        score += 2
    return score


def build_search_snippet(content: str, query: str, *, limit: int = 240) -> str:
    normalized_content = normalize_whitespace(content)
    if not normalized_content:
        return ""
    lower = normalized_content.lower()
    tokens = tokenize_query(query)
    positions = [lower.find(token) for token in tokens if token and lower.find(token) >= 0]
    if not positions:
        return normalized_content[:limit]
    start = max(0, min(positions) - 60)
    end = min(len(normalized_content), start + limit)
    snippet = normalized_content[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(normalized_content):
        snippet = snippet + "..."
    return snippet


def present_search_hit(entry: dict[str, Any], query: str) -> dict[str, Any]:
    presented = {
        "source_type": entry.get("source_type", ""),
        "relative_path": entry.get("relative_path", ""),
        "title": entry.get("title", ""),
        "page_type": entry.get("page_type", ""),
        "primary_axis": entry.get("primary_axis", ""),
        "tags": entry.get("tags", []),
        "aliases": entry.get("aliases", []),
        "source_status": entry.get("source_status", ""),
        "score": entry.get("score", 0),
        "snippet": build_search_snippet(str(entry.get("content", "")), query),
    }
    for key in ["zotero_item_key", "zotero_attachment_key", "zotero_pdf_path", "source_note_path"]:
        value = normalize_whitespace(str(entry.get(key, "")))
        if value:
            presented[key] = value
    page_number = int(entry.get("page_number", 0) or 0)
    if page_number > 0:
        presented["page_number"] = page_number
    return presented


def search_index(index_payload: dict[str, Any], query: str, *, top_k: int = 10) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for entry in index_payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        score = score_entry(entry, query)
        if score <= 0:
            continue
        enriched = dict(entry)
        enriched["score"] = round(score, 2)
        matches.append(enriched)
    matches.sort(key=lambda item: (-float(item["score"]), str(item.get("title", "")), str(item.get("relative_path", ""))))
    return matches[:top_k]


def search_index_path(ops_dir: Path) -> Path:
    return ops_dir / "search" / "index.json"


def refresh_search_index(vault_root: Path, schema: dict[str, Any]) -> dict[str, Any]:
    paths = ensure_schema_dirs(vault_root, schema)
    markdown_paths = [
        path
        for path in collect_markdown_pages(paths["knowledge_base_root"])
        if path.resolve() != Path(schema["schema_path"]).resolve()
    ]
    pages = [read_page(vault_root, path) for path in markdown_paths]
    entries: list[dict[str, Any]] = []
    for page in pages:
        frontmatter = page["frontmatter"]
        entries.append(
            {
                "source_type": "wiki",
                "path": str(page["path"]),
                "relative_path": page["relative_path"],
                "title": page["title"],
                "page_type": normalize_whitespace(str(frontmatter.get("page_type", ""))) or infer_page_type_from_path(path=page["path"], schema=schema, vault_root=vault_root),
                "primary_axis": normalize_whitespace(str(frontmatter.get("primary_axis", ""))),
                "tags": normalize_string_list(frontmatter.get("tags", [])),
                "aliases": normalize_string_list(frontmatter.get("aliases", [])),
                "source_status": normalize_whitespace(str(frontmatter.get("source_status", ""))) or "current",
                "content": page["body"],
            }
        )
        raw_entries = ensure_raw_cache(paths["cache_dir"], page)
        if raw_entries:
            entries.extend(raw_entries)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "entries": entries,
    }
    index_path = search_index_path(paths["ops_dir"])
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def infer_page_type_from_path(*, path: Path, schema: dict[str, Any], vault_root: Path) -> str:
    relative = relative_to_vault(vault_root, path)
    if relative == normalize_whitespace(str(schema.get("schema_path", ""))).replace("\\", "/"):
        return "schema"
    topics_dir = normalize_whitespace(str(schema.get("topics_dir", ""))).replace("\\", "/")
    entities_dir = normalize_whitespace(str(schema.get("entities_dir", ""))).replace("\\", "/")
    ops_dir = normalize_whitespace(str(schema.get("ops_dir", ""))).replace("\\", "/")
    if relative.startswith(f"{topics_dir}/"):
        return "topic"
    if relative.startswith(f"{entities_dir}/"):
        return "entity"
    if relative.startswith(f"{ops_dir}/"):
        if relative.endswith("index.md"):
            return "ops-index"
        if relative.endswith("log.md"):
            return "ops-log"
        if relative.endswith("conflicts.md"):
            return "ops-conflicts"
        return "ops"
    return "paper"


def append_log_entry(ops_dir: Path, message: str) -> None:
    log_path = ops_dir / "log.md"
    if log_path.exists():
        content = log_path.read_text(encoding="utf-8").rstrip() + "\n"
    else:
        content = "# Wiki Log\n\n"
    content += f"- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}\n"
    log_path.write_text(content, encoding="utf-8")


def rewrite_axis_topic_page(vault_root: Path, schema: dict[str, Any], axis: str, papers: list[dict[str, Any]]) -> Path:
    topics_dir = schema_path(vault_root, schema, "topics_dir")
    axis_dir = topics_dir / axis
    axis_dir.mkdir(parents=True, exist_ok=True)
    page_path = axis_dir / "overview.md"
    preserved_query_filing = ""
    if page_path.exists():
        existing_text = page_path.read_text(encoding="utf-8")
        _, existing_body = parse_frontmatter_and_body(existing_text)
        preserved_query_filing = extract_section_block(existing_body, "查询沉淀")
    label = axis_label(schema, axis)
    entity_counts: dict[str, int] = {}
    summary_lines: list[str] = []
    question_lines: list[str] = []
    result_lines: list[str] = []
    open_question_lines: list[str] = []
    for paper in sorted(papers, key=lambda item: item["title"]):
        note_path = relative_to_vault(vault_root, Path(str(paper["path"])))
        body = str(paper["body"])
        summary = section_summary(body, "一句话总结")
        if summary:
            summary_lines.append(f"- [[{note_path}|{paper['title']}]]: {summary}")
        research_question = section_summary(body, "研究问题")
        if research_question:
            question_lines.append(f"- [[{note_path}|{paper['title']}]]: {research_question}")
        key_result = section_summary(body, "关键结果")
        if not key_result:
            key_result = summary
        if key_result:
            result_lines.append(f"- [[{note_path}|{paper['title']}]]: {key_result}")
        for open_question in collect_open_questions(body):
            open_question_lines.append(f"- [[{note_path}|{paper['title']}]]: {open_question}")
        for entity in normalize_string_list(paper["frontmatter"].get("related_entities", [])):
            entity_counts[entity] = entity_counts.get(entity, 0) + 1
    lines = [
        "---",
        'page_type: "topic"',
        f'primary_axis: "{axis}"',
        f'aliases:\n  - {json.dumps(axis, ensure_ascii=False)}',
        f'tags:\n  - {json.dumps(f"topics/{axis}", ensure_ascii=False)}',
        "---",
        "",
        f"# {label}",
        "",
        "## 概览",
        "",
        f"- 论文数量: {len(papers)}",
        f"- 轴标识: `{axis}`",
        "",
        "## 主题摘要",
        "",
    ]
    lines.extend(summary_lines or ["- 当前尚无主题摘要。"])
    lines.extend([
        "",
        "## 关键研究问题",
        "",
    ])
    lines.extend(question_lines or ["- 当前尚未从现有论文中提炼出稳定问题表述。"])
    lines.extend([
        "",
        "## 核心发现",
        "",
    ])
    lines.extend(result_lines or ["- 当前尚未从现有论文中提炼出核心发现摘要。"])
    lines.extend([
        "",
        "## 高频实体",
        "",
    ])
    if entity_counts:
        for entity, count in sorted(entity_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- [[Research/entities/{slugify_filename(entity)}.md|{entity}]] ({count})")
    else:
        lines.append("- 当前没有已登记实体。")
    lines.extend([
        "",
        "## 待跟进问题",
        "",
    ])
    deduped_open_questions: list[str] = []
    for item in open_question_lines:
        if item not in deduped_open_questions:
            deduped_open_questions.append(item)
    lines.extend(deduped_open_questions or ["- 当前没有已登记的待跟进问题。"])
    lines.extend([
        "",
        "## 论文列表",
        "",
    ])
    for paper in sorted(papers, key=lambda item: item["title"]):
        note_path = relative_to_vault(vault_root, Path(str(paper["path"])))
        lines.append(f"- [[{note_path}|{paper['title']}]]")
    content = "\n".join(lines).rstrip()
    if preserved_query_filing:
        content += "\n\n" + preserved_query_filing.strip()
    page_path.write_text(content + "\n", encoding="utf-8")
    return page_path


def rewrite_entity_pages(vault_root: Path, schema: dict[str, Any], papers: list[dict[str, Any]]) -> list[Path]:
    entities_dir = schema_path(vault_root, schema, "entities_dir")
    entity_map: dict[str, list[dict[str, Any]]] = {}
    for paper in papers:
        frontmatter = paper["frontmatter"]
        for entity in normalize_string_list(frontmatter.get("related_entities", [])):
            entity_map.setdefault(entity, []).append(paper)
    written: list[Path] = []
    for entity, related_papers in entity_map.items():
        path = entities_dir / f"{slugify_filename(entity)}.md"
        preserved_query_filing = ""
        if path.exists():
            existing_text = path.read_text(encoding="utf-8")
            _, existing_body = parse_frontmatter_and_body(existing_text)
            preserved_query_filing = extract_section_block(existing_body, "查询沉淀")
        axis_counts: dict[str, int] = {}
        summary_lines: list[str] = []
        question_lines: list[str] = []
        result_lines: list[str] = []
        open_question_lines: list[str] = []
        for paper in sorted(related_papers, key=lambda item: item["title"]):
            note_path = relative_to_vault(vault_root, Path(str(paper["path"])))
            body = str(paper["body"])
            axis_key = normalize_whitespace(str(paper.get("primary_axis", ""))) or "inbox"
            axis_counts[axis_key] = axis_counts.get(axis_key, 0) + 1
            summary = section_summary(body, "一句话总结")
            if summary:
                summary_lines.append(f"- [[{note_path}|{paper['title']}]]: {summary}")
            research_question = section_summary(body, "研究问题")
            if research_question:
                question_lines.append(f"- [[{note_path}|{paper['title']}]]: {research_question}")
            key_result = section_summary(body, "关键结果")
            if not key_result:
                key_result = summary
            if key_result:
                result_lines.append(f"- [[{note_path}|{paper['title']}]]: {key_result}")
            for open_question in collect_open_questions(body):
                open_question_lines.append(f"- [[{note_path}|{paper['title']}]]: {open_question}")
        lines = [
            "---",
            'page_type: "entity"',
            f'tags:\n  - {json.dumps("entities", ensure_ascii=False)}',
            "---",
            "",
            f"# {entity}",
            "",
            "## 概览",
            "",
            f"- 相关论文数量: {len(related_papers)}",
            "",
            "## 主题摘要",
            "",
        ]
        lines.extend(summary_lines or ["- 当前尚无主题摘要。"])
        lines.extend(
            [
                "",
                "## 相关研究问题",
                "",
            ]
        )
        lines.extend(question_lines or ["- 当前尚未提炼出稳定问题表述。"])
        lines.extend(
            [
                "",
                "## 核心发现",
                "",
            ]
        )
        lines.extend(result_lines or ["- 当前尚未提炼出核心发现摘要。"])
        lines.extend(
            [
                "",
                "## 相关研究轴",
                "",
            ]
        )
        for axis_key, count in sorted(axis_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- [[Research/topics/{axis_key}/overview.md|{axis_label(schema, axis_key)}]] ({count})")
        lines.extend(
            [
                "",
                "## 待跟进问题",
                "",
            ]
        )
        deduped_open_questions: list[str] = []
        for item in open_question_lines:
            if item not in deduped_open_questions:
                deduped_open_questions.append(item)
        lines.extend(deduped_open_questions or ["- 当前没有已登记的待跟进问题。"])
        lines.extend(
            [
                "",
            "## 相关论文",
            "",
            ]
        )
        for paper in sorted(related_papers, key=lambda item: item["title"]):
            note_path = relative_to_vault(vault_root, Path(str(paper["path"])))
            lines.append(f"- [[{note_path}|{paper['title']}]]")
        content = "\n".join(lines).rstrip()
        if preserved_query_filing:
            content += "\n\n" + preserved_query_filing.strip()
        path.write_text(content + "\n", encoding="utf-8")
        written.append(path)
    return written


def rewrite_index_page(vault_root: Path, schema: dict[str, Any], papers: list[dict[str, Any]]) -> Path:
    ops_dir = schema_path(vault_root, schema, "ops_dir")
    path = ops_dir / "index.md"
    grouped: dict[str, list[dict[str, Any]]] = {}
    for paper in papers:
        grouped.setdefault(paper["primary_axis"] or infer_axis(schema, paper["title"], paper["body"]), []).append(paper)
    lines = [
        "# Wiki Index",
        "",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 论文总数: {len(papers)}",
        "",
        "## 研究轴",
        "",
    ]
    for axis in [axis["key"] for axis in normalized_axes(schema)]:
        axis_papers = sorted(grouped.get(axis, []), key=lambda item: item["title"])
        lines.append(f"### {axis}")
        lines.append("")
        lines.append(f"- 论文数: {len(axis_papers)}")
        if axis_papers:
            for paper in axis_papers:
                note_path = relative_to_vault(vault_root, Path(str(paper["path"])))
                lines.append(f"- [[{note_path}|{paper['title']}]]")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def rewrite_conflicts_page(vault_root: Path, schema: dict[str, Any], papers: list[dict[str, Any]]) -> Path:
    ops_dir = schema_path(vault_root, schema, "ops_dir")
    path = ops_dir / "conflicts.md"
    lines = [
        "# Wiki Conflicts",
        "",
        "## 已登记冲突",
        "",
    ]
    conflict_count = 0
    for paper in sorted(papers, key=lambda item: item["title"]):
        text = section_text(paper["body"], "与既有结论的冲突")
        if not text:
            continue
        cleaned = normalize_whitespace(text.replace("-", " "))
        if not cleaned or cleaned in {"无", "暂无", "none"}:
            continue
        note_path = relative_to_vault(vault_root, Path(str(paper["path"])))
        lines.append(f"- [[{note_path}|{paper['title']}]]: {cleaned[:200]}")
        conflict_count += 1
    if conflict_count == 0:
        lines.append("- 当前没有已登记冲突。")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def repair_embeds(text: str, mapping: dict[str, str]) -> str:
    repaired = text
    for old_value, new_value in mapping.items():
        repaired = repaired.replace(old_value, new_value)
    return repaired


def move_path(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() == dest.resolve():
        return
    shutil.move(str(src), str(dest))


def prune_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    for directory in sorted((path for path in root.rglob("*") if path.is_dir()), reverse=True):
        try:
            next(directory.iterdir())
        except StopIteration:
            try:
                directory.rmdir()
            except OSError:
                continue
