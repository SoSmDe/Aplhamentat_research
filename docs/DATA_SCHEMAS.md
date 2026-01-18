# DATA_SCHEMAS.md

JSON Schema и TypeScript типы для всех структур данных Ralph Deep Research.

---

## Содержание

1. [Session](#1-session)
2. [InitialContext](#2-initialcontext)
3. [Brief](#3-brief)
4. [Plan](#4-plan)
5. [Task & Result](#5-task--result)
6. [PlannerDecision](#6-plannerdecision)
7. [AggregatedResearch](#7-aggregatedresearch)
8. [ReportConfig](#8-reportconfig)

---

## 1. Session

Контейнер состояния исследовательского workflow.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "session.json",
  "title": "Session",
  "description": "Research session state container",
  "type": "object",
  "required": ["id", "user_id", "status", "created_at", "updated_at"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^sess_[a-zA-Z0-9]{8,}$",
      "description": "Unique session identifier"
    },
    "user_id": {
      "type": "string",
      "description": "User who owns this session"
    },
    "status": {
      "type": "string",
      "enum": ["initial_research", "brief", "planning", "executing", "aggregating", "reporting", "done", "failed"],
      "description": "Current session state"
    },
    "initial_context": {
      "$ref": "initial_context.json",
      "description": "Result of Initial Research phase"
    },
    "brief": {
      "$ref": "brief.json",
      "description": "Approved research specification"
    },
    "current_round": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10,
      "default": 0,
      "description": "Current research round number"
    },
    "plans": {
      "type": "array",
      "items": { "$ref": "plan.json" },
      "description": "Plans for each round"
    },
    "data_results": {
      "type": "array",
      "items": { "$ref": "data_result.json" },
      "description": "All Data agent results"
    },
    "research_results": {
      "type": "array",
      "items": { "$ref": "research_result.json" },
      "description": "All Research agent results"
    },
    "aggregated_research": {
      "$ref": "aggregated_research.json",
      "description": "Final synthesized research"
    },
    "reports": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "format": { "type": "string", "enum": ["pdf", "excel", "pptx", "csv"] },
          "file_path": { "type": "string" },
          "url": { "type": "string", "format": "uri" }
        }
      }
    },
    "error": {
      "type": "object",
      "properties": {
        "code": { "type": "string" },
        "message": { "type": "string" },
        "details": { "type": "object" }
      }
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### TypeScript

```typescript
type SessionStatus =
  | "initial_research"
  | "brief"
  | "planning"
  | "executing"
  | "aggregating"
  | "reporting"
  | "done"
  | "failed";

interface Session {
  id: string;                              // sess_abc123
  user_id: string;
  status: SessionStatus;
  initial_context?: InitialContext;
  brief?: Brief;
  current_round: number;
  plans: Plan[];
  data_results: DataResult[];
  research_results: ResearchResult[];
  aggregated_research?: AggregatedResearch;
  reports: ReportFile[];
  error?: SessionError;
  created_at: string;                      // ISO 8601
  updated_at: string;
}

interface ReportFile {
  format: "pdf" | "excel" | "pptx" | "csv";
  file_path: string;
  url: string;
}

interface SessionError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
```

---

## 2. InitialContext

Результат первичного исследования (Initial Research Agent).

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "initial_context.json",
  "title": "InitialContext",
  "description": "Result of Initial Research phase",
  "type": "object",
  "required": ["session_id", "query_analysis", "entities", "context_summary"],
  "properties": {
    "session_id": {
      "type": "string"
    },
    "query_analysis": {
      "type": "object",
      "required": ["original_query", "detected_language", "detected_intent"],
      "properties": {
        "original_query": {
          "type": "string",
          "description": "User's raw input"
        },
        "detected_language": {
          "type": "string",
          "enum": ["ru", "en"],
          "description": "Detected query language"
        },
        "detected_intent": {
          "type": "string",
          "enum": ["investment", "market_research", "competitive", "learning", "other"],
          "description": "Detected user intent"
        },
        "confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Confidence score for intent detection"
        }
      }
    },
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "type"],
        "properties": {
          "name": {
            "type": "string",
            "description": "Entity name (company, concept, etc.)"
          },
          "type": {
            "type": "string",
            "enum": ["company", "market", "concept", "product", "person", "sector"]
          },
          "identifiers": {
            "type": "object",
            "properties": {
              "ticker": { "type": ["string", "null"] },
              "website": { "type": ["string", "null"], "format": "uri" },
              "country": { "type": ["string", "null"] },
              "exchange": { "type": ["string", "null"] }
            }
          },
          "brief_description": {
            "type": "string",
            "maxLength": 500
          },
          "category": { "type": "string" },
          "sector": { "type": ["string", "null"] }
        }
      }
    },
    "context_summary": {
      "type": "string",
      "description": "3-5 sentence overview of the topic",
      "maxLength": 1000
    },
    "suggested_topics": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Suggested research topics"
    },
    "sources_used": {
      "type": "array",
      "items": { "type": "string", "format": "uri" }
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### TypeScript

```typescript
type UserIntent = "investment" | "market_research" | "competitive" | "learning" | "other";
type EntityType = "company" | "market" | "concept" | "product" | "person" | "sector";

interface InitialContext {
  session_id: string;
  query_analysis: {
    original_query: string;
    detected_language: "ru" | "en";
    detected_intent: UserIntent;
    confidence: number;
  };
  entities: Entity[];
  context_summary: string;
  suggested_topics: string[];
  sources_used: string[];
  created_at: string;
}

interface Entity {
  name: string;
  type: EntityType;
  identifiers: {
    ticker?: string | null;
    website?: string | null;
    country?: string | null;
    exchange?: string | null;
  };
  brief_description: string;
  category: string;
  sector?: string | null;
}
```

---

## 3. Brief

Утверждённое техническое задание на исследование.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "brief.json",
  "title": "Brief",
  "description": "Approved research specification",
  "type": "object",
  "required": ["brief_id", "version", "status", "goal", "scope", "output_formats"],
  "properties": {
    "brief_id": {
      "type": "string",
      "pattern": "^brief_[a-zA-Z0-9]{8,}$"
    },
    "version": {
      "type": "integer",
      "minimum": 1,
      "description": "Brief version number (increments on user edits)"
    },
    "status": {
      "type": "string",
      "enum": ["draft", "approved"],
      "description": "Brief approval status"
    },
    "goal": {
      "type": "string",
      "minLength": 10,
      "maxLength": 500,
      "description": "Clear research objective"
    },
    "user_context": {
      "type": "object",
      "properties": {
        "intent": {
          "type": "string",
          "enum": ["investment", "market_research", "competitive", "learning", "due_diligence"]
        },
        "horizon": {
          "type": ["string", "null"],
          "description": "Time horizon (e.g., '5+ years', 'short-term')"
        },
        "risk_profile": {
          "type": ["string", "null"],
          "enum": ["conservative", "moderate", "aggressive", null]
        },
        "budget": {
          "type": ["string", "null"]
        },
        "additional": {
          "type": "object",
          "additionalProperties": true,
          "description": "Any additional context from user"
        }
      }
    },
    "scope": {
      "type": "array",
      "minItems": 1,
      "maxItems": 10,
      "items": { "$ref": "#/$defs/scope_item" },
      "description": "Topics to be researched"
    },
    "output_formats": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "enum": ["pdf", "excel", "pptx", "csv"]
      },
      "uniqueItems": true
    },
    "constraints": {
      "type": "object",
      "properties": {
        "focus_areas": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Areas to prioritize"
        },
        "exclude": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Topics to exclude"
        },
        "time_period": {
          "type": ["string", "null"],
          "description": "Time period for data (e.g., 'last 5 years')"
        },
        "geographic_focus": {
          "type": ["string", "null"]
        },
        "max_sources": {
          "type": "integer",
          "minimum": 1
        }
      }
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "approved_at": {
      "type": ["string", "null"],
      "format": "date-time"
    }
  },
  "$defs": {
    "scope_item": {
      "type": "object",
      "required": ["id", "topic", "type"],
      "properties": {
        "id": {
          "type": "integer",
          "minimum": 1
        },
        "topic": {
          "type": "string",
          "minLength": 3,
          "maxLength": 200
        },
        "type": {
          "type": "string",
          "enum": ["data", "research", "both"],
          "description": "data = quantitative, research = qualitative, both = mixed"
        },
        "details": {
          "type": ["string", "null"],
          "maxLength": 500,
          "description": "Additional details about what to cover"
        },
        "priority": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "default": "medium"
        }
      }
    }
  }
}
```

### TypeScript

```typescript
type BriefStatus = "draft" | "approved";
type ScopeType = "data" | "research" | "both";
type Priority = "high" | "medium" | "low";
type RiskProfile = "conservative" | "moderate" | "aggressive";
type OutputFormat = "pdf" | "excel" | "pptx" | "csv";

interface Brief {
  brief_id: string;                        // brief_abc123
  version: number;
  status: BriefStatus;
  goal: string;
  user_context: UserContext;
  scope: ScopeItem[];
  output_formats: OutputFormat[];
  constraints?: BriefConstraints;
  created_at: string;
  approved_at?: string | null;
}

interface UserContext {
  intent: UserIntent | "due_diligence";
  horizon?: string | null;
  risk_profile?: RiskProfile | null;
  budget?: string | null;
  additional?: Record<string, unknown>;
}

interface ScopeItem {
  id: number;
  topic: string;
  type: ScopeType;
  details?: string | null;
  priority?: Priority;
}

interface BriefConstraints {
  focus_areas?: string[];
  exclude?: string[];
  time_period?: string | null;
  geographic_focus?: string | null;
  max_sources?: number;
}
```

---

## 4. Plan

План исследования на один раунд.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "plan.json",
  "title": "Plan",
  "description": "Research plan for a single round",
  "type": "object",
  "required": ["round", "brief_id", "data_tasks", "research_tasks"],
  "properties": {
    "round": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10
    },
    "brief_id": {
      "type": "string"
    },
    "data_tasks": {
      "type": "array",
      "items": { "$ref": "data_task.json" }
    },
    "research_tasks": {
      "type": "array",
      "items": { "$ref": "research_task.json" }
    },
    "total_tasks": {
      "type": "integer",
      "description": "Computed: data_tasks.length + research_tasks.length"
    },
    "estimated_duration_seconds": {
      "type": "integer",
      "description": "Estimated time to complete this round"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### TypeScript

```typescript
interface Plan {
  round: number;
  brief_id: string;
  data_tasks: DataTask[];
  research_tasks: ResearchTask[];
  total_tasks: number;
  estimated_duration_seconds?: number;
  created_at: string;
}
```

---

## 5. Task & Result

### 5.1 DataTask

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "data_task.json",
  "title": "DataTask",
  "description": "Task for Data Agent",
  "type": "object",
  "required": ["id", "scope_item_id", "description", "source"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^d[0-9]+$",
      "description": "Task ID (e.g., d1, d2)"
    },
    "scope_item_id": {
      "type": "integer",
      "description": "Reference to Brief scope item"
    },
    "description": {
      "type": "string",
      "minLength": 10,
      "maxLength": 500,
      "description": "What data to collect"
    },
    "source": {
      "type": "string",
      "enum": ["financial_api", "web_search", "custom_api", "database"],
      "description": "Data source type"
    },
    "priority": {
      "type": "string",
      "enum": ["high", "medium", "low"],
      "default": "medium"
    },
    "expected_output": {
      "type": "string",
      "description": "Description of expected data"
    },
    "parameters": {
      "type": "object",
      "additionalProperties": true,
      "description": "API-specific parameters"
    }
  }
}
```

### 5.2 DataResult

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "data_result.json",
  "title": "DataResult",
  "description": "Result from Data Agent",
  "type": "object",
  "required": ["task_id", "status"],
  "properties": {
    "task_id": {
      "type": "string"
    },
    "round": {
      "type": "integer"
    },
    "status": {
      "type": "string",
      "enum": ["done", "failed", "partial"]
    },
    "output": {
      "type": "object",
      "properties": {
        "metrics": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "value": {},
              "unit": { "type": ["string", "null"] },
              "period": { "type": ["string", "null"] },
              "as_of_date": { "type": "string", "format": "date" }
            }
          }
        },
        "tables": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "headers": { "type": "array", "items": { "type": "string" } },
              "rows": { "type": "array", "items": { "type": "array" } }
            }
          }
        },
        "raw_data": {
          "type": "object",
          "additionalProperties": true
        }
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "source": { "type": "string" },
        "api_used": { "type": "string" },
        "timestamp": { "type": "string", "format": "date-time" },
        "data_freshness": {
          "type": "string",
          "enum": ["real-time", "daily", "weekly", "monthly", "quarterly", "annual"]
        }
      }
    },
    "questions": {
      "type": "array",
      "items": { "$ref": "question.json" }
    },
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": { "type": "string" },
          "error": { "type": "string" },
          "fallback": { "type": ["string", "null"] }
        }
      }
    },
    "completed_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### 5.3 ResearchTask

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "research_task.json",
  "title": "ResearchTask",
  "description": "Task for Research Agent",
  "type": "object",
  "required": ["id", "scope_item_id", "description"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^r[0-9]+$",
      "description": "Task ID (e.g., r1, r2)"
    },
    "scope_item_id": {
      "type": "integer"
    },
    "description": {
      "type": "string",
      "minLength": 10,
      "maxLength": 500
    },
    "focus": {
      "type": "string",
      "description": "What to focus on"
    },
    "source_types": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["news", "reports", "company_website", "analyst_reports", "sec_filings", "academic", "social_media"]
      }
    },
    "priority": {
      "type": "string",
      "enum": ["high", "medium", "low"],
      "default": "medium"
    },
    "search_queries": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Suggested search queries"
    }
  }
}
```

### 5.4 ResearchResult

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "research_result.json",
  "title": "ResearchResult",
  "description": "Result from Research Agent",
  "type": "object",
  "required": ["task_id", "status"],
  "properties": {
    "task_id": {
      "type": "string"
    },
    "round": {
      "type": "integer"
    },
    "status": {
      "type": "string",
      "enum": ["done", "failed", "partial"]
    },
    "output": {
      "type": "object",
      "properties": {
        "summary": {
          "type": "string",
          "maxLength": 500
        },
        "key_findings": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "finding": { "type": "string" },
              "type": { "type": "string", "enum": ["fact", "opinion", "analysis"] },
              "confidence": { "type": "string", "enum": ["high", "medium", "low"] },
              "source": { "type": "string" }
            }
          }
        },
        "detailed_analysis": {
          "type": "string"
        },
        "themes": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "theme": { "type": "string" },
              "points": { "type": "array", "items": { "type": "string" } },
              "sentiment": { "type": "string", "enum": ["positive", "negative", "neutral", "mixed"] }
            }
          }
        },
        "contradictions": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "topic": { "type": "string" },
              "view_1": { "type": "object" },
              "view_2": { "type": "object" }
            }
          }
        }
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": { "type": "string", "enum": ["news", "report", "website", "filing", "academic", "other"] },
          "title": { "type": "string" },
          "url": { "type": "string", "format": "uri" },
          "date": { "type": "string", "format": "date" },
          "credibility": { "type": "string", "enum": ["high", "medium", "low"] }
        }
      }
    },
    "questions": {
      "type": "array",
      "items": { "$ref": "question.json" }
    },
    "completed_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### 5.5 Question

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "question.json",
  "title": "Question",
  "description": "Follow-up question generated by agents",
  "type": "object",
  "required": ["type", "question"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["data", "research"],
      "description": "Which agent should handle this"
    },
    "question": {
      "type": "string",
      "minLength": 5,
      "maxLength": 300
    },
    "source_task_id": {
      "type": "string",
      "description": "Task that generated this question"
    },
    "context": {
      "type": "string",
      "description": "Why this question arose"
    },
    "priority": {
      "type": "string",
      "enum": ["high", "medium", "low"],
      "default": "medium"
    }
  }
}
```

### TypeScript Types

```typescript
// Data Agent Types
interface DataTask {
  id: string;                              // d1, d2, etc.
  scope_item_id: number;
  description: string;
  source: "financial_api" | "web_search" | "custom_api" | "database";
  priority: Priority;
  expected_output?: string;
  parameters?: Record<string, unknown>;
}

interface DataResult {
  task_id: string;
  round: number;
  status: "done" | "failed" | "partial";
  output: {
    metrics: Record<string, MetricValue>;
    tables: DataTable[];
    raw_data?: Record<string, unknown>;
  };
  metadata: {
    source: string;
    api_used: string;
    timestamp: string;
    data_freshness: DataFreshness;
  };
  questions: Question[];
  errors: DataError[];
  completed_at: string;
}

interface MetricValue {
  value: number | string | null;
  unit?: string | null;
  period?: string | null;
  as_of_date: string;
}

interface DataTable {
  name: string;
  headers: string[];
  rows: (string | number | null)[][];
}

type DataFreshness = "real-time" | "daily" | "weekly" | "monthly" | "quarterly" | "annual";

interface DataError {
  field: string;
  error: string;
  fallback?: string | null;
}

// Research Agent Types
type SourceType = "news" | "reports" | "company_website" | "analyst_reports" | "sec_filings" | "academic" | "social_media";

interface ResearchTask {
  id: string;                              // r1, r2, etc.
  scope_item_id: number;
  description: string;
  focus?: string;
  source_types: SourceType[];
  priority: Priority;
  search_queries?: string[];
}

interface ResearchResult {
  task_id: string;
  round: number;
  status: "done" | "failed" | "partial";
  output: {
    summary: string;
    key_findings: Finding[];
    detailed_analysis: string;
    themes: Theme[];
    contradictions: Contradiction[];
  };
  sources: Source[];
  questions: Question[];
  completed_at: string;
}

interface Finding {
  finding: string;
  type: "fact" | "opinion" | "analysis";
  confidence: "high" | "medium" | "low";
  source: string;
}

interface Theme {
  theme: string;
  points: string[];
  sentiment: "positive" | "negative" | "neutral" | "mixed";
}

interface Contradiction {
  topic: string;
  view_1: { position: string; source: string };
  view_2: { position: string; source: string };
}

interface Source {
  type: "news" | "report" | "website" | "filing" | "academic" | "other";
  title: string;
  url: string;
  date: string;
  credibility: "high" | "medium" | "low";
}

// Question
interface Question {
  type: "data" | "research";
  question: string;
  source_task_id?: string;
  context?: string;
  priority: Priority;
}
```

---

## 6. PlannerDecision

Решение Planner после ревью раунда.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "planner_decision.json",
  "title": "PlannerDecision",
  "description": "Planner's review decision after a round",
  "type": "object",
  "required": ["round", "status", "coverage", "overall_coverage"],
  "properties": {
    "round": {
      "type": "integer",
      "description": "Round number being reviewed"
    },
    "status": {
      "type": "string",
      "enum": ["continue", "done"],
      "description": "Whether to continue researching or move to aggregation"
    },
    "coverage": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "topic": { "type": "string" },
          "coverage_percent": { "type": "number", "minimum": 0, "maximum": 100 },
          "covered_aspects": { "type": "array", "items": { "type": "string" } },
          "missing_aspects": { "type": "array", "items": { "type": "string" } }
        }
      },
      "description": "Coverage assessment per scope item"
    },
    "overall_coverage": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Average coverage across all scope items"
    },
    "reason": {
      "type": "string",
      "description": "Explanation for the decision"
    },
    "new_data_tasks": {
      "type": "array",
      "items": { "$ref": "data_task.json" },
      "description": "New tasks for Data agent (if continue)"
    },
    "new_research_tasks": {
      "type": "array",
      "items": { "$ref": "research_task.json" },
      "description": "New tasks for Research agent (if continue)"
    },
    "filtered_questions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "question": { "type": "string" },
          "source_task_id": { "type": "string" },
          "relevance": { "type": "string", "enum": ["high", "medium", "low"] },
          "action": { "type": "string", "enum": ["add", "skip"] },
          "reasoning": { "type": "string" }
        }
      },
      "description": "Questions from agents with filter decisions"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### TypeScript

```typescript
interface PlannerDecision {
  round: number;
  status: "continue" | "done";
  coverage: Record<string, CoverageAssessment>;
  overall_coverage: number;
  reason: string;
  new_data_tasks: DataTask[];
  new_research_tasks: ResearchTask[];
  filtered_questions: FilteredQuestion[];
  created_at: string;
}

interface CoverageAssessment {
  topic: string;
  coverage_percent: number;
  covered_aspects: string[];
  missing_aspects: string[];
}

interface FilteredQuestion {
  question: string;
  source_task_id: string;
  relevance: "high" | "medium" | "low";
  action: "add" | "skip";
  reasoning: string;
}
```

---

## 7. AggregatedResearch

Финальный синтезированный результат исследования.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "aggregated_research.json",
  "title": "AggregatedResearch",
  "description": "Final synthesized research document",
  "type": "object",
  "required": ["session_id", "brief_id", "executive_summary", "sections", "recommendation"],
  "properties": {
    "session_id": { "type": "string" },
    "brief_id": { "type": "string" },
    "created_at": { "type": "string", "format": "date-time" },

    "executive_summary": {
      "type": "string",
      "minLength": 100,
      "maxLength": 2000,
      "description": "3-5 sentence summary answering user's main question"
    },

    "key_insights": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "insight": { "type": "string" },
          "supporting_data": { "type": "array", "items": { "type": "string" } },
          "importance": { "type": "string", "enum": ["high", "medium"] }
        }
      },
      "maxItems": 10
    },

    "sections": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "brief_scope_id"],
        "properties": {
          "title": { "type": "string" },
          "brief_scope_id": { "type": "integer" },
          "summary": { "type": "string" },
          "data_highlights": {
            "type": "object",
            "additionalProperties": { "type": "string" }
          },
          "analysis": { "type": "string" },
          "key_points": { "type": "array", "items": { "type": "string" } },
          "sentiment": { "type": "string", "enum": ["positive", "negative", "neutral", "mixed"] },
          "charts_suggested": { "type": "array", "items": { "type": "string" } },
          "data_tables": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "name": { "type": "string" },
                "headers": { "type": "array", "items": { "type": "string" } },
                "rows": { "type": "array", "items": { "type": "array" } }
              }
            }
          }
        }
      }
    },

    "contradictions_found": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "topic": { "type": "string" },
          "sources": { "type": "array", "items": { "type": "string" } },
          "resolution": { "type": "string" }
        }
      }
    },

    "recommendation": {
      "type": "object",
      "required": ["verdict", "confidence", "reasoning"],
      "properties": {
        "verdict": { "type": "string" },
        "confidence": { "type": "string", "enum": ["high", "medium", "low"] },
        "confidence_reasoning": { "type": "string" },
        "reasoning": { "type": "string" },
        "pros": { "type": "array", "items": { "type": "string" } },
        "cons": { "type": "array", "items": { "type": "string" } },
        "action_items": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "action": { "type": "string" },
              "priority": { "type": "string", "enum": ["high", "medium", "low"] },
              "rationale": { "type": "string" }
            }
          }
        },
        "risks_to_monitor": { "type": "array", "items": { "type": "string" } }
      }
    },

    "coverage_summary": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "topic": { "type": "string" },
          "coverage_percent": { "type": "number" },
          "gaps": { "type": "array", "items": { "type": "string" } }
        }
      }
    },

    "metadata": {
      "type": "object",
      "properties": {
        "total_rounds": { "type": "integer" },
        "total_data_tasks": { "type": "integer" },
        "total_research_tasks": { "type": "integer" },
        "sources_count": { "type": "integer" },
        "processing_time_seconds": { "type": "number" }
      }
    }
  }
}
```

### TypeScript

```typescript
interface AggregatedResearch {
  session_id: string;
  brief_id: string;
  created_at: string;

  executive_summary: string;
  key_insights: KeyInsight[];
  sections: Section[];
  contradictions_found: ContradictionFound[];
  recommendation: Recommendation;
  coverage_summary: Record<string, CoverageSummary>;
  metadata: AggregationMetadata;
}

interface KeyInsight {
  insight: string;
  supporting_data: string[];
  importance: "high" | "medium";
}

interface Section {
  title: string;
  brief_scope_id: number;
  summary: string;
  data_highlights: Record<string, string>;
  analysis: string;
  key_points: string[];
  sentiment: "positive" | "negative" | "neutral" | "mixed";
  charts_suggested: string[];
  data_tables: DataTable[];
}

interface ContradictionFound {
  topic: string;
  sources: string[];
  resolution: string;
}

interface Recommendation {
  verdict: string;
  confidence: "high" | "medium" | "low";
  confidence_reasoning: string;
  reasoning: string;
  pros: string[];
  cons: string[];
  action_items: ActionItem[];
  risks_to_monitor: string[];
}

interface ActionItem {
  action: string;
  priority: Priority;
  rationale: string;
}

interface CoverageSummary {
  topic: string;
  coverage_percent: number;
  gaps: string[];
}

interface AggregationMetadata {
  total_rounds: number;
  total_data_tasks: number;
  total_research_tasks: number;
  sources_count: number;
  processing_time_seconds: number;
}
```

---

## 8. ReportConfig

Конфигурация генерации отчётов.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "report_config.json",
  "title": "ReportConfig",
  "description": "Configuration for report generation",
  "type": "object",
  "required": ["session_id", "formats"],
  "properties": {
    "session_id": { "type": "string" },
    "formats": {
      "type": "array",
      "items": { "type": "string", "enum": ["pdf", "excel", "pptx", "csv"] }
    },
    "language": {
      "type": "string",
      "enum": ["ru", "en"],
      "default": "ru"
    },
    "style": {
      "type": "string",
      "enum": ["formal", "casual"],
      "default": "formal"
    },
    "detail_level": {
      "type": "string",
      "enum": ["detailed", "summary"],
      "default": "detailed"
    },

    "pdf_config": {
      "type": "object",
      "properties": {
        "template_id": { "type": ["string", "null"] },
        "include_toc": { "type": "boolean", "default": true },
        "include_charts": { "type": "boolean", "default": true },
        "include_sources": { "type": "boolean", "default": true },
        "page_size": { "type": "string", "enum": ["A4", "Letter"], "default": "A4" },
        "branding": {
          "type": "object",
          "properties": {
            "logo_url": { "type": ["string", "null"] },
            "primary_color": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" },
            "company_name": { "type": ["string", "null"] }
          }
        }
      }
    },

    "excel_config": {
      "type": "object",
      "properties": {
        "template_id": { "type": ["string", "null"] },
        "include_summary_sheet": { "type": "boolean", "default": true },
        "include_raw_data": { "type": "boolean", "default": true },
        "include_charts": { "type": "boolean", "default": true },
        "sheets_to_include": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },

    "pptx_config": {
      "type": "object",
      "properties": {
        "template_id": { "type": ["string", "null"] },
        "slides_per_section": { "type": "integer", "minimum": 1, "maximum": 5, "default": 2 },
        "include_speaker_notes": { "type": "boolean", "default": false },
        "include_appendix": { "type": "boolean", "default": true },
        "aspect_ratio": { "type": "string", "enum": ["16:9", "4:3"], "default": "16:9" }
      }
    },

    "csv_config": {
      "type": "object",
      "properties": {
        "delimiter": { "type": "string", "enum": [",", ";", "\t"], "default": "," },
        "include_headers": { "type": "boolean", "default": true },
        "encoding": { "type": "string", "enum": ["utf-8", "utf-8-bom", "cp1251"], "default": "utf-8" }
      }
    }
  }
}
```

### TypeScript

```typescript
interface ReportConfig {
  session_id: string;
  formats: OutputFormat[];
  language: "ru" | "en";
  style: "formal" | "casual";
  detail_level: "detailed" | "summary";

  pdf_config?: PDFConfig;
  excel_config?: ExcelConfig;
  pptx_config?: PPTXConfig;
  csv_config?: CSVConfig;
}

interface PDFConfig {
  template_id?: string | null;
  include_toc: boolean;
  include_charts: boolean;
  include_sources: boolean;
  page_size: "A4" | "Letter";
  branding?: {
    logo_url?: string | null;
    primary_color?: string;
    company_name?: string | null;
  };
}

interface ExcelConfig {
  template_id?: string | null;
  include_summary_sheet: boolean;
  include_raw_data: boolean;
  include_charts: boolean;
  sheets_to_include?: string[];
}

interface PPTXConfig {
  template_id?: string | null;
  slides_per_section: number;
  include_speaker_notes: boolean;
  include_appendix: boolean;
  aspect_ratio: "16:9" | "4:3";
}

interface CSVConfig {
  delimiter: "," | ";" | "\t";
  include_headers: boolean;
  encoding: "utf-8" | "utf-8-bom" | "cp1251";
}
```

---

## Связи между структурами

```
Session
 ├── InitialContext (1:1)
 ├── Brief (1:1)
 ├── Plan[] (1:N, по раундам)
 │    ├── DataTask[]
 │    └── ResearchTask[]
 ├── DataResult[] (1:N)
 ├── ResearchResult[] (1:N)
 ├── PlannerDecision[] (1:N, по раундам)
 ├── AggregatedResearch (1:1)
 └── ReportConfig → Report files
```

## Валидация

Все схемы поддерживают валидацию через:
- JSON Schema Draft 2020-12
- Pydantic (Python) с автоматической генерацией из JSON Schema
- Zod (TypeScript) для runtime валидации
