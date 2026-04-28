# IO Contract

## Instruction Key

`project_manuscript_compiling.default`

## Task

`project_generate_manuscript`

## Feature

`project_generate_manuscript_default`

## Input

```json
{
  "project": {
    "project_id": "uuid",
    "project_slug": "slug",
    "name": "string",
    "summary": "string",
    "status": "writing"
  },
  "focus_instructions": "optional user focus",
  "current_documents": {
    "overview": "current overview.md",
    "related_work": "current related-work.md",
    "method": "current method.md",
    "experiment": "current experiment.md",
    "conclusion": "current conclusion.md",
    "manuscript": "current manuscript.md"
  },
  "linked_papers": [],
  "linked_knowledge": [],
  "linked_datasets": [],
  "skip_locked_blocks": true
}
```

## Output

```json
{
  "blocks": {
    "manuscript_abstract": "Markdown",
    "manuscript_introduction": "Markdown",
    "manuscript_related_work": "Markdown",
    "manuscript_method": "Markdown",
    "manuscript_experiment": "Markdown",
    "manuscript_conclusion": "Markdown"
  }
}
```

## Block IDs

- `manuscript_abstract`
- `manuscript_introduction`
- `manuscript_related_work`
- `manuscript_method`
- `manuscript_experiment`
- `manuscript_conclusion`

## Merge Rules

- Backend writes output to `manuscript.md`.
- Backend wraps blocks with RF markers.
- Skip existing locked blocks when requested.
