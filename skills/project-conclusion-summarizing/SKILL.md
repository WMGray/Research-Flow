---
name: project-conclusion-summarizing
description: Maintain Research-Flow Project conclusion summarization contracts. Use when changing Project conclusion generation, open-problem blocks, next-step planning, cross-module synthesis, or `project_conclusion_summarizing.default`.
---

# Project Conclusion Summarizing

## Core Rule

Summarize the current Project state from existing Project modules. Do not create new paper claims, method details, or experiment results that are not already present in supplied modules.

## Inputs

Use supplied context:

- Current `overview.md`, `related-work.md`, `method.md`, and `experiment.md`.
- Existing `conclusion.md`.
- Recent Project job summaries.
- User focus instructions.

## Output Blocks

Return these managed blocks:

- `conclusion_summary`: current stage conclusion and confidence.
- `open_problems`: unresolved research, method, data, and evaluation issues.
- `next_steps`: concrete follow-up actions.

## Workflow

1. Read `references/io-contract.md` before changing task, feature, or block IDs.
2. Use `references/runtime-instructions.md` for runtime instructions.
3. Base every conclusion on supplied module content.
4. Keep next steps operational and checkable.
5. Preserve locked and free-form user content during write-back.

## Runtime Reference

The runtime instruction for `project_conclusion_summarizing.default` is `references/runtime-instructions.md`.

## Validation

Run focused Project task tests after changes:

```powershell
python -m pytest backend\tests -q
```
