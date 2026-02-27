# Skill: Term Definition

## Purpose
Teaches how to write accessible glossary entries for domain-specific terms that readers need to understand the summary.

## When to Use
- Term is essential to understanding the main argument
- Term would confuse a CS generalist
- Term is used in a specific technical sense
- Misunderstanding the term would cause confusion about key points

## When to SKIP
- Common CS terms (API, database, algorithm, function)
- Terms defined inline in the summary itself
- Terms that are self-explanatory in context
- Terms only mentioned once without importance

## Research Approach

### For Most Terms: Use Your Knowledge
Most domain terms don't need lookup—use training knowledge. Only search when:
- The term has a very specific technical meaning you're unsure of
- It's a recent/emerging concept (post-2023)
- It's highly field-specific jargon
- Context suggests a non-standard usage

### When Search IS Needed
```
Perplexity: "[Term]" definition meaning [field] context
```

## What to Include

### Structure (2-3 sentences total)
1. **Plain-language definition** - What does this MEAN?
2. **Context-specific usage** - How is it used in THIS content specifically?
3. **Brief example** (optional) - Only if it significantly aids understanding

### Writing Style
- Use analogies to familiar concepts when helpful
- Avoid defining jargon with more jargon
- Write for someone smart but unfamiliar with this specific field
- Be precise but accessible

## Output Format
```markdown
**[Term]**: [Plain-language definition]. [How it's used in this context]. [Example if helpful.]
```

## Quality Criteria

### Good Definition
- A reader could explain the term to someone else after reading
- No circular definitions (don't use the term to define itself)
- Doesn't assume knowledge of related specialized terms
- Connects to something the reader likely DOES know

### Bad Definition Signs
- "A type of X used in Y systems" (too abstract)
- Uses 3+ other technical terms in the definition
- Could apply to many different things (not specific enough)
- Longer than 3 sentences

## Examples

**Term**: "Attention mechanism" (in ML content)

**Bad**:
```markdown
**Attention mechanism**: A component in neural network architectures that computes weighted sums of value vectors based on query-key compatibility scores.
```

**Good**:
```markdown
**Attention mechanism**: A technique that lets AI models focus on relevant parts of their input, similar to how you'd scan a document looking for specific information rather than reading every word equally. In this content, it's discussed as the key innovation that made large language models practical.
```

---

**Term**: "Context window" (in LLM content)

**Good**:
```markdown
**Context window**: The maximum amount of text an AI model can "see" at once when generating a response—like the model's working memory. When this content discusses "context limits," it's referring to this constraint and strategies to work within it.
```

---

**Term**: "Epistemic uncertainty" (in ML safety content)

**Good**:
```markdown
**Epistemic uncertainty**: Uncertainty that comes from lack of knowledge (which could theoretically be reduced with more data), as opposed to inherent randomness. The author uses this to distinguish between "the model doesn't know" vs "the outcome is genuinely unpredictable."
```

## Checklist Before Finalizing
- [ ] Would a CS grad understand this without further lookup?
- [ ] Is it specific to how the term is used HERE?
- [ ] Is it 2-3 sentences max?
- [ ] Does it avoid circular definitions?
- [ ] Is jargon in the definition itself explained or avoided?
