# IO Contract

## Instruction Key

`project_method_drafting.default`

## Task

`project_generate_method`

## Feature

`project_generate_method_default`

## Input

```json
{
  "project": {
    "project_id": "uuid",
    "project_slug": "slug",
    "name": "string",
    "summary": "string"
  },
  "focus_instructions": "optional user focus",
  "current_documents": {
    "related_work": "current related-work.md",
    "method": "current method.md"
  },
  "linked_papers": [
    {
      "paper_id": 123,
      "title": "paper title",
      "relationship": "method_reference|inspiration|baseline|related_work|experiment_reference",
      "note_blocks": {},
      "sections": {
        "method": "markdown snippet"
      }
    }
  ],
  "linked_knowledge": [],
  "skip_locked_blocks": true
}
```

## Output

```json
{
  "blocks": {
    "method_draft": "Markdown",
    "innovation_points": "Markdown",
    "design_risks": "Markdown"
  }
}
```

## Block IDs

- `method_draft`
- `innovation_points`
- `design_risks`

## Merge Rules

- Backend writes output to `method.md`.
- Backend wraps blocks with RF markers.
- Skip existing locked blocks when requested.
