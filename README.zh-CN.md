<div align="center">

# Zotero-Obsidian-Wiki-Bridge

**从 Zotero 论文管理到 Obsidian 深度阅读笔记与维基维护的全流程自动化。**

[English](./README.md) | [简体中文](./README.zh-CN.md)

[![License](https://img.shields.io/badge/license-MIT-c9a227)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-0f766e)](https://www.python.org/)

</div>

## 项目简介

Zotero-Obsidian-Wiki-Bridge 将两个强大的 Codex 技能整合为一条无缝的研究工作流：

| 技能 | 角色 |
| --- | --- |
| **[DeepPaperNote](./deeppapernote/)** | 将单篇研究论文转化为高质量 Obsidian 深度阅读笔记：证据优先分析、图表占位、结构化排版 |
| **[Obsidian Wiki Maintainer](./obsidian-wiki-maintainer/)** | 维护 Obsidian 研究维基的一致性：自动索引、全文搜索、质量检查、回填迁移、主题/实体页面生成 |

两者结合，自动化了学术阅读和知识管理中最繁琐的环节——让你专注于真正的思考。

## 工作流

```
 PDF / DOI / arXiv / Zotero
         │
         ▼
   DeepPaperNote
   （证据收集、图表规划、笔记撰写、校验+复核）
         │
         ▼
   Obsidian Vault ──► Obsidian Wiki Maintainer
                      （索引更新、搜索刷新、冲突追踪）
```

## 快速开始

### 安装

每个技能可通过 Codex skill installer 独立安装：

```bash
npx skills add XuanjinZhu/zotero-obsidian-wiki-bridge/deeppapernote -a codex
npx skills add XuanjinZhu/zotero-obsidian-wiki-bridge/obsidian-wiki-maintainer -a codex
```

或克隆整个仓库直接使用脚本。

### 环境要求

- Python >= 3.10
- PyMuPDF（`pip install PyMuPDF`）—— DeepPaperNote 必需，Wiki Maintainer 可选
- Obsidian vault（推荐）
- 可选：Zotero 用于本地论文管理

### 生成论文笔记

在 Codex（或任何兼容 agent 环境）中调用 DeepPaperNote：

```
{给我这篇论文生成深度笔记
- DOI: 10.xxxx/xxxxx
```

### 维护你的维基

笔记写完后运行维护脚本：

```bash
python obsidian-wiki-maintainer/scripts/ingest_maintain.py \
  --vault /path/to/your/vault \
  --note /path/to/new/note.md
```

## 仓库结构

```text
zotero-obsidian-wiki-bridge/
├── README.md
├── README.zh-CN.md
├── LICENSE
├── .gitignore
├── deeppapernote/                 # 深度论文阅读技能
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
└── obsidian-wiki-maintainer/      # 维基维护技能
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

## 核心特性

### DeepPaperNote

- 证据优先的深度阅读流程（非摘要生成器）
- 模型主导理解：机制拆解、关键数字、公式、局限分析
- 图表占位优先策略——即使图像抽取不完整，也保留图表上下文
- Obsidian 原生输出：论文独立文件夹、Markdown 笔记、本地 `images/` 目录
- Zotero 集成，优先复用本地文献库
- 格式校验 + 最终可读性复核，写入前兜底

### Obsidian Wiki Maintainer

- Schema 驱动：一份 `Research/AGENTS.md` 定义整个维基布局
- 自动索引：`index.md`、`log.md`、`conflicts.md` 保持同步
- 全文搜索，支持原始数据源回退层
- 质量检查：断链、孤立页面、缺失前置元数据、过期条目
- 回填迁移：将旧笔记迁入规范目录结构
- 查询沉淀：将有价值的搜索结果持久化到主题/实体页面

## 二次开发

各技能的开发环境搭建、测试和贡献指南详见各自 README：

- [DeepPaperNote 开发](./deeppapernote/README.md#development)
- [Wiki Maintainer 开发](./obsidian-wiki-maintainer/README.md#development)

## 致谢

- **DeepPaperNote** 最初由 [dingdingcar](https://github.com/917Dhj/DeepPaperNote) 创建。本分支保留原始工作流，并将其整合到统一的 Zotero-Obsidian-Wiki-Bridge 项目中。
- 感谢 Obsidian 和 Zotero 社区构建了优秀的知识管理工具。

## License

MIT — 详见 [LICENSE](./LICENSE)。各子技能也均采用 MIT 许可。
