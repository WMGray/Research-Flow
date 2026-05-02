---
name: paper-knowledge-mining
description: Extract reusable Paper Knowledge from paper metadata, canonical sections, and note.md. Use when maintaining citable views, definitions, feature semantics, feature extraction, metric or annotation-rule extraction, original evidence text, citation markers such as `[32]`, source locators, confidence filtering, review routing, or `paper_knowledge_mining.default` runtime instructions.
---

# Paper Knowledge Mining

## Goal

Extract reusable Knowledge from Paper metadata, selected canonical section files, and the generated `note.md`. The output is a reviewable JSON item list for long-term research memory:

```text
author view / technical definition -> Knowledge item -> Paper EXTRACTED_FROM link
```

Use this skill to answer "what citable views, definitions, feature descriptions, metrics, or annotation rules can be reused from this paper?" Do not use it to produce a paper summary or dataset catalog.

## Skill Design

Follow the Paper skill shape:

- Keep `SKILL.md` concise: routing, evidence plan, workflow, output categories, and reference map only.
- Put long prompt text, category rules, and section budget details in `references/`.
- Load references only when changing runtime prompts, section selection, or backend context building.
- Keep frontmatter limited to `name` and `description`; all trigger context belongs in `description`.

## Boundary

This skill uses only supplied Paper metadata, `paper-sectioning` outputs, and `paper-note-generate` output. `note.md` helps identify candidate knowledge and organize Chinese explanations, but final `evidence_text` and `original_text_en` must come from section text. Do not trace or infer the earliest origin of an idea; preserve only the source Paper and citation marker found in the current paper.

Do not read `refined.md` directly except when debugging upstream sectioning failures.

## Pipeline Position

```text
refine-parse -> sectioning --> note-generate --> knowledge-mining
                            \-> dataset-mining
```

`paper-knowledge-mining` runs after `note.md` is generated. It shares canonical sections with Dataset extraction but has a separate prompt, output schema, and write-back path.

## Output Categories

Use exactly two levels:

| `knowledge_type` | `category_label` | Meaning |
|------------------|------------------|---------|
| `view` | `field_status` | Author view about field status, trend, need, or importance |
| `view` | `method_critique` | Author critique of prior methods or failure modes |
| `view` | `core_insight` | Author hypothesis, claim, or methodological insight |
| `view` | `key_conclusion` | Strong conclusion or notable experimental finding |
| `definition` | `concept_term` | Concept or terminology definition |
| `definition` | `task_definition` | Task objective, input/output, or boundary definition |
| `definition` | `feature_semantics` | Feature meaning, modality semantics, or physical interpretation |
| `definition` | `feature_extraction` | Algorithm, architecture, or processing flow for extracting features |
| `definition` | `evaluation_metric` | Metric definition, formula, or evaluation protocol |
| `definition` | `data_annotation_rule` | Data collection, cleaning, labeling, or annotation rule |

`view` items require `original_text_en`. `definition` items may set it to `null` when the section evidence is sufficient but no compact original sentence exists.

## Evidence Plan

| Input | Use | Purpose |
|-------|-----|---------|
| Paper metadata | Required | Paper identity, venue/year context, source Paper linkage |
| `note.md` | Required, P0 | Candidate discovery, Chinese explanation structure, cross-block context |
| `01_introduction.md` | Required, P0 | Field status, gap, motivation, core claims, task definitions |
| `03_method.md` | Required, P0 | Technical definitions, feature semantics, feature extraction, formulas |
| `04_experiment.md` | Required, P1 | Metrics, annotation rules, evaluation protocol, key conclusions |
| `02_related_work.md` | Recommended, P1 | Prior-method critique, field context, literature comparison |
| `05_conclusion.md` | Recommended, P2 | Key conclusions, limitations, future work, open questions |

Do not inject `06_appendix.md` directly; appendix method and experiment evidence should be copied into `method` or `experiment` by `paper-sectioning` multi-section matching.

## Output Contract

Return JSON only:

```json
{
  "items": [
    {
      "title": "Brief English title",
      "knowledge_type": "view|definition",
      "category_label": "field_status|method_critique|core_insight|key_conclusion|concept_term|task_definition|feature_semantics|feature_extraction|evaluation_metric|data_annotation_rule",
      "summary_zh": "中文摘要，2-5 句完整表达",
      "original_text_en": "source English sentence or null",
      "citation_marker": "[32] or null",
      "research_field": "NLP/CV/RL/etc.",
      "source_section": "introduction|related_work|method|experiment|conclusion",
      "source_locator": "line range, heading, or paragraph locator",
      "evidence_text": "verbatim evidence from input",
      "confidence_score": 0.85
    }
  ]
}
```

The backend owns `review_status`, persistence to `biz_knowledge`, and `asset_link(EXTRACTED_FROM)` creation.

## Workflow

1. Read Paper metadata and generated `note.md`.
2. Build `{{section_context}}` from `introduction`, `related_work`, `method`, `experiment`, and `conclusion` per `references/section-scope.md`.
3. Build `{{note_context}}` from `note.md`; use it for candidate discovery, not as final evidence.
4. Render `references/runtime-instructions.md` through `paper_knowledge_mining.default`.
5. Require JSON-only LLM output.
6. Validate `knowledge_type` and `category_label` pairings.
7. Require `original_text_en` for `view` items and preserve citation markers exactly.
8. Verify `evidence_text` can be traced back to supplied section context.
9. Filter or route `confidence_score < 0.6` to review.
10. Write accepted items with initial review state and record raw response, prompt, validation result, and pipeline run metadata.

## Progressive Disclosure Map

Load only the file needed for the task:

- `references/runtime-instructions.md` — LLM prompt template and JSON schema.
- `references/section-scope.md` — section selection, category coverage matrix, context budgets, and backend implementation contract.

## Backend Touchpoints

- `backend/core/services/papers/skill_runtime.py` — runtime instruction loading.
- `backend/core/services/papers/repository.py` — pipeline integration and Knowledge extraction entry point.
- `backend/core/services/papers/note/` — upstream note generation and `note.md` structure.
- `backend/core/schema.py` — `biz_knowledge`, asset registry, and asset links.

## Validation

Run focused tests after Knowledge extraction changes:

```powershell
python -m pytest backend\tests\test_papers_api.py backend\tests\test_config_api.py -q
```

Review generated `knowledge.json` manually when prompt behavior changes. Confirm no invented claims, valid category pairings, exact evidence text, `view` original-text coverage, citation marker preservation, and correct low-confidence handling.
