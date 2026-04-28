# IO Contract

## Instruction Key

`project_overview_refreshing.default`

## Task

`project_refresh_overview`

## Feature

No LLM feature is required. This task is deterministic.

## Input

```json
{
  "project": {
    "project_id": "uuid",
    "project_slug": "slug",
    "name": "string",
    "status": "planning|researching|experimenting|writing|archived",
    "summary": "string",
    "owner": "string",
    "updated_at": "iso datetime"
  },
  "statistics": {
    "linked_papers": 0,
    "linked_knowledge": 0,
    "linked_datasets": 0,
    "linked_presentations": 0,
    "experiments": 0
  },
  "recent_jobs": [
    {
      "type": "project_generate_method",
      "status": "succeeded",
      "created_at": "iso datetime"
    }
  ],
  "current_document": "existing overview.md"
}
```

## Output

Return a block payload:

```json
{
  "blocks": {
    "overview_stats": "| 指标 | 当前值 |\\n|---|---|\\n| 课题状态 | researching |"
  }
}
```

## Block IDs

- `overview_stats`

## Merge Rules

- Update only blocks whose existing marker has `managed="true"`.
- Skip an existing `overview_stats` block when it has `managed="false"`.
- Keep all content outside RF blocks unchanged.
