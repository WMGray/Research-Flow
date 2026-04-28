# IO Contract

## Instruction Key

`project_related_work_writing.default`

## Task

`project_generate_related_work`

## Feature

`project_generate_related_work_default`

## Input

```json
{
  "project": {
    "project_id": "uuid",
    "project_slug": "slug",
    "name": "string",
    "summary": "string",
    "status": "researching"
  },
  "focus_instructions": "optional user focus",
  "current_document": "existing related-work.md",
  "linked_papers": [
    {
      "paper_id": 123,
      "title": "paper title",
      "relationship": "related_work|baseline|inspiration|method_reference|experiment_reference",
      "note_blocks": {},
      "sections": {
        "related_work": "markdown snippet",
        "method": "markdown snippet"
      }
    }
  ],
  "linked_knowledge": [],
  "skip_locked_blocks": true
}
```

## Output

Return JSON only:

```json
{
  "blocks": {
    "related_work_summary": "Markdown",
    "paper_grouping": "Markdown",
    "method_comparison": "Markdown"
  }
}
```

## Block IDs

- `related_work_summary`
- `paper_grouping`
- `method_comparison`

## Merge Rules

- Backend wraps each value with RF block markers.
- Existing `managed="false"` blocks must be skipped when `skip_locked_blocks=true`.
- Content outside RF blocks is user-owned.
