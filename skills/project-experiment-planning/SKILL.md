---
name: project-experiment-planning
description: Maintain Research-Flow Project experiment planning contracts. Use when changing Project experiment generation, baseline comparison blocks, metric suggestions, Dataset-aware evaluation planning, or `project_experiment_planning.default`.
---

# Project Experiment Planning

## Core Rule

Generate experiment planning blocks that are testable and traceable to the Project method, linked baselines, datasets, and metrics. Do not invent benchmark results.

## Inputs

Use supplied context:

- Current `method.md` and `experiment.md` content.
- Linked paper experiment sections, baselines, datasets, metrics, and reported settings.
- Linked Dataset summaries and Knowledge records.
- User focus instructions and skip-lock settings.

## Output Blocks

Return these managed blocks:

- `experiment_plan`: hypotheses, experiment groups, ablations, and execution order.
- `baseline_comparison`: baseline candidates and what each comparison tests.
- `metric_suggestions`: metrics, datasets, expected reporting format, and caveats.

## Workflow

1. Read `references/io-contract.md` before changing task, feature, or block contracts.
2. Use `references/runtime-instructions.md` for runtime instructions.
3. Tie each experiment to a method claim or research question.
4. Separate planned experiments from observed results.
5. Preserve locked and free-form user content during write-back.

## Runtime Reference

The runtime instruction for `project_experiment_planning.default` is `references/runtime-instructions.md`.

## Validation

Run focused Project task tests after changes:

```powershell
python -m pytest backend\tests -q
```
