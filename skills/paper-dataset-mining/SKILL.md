---
name: paper-dataset-mining
description: Maintain Research-Flow's Paper Dataset extraction skill. Use when changing extraction of datasets, benchmarks, tasks, modalities, scale, split rules, source Paper linkage, original evidence text, citation markers, confidence filtering, or `paper_dataset_mining.default` runtime instructions.
---

# Paper Dataset Mining

## Core Rule

Extract dataset and benchmark mentions only from supplied Paper metadata and canonical sections. Preserve the source Paper, original evidence, and citation markers; do not infer missing dataset facts.

## Hierarchy

This is a P1 Paper skill under `paper-pipeline`. It consumes outputs from:

- `paper-refine-parse`
- `paper-sectioning`

It runs in parallel with `paper-note-generate` after sectioning; it does not depend on `note.md`.

## Workflow

1. Read Paper metadata and canonical section text.
2. Extract datasets, benchmarks, tasks, modalities, scale, splits, metrics, source URL/DOI, and license only when stated.
3. Record the source Paper and source section for every mention.
4. Copy citation markers such as `[32]` from the source text when present.
5. Preserve original evidence text for review.
6. Use `confidence_score < 0.6` for uncertain or weak mentions.
7. Return JSON only.

## Section Selection

This skill consumes canonical sections produced by `paper-sectioning`. Only three of six sections carry dataset signal; the selection contract and per-section budget allocation are documented in `references/section-scope.md`.

## Runtime Reference

The backend runtime instruction for `paper_dataset_mining.default` is `references/runtime-instructions.md`. The runtime must apply section selection and truncation per `references/section-scope.md` before rendering `{{section_context}}` into the prompt template.

## References

- `references/runtime-instructions.md` — LLM prompt template with JSON output schema
- `references/section-scope.md` — section selection strategy, budget allocation, and backend implementation contract
