# Skill: Link Summarization

## Purpose
Teaches how to fetch and summarize linked content that would enhance the main summary. **Critical: ONE LEVEL RECURSION ONLY.**

## The One-Level Rule

```
ALLOWED:
Main Content → [Link A] → Summarize Link A ✓

NOT ALLOWED:
Main Content → [Link A] → [Link B in Link A] → Summarize Link B ✗
```

When you follow a link and summarize that page:
- ✓ Extract relevant information from that page
- ✓ Note key points that enrich the main summary  
- ✗ DO NOT follow any links found within that page
- ✗ DO NOT recursively fetch referenced content

**This rule is absolute. No exceptions.**

## When to Follow Links

### FOLLOW when:
- Link provides essential context for understanding a claim
- Link is to primary source of data/research being cited
- Link explains a concept central to the main argument
- Link is referenced as "see [X] for details" for something important

### SKIP when:
- Link is tangential or "for more information"
- Link is to generic resources (Wikipedia, documentation home)
- Link content would be redundant with the main content
- Link is behind paywall or requires authentication
- Link is to social media, video (can't be scraped effectively)

## Tool Usage

### Use Firecrawl
```
mcp__firecrawl__firecrawl_scrape with URL
```

Firecrawl returns parsed content. Extract what's relevant—don't try to summarize the entire page.

### Fallback: WebFetch
If Firecrawl unavailable:
```
WebFetch tool with URL
```

### If Fetch Fails
- Note "[Content unavailable]" 
- Do not make up or infer what the link contains
- Move on to next item

## What to Extract from Linked Content

### For Research/Papers
- Key finding or conclusion
- Methodology if relevant to understanding the finding
- Sample size / scope if it matters
- Publication date and source credibility

### For Blog Posts/Articles
- Main thesis or argument
- Key supporting points (max 3)
- Author credentials if relevant

### For Documentation/Technical Content
- What the thing DOES
- Why it's relevant to the main content
- Key capabilities mentioned in main content

### For Data/Statistics
- The actual numbers
- Source and date
- Methodology notes if they affect interpretation

## Output Format

```json
{
  "url": "https://...",
  "title": "Page title",
  "fetch_status": "success|failed|partial",
  "relevance_to_main": "Why this link matters for the summary",
  "key_points": [
    "Point 1 extracted from the page",
    "Point 2 extracted from the page"
  ],
  "integration_suggestion": "How to weave this into the main summary"
}
```

## Integration Guidelines

Don't create a separate "Links Summary" section. Instead:
- Weave relevant information naturally into the main summary
- Cite the source inline: "According to [linked research], ..."
- Add to glossary/people/tech sections if the link reveals relevant context

## Quality Checklist

- [ ] ONE LEVEL ONLY - no links from the linked page followed
- [ ] Only fetched links that genuinely enhance understanding
- [ ] Extracted only relevant portions, not full page summary
- [ ] Failed fetches noted, not fabricated
- [ ] Integration suggestion focuses on how this helps the READER

## Example

**Main content mentions**: "As shown in the Bitter Lesson essay..."

**Action**: Fetch http://www.incompleteideas.net/IncIdeas/BitterLesson.html

**Output**:
```json
{
  "url": "http://www.incompleteideas.net/IncIdeas/BitterLesson.html",
  "title": "The Bitter Lesson - Rich Sutton",
  "fetch_status": "success",
  "relevance_to_main": "Primary source for the 'bitter lesson' concept being discussed",
  "key_points": [
    "General methods that leverage computation beat specialized approaches as compute scales",
    "AI researchers repeatedly fail to learn this, rebuilding domain-specific solutions",
    "Search and learning are the two methods that scale indefinitely with compute"
  ],
  "integration_suggestion": "Define 'bitter lesson' in glossary using these points; reference Sutton as the source in the summary where this concept appears"
}
```

**What I did NOT do**: Follow any links within Sutton's essay to his other work.
