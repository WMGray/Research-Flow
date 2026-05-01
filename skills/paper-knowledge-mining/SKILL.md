---
name: paper-knowledge-mining
description: Maintain Research-Flow's Paper Knowledge extraction skill. Use when changing extraction of reusable views, definitions, feature descriptions, original evidence text, citation markers such as `[32]`, source section locators, confidence filtering, or `paper_knowledge_mining.default` runtime instructions.
---

# Paper Knowledge Mining

## Core Rule

Extract reusable Knowledge only from supplied Paper metadata, canonical sections, and note content. Preserve original evidence and citation markers; do not trace or infer the earliest origin of an idea.

## Hierarchy

This is a P1 Paper skill under `paper-pipeline`. It consumes outputs from:

- `paper-refine-parse`
- `paper-sectioning`
- `paper-note-generate`

## Output Categories

Use two levels:

- `knowledge_type=view`
  - `field_status`
  - `method_critique`
  - `core_insight`
  - `key_conclusion`
- `knowledge_type=definition`
  - `concept_term`
  - `task_definition`
  - `feature_semantics`
  - `feature_extraction`
  - `evaluation_metric`
  - `data_annotation_rule`

## Workflow

1. Read Paper metadata, canonical section text, and generated note text.
2. Extract only citable author claims, definitions, feature semantics, metric definitions, and data annotation rules.
3. Store the source Paper, source section, source locator, original text, and evidence text for every item.
4. Copy citation markers from the source Paper text, for example `[32]`; do not resolve them across papers.
5. Require `original_text_en` for `view` items.
6. Use `confidence_score < 0.6` for low-evidence items so they are filtered or routed to review.
7. Return JSON only.

## Section Selection

This skill consumes canonical sections produced by `paper-sectioning` and note content from `paper-note-generate`. Four of six sections carry knowledge signal; the selection contract, category-to-section coverage matrix, and per-section budget allocation are documented in `references/section-scope.md`.

## Runtime Reference

The backend runtime instruction for `paper_knowledge_mining.default` is `references/runtime-instructions.md`. The runtime must apply section selection and truncation per `references/section-scope.md` before rendering `{{section_context}}` into the prompt template.

## References

- `references/runtime-instructions.md` — LLM prompt template with JSON output schema
- `references/section-scope.md` — section selection strategy, category coverage matrix, budget allocation, and backend implementation contract
