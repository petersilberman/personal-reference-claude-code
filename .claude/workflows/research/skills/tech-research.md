# Skill: Technology Research

## Purpose
Teaches how to effectively research technologies, tools, frameworks, and systems using Perplexity and Firecrawl MCP tools.

## When to Use
- Technology is discussed substantively (not just name-dropped)
- Understanding the tech is required to follow the content
- Technology represents a key capability being discussed
- Reader likely hasn't encountered this specific tool before

## When to SKIP
- Common tools everyone knows (Python, Git, React, PostgreSQL)
- Generic categories ("machine learning", "cloud computing")
- Technologies mentioned only as analogies
- Historical technologies referenced for context only

## Tool Selection

### Use Firecrawl When:
- You have the official documentation URL
- You need accurate, up-to-date technical details
- The technology has good official docs

```
mcp__firecrawl__firecrawl_scrape on https://docs.example.com
```

### Use Perplexity When:
- You don't have the official URL
- You need a quick overview
- Official docs are too technical for a summary

```
"[Technology Name]" what is it used for main features
```

## Query Patterns

### Perplexity Query Templates
```
"[Tech Name]" what is it overview purpose
"[Tech Name]" vs [alternative] when to use (if comparison needed)
"[Tech Name]" getting started main concepts
```

### Firecrawl Targets (in order of preference)
1. Official homepage (for overview)
2. Official "About" or "Introduction" page
3. Official documentation landing page
4. GitHub README (for open source)

## What to Extract

### Required (2-3 sentences total)
1. **What it IS** - Category (framework, tool, protocol, model, platform)
2. **What problem it solves** - Why does this exist?
3. **Why it's relevant HERE** - Connection to the content being summarized

### Do NOT Include
- Installation instructions
- Version history
- Pricing details
- Exhaustive feature lists
- Comparison matrices

## Output Format
```markdown
**[Technology Name]** — [What it is in one phrase]. [What problem it solves / key capability]. [Link to official site]
```

## Link Priority
1. Official homepage
2. Official documentation
3. GitHub repository (for OSS)
4. Wikipedia (for established tech)

Never link to:
- Blog posts about the technology
- Tutorial sites
- Comparison articles

## Quality Checklist
- [ ] Description is 2-3 sentences MAX
- [ ] Explains what it IS, not how to use it
- [ ] Connects to why it matters for this content
- [ ] Link is to official/primary source
- [ ] Accessible to CS generalist (no assumed deep expertise)

## Examples

**Input**: Research "LangGraph" mentioned in agent development content

**Query**: `"LangGraph" what is it LLM agents overview`

**Output**:
```markdown
**LangGraph** — A framework for building stateful, multi-actor LLM applications with cycles and controllability. It extends LangChain to enable complex agent workflows with persistence and human-in-the-loop patterns. [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/)
```

---

**Input**: Research "RLHF" mentioned in model training content

**Query**: `"RLHF" reinforcement learning human feedback what is it`

**Output**:
```markdown
**RLHF (Reinforcement Learning from Human Feedback)** — A training technique that fine-tunes language models using human preference data rather than explicit labels. It's the key method behind making models like ChatGPT more helpful and aligned with human intent. [OpenAI's InstructGPT paper](https://arxiv.org/abs/2203.02155)
```
