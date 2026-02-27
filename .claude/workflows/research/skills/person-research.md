# Skill: Person Research

## Purpose
Teaches how to effectively research people mentioned in content using Perplexity MCP.

## When to Use
- Person is cited as an authority or source
- Person made claims being discussed
- Person's credentials are relevant to evaluating content
- Person is NOT just mentioned in passing pleasantries

## Query Patterns for Perplexity

### Primary Query Template
```
"[Full Name]" [affiliation if known] background expertise contributions
```

### Fallback Queries (if primary returns weak results)
```
"[Full Name]" [field/industry] work
"[Full Name]" [company/university] role
```

### Query Anti-Patterns (AVOID)
- ❌ Just the name alone (too ambiguous)
- ❌ Adding "biography" (returns Wikipedia-style fluff)
- ❌ Adding "net worth" or personal details (irrelevant)

## What to Extract

### Required (2-3 sentences total)
1. **Current role/affiliation** - Where do they work? What's their title?
2. **Relevant expertise** - Why are they credible on THIS topic?
3. **One notable contribution** - What have they done that matters here?

### Do NOT Include
- Full career history
- Personal life details
- Awards/honors (unless directly relevant)
- Net worth, age, etc.
- Anything not helping understand why they're cited

## Output Format
```markdown
**[Full Name]** — [Current role at Organization]. [1-2 sentences on relevant expertise]. [Link]
```

## Link Priority
1. Personal website or blog (most authoritative)
2. Institution faculty/team page
3. Wikipedia (if notable figure)
4. LinkedIn (last resort, often paywalled)
5. If no good link found, omit rather than link to random article

## Quality Checklist
- [ ] Description is 2-3 sentences MAX
- [ ] Focuses on relevance to content topic
- [ ] Link goes to primary source, not news article about them
- [ ] No speculation or inference beyond what Perplexity returns

## Example

**Input**: Research "Andrej Karpathy" mentioned in ML content

**Query**: `"Andrej Karpathy" AI deep learning background expertise`

**Output**:
```markdown
**Andrej Karpathy** — Former Director of AI at Tesla and founding member of OpenAI. Known for his educational work on neural networks and his development of key architectures at Tesla's Autopilot. [karpathy.ai](https://karpathy.ai)
```
