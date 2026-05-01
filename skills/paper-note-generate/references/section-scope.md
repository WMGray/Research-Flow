# Section Scope - Note Generation

`paper-note-generate` consumes all six canonical section files produced by `paper-sectioning` to produce a paper-style deep-reading note. The note follows:

```
摘要信息 -> 术语 -> 背景动机 -> 方法 -> 实验/结果 -> 结论局限
```

Unlike `paper-dataset-mining` and `paper-knowledge-mining`, note generation excludes no canonical section. Each block needs a different evidence slice.

## Contents

- Upstream Contract
- Section Selection Strategy
- Block-Section Mapping
- Context Budget Allocation
- Budget Comparison with Mining Skills
- Runtime Behavior

## Upstream Contract

This skill depends on the six sections split by `paper-sectioning`:

| Section Key | Source File | Semantic Content |
|-------------|-------------|------------------|
| `introduction` | `01_introduction.md` | Title, authors, abstract, problem definition, motivation, contributions, paper organization |
| `related_work` | `02_related_work.md` | Prior-work discussion, literature comparison, research gaps |
| `method` | `03_method.md` | Method, model, algorithm, architecture, theoretical derivations, proofs |
| `experiment` | `04_experiment.md` | Experiment setup, datasets, results, ablations, analysis, implementation details |
| `conclusion` | `05_conclusion.md` | Conclusion, limitations, future work, discussion |
| `appendix` | `06_appendix.md` | Full appendix/supplementary content |

Additional inputs:

- `{{figure_context}}`: figure/table evidence collected by the backend from all six sections (max 8 figures, sorted by role priority).
- `{{metadata_json}}`: paper metadata (title, authors, year, venue, doi).

## Section Selection Strategy

### All Included (6/6)

| Section Key | Required | Blocks Served |
|-------------|----------|---------------|
| `introduction` | Yes | `paper_overview`, `terminology_guide`, `background_motivation` |
| `related_work` | Yes | `paper_overview`, `terminology_guide`, `background_motivation` |
| `method` | Yes | `terminology_guide`, `method` |
| `experiment` | Yes | `terminology_guide`, `experimental_results`, `conclusion_limitations` |
| `conclusion` | Yes | `paper_overview`, `conclusion_limitations` |
| `appendix` | Yes | `method`, `experimental_results`, `conclusion_limitations` |

## Block-Section Mapping

### `paper_overview` / 摘要信息 (>=600 chars)

| Source Section | Extracted Content |
|----------------|-------------------|
| `introduction` | Title, authors, abstract, problem statement, contributions |
| `related_work` | Conservative domain positioning when introduction is sparse |
| `conclusion` | High-level outcome wording when abstract is incomplete |

- Write paper identity: title, authors, year, venue full name and abbreviation, DOI.
- Domain positioning format: `大领域 > 细分领域`, grounded in paper content.
- Rewrite the abstract in Chinese, covering research problem, method, results, and contribution.
- Do not exceed 80% of the original abstract length.

### `terminology_guide` / 术语 (>=1200 chars)

| Source Section | Extracted Content |
|----------------|-------------------|
| `introduction` | Task definitions, general concepts |
| `related_work` | Prior method families and field-specific terms |
| `method` | Model/architecture terms, feature representation terms |
| `experiment` | Dataset, benchmark, metric, baseline terms |

- Organize by four categories: task definitions, model and architecture terms, feature representations, evaluation metrics.
- Each term >=50 Chinese characters.
- List terms in first-appearance order.
- Do not present paper-invented modules as general concepts.

### `background_motivation` / 背景动机 (>=1600 chars)

| Source Section | Extracted Content |
|----------------|-------------------|
| `introduction` | Research background, task motivation, field status |
| `related_work` | Prior method analysis, literature context, research gaps |

- Analyze research background first, then related-work context.
- Discuss at least 3 prior works or representative methods, each >=50 Chinese characters.
- Include pain-point mapping table: `| 核心痛点 | 本文切入点 | 对应实现技术 | 实现效果 |`.

### `method` / 方法 (>=2600 chars)

| Source Section | Extracted Content |
|----------------|-------------------|
| `method` | Method architecture, algorithm flow, formulas, theoretical derivations |
| `appendix` | Appendix proofs, method variants, architectural supplements |

- Must begin with `### 方法总览`.
- Each module follows: background -> principles -> formulas -> role.
- Each sub-component follows the four-element rule: narrative -> verbatim formula -> variable-by-variable explanation -> linkage.
- Figure analysis follows the three-part rule: what it shows -> how to read it -> why it matters.

### `experimental_results` / 实验/结果 (>=2200 chars)

| Source Section | Extracted Content |
|----------------|-------------------|
| `experiment` | Dataset setup, features, training settings, main results, ablations, metric comparisons |
| `appendix` | Supplementary hyperparameters, implementation details, supplementary experiments and ablations |

- Start with `### 实验设置`.
- Cover datasets (source/scale/content/splits), features, training settings, hyperparameters, hardware, and missing items.
- Follow the original experiment section order and subsection headings.
- Main results and ablations must include exact metrics and Table/Figure numbers when available.
- Appendix experiments belong under `### 附录证据`, not new top-level note blocks.

### `conclusion_limitations` / 结论局限 (>=1000 chars)

| Source Section | Extracted Content |
|----------------|-------------------|
| `conclusion` | Conclusion, limitations, future work |
| `experiment` | Experiment-backed final findings, failure cases, discussion |
| `appendix` | Supplementary limitations, assumptions, failure modes, future directions |

- Use `### 结论`, `### 局限性`, and `### 未来工作与开放问题`.
- Ground conclusions in the method and experiment evidence.
- Write only explicit limitations, assumptions, failure modes, scope constraints, and future work from the paper.
- If no direct evidence exists, write `解析内容未提供直接证据。`

## Context Budget Allocation

Total full-note budget: **10000 characters**.

| Section Key | Budget | Share | Justification |
|-------------|--------|-------|---------------|
| `method` | 3000 chars | 30% | Carries formulas, module decomposition, and sub-component analysis |
| `experiment` | 2500 chars | 25% | Primary source for setup, results, ablations, and metrics |
| `introduction` | 1800 chars | 18% | Supports overview, terminology, and background |
| `related_work` | 1200 chars | 12% | Literature context and motivation source |
| `conclusion` | 800 chars | 8% | Conclusions, limitations, and future work |
| `appendix` | 700 chars | 7% | Supplementary method, hyperparameters, and experiments |

When a section exceeds its budget, truncation occurs at line boundaries while preserving complete paragraphs where possible.

## Budget Comparison with Mining Skills

| Dimension | Note Generation | Dataset/Knowledge Mining |
|-----------|-----------------|--------------------------|
| Total budget | 10000 chars | 8000 chars |
| Sections selected | All 6 | 3-4 targeted sections |
| method budget share | 30% | 0% (dataset) / 35% (knowledge) |
| experiment budget share | 25% | 50% (dataset) / 20% (knowledge) |
| Primary reason | Must support six paper-style explanatory blocks | Only needs targeted entity extraction |

## Runtime Behavior

1. Read all six section files from `parsed/sections/`.
2. Truncate each section to its budget, then concatenate into `{{section_context}}` for full-note mode.
3. In per-block mode, select each block's `section_keys` from `schema.py`, then compact high-value lines with `context.py`.
4. Build `{{figure_context}}` independently by collecting image links from all six sections, classifying roles, sorting by priority, and capping at 8 figures.
5. Build `{{metadata_json}}` independently from paper metadata.
