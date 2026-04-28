# IO Contract

## Instruction Key

`project_conclusion_summarizing.default`

## Task

`project_generate_conclusion`

## Feature

`project_generate_conclusion_default`

## Input

```json
{
  "project": {
    "project_id": "uuid",
    "project_slug": "slug",
    "name": "string",
    "summary": "string",
    "status": "experimenting"
  },
  "focus_instructions": "optional user focus",
  "current_documents": {
    "overview": "current overview.md",
    "related_work": "current related-work.md",
    "method": "current method.md",
    "experiment": "current experiment.md",
    "conclusion": "current conclusion.md"
  },
  "recent_jobs": [],
  "skip_locked_blocks": true
}
```

## Output

```json
{
  "blocks": {
    "conclusion_summary": "Markdown",
    "open_problems": "Markdown",
    "next_steps": "Markdown"
  }
}
```

## Block IDs

- `conclusion_summary`
- `open_problems`
- `next_steps`

## Merge Rules

- Backend writes output to `conclusion.md`.
- Backend wraps blocks with RF markers.
- Skip existing locked blocks when requested.
