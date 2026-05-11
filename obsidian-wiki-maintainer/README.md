<div align="center">

# Obsidian Wiki Maintainer

**Keep your Obsidian research wiki consistent, searchable, and well-structured automatically.**

[English](./README.md) | [简体中文](./README.zh-CN.md)

[![License](https://img.shields.io/badge/license-MIT-c9a227)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-0f766e)](https://www.python.org/)

</div>

## What It Does

Obsidian Wiki Maintainer is a set of deterministic Python scripts that keep a schema-driven Obsidian research wiki in good shape. It automates the repetitive maintenance tasks that are easy to forget but expensive to fix later:

- **Auto-indexing**: keeps `index.md`, `log.md`, and `conflicts.md` up to date
- **Topic & entity pages**: auto-generates and updates topic overviews and entity reference pages
- **Full-text search**: builds a local search index with optional raw-source fallback
- **Linting**: catches broken wikilinks, orphan pages, missing frontmatter, stale entries, and unregistered conflicts
- **Backfill & migration**: moves legacy notes into the canonical directory layout and repairs embeds

It pairs naturally with [DeepPaperNote](../deeppapernote/) — after DeepPaperNote writes a paper note, Wiki Maintainer can automatically update all indices.

## Requirements

| Component | Status | Notes |
| --- | --- | --- |
| Python 3.10+ | Required | Runs the helper scripts |
| Obsidian vault | Required | Must follow the schema contract (`Research/AGENTS.md`) |
| PyMuPDF | Optional | Needed only for raw-source PDF indexing |

## Quick Start

### 1. Set up your vault schema

Create `Research/AGENTS.md` in your Obsidian vault with a JSON schema block:

```md
<!-- WIKI_SCHEMA_START -->
{
  "knowledge_base_root": "Research",
  "papers_dir": "Research/papers",
  "topics_dir": "Research/topics",
  "entities_dir": "Research/entities",
  "ops_dir": "Research/ops",
  "cache_dir": "Research/cache",
  "paper_tag_prefix": "papers",
  "default_axis": "inbox",
  "axes": [
    {"key": "methodology", "label": "Methodology", "keywords": ["method", "algorithm", "pipeline"]},
    {"key": "evaluation", "label": "Evaluation", "keywords": ["benchmark", "metric", "evaluation"]}
  ],
  "required_paper_frontmatter": ["title", "primary_axis", "source_status", "tags"]
}
<!-- WIKI_SCHEMA_END -->
```

Customize the `axes` list to match your research domains.

### 2. Run maintenance commands

```bash
# Backfill legacy notes
python scripts/backfill_vault.py --vault /path/to/vault

# After adding a new paper note
python scripts/ingest_maintain.py --vault /path/to/vault --note /path/to/note.md

# Refresh search index
python scripts/refresh_search_index.py --vault /path/to/vault

# Search the wiki
python scripts/query_wiki.py --vault /path/to/vault --query "your question"

# File a valuable query result
python scripts/file_query_result.py --vault /path/to/vault --query "..." --answer "..." --target-type topic --target-key methodology

# Lint the wiki
python scripts/lint_wiki.py --vault /path/to/vault
```

## Detailed Usage

### Schema Contract

The `Research/AGENTS.md` file is the single source of truth. Its embedded JSON schema defines:

- Directory routing (`papers_dir`, `topics_dir`, `entities_dir`, `ops_dir`)
- Research axes (topics you study)
- Required frontmatter keys for paper notes
- Tag prefix conventions

See [references/schema-contract.md](references/schema-contract.md) for the full specification.

### Ingest Maintenance

After creating a new paper note (e.g., via DeepPaperNote), run:

```bash
python scripts/ingest_maintain.py --vault /path/to/vault --note path/to/paper.md
```

This updates:
- The axis topic overview page
- Entity pages referenced in frontmatter
- `ops/index.md` (full paper index)
- `ops/log.md` (audit trail)
- `ops/conflicts.md` (registered conflicts)
- The local search index
- The note itself (auto-related pages section)

### Searching

```bash
python scripts/query_wiki.py --vault /path/to/vault --query "your question" --top-k 10
```

Results come from two layers:
- `wiki_hits`: maintained knowledge pages
- `raw_hits`: cached raw-source evidence (PDF extracts)

### Linting

```bash
python scripts/lint_wiki.py --vault /path/to/vault
```

Checks for:
- Missing required frontmatter
- Broken wikilinks
- Orphan pages (no inbound links)
- Stale `source_status` fields
- Duplicate topic pages
- Unregistered conflicts

### Query Filing

When a search yields a valuable insight, persist it into the knowledge base:

```bash
python scripts/file_query_result.py \
  --vault /path/to/vault \
  --query "what are the key findings?" \
  --answer "The key findings are..." \
  --target-type topic \
  --target-key methodology
```

## Repository Layout

```text
obsidian-wiki-maintainer/
├── SKILL.md                  # Codex skill entrypoint
├── README.md
├── README.zh-CN.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── agents/
│   └── openai.yaml
├── references/
│   └── schema-contract.md
├── scripts/
│   ├── backfill_vault.py
│   ├── common.py
│   ├── file_query_result.py
│   ├── ingest_maintain.py
│   ├── lint_wiki.py
│   ├── query_wiki.py
│   └── refresh_search_index.py
└── tests/
    └── test_common.py
```

## Development

### Setup

```bash
pip install -e '.[dev]'
```

### Running tests

```bash
python -m pytest -q
```

### Code style

```bash
ruff check scripts/ tests/
ruff format scripts/ tests/
```

## Future Extensions

- [ ] Multi-vault support
- [ ] Incremental search index updates
- [ ] Web UI dashboard
- [ ] Git-based version history for ops pages
- [ ] Plugin system for custom page generators
- [ ] Obsidian plugin wrapper for GUI access

## License

MIT — see [LICENSE](./LICENSE).
