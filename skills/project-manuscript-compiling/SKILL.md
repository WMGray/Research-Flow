---
name: project-manuscript-compiling
description: Maintain Research-Flow Project manuscript compilation contracts. Use when changing Project manuscript generation, cross-module paper draft blocks, Abstract or section drafting, locked manuscript write-back, or `project_manuscript_compiling.default`.
---

# Project Manuscript Compiling

## Core Rule

Compile existing Project modules into manuscript draft blocks. Do not bypass upstream module evidence or overwrite locked manuscript sections.

## Inputs

Use supplied context:

- Current `overview.md`, `related-work.md`, `method.md`, `experiment.md`, `conclusion.md`, and `manuscript.md`.
- Linked paper notes and selected sections.
- Linked Knowledge and Dataset summaries.
- User focus instructions and skip-lock settings.

## Output Blocks

Return these managed blocks:

- `manuscript_abstract`
- `manuscript_introduction`
- `manuscript_related_work`
- `manuscript_method`
- `manuscript_experiment`
- `manuscript_conclusion`

## Workflow

1. Read `references/io-contract.md` before changing task, feature, or block contracts.
2. Use `references/runtime-instructions.md` for runtime instructions.
3. Treat Project modules as the primary source of truth.
4. Keep manuscript prose draft-like; avoid pretending results are final when experiment content is only planned.
5. Preserve locked and free-form user content during write-back.

## Runtime Reference

The runtime instruction for `project_manuscript_compiling.default` is `references/runtime-instructions.md`.

## Validation

Run focused Project task tests after changes:

```powershell
python -m pytest backend\tests -q
```
