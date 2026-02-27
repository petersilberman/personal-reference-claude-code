# Intelligent Content Summarizer

Orchestrates a multi-agent workflow to create educational summaries with research enrichment.

## Input
$ARGUMENTS

---

## PHASE 1: ANALYSIS & PLANNING

**Invoke subagent: `content:planner`**

```
Analyze this content completely. Create a structured research TODO list identifying:
- Terms needing definition
- People needing context  
- Technologies needing explanation
- Links worth following (for context enrichment)
- Quotes worth preserving

Cover the entire content—beginning, middle, AND end sections.
Output as structured JSON per your specification.

CONTENT:
[Paste or reference the input content]
```

**Wait for output: `research-plan.json`**

Store this plan—it guides all subsequent phases.

---

## PHASE 2: RESEARCH EXECUTION

**Invoke subagent: `research:executor`**

```
Execute this research plan using MCP tools.

CRITICAL RULES:
1. ONE-LEVEL RECURSION ONLY for links. Do NOT follow links found within fetched pages.
2. Load and follow the research skills for each category.
3. Note failures gracefully—do not fabricate.

RESEARCH PLAN:
[Pass the JSON from Phase 1]

Tools available:
- mcp__perplexity__perplexity_ask (for people, terms, tech overview)
- mcp__firecrawl__firecrawl_scrape (for links, tech docs)
- WebSearch, WebFetch (fallbacks)

Execute HIGH priority items first, then MEDIUM.
Output as structured JSON per your specification.
```

**Wait for output: `research-context.json`**

This contains all the enrichment data for the summary.

---

## PHASE 3: SYNTHESIS

**Invoke subagent: `content:summarizer`**

```
Write a flowing prose summary that educates the reader.

INPUTS:
1. Original content: [the full content]
2. Research context: [JSON from Phase 2]
3. Content plan: [JSON from Phase 1]

REQUIREMENTS:
- Write PROSE, not bullet points
- Organize by IMPORTANCE, not by order of appearance
- Integrate research naturally into the narrative
- Cover beginning/middle/end proportionally by importance
- Explain WHY ideas matter, not just WHAT they are

AUDIENCE: College graduate, CS background, general math/AI familiarity, NOT domain specialist.

Output the complete summary per your format specification.
```

**Wait for output: `draft-summary.md`**

---

## PHASE 4: VALIDATION

**Invoke subagent: `content:validator`**

```
Validate this summary for completeness and accuracy.

INPUTS:
1. Draft summary: [from Phase 3]
2. Original content: [for reference]
3. Research context: [from Phase 2]

TASKS:
1. Generate 5-7 comprehension questions (foundation, core argument, application, synthesis)
2. Check if summary enables answering each question
3. Identify gaps with specific revision guidance
4. Verify factual accuracy and research integration

Pass threshold: ≥80% of questions fully answerable.

Output validation report with revision guidance if needed.
```

**Check validation result:**

### If PASS:
Proceed to final assembly.

### If NEEDS REVISION:
Apply the specific revision guidance to `draft-summary.md`, then re-validate.
Maximum 2 revision cycles—if still failing, proceed with best effort and note limitations.

---

## PHASE 5: FINAL ASSEMBLY

Combine all outputs into the final deliverable:

```markdown
# [Descriptive Title Based on Content]

## TLDR

[2-3 sentences from the summary]

## Summary

[The full flowing prose summary from content-summarizer, with research integrated]

---

## Notable Quotes

> "[Exact quote 1]"
> — [Speaker]

> "[Exact quote 2]"
> — [Speaker]

[Only if quotes genuinely add value. Omit section entirely if none qualify.]

---

## Glossary

**[Term 1]**: [Definition contextualized to this content]

**[Term 2]**: [Definition contextualized to this content]

[Only terms essential for understanding. Omit if none needed.]

---

## People Mentioned

**[Name]** — [Bio]. [Link]

[Only people substantively discussed. Omit if none.]

---

## Technologies Referenced

**[Tech]** — [Description]. [Link]

[Only tech substantively discussed. Omit if none.]

---

## Sources Consulted

[List any links that were fetched and contributed to the summary]
```

---

## ERROR HANDLING

### If content-planner fails:
Proceed with basic analysis—extract obvious terms, people, tech manually.

### If research-executor fails partially:
Continue with successful lookups. Note "[Research unavailable]" for failed items.

### If MCP tools unavailable:
Fall back to WebSearch and WebFetch. Note reduced enrichment quality.

### If validation fails repeatedly:
Deliver best-effort summary with note: "This summary may have gaps in [specific areas]."

---

## QUALITY CHECKLIST (Before Delivery)

- [ ] Summary is flowing PROSE, not bullet points
- [ ] Ideas organized by IMPORTANCE, not appearance order
- [ ] Beginning/middle/end of content all represented
- [ ] Research integrated naturally, not bolted on
- [ ] Quotes are EXACT text
- [ ] Links followed ONE LEVEL ONLY
- [ ] Reader could explain these ideas to someone else
- [ ] Appropriate length for content complexity
