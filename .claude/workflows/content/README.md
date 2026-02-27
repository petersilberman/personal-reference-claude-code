# Content Workflow

Intelligent content summarization with research enrichment.

## Command

```
/summarize [content or file path]
```

## Flow

```
/summarize command
       ↓
content:planner agent    →  research-plan.json
       ↓
research:executor agent  →  research-context.json
       ↓
content:summarizer agent →  draft-summary.md
       ↓
content:validator agent  →  validated summary
```

## Agents

| Agent | Purpose |
|-------|---------|
| `planner.md` | Analyze content, create research TODO list |
| `summarizer.md` | Write flowing prose summary |
| `validator.md` | Validate completeness, generate comprehension questions |

## Skills

Currently uses `research/skills/` for research execution.

## Notes

This workflow orchestrates multiple agents in sequence:
1. **Planning** - Identify what needs research (terms, people, tech, links)
2. **Research** - Execute research using MCP tools (Perplexity, Firecrawl)
3. **Synthesis** - Write educational prose organized by importance
4. **Validation** - Ensure summary answers comprehension questions
