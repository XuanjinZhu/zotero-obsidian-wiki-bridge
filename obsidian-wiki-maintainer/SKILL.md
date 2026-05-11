---
name: obsidian-wiki-maintainer
description: "Maintain a schema-driven Obsidian research wiki backed by Zotero raw sources. Use when Codex needs to: (1) initialize or update a vault schema such as `Research/AGENTS.md`, (2) refresh or query a local wiki search index, (3) update index/log/conflict/topic/entity pages after a new note is added, (4) lint wiki consistency, backlinks, and frontmatter, or (5) backfill and migrate existing notes into the canonical vault layout."
---

# Obsidian Wiki Maintainer

## Overview

Use this skill to operate a long-lived Obsidian research wiki where Zotero is the raw-source layer and Obsidian is the maintained knowledge layer.

## Workflow

1. Read the vault schema from `Research/AGENTS.md`.
2. Use the schema as the only authority for directory routing, page types, frontmatter, and research axes.
3. Pick the correct script for the requested operation instead of improvising:
   - `scripts/backfill_vault.py`
   - `scripts/ingest_maintain.py`
   - `scripts/refresh_search_index.py`
   - `scripts/query_wiki.py`
   - `scripts/file_query_result.py`
   - `scripts/lint_wiki.py`
4. Prefer deterministic updates to `index.md`, `log.md`, `conflicts.md`, topic pages, and entity pages.
5. When answering questions, search the wiki first and read Zotero raw sources only when the query needs direct evidence, page-level details, or conflict resolution.

## Operation Guide

### Initialize or Migrate

- Use `scripts/backfill_vault.py` when the vault still contains legacy notes under `Research/Papers` or when schema files and ops pages do not exist yet.
- This script creates the canonical `Research/Citrus/` tree, migrates citrus notes into `papers/<axis>/`, repairs embeds, initializes topic pages, and refreshes the search index.

### Maintain After Ingest

- Use `scripts/ingest_maintain.py --note <path>` after a new paper note is created by `deeppapernote`.
- This updates:
  - the axis topic overview
  - entity pages named in frontmatter
  - `ops/index.md`
  - `ops/log.md`
  - `ops/conflicts.md`
  - the local search index

### Query the Wiki

- Use `scripts/query_wiki.py --query "<question>"`.
- Interpret the result in two layers:
  - `wiki_hits`: maintained knowledge pages
  - `raw_hits`: cached or recoverable raw-source evidence from Zotero attachments
- When `used_raw_layer` is `true`, distinguish maintained wiki conclusions from raw-source evidence in the final answer.

### File a High-Value Query

- Use `scripts/file_query_result.py` when a query answer should become part of the maintained wiki.
- File into:
  - a topic page when the conclusion belongs to an axis-level synthesis
  - an entity page when the conclusion belongs to a stable concept or object such as `细胞质遗传`
- This script appends a `查询沉淀` block with:
  - the question
  - the condensed answer
  - evidence lines from wiki hits and raw-source page hits
- The maintenance scripts preserve `查询沉淀` when topic and entity pages are regenerated.

### Lint the Wiki

- Use `scripts/lint_wiki.py` to inspect:
  - missing required frontmatter
  - broken wikilinks and embeds
  - orphan pages
  - stale `source_status`
  - duplicate topic pages
  - conflict pages not registered in `ops/conflicts.md`

## References

- Read [references/schema-contract.md](references/schema-contract.md) when editing `Research/AGENTS.md` or extending the schema.
