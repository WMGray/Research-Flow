---
name: paper-dataset-mining
description: Extract dataset and benchmark mentions from paper metadata and canonical sections. Use when maintaining Dataset extraction, dataset/benchmark evidence, task/modality/scale/split/metric fields, source Paper linkage, citation markers, confidence filtering, Dataset normalization handoff, or `paper_dataset_mining.default` runtime instructions.
---

# Paper Dataset Mining

## Goal

Extract dataset and benchmark mentions from Paper metadata and selected canonical section files. The output is a reviewable JSON mention list that can be normalized into global `Dataset` resources:

```text
dataset / benchmark mention -> normalized Dataset -> Paper USES Dataset link
```

Use this skill to answer "what data or benchmarks does this paper use, propose, extend, or evaluate on?" Do not use it to summarize the paper or extract author views.

## Skill Design

Follow the Paper skill shape:

- Keep `SKILL.md` concise: routing, evidence plan, workflow, output contract, and reference map only.
- Put long prompt text and section budget details in `references/`.
- Load references only when changing runtime prompts, section selection, or backend context building.
- Keep frontmatter limited to `name` and `description`; all trigger context belongs in `description`.

## Boundary

This skill uses only supplied Paper metadata and `paper-sectioning` outputs. It does not consume `note.md` and does not read `refined.md` directly. If a dataset fact is missing, return `null` for that field instead of inferring it. Preserve original evidence text and citation markers exactly as they appear in the source section.

## Pipeline Position

```text
refine-parse -> sectioning --> dataset-mining
                            \-> note-generate --> knowledge-mining
```

`paper-dataset-mining` may run in parallel with `paper-note-generate` after sectioning succeeds. It does not depend on generated notes.

## Evidence Plan

| Input | Use | Purpose |
|-------|-----|---------|
| Paper metadata | Required | Paper identity, venue/year context, source Paper linkage |
| `04_experiment.md` | Required, P0 | Datasets, benchmarks, splits, metrics, scales, experimental use |
| `02_related_work.md` | Recommended, P1 | Community-standard benchmarks and prior-work dataset mentions |
| `01_introduction.md` | Optional, P2 | Task-level dataset or benchmark mentions in problem framing |

Do not inject `note.md`. Do not inject `06_appendix.md` directly; appendix dataset evidence should be copied into `experiment` or `related_work` by `paper-sectioning` multi-section matching. Use `refined.md` only for debugging upstream sectioning failures.

## Output Contract

Return JSON only:

```json
{
  "items": [
    {
      "dataset_name": "Dataset or benchmark name",
      "task": "task name or null",
      "modality": "text|image|audio|video|multimodal|tabular|graph|other|null",
      "scale": "sample count, size, or null",
      "split_rule": "train/dev/test split or null",
      "metrics": ["metric names"],
      "source_url": "URL or null",
      "doi": "DOI or null",
      "license": "license or null",
      "description_zh": "中文描述",
      "citation_marker": "[32] or null",
      "source_section": "introduction|related_work|experiment",
      "source_locator": "line range, heading, or paragraph locator",
      "evidence_text": "verbatim evidence from input",
      "confidence_score": 0.85
    }
  ]
}
```

The backend owns `normalized_name`, Dataset deduplication, alias matching, and `asset_link(USES)` creation.

## Workflow

1. Read Paper metadata.
2. Build `{{section_context}}` from `experiment`, `related_work`, and `introduction` per `references/section-scope.md`.
3. Render `references/runtime-instructions.md` through `paper_dataset_mining.default`.
4. Require JSON-only LLM output.
5. Validate required fields and keep original `evidence_text`.
6. Filter or route `confidence_score < 0.6` to review.
7. Normalize accepted dataset names in backend code, then link or create global `Dataset` resources.
8. Record raw response, prompt, validation result, and pipeline run metadata.

## Progressive Disclosure Map

Load only the file needed for the task:

- `references/runtime-instructions.md` — LLM prompt template and JSON schema.
- `references/section-scope.md` — section selection, budget allocation, excluded inputs, and backend implementation contract.

## Backend Touchpoints

- `backend/core/services/papers/skill_runtime.py` — runtime instruction loading.
- `backend/core/services/papers/repository.py` — pipeline integration and Dataset extraction entry point.
- `backend/core/services/system_config/` — SkillBinding and feature routing, when changing runtime keys.
- `backend/core/schema.py` — `biz_dataset`, asset registry, and asset links.

## Validation

Run focused tests after Dataset extraction changes:

```powershell
python -m pytest backend\tests\test_papers_api.py backend\tests\test_config_api.py -q
```

Review generated `datasets.json` manually when prompt behavior changes. Confirm no invented dataset facts, exact evidence text, valid `source_section`, and correct low-confidence handling.
