# Changelog

## v1.0.0

First public release of Obsidian Wiki Maintainer as a standalone, domain-agnostic tool.

### Added

- Schema-driven wiki maintenance: backfill, ingest, search, lint, and index refresh
- Deterministic page generation for index, log, conflicts, topic, and entity pages
- Search index with cached raw-source fallback layer
- Query filing for persistent knowledge base entries
- Wikilink and embed repair during backfill migrations
- Frontmatter validation and stale-page detection

### Changed

- Removed hardcoded domain-specific (`citrus`) paths and filters
- Generalized `Research/Citrus/` to configurable `Research/` schema root
- Generalized schema markers from `CITRUS_WIKI_SCHEMA` to `WIKI_SCHEMA`

