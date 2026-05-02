---
name: paper-sectioning
description: Splits parsed paper Markdown into six canonical section files using LLM-classified semantic line ranges with deterministic coverage fill. Use when the user asks to split papers into sections, classify paper sections, fix section classification, update section keys, or maintain the six-file paper section split.
---

# Paper Sectioning

## Goal

Split `parsed/refined.md` into six canonical Markdown files using LLM-classified semantic line ranges. The backend validates ranges, copies accepted lines, and fills coverage gaps deterministically.

## Boundary

This skill plans semantic line ranges. It does not rewrite, summarize, or improve paper content. The backend copies accepted lines into canonical section files, writes empty files for missing sections, and provides deterministic fallback. The backend does not infer related-work semantics from keywords or citations — the LLM owns that judgment.

## Output Files

The backend always writes these files under `parsed/sections/`:

| File | Content |
|---|---|
| `01_introduction.md` | Title, authors, abstract, problem, motivation, contributions |
| `02_related_work.md` | Prior-work discussion (secondary semantic view; copy, not move) |
| `03_method.md` | Method, model, algorithm, architecture, theory, proofs |
| `04_experiment.md` | Experiments, results, ablations, analysis, implementation |
| `05_conclusion.md` | Conclusion, limitations, future work |
| `06_appendix.md` | Complete appendix/supplementary content in original order |

Together the six files cover the entire paper except References/Bibliography and parser metadata. Every non-reference line must appear in at least one range. Figures, tables, captions, and callouts move with their surrounding semantic block.

## LLM Contract

The LLM returns JSON with `sections[]`. Each item is an audited 1-based inclusive line range with `section_key`, `start_line`, `end_line`, `confidence`, and `rationale`. Use `confidence < 0.65` only for ranges the backend should reject.

Key rules:
- Classify by semantic role, not heading text.
- A line range may appear in multiple sections when it has multiple semantic roles (see `references/runtime-instructions.md` for multi-section matching rules).
- Omit a section key when there is no evidence; never invent content.
- Exclude References, Bibliography, parser metadata, page headers/footers.

Complete JSON schema and classification rules are in `references/runtime-instructions.md`.

## Backend Touchpoints

- Runtime: `backend/core/services/papers/split/runtime.py`
- Skill runtime helper: `backend/core/services/papers/skill_runtime.py`
- Deterministic fallback: `backend/core/services/papers/split/heuristics.py`
- Pipeline integration: `backend/core/services/papers/repository.py`
- Runtime sectioning instructions: `skills/paper-sectioning/references/runtime-instructions.md`
- Tests: `backend/tests/test_paper_refine_runtime.py`, `backend/tests/test_papers_api.py`

## Progressive Disclosure Map

Load only the file needed for the task:

- `references/runtime-instructions.md` — LLM prompt template, classification rules, multi-section matching rules, and JSON schema for section ranges.

## Validation

Run focused tests after changes:

```powershell
python -m pytest backend\tests\test_paper_refine_runtime.py backend\tests\test_papers_api.py -q
```
