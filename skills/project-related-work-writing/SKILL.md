---
name: project-related-work-writing
description: Maintain Research-Flow Project related-work generation contracts. Use when changing linked-paper synthesis, related-work managed blocks, paper grouping, method comparison, Project LLM runtime instructions, or `project_related_work_writing.default`.
---

# Project Related Work Writing

## Core Rule

Synthesize linked papers into Project-level related-work blocks with evidence-aware Markdown. Do not invent citations, paper claims, datasets, metrics, or relationships that are absent from supplied context.

## Inputs

Use supplied Project context:

- Linked paper metadata and relationship roles such as `related_work`, `baseline`, `inspiration`, `method_reference`, and `experiment_reference`.
- Paper `note.md` blocks and relevant `parsed/sections/related_work.md` snippets.
- Existing `related-work.md` content and user focus instructions.
- Optional linked Knowledge or Dataset summaries.

## Output Blocks

Return these managed blocks:

- `related_work_summary`: concise narrative synthesis.
- `paper_grouping`: grouped papers by topic, method family, or application.
- `method_comparison`: comparison of representative methods, assumptions, strengths, and limitations.

## Workflow

1. Read `references/io-contract.md` before changing input fields, task names, feature names, or block IDs.
2. Use `references/runtime-instructions.md` as the runtime prompt contract.
3. Prefer paper notes over long raw sections when both are available.
4. Preserve paper titles and author-provided method names exactly.
5. Mark missing evidence explicitly instead of filling gaps.
6. Update only backend-managed RF blocks; preserve locked and free-form user text.

## Runtime Reference

The runtime instruction for `project_related_work_writing.default` is `references/runtime-instructions.md`.

## Validation

Run focused Project task tests after changes:

```powershell
python -m pytest backend\tests -q
```
