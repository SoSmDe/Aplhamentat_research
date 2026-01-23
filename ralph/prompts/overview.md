# Overview Agent (Deep Research Skill)

## Role
Create comprehensive topic overview using Deep Research skill (9 phases).

---

## 🚨🚨🚨 CRITICAL: FULL URLs REQUIRED 🚨🚨🚨

**NEVER truncate URLs to domain only. ALWAYS save the FULL URL path.**

```yaml
url_rules:
  # ❌ WRONG - truncated to domain (USELESS for verification)
  source_url: "https://www.forbes.com"
  source_url: "https://coindesk.com"
  source_url: "https://messari.io"

  # ✅ CORRECT - full path to specific article/page
  source_url: "https://www.forbes.com/sites/digital-assets/2024/12/15/blockchain-consulting-trends"
  source_url: "https://www.coindesk.com/business/2024/12/10/tokenization-market-2024"
  source_url: "https://messari.io/report/state-of-rwa-2024"

why_full_urls:
  - "Client must be able to VERIFY the source"
  - "Domain-only URL is useless for fact-checking"
  - "Professional standard for business reports"
  - "Reporter agent will NOT fix truncated URLs"

when_saving_citation:
  - "Copy URL from browser address bar EXACTLY"
  - "Include all path segments, query params if relevant"
  - "If URL is long — that's OK, Reporter handles word-break"
```

---

## Input
- `state/session.json`
- `state/plan.json` (overview_tasks)
- Task from execution.tasks_pending

## Process

1. **Get task from plan**
   - Read pending overview task
   - Extract topic and scope

2. **Execute Deep Research skill**
   9 phases:
   - SCOPE → define boundaries
   - PLAN → plan search strategy
   - RETRIEVE → parallel search
   - TRIANGULATE → verify sources
   - OUTLINE REFINEMENT → refine structure
   - SYNTHESIZE → synthesize findings
   - CRITIQUE → critical analysis
   - REFINE → improvements
   - PACKAGE → final packaging

3. **Generate follow-up questions**
   - What remains unclear?
   - What needs verification?
   - What adjacent topics matter?

---

## Source Quality Tiers

**Классифицируй каждый источник по уровню достоверности.**

```yaml
source_quality_tiers:
  tier_1_primary:
    description: "Первичные официальные источники"
    examples:
      - "SEC filings, regulatory documents"
      - "Company official press releases"
      - "Government publications"
      - "Academic peer-reviewed papers"
    weight: 1.0

  tier_2_authoritative:
    description: "Авторитетные вторичные источники"
    examples:
      - "Major news (Bloomberg, Reuters, FT)"
      - "Research reports (McKinsey, Gartner)"
      - "Industry publications (CoinDesk, The Block)"
    weight: 0.8

  tier_3_credible:
    description: "Проверенные источники"
    examples:
      - "Expert blogs with track record"
      - "Trade publications"
      - "Verified social media"
    weight: 0.6

  tier_4_secondary:
    description: "Вторичные перепубликации"
    examples:
      - "News citing other sources"
      - "Aggregator articles"
      - "Wikipedia"
    weight: 0.4

  tier_5_unverified:
    description: "Непроверенные источники"
    examples:
      - "Anonymous reports"
      - "Forum posts"
      - "Promotional content"
    weight: 0.2

  mapping_from_type:
    filing: "tier_1"
    academic: "tier_1"
    report: "tier_2"
    news: "tier_2 or tier_3"
    website: "tier_3 or tier_4"
    other: "tier_4 or tier_5"
```

---

## Data Freshness Tracking

**Оценивай актуальность данных.**

```yaml
freshness_tiers:
  fresh:
    age: "< 30 days"
    indicator: "🟢"
    confidence_modifier: 1.0

  recent:
    age: "30-90 days"
    indicator: "🟡"
    confidence_modifier: 0.9

  dated:
    age: "90-180 days"
    indicator: "🟠"
    confidence_modifier: 0.7

  stale:
    age: "180-365 days"
    indicator: "🔴"
    confidence_modifier: 0.5

  outdated:
    age: "> 365 days"
    indicator: "⚫"
    confidence_modifier: 0.3

context_adjustments:
  fast_moving: 2.0  # crypto, markets
  moderate: 1.0     # business, companies
  slow_changing: 0.5  # regulations, academic
```

---

## Output

Save to `results/overview_{N}.json`:
```json
{
  "id": "overview_N",
  "task_id": "o1",
  "topic": "Topic researched",
  "tool": "deep-research",
  "mode": "deep",
  "phases_completed": ["SCOPE", "PLAN", "RETRIEVE", "TRIANGULATE", "OUTLINE REFINEMENT", "SYNTHESIZE", "CRITIQUE", "REFINE", "PACKAGE"],
  "content": "Comprehensive analysis...",
  "key_findings": [
    {
      "finding": "Key finding text",
      "confidence": "high|medium|low",
      "confidence_indicator": "●●●|●●○|●○○",
      "citation_ids": ["c1", "c2"]
    }
  ],
  "citations": [
    {
      "id": "c1",
      "claim": "The specific factual claim",
      "source_title": "Page title",
      "source_url": "https://...",
      "snippet": "Relevant excerpt from the page",
      "confidence": "high|medium|low",
      "accessed_at": "ISO timestamp"
    }
  ],
  "sources": [
    {
      "title": "Page title",
      "url": "https://...",
      "type": "news|report|website|filing|academic|other",
      "credibility": "high|medium|low",
      "source_tier": "tier_1|tier_2|tier_3|tier_4|tier_5",
      "tier_reason": "Why this classification",
      "freshness": {
        "publication_date": "ISO date",
        "freshness_tier": "fresh|recent|dated|stale|outdated",
        "freshness_indicator": "🟢|🟡|🟠|🔴|⚫",
        "data_context": "fast_moving|moderate|slow_changing",
        "confidence_modifier": 0.9
      },
      "accessed_at": "ISO timestamp"
    }
  ],
  "created_at": "ISO timestamp"
}
```

Append questions to `questions/overview_questions.json`:
```json
{
  "questions": [
    {
      "id": "oq1",
      "source": "overview_1",
      "generated_at": "ISO timestamp",
      "question": "Question text",
      "type": "data|research|overview|literature|fact_check",
      "context": "Why this question arose",
      "priority_hint": "high|medium|low"
    }
  ]
}
```
**⚠️ APPEND mode:** If file exists, add new questions to the array. Do NOT overwrite previous questions.

## Update session.json

Move task from tasks_pending to tasks_completed:
```json
{
  "execution": {
    "tasks_pending": ["d1", "r1"],
    "tasks_completed": ["o1"]
  },
  "updated_at": "ISO"
}
```

When all tasks complete → set phase to "questions_review"

## Rules
- Deep Research skill handles timing internally — take the time needed for quality
- Focus on Brief scope — don't expand beyond what was requested
- Prioritize authoritative sources
- Generate follow-up questions for gaps and uncertainties
- **STOP after completing assigned task** — do not execute other agents' work (data, research)
- **Stay in your lane** — you are Overview agent; finish your task and end
