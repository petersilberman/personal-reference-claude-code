# Research Workflow

Shared research capabilities for content enrichment.

## Usage

Research agents and skills are invoked by other workflows (primarily `/summarize`).

## Agents

| Agent | Purpose |
|-------|---------|
| `executor.md` | Execute research TODO items using MCP tools |

## Skills

| Skill | Purpose |
|-------|---------|
| `SKILL.md` | Index and overview |
| `person-research.md` | How to research people via Perplexity |
| `tech-research.md` | How to research technologies |
| `term-definition.md` | How to write accessible glossary entries |
| `link-summarization.md` | How to summarize linked content (1 level max) |

## MCP Tools Used

- **Perplexity** - `mcp__perplexity__perplexity_ask` for general queries
- **Firecrawl** - `mcp__firecrawl__firecrawl_scrape` for web content
- **WebFetch** - Fallback for link fetching

## Critical Rules

1. **ONE-LEVEL RECURSION ONLY** - When fetching links, do NOT follow links found within fetched pages
2. **Graceful failures** - Note failures but don't fabricate information
3. **Load skills** - Always load relevant skill files before executing research
