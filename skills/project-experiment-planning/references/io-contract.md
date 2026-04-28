# IO Contract

## Instruction Key

`project_experiment_planning.default`

## Task

`project_generate_experiment`

## Feature

`project_generate_experiment_default`

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
    "method": "current method.md",
    "experiment": "current experiment.md"
  },
  "linked_papers": [
    {
      "paper_id": 123,
      "title": "paper title",
      "relationship": "baseline|experiment_reference|method_reference|related_work|inspiration",
      "note_blocks": {},
      "sections": {
        "experiment": "markdown snippet"
      }
    }
  ],
  "linked_datasets": [],
  "linked_knowledge": [],
  "skip_locked_blocks": true
}
```

## Output

```json
{
  "blocks": {
    "experiment_plan": "Markdown",
    "baseline_comparison": "Markdown",
    "metric_suggestions": "Markdown"
  }
}
```

## Block IDs

- `experiment_plan`
- `baseline_comparison`
- `metric_suggestions`

## Merge Rules

- Backend writes output to `experiment.md`.
- Backend wraps blocks with RF markers.
- Skip existing locked blocks when requested.
