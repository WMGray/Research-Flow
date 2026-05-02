# Section Scope — Knowledge Mining

`paper-knowledge-mining` consumes selected canonical section files produced by `paper-sectioning` and the `note.md` produced by `paper-note-generate`. This document defines runtime section selection, category coverage, and context budget allocation.

## Upstream Contract

| Upstream Skill | Output | Usage |
|---------------|--------|-------|
| `paper-sectioning` | `01_introduction.md` – `06_appendix.md` | Selected files injected as `{{section_context}}` |
| `paper-note-generate` | `note.md` | Injected as `{{note_context}}` |

The semantic definitions of the canonical sections follow `paper-sectioning` runtime classification rules.

## Section Selection Strategy

### Included (5/6)

| Priority | Section Key | Source File | Rationale |
|----------|-------------|-------------|-----------|
| **P0** | `introduction` | `01_introduction.md` | Primary source for field status, research gaps, motivation, core claims, task definitions, and contribution framing. |
| **P0** | `method` | `03_method.md` | Richest source for technical definitions, feature semantics, feature extraction, formulas, architecture, and method-specific terms. |
| **P1** | `experiment` | `04_experiment.md` | Source for evaluation metrics, annotation rules, evaluation protocol, and evidence-backed key conclusions. |
| **P1** | `related_work` | `02_related_work.md` | Source for prior-method critique, field context, literature comparison, and research gaps not repeated in the introduction. |
| **P2** | `conclusion` | `05_conclusion.md` | Reinforces key conclusions, limitations, future work, and open questions. |

### Excluded (1/6)

| Section Key | Reason |
|-------------|--------|
| `appendix` | Appendix method, proof, implementation, and experiment evidence should be copied into `method` or `experiment` by `paper-sectioning` multi-section matching. Injecting appendix directly usually duplicates content and dilutes the budget. |

## note.md Usage

`note.md` is required, but it is not the final evidence source.

- Use `note.md` to discover candidate Knowledge items and understand the paper structure.
- Use section text for `evidence_text`, `original_text_en`, citation markers, and source locators.
- Do not cite a `note.md` paraphrase as evidence when the corresponding section text is absent.

## Knowledge Type Coverage Matrix

| Category Label | knowledge_type | Primary Sources |
|---------------|----------------|-----------------|
| `field_status` | view | introduction, related_work, conclusion |
| `method_critique` | view | related_work, introduction, method |
| `core_insight` | view | introduction, method, conclusion |
| `key_conclusion` | view | experiment, conclusion, introduction |
| `concept_term` | definition | introduction, method, related_work |
| `task_definition` | definition | introduction, method |
| `feature_semantics` | definition | method |
| `feature_extraction` | definition | method |
| `evaluation_metric` | definition | experiment, method |
| `data_annotation_rule` | definition | experiment |

## Context Budget Allocation

Total section budget: **10000 characters**, weighted by Knowledge density:

| Section Key | Budget | Share | Justification |
|-------------|--------|-------|---------------|
| `method` | 2800 chars | 28% | Carries technical definitions, feature semantics, formulas, and extraction procedures |
| `introduction` | 2400 chars | 24% | Carries field views, task definitions, gaps, and core claims |
| `experiment` | 1800 chars | 18% | Carries metrics, annotation rules, and key empirical conclusions |
| `related_work` | 1800 chars | 18% | Carries critique and field context that may not appear elsewhere |
| `conclusion` | 1200 chars | 12% | Carries final claims, limitations, and future-work signals |

When a section exceeds its budget, truncate at line boundaries while preserving complete paragraphs where possible. Sentence-level truncation is not used.

Suggested `note.md` budget: **4000-6000 characters**. Prefer managed block headings and compact high-signal lines over raw full-note injection when the note is long.

## Runtime Behavior

### Backend Implementation Contract

1. Read all six section files from the `parsed/sections/` directory produced by `paper-sectioning`.
2. Select `introduction`, `related_work`, `method`, `experiment`, and `conclusion`.
3. Do not select `appendix` directly.
4. Truncate each selected section to its budget, then concatenate into `{{section_context}}`.
5. Read `note.md` from `paper-note-generate`, compact it, and inject it as `{{note_context}}`.
6. Build `{{metadata_json}}` from Paper metadata independently of section selection.

### Excluded Inputs

- `refined.md` is not injected. Use it only for debugging upstream split quality.
- `note.md` does not replace section evidence.
- `appendix` is not injected directly unless a future recall audit proves that `paper-sectioning` is failing to copy appendix evidence into method or experiment sections.

## Design Rationale

Knowledge extraction optimizes for reusable research memory, not for short paper summarization. The prompt needs both structured understanding (`note.md`) and traceable source evidence (sections). Including `related_work` improves `method_critique` recall, while excluding direct appendix injection keeps the context focused and avoids duplicate evidence.
