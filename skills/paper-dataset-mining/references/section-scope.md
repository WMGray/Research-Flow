# Section Scope — Dataset Mining

`paper-dataset-mining` consumes the six canonical section files produced by `paper-sectioning`. This document defines the runtime section selection rules and context budget allocation.

## Upstream Contract

This skill depends on the six sections split by `paper-sectioning`:

| Section Key | Source File | Semantic Content |
|-------------|-------------|-----------------|
| `introduction` | `01_introduction.md` | Title, authors, abstract, problem definition, motivation, contributions |
| `related_work` | `02_related_work.md` | Prior-work discussion, literature comparison, research gaps |
| `method` | `03_method.md` | Method, model, algorithm, architecture, theoretical derivations |
| `experiment` | `04_experiment.md` | Experiments, results, ablations, analysis, implementation details |
| `conclusion` | `05_conclusion.md` | Conclusion, limitations, future work |
| `appendix` | `06_appendix.md` | Full appendix/supplementary content |

## Section Selection Strategy

### Included (3/6)

| Priority | Section Key | Rationale |
|----------|-------------|-----------|
| **P0** | `experiment` | Primary source for dataset names, scale, splits, and evaluation metrics. The experimental setup and results paragraphs are the highest-density regions for dataset mentions. |
| **P1** | `related_work` | Benchmark comparisons against prior work typically enumerate dataset names here; supplements experiment with community-standard datasets that may not appear in the experiment section. |
| **P2** | `introduction` | Task definition paragraphs may mention representative datasets. Signal is sparse but covers overview-level dataset references. |

### Excluded (3/6)

| Section Key | Reason |
|-------------|--------|
| `method` | Describes algorithms and model architecture — produces no dataset metadata. Dataset names appearing in method are typically instrumental references (e.g., "we use X dataset for pre-training"); the actual metadata lives in experiment. |
| `conclusion` | Summarizes findings; contains no dataset descriptions. |
| `appendix` | Dataset-related lines in the appendix are already copied to `experiment` or `related_work` by `paper-sectioning`'s multi-section matching rules. Including appendix separately would produce duplicates and noise. |

## Context Budget Allocation

Total budget: **8000 characters**, weighted by dataset information density:

| Section Key | Budget | Share | Justification |
|-------------|--------|-------|---------------|
| `experiment` | 4000 chars | 50% | Highest density — experimental setup, dataset tables, and benchmark comparisons all reside here |
| `related_work` | 2400 chars | 30% | Benchmark comparisons often span multiple paragraphs; full context is needed to determine dataset attribution |
| `introduction` | 1600 chars | 20% | Typically 1–2 sentences mentioning dataset names; low budget suffices |

When a section exceeds its budget, truncation occurs at line boundaries (preserving complete paragraphs). Sentence-level truncation is not used.

## Runtime Behavior

### Backend Implementation Contract

1. Read all six section files from the `parsed/sections/` directory produced by `paper-sectioning`.
2. Select only `experiment`, `related_work`, and `introduction`.
3. Truncate each section to its budget, then concatenate into `{{section_context}}` for injection into the `runtime-instructions.md` template.
4. `{{metadata_json}}` is built from Paper metadata independently of section selection.

### Excluded Sections

`method`, `conclusion`, and `appendix` are not injected. Dataset mentions in these sections are either noise or already covered by experiment/related_work.

## Design Rationale

Excluding low-signal sections buys deeper context for each retained section. This is more effective than splitting the budget evenly across all six: a dataset name appearing outside of experiment but absent from experiment is extremely rare and typically indicates the paper did not actually use that dataset — a false positive worth suppressing.
