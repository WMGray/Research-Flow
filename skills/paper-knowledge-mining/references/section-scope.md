# Section Scope — Knowledge Mining

`paper-knowledge-mining` consumes the six canonical section files produced by `paper-sectioning` and the `note.md` produced by `paper-note-generate`. This document defines the runtime section selection rules and context budget allocation.

## Upstream Contract

This skill depends on two upstream skills:

| Upstream Skill | Output | Usage |
|---------------|--------|-------|
| `paper-sectioning` | `01_introduction.md` – `06_appendix.md` | Injected as `{{section_context}}` |
| `paper-note-generate` | `note.md` | Injected as `{{note_context}}` |

The semantic definitions of the six canonical sections follow `paper-sectioning`'s runtime Classification Rules and are not repeated here.

## Section Selection Strategy

### Included (4/6)

| Priority | Section Key | Rationale |
|----------|-------------|-----------|
| **P0** | `method` | Carries 4 knowledge types (feature_semantics, feature_extraction, task_definition, concept_term) — the richest source of technical definitions and feature semantics. |
| **P0** | `introduction` | Carries 5 knowledge types (field_status, method_critique, core_insight, key_conclusion, concept_term, task_definition) — the primary source of field-level views and core insights. |
| **P1** | `experiment` | Carries evaluation_metric and data_annotation_rule definitions, plus method-validation views. |
| **P2** | `conclusion` | Reinforces key_conclusion and core_insight, often restating introduction claims in more concise form, sometimes with added nuance. |

### Excluded (2/6)

| Section Key | Reason |
|-------------|--------|
| `related_work` | method_critique appears here, but introduction typically summarizes the key critiques. The risk of exclusion: when authors bury method critiques solely in related_work without summarizing them in the introduction, method_critique recall will drop. This is a recall trade-off to monitor. |
| `appendix` | Technical definition lines in the appendix are already copied to `method` or `experiment` by `paper-sectioning`'s multi-section matching rules. Including appendix separately produces redundancy. |

## Knowledge Type Coverage Matrix

All 10 category labels are covered by the 4 selected sections:

| Category Label | knowledge_type | Covered By |
|---------------|---------------|-------------|
| `field_status` | view | introduction |
| `method_critique` | view | introduction (summary), method (method choices) |
| `core_insight` | view | introduction, conclusion |
| `key_conclusion` | view | introduction, conclusion |
| `concept_term` | definition | introduction, method |
| `task_definition` | definition | introduction, method |
| `feature_semantics` | definition | method |
| `feature_extraction` | definition | method |
| `evaluation_metric` | definition | experiment, method |
| `data_annotation_rule` | definition | experiment |

No category depends solely on `related_work` or `appendix`.

## Context Budget Allocation

Total budget: **8000 characters**, weighted by knowledge type carrying capacity:

| Section Key | Budget | Share | Justification |
|-------------|--------|-------|---------------|
| `method` | 2800 chars | 35% | Carries 4 knowledge types; typically the longest section with the highest content density |
| `introduction` | 2400 chars | 30% | Carries 5 knowledge types; core source of views and definitions |
| `experiment` | 1600 chars | 20% | Only evaluation_metric and data_annotation_rule; shorter budget suffices |
| `conclusion` | 1200 chars | 15% | Reinforces introduction content with signal redundancy; lower budget acceptable |

When a section exceeds its budget, truncation occurs at line boundaries (preserving complete paragraphs). Sentence-level truncation is not used.

## Runtime Behavior

### Backend Implementation Contract

1. Read all six section files from the `parsed/sections/` directory produced by `paper-sectioning`.
2. Select only `method`, `introduction`, `experiment`, and `conclusion`.
3. Truncate each section to its budget, then concatenate into `{{section_context}}` for injection into the `runtime-instructions.md` template.
4. Read `note.md` from `paper-note-generate` output and inject as `{{note_context}}`.
5. `{{metadata_json}}` is built from Paper metadata independently of section selection.

### Excluded Sections

`related_work` and `appendix` are not injected.

## Design Rationale

Allocating 35% + 30% of the budget to method and introduction ensures these two high-density sections receive sufficient context depth. The 15% for conclusion is cost-effective: it provides a refined version of introduction claims in very little space.

### method_critique Recall Risk and Mitigation

**Known risk of excluding `related_work`**: method_critique is the only covered category whose sole non-covered section is related_work. When authors place critiques of prior methods only in related_work without summarizing them in the introduction, the current section selection will miss them.

**Mitigation strategy:**
- Monitor method_critique recall in production.
- If recall is insufficient, re-add `related_work` at P2 priority (budget: 800 chars).
- No changes to the prompt logic in runtime-instructions are needed — only the backend section selection and budget allocation need adjustment.
