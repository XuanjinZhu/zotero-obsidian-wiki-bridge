<div align="center">

# Obsidian Wiki Maintainer

**自动维护 Obsidian 研究维基的一致性、可搜索性和结构完整性。**

[English](./README.md) | [简体中文](./README.zh-CN.md)

[![License](https://img.shields.io/badge/license-MIT-c9a227)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-0f766e)](https://www.python.org/)

</div>

## 它能做什么

Obsidian Wiki Maintainer 是一套确定性的 Python 脚本，用于维护基于 schema 驱动的 Obsidian 研究维基。它自动化了那些容易忘记但后期修复代价昂贵的重复性维护工作：

- **自动索引**：保持 `index.md`、`log.md` 和 `conflicts.md` 实时更新
- **主题与实体页面**：自动生成和更新主题概览页及实体参考页
- **全文搜索**：构建本地搜索索引，支持原始数据源回退
- **质量检查 (Lint)**：捕获断链、孤立页面、缺失前置元数据、过期条目和未登记冲突
- **回填与迁移**：将旧笔记移入规范目录结构，并修复内嵌引用

它可与 [DeepPaperNote](../deeppapernote/) 自然配对使用——DeepPaperNote 写完论文笔记后，Wiki Maintainer 能自动更新所有索引页面。

## 依赖要求

| 组件 | 状态 | 说明 |
| --- | --- | --- |
| Python 3.10+ | 必需 | 运行辅助脚本 |
| Obsidian 库 | 必需 | 需遵循 schema 契约 (`Research/AGENTS.md`) |
| PyMuPDF | 可选 | 仅原始数据源 PDF 索引时需要 |

## 快速开始

### 1. 配置 Vault Schema

在你的 Obsidian vault 中创建 `Research/AGENTS.md`，包含 JSON schema 块：

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
    {"key": "methodology", "label": "方法论", "keywords": ["方法", "算法", "流程"]},
    {"key": "evaluation", "label": "评估", "keywords": ["基准", "指标", "评测"]}
  ],
  "required_paper_frontmatter": ["title", "primary_axis", "source_status", "tags"]
}
<!-- WIKI_SCHEMA_END -->
```

根据你的研究领域自定义 `axes` 列表。

### 2. 运行维护命令

```bash
# 回填旧笔记
python scripts/backfill_vault.py --vault /path/to/vault

# 添加新论文笔记后
python scripts/ingest_maintain.py --vault /path/to/vault --note /path/to/note.md

# 刷新搜索索引
python scripts/refresh_search_index.py --vault /path/to/vault

# 搜索维基
python scripts/query_wiki.py --vault /path/to/vault --query "你的问题"

# 沉淀有价查询结果
python scripts/file_query_result.py --vault /path/to/vault --query "..." --answer "..." --target-type topic --target-key methodology

# 检查维基质量
python scripts/lint_wiki.py --vault /path/to/vault
```

## 详细使用

### Schema 契约

`Research/AGENTS.md` 是唯一的配置来源。其内嵌的 JSON schema 定义：

- 目录路由（`papers_dir`、`topics_dir`、`entities_dir`、`ops_dir`）
- 研究轴（你研究的主题方向）
- 论文笔记必需的前置元数据字段
- 标签前缀约定

详见 [references/schema-contract.md](references/schema-contract.md)。

### 收录维护

创建新论文笔记（例如通过 DeepPaperNote）后运行：

```bash
python scripts/ingest_maintain.py --vault /path/to/vault --note path/to/paper.md
```

此命令会更新：
- 研究轴主题概览页
- 前置元数据中引用的实体页面
- `ops/index.md`（完整论文索引）
- `ops/log.md`（审计日志）
- `ops/conflicts.md`（已登记冲突）
- 本地搜索索引
- 笔记本身（自动相关页面栏目）

### 搜索

```bash
python scripts/query_wiki.py --vault /path/to/vault --query "你的问题" --top-k 10
```

搜索结果来自两层：
- `wiki_hits`：已维护的知识页面
- `raw_hits`：缓存的原始数据源证据（PDF 提取内容）

### 质量检查

```bash
python scripts/lint_wiki.py --vault /path/to/vault
```

检查项包括：
- 缺少必需的前置元数据
- 断开的 wikilink
- 孤立页面（无入站链接）
- 过期的 `source_status` 字段
- 重复的主题页面
- 未登记的冲突

### 查询沉淀

当搜索产生了有价值的洞察时，可将其持久化到知识库中：

```bash
python scripts/file_query_result.py \
  --vault /path/to/vault \
  --query "关键发现是什么？" \
  --answer "关键发现是..." \
  --target-type topic \
  --target-key methodology
```

## 仓库结构

```text
obsidian-wiki-maintainer/
├── SKILL.md                  # Codex skill 入口
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

## 二次开发

### 环境搭建

```bash
pip install -e '[dev]'
```

### 运行测试

```bash
python -m pytest -q
```

### 代码风格

```bash
ruff check scripts/ tests/
ruff format scripts/ tests/
```

## 未来扩展

- [ ] 多 vault 支持
- [ ] 增量搜索索引更新
- [ ] Web UI 仪表盘
- [ ] 基于 Git 的运维页面版本历史
- [ ] 自定义页面生成器插件系统
- [ ] Obsidian 插件封装（GUI 访问）

## License

MIT — 详见 [LICENSE](./LICENSE)。
