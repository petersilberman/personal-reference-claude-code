# Research Skills

This directory contains skills that teach effective research patterns using MCP tools.

## Available Skills

| Skill | File | Purpose |
|-------|------|---------|
| Person Research | `person-research.md` | How to research people via Perplexity |
| Technology Research | `tech-research.md` | How to research technologies via Perplexity/Firecrawl |
| Term Definition | `term-definition.md` | How to write accessible glossary entries |
| Link Summarization | `link-summarization.md` | How to summarize linked content (1 level max) |

## How Skills Work

Skills are **loaded into subagent context** when relevant. They provide:
- Query patterns for MCP tools
- Output format standards
- Quality criteria
- Common pitfalls to avoid

Skills do NOT execute actions. They teach HOW to execute well.

## Loading Skills

Subagents specify skills in their frontmatter:
```yaml
skills: person-research, tech-research
```

Or the orchestrator can instruct: "Load the person-research skill before researching [Name]"
