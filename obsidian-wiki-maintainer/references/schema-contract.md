# Schema Contract

The vault schema authority is the Markdown file at `Research/AGENTS.md`.

The file must contain a machine-readable JSON block between:

- `<!-- WIKI_SCHEMA_START -->`
- `<!-- WIKI_SCHEMA_END -->`

The JSON block must at least define:

- `knowledge_base_root`
- `papers_dir`
- `topics_dir`
- `entities_dir`
- `ops_dir`
- `cache_dir`
- `paper_tag_prefix`
- `default_axis`
- `axes`
- `required_paper_frontmatter`

Each axis record should contain:

- `key`
- `label`
- `keywords`
- optional `aliases`

The maintainer scripts treat this JSON block as the canonical routing, frontmatter, and search configuration.
