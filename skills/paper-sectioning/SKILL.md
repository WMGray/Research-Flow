---
name: paper-sectioning
description: Maintain Research-Flow's Paper semantic sectioning skill. Use when changing canonical section names, line-range section plans, appendix handling, reference exclusion, section split validation, or Paper LLM runtime instructions for `paper_sectioning.default`.
---

# Paper Sectioning

## Core Rule

Produce audited line ranges from `parsed/refined.md`; do not summarize, rewrite, or invent paper content. Backend code owns copying Markdown lines into canonical section files.

## Canonical Sections

Use these section keys:

- `related_work`: background, motivation, Introduction, problem setting, and Related Work.
- `method`: main approach, model, algorithm, architecture, system, and theory.
- `experiment`: datasets, metrics, baselines, implementation, experiments, evaluation, results, and analysis.
- `appendix`: supplementary material, extra experiments, proofs, implementation details, and appendix figures/tables.
- `conclusion`: conclusion, limitations, discussion, and future work.

## Workflow

1. Read the heading outline and local snippets built from the complete `parsed/refined.md`.
2. Return JSON-only ranges with `section_key`, `start_line`, `end_line`, `confidence`, and `rationale`.
3. Merge Introduction and Related Work into `related_work` when both exist.
4. Trust numbering hierarchy over Markdown heading level when MinerU gives parent and child headings the same level.
5. Exclude References, Bibliography, Acknowledgments, author affiliations, parser metadata, and boilerplate.
6. Preserve Appendix content under `appendix`, including appendix content that appears after References.
7. Include nearby image lines, blockquoted captions, and caution callouts inside the selected range.
8. Use confidence below `0.65` for uncertain ranges so the backend rejects them.

## Runtime Reference

The backend runtime instruction for `paper_sectioning.default` is `references/runtime-instructions.md`. Keep the reference JSON schema aligned with `backend/core/services/papers/split/runtime.py`.

## Validation

Run focused checks after changes:

```powershell
python -m pytest tests\test_paper_refine_runtime.py -q
```
