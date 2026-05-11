<div align="center">

# Zotero-Obsidian-Wiki-Bridge

**End-to-end automation: from Zotero paper management to Obsidian deep-reading notes and wiki maintenance.**

[English](./README.md) | [简体中文](./README.zh-CN.md)

[![License](https://img.shields.io/badge/license-MIT-c9a227)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-0f766e)](https://www.python.org/)

</div>

## Overview

Zotero-Obsidian-Wiki-Bridge connects two powerful Codex skills into one seamless research workflow:

| Skill | Role |
| --- | --- |
| **[DeepPaperNote](./deeppapernote/)** | Turns a single research paper into a high-quality Obsidian deep-reading note with evidence-first analysis, figure placeholders, and structured formatting |
| **[Obsidian Wiki Maintainer](./obsidian-wiki-maintainer/)** | Keeps your Obsidian research wiki consistent: auto-indexes, full-text search, linting, backfill, and topic/entity page generation |

Together they automate the most tedious parts of academic reading and knowledge management — so you can focus on thinking.

## Workflow

```
 PDF / DOI / arXiv / Zotero
         │
         ▼
   DeepPaperNote
   (evidence gathering, figure planning, note writing, lint + review)
         │
         ▼
   Obsidian Vault ──► Obsidian Wiki Maintainer
                      (index update, search refresh, conflict tracking)
```

## Quick Start

### Installation

Each skill can be installed independently via Codex skill installer:

```bash
npx skills add XuanjinZhu/zotero-obsidian-wiki-bridge/deeppapernote -a codex
npx skills add XuanjinZhu/zotero-obsidian-wiki-bridge/obsidian-wiki-maintainer -a codex
```

Or clone the entire repository and use the scripts directly.

### Prerequisites

- Python >= 3.10
- PyMuPDF (`pip install PyMuPDF`) — required for DeepPaperNote, optional for Wiki Maintainer
- An Obsidian vault (recommended)
- Optional: Zotero for local paper management

### Generate a Paper Note

Within Codex (or any compatible agent environment), invoke DeepPaperNote:

```
{给我这篇论文生成深度笔记
- DOI: 10.xxxx/xxxxx
```

### Maintain Your Wiki

After notes are written, run the maintainer:

```bash
python obsidian-wiki-maintainer/scripts/ingest_maintain.py \
  --vault /path/to/your/vault \
  --note /path/to/new/note.md
```

## Repository Structure

```text
zotero-obsidian-wiki-bridge/
├── README.md
├── README.zh-CN.md
├── LICENSE
├── .gitignore
├── deeppapernote/                 # Deep paper reading skill
│   ├── SKILL.md
│   ├── README.md / README.zh-CN.md
│   ├── CHANGELOG.md
│   ├── LICENSE
│   ├── pyproject.toml
│   ├── agents/openai.yaml
│   ├── assets/
│   ├── references/
│   ├── scripts/
│   └── tests/
└── obsidian-wiki-maintainer/      # Wiki maintenance skill
    ├── SKILL.md
    ├── README.md / README.zh-CN.md
    ├── CHANGELOG.md
    ├── LICENSE
    ├── pyproject.toml
    ├── agents/openai.yaml
    ├── references/
    ├── scripts/
    └── tests/
```

## Key Features

### DeepPaperNote

- Evidence-first deep reading pipeline (not a summary generator)
- Model-led understanding: mechanism breakdown, key numbers, formulas, limitations
- Placeholder-first figure strategy — preserves figure context even when extraction is partial
- Obsidian-native output: paper-specific folder, Markdown note, local `images/` directory
- Zotero integration for local-library-first paper resolution
- Lint gate + final readability review before save

### Obsidian Wiki Maintainer

- Schema-driven: single `Research/AGENTS.md` defines your entire wiki layout
- Auto-indexing: `index.md`, `log.md`, `conflicts.md` kept in sync
- Full-text search with raw-source fallback layer
- Lint checks: broken links, orphans, missing frontmatter, stale entries
- Backfill: migrate legacy notes into canonical directory structure
- Query filing: persist valuable search insights into topic/entity pages

## Development

See each skill's own README for development setup, testing, and contribution guidelines.

- [DeepPaperNote Development](./deeppapernote/README.md#development)
- [Wiki Maintainer Development](./obsidian-wiki-maintainer/README.md#development)

## Acknowledgments

- **DeepPaperNote** was originally created by [dingdingcar](https://github.com/917Dhj/DeepPaperNote). This fork preserves the original workflow and adapts it into the unified Zotero-Obsidian-Wiki-Bridge project.
- Thanks to the Obsidian and Zotero communities for building excellent knowledge management tools.

## License

MIT — see [LICENSE](./LICENSE). Each sub-skill also carries its own MIT license.
